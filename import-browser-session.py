from __future__ import annotations

import argparse
import base64
import ctypes
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

import requests
from Crypto.Cipher import AES


HERE = Path(__file__).resolve().parent
LOGIN_URL = (
    "https://account.xiaomi.com/pass/serviceLogin?"
    "sid=xiaomiio&_json=true&callback=https%3A%2F%2Fsts.api.io.mi.com%2Fsts"
)
COOKIE_NAMES = {"serviceToken", "userId", "cUserId", "passToken"}


@dataclass(frozen=True)
class BrowserSource:
    name: str
    kind: str
    root: Path


class DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def dpapi_decrypt(data: bytes) -> bytes:
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


def chromium_key(root: Path) -> bytes:
    state = json.loads((root / "Local State").read_text(encoding="utf-8"))
    encrypted = base64.b64decode(state["os_crypt"]["encrypted_key"])
    if not encrypted.startswith(b"DPAPI"):
        raise RuntimeError("unsupported encryption key format")
    return dpapi_decrypt(encrypted[5:])


def decrypt_chromium_cookie(encrypted: bytes, key: bytes, host: str) -> str:
    if encrypted.startswith((b"v10", b"v11")):
        nonce, payload = encrypted[3:15], encrypted[15:]
        plain = AES.new(key, AES.MODE_GCM, nonce=nonce).decrypt_and_verify(
            payload[:-16], payload[-16:]
        )
    elif encrypted.startswith(b"v20"):
        raise RuntimeError("application-bound v20 cookie encryption is not transferable")
    else:
        plain = dpapi_decrypt(encrypted)
    digest = hashlib.sha256(host.encode()).digest()
    if plain.startswith(digest):
        plain = plain[len(digest) :]
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
        BrowserSource(
            "Tor Browser",
            "firefox",
            home / "Desktop/Tor Browser/Browser/TorBrowser/Data/Browser",
        ),
    ]
    return [source for source in candidates if source.root.is_dir()]


def default_sources_linux() -> list[BrowserSource]:
    home = Path.home()
    candidates = [
        BrowserSource("Chrome", "chromium", home / ".config/google-chrome/Default"),
        BrowserSource("Chromium", "chromium", home / ".config/chromium/Default"),
        BrowserSource("Firefox", "firefox", home / ".mozilla/firefox"),
        BrowserSource("Brave", "chromium", home / ".config/BraveSoftware/Brave-Browser/Default"),
        BrowserSource("Vivaldi", "chromium", home / ".config/vivaldi/Default"),
        BrowserSource("Opera", "chromium", home / ".config/opera"),
        BrowserSource("Yandex", "chromium", home / ".config/yandex-browser/Default"),
    ]
    return [source for source in candidates if source.root.is_dir()]


def default_sources_macos() -> list[BrowserSource]:
    home = Path.home()
    candidates = [
        BrowserSource("Chrome", "chromium", home / "Library/Application Support/Google/Chrome/Default"),
        BrowserSource("Chromium", "chromium", home / "Library/Application Support/Chromium/Default"),
        BrowserSource("Firefox", "firefox", home / "Library/Application Support/Firefox/Profiles"),
        BrowserSource("Brave", "chromium", home / "Library/Application Support/BraveSoftware/Brave-Browser/Default"),
        BrowserSource("Vivaldi", "chromium", home / "Library/Application Support/Vivaldi/Default"),
        BrowserSource("Opera", "chromium", home / "Library/Application Support/Opera/Default"),
    ]
    return [source for source in candidates if source.root.is_dir()]


def default_sources() -> list[BrowserSource]:
    if os.name == "nt":
        return default_sources_windows()
    elif sys.platform == "linux":
        return default_sources_linux()
    elif sys.platform == "darwin":
        return default_sources_macos()
    else:
        raise RuntimeError(f"unsupported platform: {sys.platform}")


def profiles(source: BrowserSource) -> list[Path]:
    if source.kind == "firefox":
        found = [path for path in source.root.iterdir() if (path / "cookies.sqlite").is_file()]
        if (source.root / "cookies.sqlite").is_file():
            found.insert(0, source.root)
        return found
    found = []
    if (source.root / "Network/Cookies").is_file():
        found.append(source.root)
    found.extend(
        path
        for path in source.root.iterdir()
        if path.is_dir()
        and (path.name == "Default" or path.name.startswith("Profile "))
        and (path / "Network/Cookies").is_file()
    )
    return found


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
        raise RuntimeError(
            "The browser is currently open. Please close it completely and try again."
        ) from exc
    except OSError as exc:
        temporary.cleanup()
        raise RuntimeError(
            "The browser is currently open. Please close it completely and try again."
        ) from exc


def chromium_cookies(profile: Path, key: bytes) -> list[dict]:
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
    for host, name, path, value, encrypted in rows:
        if name not in COOKIE_NAMES:
            continue
        try:
            value = value or decrypt_chromium_cookie(bytes(encrypted), key, host)
        except (UnicodeError, ValueError):
            continue
        if value:
            result.append({"domain": host, "name": name, "path": path or "/", "value": value})
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Import an existing Xiaomi browser session")
    parser.add_argument(
        "--browser",
        help="Installed browser name filter, for example Chrome or Firefox",
    )
    parser.add_argument("--profile", type=Path, help="Custom Chromium/Firefox profile path")
    parser.add_argument("--kind", choices=("chromium", "firefox"), default="chromium")
    parser.add_argument("--output", type=Path, default=HERE / "state/cloud_auth.json")
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
    for source in sources:
        print(f"Checking {source.name}...")
        try:
            key = chromium_key(source.root) if source.kind == "chromium" else None
            for profile in profiles(source):
                cookies = chromium_cookies(profile, key) if key else firefox_cookies(profile)
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
    raise RuntimeError("no browser profile yielded complete Mi Home credentials")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"IMPORT ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
