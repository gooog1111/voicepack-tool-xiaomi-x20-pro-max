from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import parse_qs

import requests
from providers.xiaomi import inventory as xiaomi_inventory
from providers.xiaomi import voice_modern_cloud


HERE = Path(__file__).resolve().parent
DEFAULT_ORIGINAL_URL = (
    "https://ksyru0-fusion.fds.api.xiaomi.com/"
    "xiaomi-d109gl/audio/1104/ru.zip"
)
DEFAULT_DID = ""
DEFAULT_COUNTRY = "ru"
DEFAULT_COUNTRY_CANDIDATES = (
    "ru",
    "cn",
    "de",
    "i2",
    "in",
    "sg",
    "us",
    "tw",
)


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def file_info(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    return hashlib.md5(data).hexdigest(), len(data)


def auth_marker_path(path: Path) -> Path:
    return path.with_name(path.stem + ".sha256")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def auth_marker_ok(path: Path) -> bool:
    marker = auth_marker_path(path)
    return path.exists() and marker.exists() and marker.read_text(encoding="utf-8").strip() == file_sha256(path)


def mark_auth_verified(path: str | Path) -> None:
    auth_path = Path(path).expanduser()
    if not auth_path.exists():
        return
    marker = auth_marker_path(auth_path)
    marker.write_text(file_sha256(auth_path) + "\n", encoding="utf-8")
    try:
        os.chmod(marker, 0o600)
    except OSError:
        pass


def local_write_path(value: str | Path, label: str) -> Path:
    path = Path(value).expanduser()
    path = (path if path.is_absolute() else HERE / path).resolve()
    try:
        path.relative_to(HERE)
    except ValueError as error:
        raise RuntimeError(f"{label} must stay inside {HERE}: {path}") from error
    return path


def parse_country_candidates(value: str | None) -> list[str]:
    if value is None:
        return [DEFAULT_COUNTRY]

    text = str(value).strip()
    if not text:
        return [DEFAULT_COUNTRY]
    if text.lower() in {"auto", "detect", "all"}:
        return [DEFAULT_COUNTRY, *[country for country in DEFAULT_COUNTRY_CANDIDATES if country != DEFAULT_COUNTRY]]

    parts: list[str] = []
    for chunk in text.replace(";", ",").split(","):
        for token in chunk.split():
            token = token.strip().lower()
            if token:
                parts.append(token)

    if not parts:
        return [DEFAULT_COUNTRY]

    return list(dict.fromkeys(parts))


def resolve_country_candidates(api, args, probe_paths: list[str] | None = None, payload: dict | None = None) -> list[str]:
    candidates = parse_country_candidates(getattr(args, "country", ""))
    if getattr(args, "skip_country_probe", False):
        args.country_candidates = candidates
        args.country = candidates[0]
        return candidates

    probe_paths = probe_paths or ["/v2/home/device_list", "/home/device_list", "/v2/homeroom/gethome", "/homeroom/gethome"]
    probe_payload = payload or {"getVirtualModel": False, "getHuamiDevices": 0}
    successful: list[str] = []
    for country in candidates:
        for path in probe_paths:
            try:
                request_json(api, path, country, probe_payload)
                successful.append(country)
                break
            except Exception as exc:
                if getattr(args, "debug_devices", False):
                    print(f"DEBUG country probe failed country={country} path={path}: {type(exc).__name__}: {exc}", file=sys.stderr)
    resolved = successful or candidates
    args.country_candidates = resolved
    args.country = resolved[0]
    return resolved


def request_json_for_country_candidates(api, path: str, args, payload: dict, country_candidates: list[str] | None = None) -> tuple[str, dict]:
    candidates = list(country_candidates or getattr(args, "country_candidates", []) or parse_country_candidates(getattr(args, "country", "")))
    errors: list[str] = []
    for country in candidates:
        try:
            response = request_json(api, path, country, payload)
            args.country = country
            args.country_candidates = candidates
            return country, response
        except Exception as exc:
            errors.append(f"{country}: {type(exc).__name__}: {exc}")
    raise RuntimeError("; ".join(errors))


def request_json(api, path: str, country: str, payload: dict) -> dict:
    raw = api.request_country(
        path,
        country,
        {"data": json.dumps(payload, separators=(",", ":"))},
    )
    data = json.loads(raw)
    if data.get("code") != 0:
        raise RuntimeError(f"{path}: code={data.get('code')} message={data.get('message')}")
    return data


class CapturedSessionApi:
    def __init__(self, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        parsed = parse_qs(data.get("body", ""), keep_blank_values=True)
        self.ssecurity = (parsed.get("ssecurity") or [None])[0]
        if not self.ssecurity:
            raise RuntimeError(f"{path} does not contain ssecurity")
        self.session = requests.Session()
        for key, value in (data.get("headers") or {}).items():
            if key.lower() not in {"content-length", "host"}:
                self.session.headers[key] = value
        self.session.headers["content-type"] = "application/x-www-form-urlencoded"
        self.session.headers["Accept-Encoding"] = "identity"

    def request_country(self, path: str, country: str, params: dict[str, str]) -> str:
        import gzip
        from micloud import miutils

        url = f"https://{country}.api.io.mi.com/app{path}"
        nonce = miutils.gen_nonce()
        signed_nonce = miutils.signed_nonce(self.ssecurity, nonce)
        post_data = miutils.generate_enc_params(
            url, "POST", signed_nonce, nonce, dict(params), self.ssecurity
        )
        response = self.session.post(url, data=post_data, timeout=30)
        response.raise_for_status()
        decrypted = miutils.decrypt_rc4(
            miutils.signed_nonce(self.ssecurity, post_data["_nonce"]), response.text
        )
        if decrypted.startswith(b"\x1f\x8b"):
            decrypted = gzip.decompress(decrypted)
        return decrypted.decode("utf-8", errors="replace")


def make_api(args):
    from micloud import MiCloud

    cloud_auth_file = Path(args.cloud_auth_file).expanduser()
    if cloud_auth_file.exists():
        data = json.loads(cloud_auth_file.read_text(encoding="utf-8"))
        required = ("user_id", "service_token", "ssecurity")
        if all(data.get(key) for key in required):
            cloud = MiCloud()
            cloud.user_id = str(data["user_id"])
            cloud.service_token = data["service_token"]
            cloud.ssecurity = data["ssecurity"]
            cloud.cuser_id = data.get("cuser_id")
            cloud.pass_token = data.get("pass_token")
            print(f"Cloud auth: browser session {cloud_auth_file}")
            if auth_marker_ok(cloud_auth_file):
                print(f"Cloud auth marker: verified {auth_marker_path(cloud_auth_file)}")
            else:
                print("Cloud auth marker: not verified yet; it will be updated after a successful Xiaomi Cloud call")
            return cloud
    session_file = Path(args.session_file).expanduser()
    if session_file.exists():
        print(f"Cloud auth: captured Mi Home session {session_file}")
        return CapturedSessionApi(session_file)
    username = args.username or env("XIAOMI_USER")
    password = args.password or env("XIAOMI_PASSWORD")
    if not username or not password:
        raise RuntimeError(
            "Provide --session-file or set XIAOMI_USER and XIAOMI_PASSWORD"
        )
    cloud = MiCloud(username, password)
    if not cloud.login():
        raise RuntimeError("Mi Cloud login failed; capture a Mi Home session instead")
    print("Cloud auth: password login OK")
    return cloud



MIIO_PORT = 54321
MIIO_HELLO = bytes.fromhex("21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff")


def guess_local_subnet() -> str:
    """Return a conservative /24 subnet based on the active local IPv4 address."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
        finally:
            sock.close()
        parts = local_ip.split(".")
        if len(parts) == 4:
            return ".".join(parts[:3]) + ".0/24"
    except OSError:
        pass
    return "192.168.1.0/24"


def parse_miio_hello_response(data: bytes, ip: str) -> dict | None:
    if len(data) < 16 or data[:2] != b"\x21\x31":
        return None
    did = int.from_bytes(data[8:12], "big", signed=False)
    stamp = int.from_bytes(data[12:16], "big", signed=False)
    token_part = data[16:32].hex() if len(data) >= 32 else ""
    if did <= 0:
        return None
    return {
        "name": "",
        "did": str(did),
        "model": "",
        "ip": ip,
        "mac": "",
        "online": True,
        "source": "local-miio-udp-54321",
        "stamp": stamp,
        "token_preview": token_part,
    }


def explain_miio_hello_response(data: bytes) -> str:
    if len(data) < 16:
        return f"short reply len={len(data)}"
    if data[:2] != b"\x21\x31":
        return f"not miIO hello magic={data[:2].hex()} len={len(data)}"
    did = int.from_bytes(data[8:12], "big", signed=False)
    if did <= 0:
        return "miIO hello with empty did"
    return "ok"


def probe_miio_host(host: str, timeout: float, raw: bool = False, retries: int = 1) -> dict | None:
    """Send a Xiaomi miIO hello packet to one host and parse the response."""
    item, _ = probe_miio_host_diagnostic(host, timeout, raw=raw, retries=retries)
    return item


def probe_miio_host_diagnostic(host: str, timeout: float, raw: bool = False, retries: int = 1) -> tuple[dict | None, str]:
    """Send a Xiaomi miIO hello packet to one host and return a diagnostic status."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        for _ in range(max(1, retries)):
            sock.sendto(MIIO_HELLO, (host, MIIO_PORT))
            try:
                data, address = sock.recvfrom(1024)
            except socket.timeout:
                continue
            if raw:
                print(f"RAW {address[0]}:{address[1]} len={len(data)} hex={data.hex()}")
            item = parse_miio_hello_response(data, address[0])
            if item:
                return item, "ok"
            return None, f"{address[0]}:{address[1]} {explain_miio_hello_response(data)}"
        return None, "timeout"
    except OSError as exc:
        return None, f"OSError: {exc}"
    finally:
        sock.close()


def build_scan_subnets(explicit_subnet: str | None = None, local_ip: str = "", include_common: bool = False) -> list[str]:
    explicit = []
    if explicit_subnet:
        for chunk in str(explicit_subnet).replace(";", ",").split(","):
            value = chunk.strip()
            if value:
                explicit.append(value)
    if explicit:
        return list(dict.fromkeys(explicit))

    candidates: list[str] = []
    if local_ip:
        if "/" in local_ip:
            candidates.append(local_ip)
        else:
            parts = local_ip.split(".")
            if len(parts) == 4:
                candidates.append(".".join(parts[:3]) + ".0/24")
    if not candidates:
        candidates.append(guess_local_subnet())

    if include_common:
        common_subnets = [
            "192.168.0.0/24",
            "192.168.1.0/24",
            "192.168.31.0/24",
            "10.0.0.0/24",
            "10.0.1.0/24",
            "172.16.0.0/24",
            "172.16.1.0/24",
        ]
        for subnet in common_subnets:
            if subnet not in candidates:
                candidates.append(subnet)
    return list(dict.fromkeys(candidates))


def local_miio_scan(args, known_hosts: list[str] | None = None) -> list[dict]:
    timeout = float(args.scan_timeout)
    retries = max(1, int(getattr(args, "scan_retries", 1)))
    devices: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add_device(item: dict | None) -> None:
        if not item:
            return
        key = (item.get("did", ""), item.get("ip", ""))
        if key not in seen:
            seen.add(key)
            devices.append(item)

    scan_host = getattr(args, "scan_host", "") or ""
    if scan_host:
        print(f"Подождите, отправляю miIO hello на {scan_host}:{MIIO_PORT}, timeout {timeout}s, попыток {retries}...")
        item, status = probe_miio_host_diagnostic(scan_host, timeout, raw=getattr(args, "raw_scan", False), retries=retries)
        add_device(item)
        if item:
            print("Найден miIO: " + json.dumps({"ip": item.get("ip"), "did": item.get("did"), "stamp": item.get("stamp")}, ensure_ascii=False))
        else:
            print(f"miIO не ответил на {scan_host}:{MIIO_PORT}: {status}")
        return devices

    subnets = build_scan_subnets(
        getattr(args, "scan_subnet", ""),
        getattr(args, "scan_host", "") or getattr(args, "device_ip", ""),
        include_common=getattr(args, "scan_common_subnets", False),
    )
    for subnet in subnets:
        try:
            network = ipaddress.ip_network(subnet, strict=False)
            broadcast = str(network.broadcast_address)
        except ValueError:
            broadcast = "255.255.255.255"

        if not getattr(args, "direct_scan", False):
            print(f"Локальный быстрый поиск miIO: broadcast UDP {MIIO_PORT}, subnet {subnet}, timeout {timeout}s, попыток {retries}")
            print(f"Broadcast probe: {broadcast}:{MIIO_PORT}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                for _ in range(retries):
                    sock.sendto(MIIO_HELLO, (broadcast, MIIO_PORT))
                    deadline = time.time() + timeout
                    while time.time() < deadline:
                        try:
                            data, address = sock.recvfrom(1024)
                        except socket.timeout:
                            break
                        if getattr(args, "raw_scan", False):
                            print(f"RAW {address[0]}:{address[1]} len={len(data)} hex={data.hex()}")
                        add_device(parse_miio_hello_response(data, address[0]))
            finally:
                sock.close()
            continue

        try:
            hosts = [str(host) for host in ipaddress.ip_network(subnet, strict=False).hosts()]
        except ValueError as exc:
            raise RuntimeError(f"Invalid --scan-subnet: {subnet}") from exc

        workers = max(1, int(getattr(args, "scan_workers", 96)))
        total = len(hosts)
        print(f"Подождите, идёт сканирование сети {subnet} по UDP {MIIO_PORT}...")
        print(f"На каждый найденный/доступный адрес отправляется miIO hello. Адресов: {total}, потоков: {workers}, timeout: {timeout}s, попыток: {retries}")

        done = 0
        next_report = 0
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(probe_miio_host, host, timeout, getattr(args, "raw_scan", False), retries): host for host in hosts}
            for future in as_completed(futures):
                done += 1
                item = None
                try:
                    item = future.result()
                except Exception:
                    item = None
                if item:
                    add_device(item)
                    print("Найден miIO: " + json.dumps({"ip": item.get("ip"), "did": item.get("did"), "stamp": item.get("stamp")}, ensure_ascii=False))
                if done >= next_report or done == total:
                    print(f"Сканирование: {done}/{total}")
                    next_report = done + 32

    for host in list(dict.fromkeys(known_hosts or [])):
        if not host:
            continue
        print(f"Точечная проверка miIO из cloud inventory: {host}:{MIIO_PORT}, timeout {timeout}s, попыток {retries}")
        item, status = probe_miio_host_diagnostic(host, timeout, raw=getattr(args, "raw_scan", False), retries=retries)
        add_device(item)
        if item:
            print("Найден miIO cloud-IP: " + json.dumps({"ip": item.get("ip"), "did": item.get("did"), "stamp": item.get("stamp")}, ensure_ascii=False))
        elif getattr(args, "debug_devices", False):
            print(f"DEBUG miIO cloud-IP no reply {host}:{MIIO_PORT}: {status}")

    if getattr(args, "mdns_scan", False):
        for item in local_miio_mdns_scan(args):
            add_device(item)

    return devices


def local_miio_mdns_scan(args) -> list[dict]:
    timeout = float(getattr(args, "mdns_timeout", 5.0))
    try:
        from miio.discovery import Discovery
    except ImportError as exc:
        if getattr(args, "debug_devices", False):
            print(f"mDNS miIO scan skipped: python-miio discovery unavailable: {exc}", file=sys.stderr)
        return []

    print(f"Локальный mDNS поиск miIO: _miio._udp.local, timeout {timeout}s")
    try:
        found = Discovery.discover_mdns(timeout=timeout)
    except Exception as exc:
        if getattr(args, "debug_devices", False):
            print(f"mDNS miIO scan failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return []

    devices: list[dict] = []
    for ip, device in found.items():
        model = str(
            getattr(device, "model", "")
            or getattr(device, "_model", "")
            or getattr(device, "MODEL", "")
            or ""
        )
        did = str(
            getattr(device, "device_id", "")
            or getattr(device, "_device_id", "")
            or getattr(device, "did", "")
            or ""
        )
        item = {
            "name": "",
            "did": did,
            "model": model,
            "ip": str(ip),
            "mac": "",
            "online": True,
            "source": "local-miio-mdns",
        }
        item.update(xiaomi_inventory.compatibility.classify_model(model))
        devices.append(item)
    return devices

def print_local_devices(devices: list[dict]) -> None:
    if not devices:
        print("No local miIO devices answered on UDP 54321")
        return
    print("Local miIO devices:")
    for item in devices:
        public = {k: item.get(k, "") for k in ("did", "ip", "model", "source", "stamp")}
        print("  " + json.dumps(public, ensure_ascii=False))



def load_env_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8-sig").splitlines()


def save_env_value(path: Path, name: str, value: str) -> None:
    lines = load_env_lines(path)
    updated = False
    output: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{name}=") or stripped.startswith(f"# {name}=") or stripped.startswith(f"#{name}="):
            output.append(f"{name}={value}")
            updated = True
        else:
            output.append(line)
    if not updated:
        output.append(f"{name}={value}")
    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def unique_devices(devices: list[dict]) -> list[dict]:
    result: list[dict] = []
    by_did: dict[str, dict] = {}
    for item in devices:
        did = item.get("did") or ""
        if not did:
            continue
        existing = by_did.get(did)
        if not existing:
            by_did[did] = item
            result.append(item)
            continue
        for key in ("name", "model", "ip", "mac", "online", "permit_level", "provider", "vendor", "family", "display_model", "voice_install_method", "voice_pack_format", "capabilities", "supported", "fds", "fds_error", "region", "home_id", "home_name", "home_source", "home_shareflag", "home_permit_level", "home_uid", "room_id", "room_name"):
            if not existing.get(key) and item.get(key):
                existing[key] = item[key]
        if item.get("source") and item["source"] not in existing.get("source", ""):
            existing["source"] = (existing.get("source", "") + "," + item["source"]).strip(",")
    return result


def list_cloud_devices(api, args) -> list[dict]:
    """
    Return a flat device list from the home-centric inventory.
    Xiaomi has several cloud layouts: owned homes, shared homes, and room-only
    DID references. The Xiaomi inventory provider normalizes those first.
    """
    homes_map = xiaomi_inventory.build_homes_map(api, args)
    if getattr(args, "resolve_fds", True):
        voice_modern_cloud.enrich_homes_map_fds(api, args, homes_map)
    xiaomi_inventory.save_homes_map(homes_map, args)
    devices = xiaomi_inventory.flatten_homes_map_devices(homes_map)
    if devices or homes_map.get("errors"):
        return devices
    raise RuntimeError("cannot get Xiaomi device list")


def print_devices(devices: list[dict]) -> None:
    if not devices:
        print("No Xiaomi devices found in this account/region")
        return
    print("Xiaomi devices:")
    for item in devices:
        print(
            "  "
            + json.dumps(
                {
                    "name": item.get("name", ""),
                    "did": item.get("did", ""),
                    "model": item.get("model", ""),
                    "ip": item.get("ip", ""),
                    "home": item.get("home_name", ""),
                    "room": item.get("room_name", ""),
                    "family": item.get("family", ""),
                    "voice_install_method": item.get("voice_install_method", ""),
                    "fds_host": (item.get("fds") or {}).get("upload_host", ""),
                    "supported": item.get("supported"),
                    "permit_level": item.get("permit_level"),
                    "online": item.get("online"),
                    "source": item.get("source", ""),
                },
                ensure_ascii=False,
            )
        )


def filtered_devices(devices: list[dict], args) -> list[dict]:
    candidates = devices
    if args.device_ip:
        candidates = [item for item in candidates if item.get("ip") == args.device_ip]
    if args.model:
        model_matches = [item for item in candidates if item.get("model") == args.model]
        if model_matches:
            candidates = model_matches
    if args.device_name:
        needle = args.device_name.lower()
        candidates = [item for item in candidates if needle in str(item.get("name", "")).lower()]
    return candidates


def map_local_to_cloud_devices(cloud_devices: list[dict], local_devices: list[dict]) -> list[dict]:
    """
    Prefer the Mi Cloud DID for devices that were also found locally.
    miIO UDP hello can expose a local DID-like value which is not always the
    identifier accepted by cloud MiOT actions.
    """
    cloud_by_ip = {
        str(item.get("ip")): item
        for item in cloud_devices
        if item.get("ip")
    }
    cloud_by_mac = {
        str(item.get("mac")).lower(): item
        for item in cloud_devices
        if item.get("mac")
    }
    mapped: list[dict] = []

    for local in local_devices:
        cloud = None
        if local.get("ip"):
            cloud = cloud_by_ip.get(str(local["ip"]))
        if not cloud and local.get("mac"):
            cloud = cloud_by_mac.get(str(local["mac"]).lower())

        if cloud:
            item = dict(cloud)
            for key in ("ip", "mac", "online"):
                if local.get(key) and not item.get(key):
                    item[key] = local[key]
            if local.get("did") and str(local["did"]) != str(item.get("did") or ""):
                item["local_did"] = str(local["did"])
            sources = [str(item.get("source") or ""), str(local.get("source") or "")]
            item["source"] = ",".join(part for part in sources if part)
            mapped.append(item)
            continue

        mapped.append(local)

    return unique_devices(mapped)


def device_label(item: dict) -> str:
    parts = [
        item.get("name") or "unnamed",
        item.get("model") or "unknown-model",
        "did=" + str(item.get("did") or ""),
    ]
    if item.get("local_did"):
        parts.append("local_did=" + str(item["local_did"]))
    if item.get("ip"):
        parts.append("ip=" + str(item["ip"]))
    if item.get("region"):
        parts.append("region=" + str(item["region"]))
    if item.get("online") not in (None, ""):
        parts.append("online=" + str(item["online"]))
    if item.get("source"):
        parts.append("source=" + str(item["source"]))
    return " | ".join(parts)


def save_selected_device(item: dict, args) -> None:
    if not args.save_did:
        return
    env_path = local_write_path(args.env_file, "env file")
    save_env_value(env_path, "XIAOMI_DID", str(item["did"]))
    if item.get("region"):
        save_env_value(env_path, "XIAOMI_COUNTRY", str(item["region"]))
    if item.get("ip"):
        save_env_value(env_path, "XIAOMI_DEVICE_IP", str(item["ip"]))
    print(f"Saved device selection to {args.env_file}")


def save_device_inventory(devices: list[dict], args, active_did: str = "") -> None:
    if not getattr(args, "save_devices", False):
        return

    path = local_write_path(args.devices_file, "devices file")
    path.parent.mkdir(parents=True, exist_ok=True)
    inventory = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "active_did": active_did or "",
        "devices": unique_devices(devices),
    }
    path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(inventory['devices'])} discovered device(s) to {path}")


def choose_device(candidates: list[dict], args, source: str, inventory_devices: list[dict] | None = None) -> dict:
    inventory_devices = inventory_devices or candidates
    if len(candidates) == 1:
        item = candidates[0]
        if item.get("region"):
            args.country = str(item["region"])
        print(f"Auto DID from {source}: " + json.dumps(item, ensure_ascii=False))
        save_selected_device(item, args)
        save_device_inventory(inventory_devices, args, str(item["did"]))
        return item

    if args.device_index:
        index = int(args.device_index)
        if 1 <= index <= len(candidates):
            item = candidates[index - 1]
            if item.get("region"):
                args.country = str(item["region"])
            print(f"Selected DID #{index} from {source}: " + json.dumps(item, ensure_ascii=False))
            save_selected_device(item, args)
            save_device_inventory(inventory_devices, args, str(item["did"]))
            return item
        raise RuntimeError(f"--device-index must be between 1 and {len(candidates)}")

    print(f"Found multiple Xiaomi devices from {source}:")
    for index, item in enumerate(candidates, start=1):
        print(f"  {index}. {device_label(item)}")

    if sys.stdin.isatty():
        while True:
            value = input("Выберите устройство по номеру: ").strip()
            try:
                index = int(value)
            except ValueError:
                print("Введите номер из списка.")
                continue
            if 1 <= index <= len(candidates):
                item = candidates[index - 1]
                if item.get("region"):
                    args.country = str(item["region"])
                save_selected_device(item, args)
                save_device_inventory(inventory_devices, args, str(item["did"]))
                return item
            print("Нет такого номера.")

    raise RuntimeError("More than one matching device was found. Use --device-index, --device-ip, --device-name or --did.")


def resolve_did(api, args) -> str:
    if args.did and args.did != "YOUR_DEVICE_DID":
        return args.did

    devices: list[dict] = []
    cloud_error = None
    try:
        devices = list_cloud_devices(api, args)
    except Exception as exc:
        cloud_error = exc
        if getattr(args, "debug_devices", False):
            print(f"Cloud device list failed: {type(exc).__name__}: {exc}", file=sys.stderr)

    candidates = filtered_devices(devices, args)

    cloud_candidate = candidates[0] if len(candidates) == 1 else None

    # Fallback: local miIO discovery. This does not require the local device token.
    # Broadcast is cheap but incomplete; cloud IPs are probed directly when known.
    known_hosts = [str(item.get("ip") or "") for item in devices if item.get("ip")]
    local_devices = local_miio_scan(args, known_hosts=known_hosts)
    save_device_inventory(devices + local_devices, args)
    mapped_local_devices = map_local_to_cloud_devices(devices, local_devices)
    local_candidates = filtered_devices(mapped_local_devices, args)

    if cloud_candidate:
        return choose_device([cloud_candidate], args, "cloud", devices + local_devices)["did"]

    if len(local_candidates) == 1:
        return choose_device(local_candidates, args, "local UDP scan", devices + local_devices)["did"]

    combined_candidates = filtered_devices(unique_devices(candidates + local_candidates), args)
    if combined_candidates:
        return choose_device(combined_candidates, args, "cloud/local discovery", devices + local_devices)["did"]

    if cloud_error:
        print(f"Cloud device list failed: {type(cloud_error).__name__}: {cloud_error}")
    print_devices(devices)
    print_local_devices(local_devices)
    if not candidates and not local_candidates:
        raise RuntimeError("DID was not set and no matching device was found. Use --device-ip, --scan-subnet, --direct-scan or --did.")
    raise RuntimeError("DID was not set and more than one matching device was found. Use --device-index, --device-ip, --device-name or --did.")

def safe_extract_voice(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        if not names or any(
            "/" in name or "\\" in name or name.startswith(".") for name in names
        ):
            raise RuntimeError("official archive must contain only flat voice files")
        for item in destination.iterdir():
            if item.is_file():
                item.unlink()
        zf.extractall(destination)


def download_original(args) -> Path:
    archive = local_write_path(args.original_archive, "original archive")
    base_dir = local_write_path(args.base_dir, "base directory")
    archive.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading official pack: {args.original_url}")
    with requests.get(args.original_url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with archive.open("wb") as output:
            for chunk in response.iter_content(256 * 1024):
                output.write(chunk)
    with zipfile.ZipFile(archive) as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"corrupt official ZIP entry: {bad}")
    safe_extract_voice(archive, base_dir)
    md5, size = file_info(archive)
    print(f"Official pack: {archive} md5={md5} size={size}")
    return archive


def ffmpeg_normalize(ffmpeg: str, source: Path, output: Path) -> None:
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-nostdin",
        "-i",
        str(source),
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "32k",
        "-write_xing",
        "0",
        "-id3v2_version",
        "0",
        str(output),
    ]
    subprocess.run(command, check=True)


def build_pack(args) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required in PATH")
    base_dir = Path(args.base_dir)
    source_dir = Path(args.source_dir)
    build_dir = local_write_path(args.build_dir, "build directory")
    archive = local_write_path(args.archive, "output archive")
    if not base_dir.is_dir() or not list(base_dir.glob("*.mp3")):
        raise RuntimeError("official base is missing; run download first")
    if not source_dir.is_dir():
        raise RuntimeError(f"custom source directory is missing: {source_dir}")

    shutil.rmtree(build_dir, ignore_errors=True)
    build_dir.mkdir(parents=True)
    base_files = {path.name: path for path in base_dir.glob("*.mp3")}
    numeric_names = {f"{int(path.stem)}.mp3": path.name for path in base_files.values()}
    replaced: list[str] = []

    for name, source in sorted(base_files.items()):
        ffmpeg_normalize(ffmpeg, source, build_dir / name)
    for source in sorted(source_dir.glob("*.mp3")):
        if not source.stem.isdigit():
            raise RuntimeError(f"custom filename must be numeric: {source.name}")
        target = base_files.get(source.name)
        target_name = target.name if target else numeric_names.get(source.name)
        if not target_name:
            raise RuntimeError(f"custom file is absent from official pack: {source.name}")
        ffmpeg_normalize(ffmpeg, source, build_dir / target_name)
        replaced.append(target_name)

    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(build_dir.glob("*.mp3")):
            zf.write(path, path.name)
    md5, size = file_info(archive)
    archive.with_suffix(".md5").write_text(md5 + "\n", encoding="ascii")
    archive.with_suffix(".size").write_text(str(size) + "\n", encoding="ascii")
    print(f"Built: {archive} md5={md5} size={size} replacements={len(replaced)}")
    print("Replaced: " + ", ".join(replaced))
    return archive


def verify_pack(args, archive: Path | None = None) -> dict:
    archive = archive or Path(args.archive)
    base_names = {path.name for path in Path(args.base_dir).glob("*.mp3")}
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        bad = zf.testzip()
    report = {
        "archive": str(archive),
        "md5": file_info(archive)[0],
        "size": file_info(archive)[1],
        "count": len(names),
        "missing": sorted(base_names - set(names)),
        "extra": sorted(set(names) - base_names),
        "nested": sorted(name for name in names if "/" in name or "\\" in name),
        "corrupt": bad,
    }
    report["ok"] = not any(
        report[key] for key in ("missing", "extra", "nested", "corrupt")
    )
    if not report["ok"]:
        raise RuntimeError("voice pack verification failed: " + json.dumps(report))
    print("Verified: " + json.dumps(report, ensure_ascii=False))
    return report


def generate_upload(api, args, archive: Path) -> tuple[str, str]:
    return voice_modern_cloud.generate_upload(api, args, archive, file_info, local_write_path)


def send_action(api, args, language: str, url: str, md5: str, size: int) -> dict:
    return voice_modern_cloud.send_action(api, args, language, url, md5, size)


VoiceStatusUnavailable = voice_modern_cloud.VoiceStatusUnavailable


def voice_status(api, args) -> dict:
    return voice_modern_cloud.voice_status(api, args)


def wait_voice(api, args, target: str, timeout: int = 180) -> dict:
    return voice_modern_cloud.wait_voice(api, args, target, timeout)


def install_pack(api, args, archive: Path, get_url: str) -> None:
    voice_modern_cloud.install_pack(api, args, archive, get_url, file_info)


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--country", default=env("XIAOMI_COUNTRY", DEFAULT_COUNTRY))
    parser.add_argument("--did", default=env("XIAOMI_DID", DEFAULT_DID))
    parser.add_argument("--device-ip", default=env("XIAOMI_DEVICE_IP", ""), help="Optional local IP used to select the device from the Mi Cloud device list")
    parser.add_argument("--device-name", default=env("XIAOMI_DEVICE_NAME", ""), help="Optional name substring used to select the device from the Mi Cloud device list")
    parser.add_argument("--device-index", type=int, default=0, help="Select a device by number when several devices match")
    parser.add_argument("--debug-devices", action="store_true", help="Print device API probing diagnostics")
    parser.add_argument("--scan-subnet", default=env("XIAOMI_SCAN_SUBNET", ""), help="Local subnet for miIO UDP discovery, for example 192.168.1.0/24")
    parser.add_argument("--scan-host", default=env("XIAOMI_SCAN_HOST", env("XIAOMI_DEVICE_IP", "")), help="Probe one exact local IP with miIO hello")
    parser.add_argument("--scan-timeout", type=float, default=float(env("XIAOMI_SCAN_TIMEOUT", "1.5")), help="UDP discovery timeout per host in seconds")
    parser.add_argument("--scan-retries", type=int, default=int(env("XIAOMI_SCAN_RETRIES", "3")), help="UDP discovery attempts per host")
    parser.add_argument("--scan-workers", type=int, default=int(env("XIAOMI_SCAN_WORKERS", "96")), help="Parallel workers for directed subnet scan")
    parser.add_argument("--direct-scan", action="store_true", help="Probe every address in --scan-subnet instead of broadcast only")
    parser.add_argument("--scan-common-subnets", action="store_true", help="Also try common private /24 subnets during local miIO scan")
    parser.add_argument("--mdns-scan", action="store_true", help="Also discover devices advertising _miio._udp.local via mDNS")
    parser.add_argument("--mdns-timeout", type=float, default=float(env("XIAOMI_MDNS_TIMEOUT", "5")), help="mDNS discovery timeout in seconds")
    parser.add_argument("--raw-scan", action="store_true", help="Print raw UDP replies during local scan")
    parser.add_argument("--save-did", action="store_true", help="Save the auto-detected DID to .env")
    parser.add_argument("--devices-file", default=env("XIAOMI_DEVICES_FILE", str(HERE / "state/devices.json")), help="Discovered device inventory file")
    parser.add_argument("--homes-map-file", default=env("XIAOMI_HOMES_MAP_FILE", str(HERE / "state/homes_map.json")), help="Discovered homes/devices map file")
    parser.add_argument("--no-save-devices", dest="save_devices", action="store_false", help="Do not save discovered devices to --devices-file")
    parser.add_argument("--no-resolve-fds", dest="resolve_fds", action="store_false", help="Do not resolve regional Xiaomi FDS endpoint for cloud voice devices")
    parser.set_defaults(save_devices=True)
    parser.set_defaults(resolve_fds=True)
    parser.add_argument("--env-file", default=str(HERE / ".env"))
    parser.add_argument("--model", default=env("XIAOMI_MODEL", ""))
    parser.add_argument(
        "--service-id", type=int, default=int(env("XIAOMI_VOICE_SIID", "15"))
    )
    parser.add_argument(
        "--install-action-id", type=int, default=int(env("XIAOMI_VOICE_INSTALL_AIID", "1"))
    )
    parser.add_argument(
        "--status-action-id", type=int, default=int(env("XIAOMI_VOICE_STATUS_AIID", "2"))
    )
    parser.add_argument(
        "--session-file",
        default=env("XIAOMI_SESSION_FILE", str(HERE / "state/captured_mihome_session.json")),
    )
    parser.add_argument(
        "--cloud-auth-file",
        default=env("XIAOMI_CLOUD_AUTH_FILE", str(HERE / "state/cloud_auth.json")),
    )
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--source-dir", default=str(HERE / "custom_voicepack/audio"))
    parser.add_argument("--base-dir", default=str(HERE / "resources/official_voice_ru"))
    parser.add_argument("--build-dir", default=str(HERE / "work/normalized"))
    parser.add_argument("--archive", default=str(HERE / "ready_voicepacks/custom_voicepack.zip"))
    parser.add_argument("--original-url", default=DEFAULT_ORIGINAL_URL)
    parser.add_argument("--original-archive", default=str(HERE / "cache/official_ru.zip"))
    parser.add_argument("--suffix", default="ru.zip")
    parser.add_argument("--state-file", default=str(HERE / "state/latest_upload.json"))
    parser.add_argument("--target-language", default="ru")
    parser.add_argument("--reset-language", default="it")
    parser.add_argument("--reset-url", default="/xiaomi-d109gl/audio/it.zip")
    parser.add_argument("--reset-md5", default="38c8083367c35d628a7ff3feac10deb4")


def main() -> int:
    parser = argparse.ArgumentParser(description="Xiaomi X20 Max custom voice full cycle")
    add_common(parser)
    parser.add_argument(
        "command",
        choices=("list-devices", "local-scan", "preflight", "download", "build", "verify", "deploy", "all"),
    )
    parser.add_argument("--refresh-original", action="store_true")
    args = parser.parse_args()

    if args.command == "local-scan":
        local_devices = local_miio_scan(args)
        print_local_devices(local_devices)
        save_device_inventory(local_devices, args)
        return 0

    if args.command == "list-devices":
        api = make_api(args)
        devices = []
        try:
            devices = list_cloud_devices(api, args)
            mark_auth_verified(args.cloud_auth_file)
            print_devices(devices)
        except Exception as exc:
            print(f"Cloud device list failed: {type(exc).__name__}: {exc}")
            print_devices([])
        known_hosts = [str(item.get("ip") or "") for item in devices if item.get("ip")]
        local_devices = local_miio_scan(args, known_hosts=known_hosts)
        print_local_devices(local_devices)
        save_device_inventory(devices + local_devices, args)
        return 0

    if args.command in {"preflight", "deploy", "all"}:
        api = make_api(args)
        # When a DID is discovered during install/preflight, persist it so the next run
        # does not need to rescan the LAN.
        if not args.did:
            args.save_did = True
        args.did = resolve_did(api, args)
    else:
        api = None

    if args.command == "preflight":
        status = voice_status(api, args)
        mark_auth_verified(args.cloud_auth_file)
        print(
            "Preflight OK: "
            + json.dumps(
                {
                    "model": args.model,
                    "did": args.did,
                    "service_id": args.service_id,
                    "install_action_id": args.install_action_id,
                    "status_action_id": args.status_action_id,
                    "voice_status": status,
                },
                ensure_ascii=False,
            )
        )
        return 0

    if args.command == "download":
        download_original(args)
        return 0
    if args.command == "build":
        build_pack(args)
        return 0
    if args.command == "verify":
        verify_pack(args)
        return 0

    if args.command == "all":
        base = Path(args.base_dir)
        if args.refresh_original or not base.is_dir() or not list(base.glob("*.mp3")):
            download_original(args)
        archive = build_pack(args)
        verify_pack(args, archive)
    else:
        archive = Path(args.archive)
        verify_pack(args, archive)

    if api is None:
        api = make_api(args)
        args.did = resolve_did(api, args)
    _, get_url = generate_upload(api, args, archive)
    install_pack(api, args, archive, get_url)
    mark_auth_verified(args.cloud_auth_file)
    print("Custom voice cycle completed successfully")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
