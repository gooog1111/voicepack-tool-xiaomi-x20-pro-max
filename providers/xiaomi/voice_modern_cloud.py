from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests

from providers.xiaomi.inventory import request_json
from providers.xiaomi.inventory import iter_region_nodes


class VoiceStatusUnavailable(RuntimeError):
    pass


def sanitized_fds_endpoint(country: str, put_url: str, obj_name: str = "") -> dict:
    split = urlsplit(put_url)
    path_parts = [part for part in split.path.split("/") if part]
    obj_parts = [part for part in obj_name.split("/") if part]
    return {
        "country": country,
        "scheme": split.scheme,
        "upload_host": split.netloc,
        "upload_base_url": f"{split.scheme}://{split.netloc}" if split.scheme and split.netloc else "",
        "path_prefix": path_parts[0] if path_parts else "",
        "obj_name_prefix": "/".join(obj_parts[:2]),
    }


def resolve_fds_endpoint(api, country: str, did: str, suffix: str = "fds_probe.zip") -> dict:
    """
    Resolve the regional Xiaomi FDS endpoint without sending an action to the robot.
    The signed URL itself is intentionally not returned because it contains
    temporary credentials in the query string.
    """
    response = request_json(
        api,
        "/v2/home/genpresignedurl_v3",
        country,
        {"did": did, "suffix": suffix},
    )
    entry = response["result"][suffix]
    return sanitized_fds_endpoint(country, entry.get("url", ""), entry.get("obj_name", ""))


def enrich_device_fds(api, country: str, device: dict, suffix: str = "fds_probe.zip") -> bool:
    if device.get("voice_install_method") != "cloud_miot" or not device.get("did"):
        return False
    device["fds"] = resolve_fds_endpoint(api, country, str(device["did"]), suffix=suffix)
    return True


def enrich_homes_map_fds(api, args, homes_map: dict, suffix: str = "fds_probe.zip") -> int:
    updated = 0
    for region in iter_region_nodes(homes_map):
        region_country = region.get("country") or args.country
        for home in region.get("homes", []):
            home_country = home.get("region") or region_country
            for device in home.get("devices", []):
                try:
                    country = device.get("region") or home_country
                    updated += int(enrich_device_fds(api, country, device, suffix=suffix))
                except Exception as exc:
                    device["fds_error"] = f"{type(exc).__name__}: {exc}"
                    if getattr(args, "debug_devices", False):
                        print(f"DEBUG FDS resolve failed did={device.get('did')}: {device['fds_error']}")
            for room in home.get("rooms", []):
                for device in room.get("devices", []):
                    try:
                        country = device.get("region") or room.get("region") or home_country
                        updated += int(enrich_device_fds(api, country, device, suffix=suffix))
                    except Exception as exc:
                        device["fds_error"] = f"{type(exc).__name__}: {exc}"
                        if getattr(args, "debug_devices", False):
                            print(f"DEBUG FDS resolve failed did={device.get('did')}: {device['fds_error']}")
        for device in region.get("unassigned_devices", []):
            try:
                country = device.get("region") or region_country
                updated += int(enrich_device_fds(api, country, device, suffix=suffix))
            except Exception as exc:
                device["fds_error"] = f"{type(exc).__name__}: {exc}"
                if getattr(args, "debug_devices", False):
                    print(f"DEBUG FDS resolve failed did={device.get('did')}: {device['fds_error']}")
    if getattr(args, "debug_devices", False):
        print(f"DEBUG FDS endpoints resolved: {updated}")
    return updated


def generate_upload(api, args, archive: Path, file_info, local_write_path) -> tuple[str, str]:
    suffix = args.suffix
    response = request_json(
        api,
        "/v2/home/genpresignedurl_v3",
        args.country,
        {"did": args.did, "suffix": suffix},
    )
    entry = response["result"][suffix]
    put_url = entry["url"]
    obj_name = entry["obj_name"]
    with archive.open("rb") as source:
        upload = requests.put(
            put_url,
            data=source,
            headers={"Content-Type": "application/octet-stream"},
            timeout=180,
        )
    upload.raise_for_status()
    print(f"Uploaded: obj_name={obj_name} status={upload.status_code}")
    get_response = request_json(
        api,
        "/v2/home/getfileurl_v3",
        args.country,
        {"obj_name": obj_name},
    )
    get_url = get_response["result"]["url"]
    md5, size = file_info(archive)
    with requests.get(get_url, stream=True, timeout=60) as response:
        response.raise_for_status()
        digest = __import__("hashlib").md5()
        downloaded = 0
        for chunk in response.iter_content(256 * 1024):
            digest.update(chunk)
            downloaded += len(chunk)
    if digest.hexdigest() != md5 or downloaded != size:
        raise RuntimeError("signed GET content does not match uploaded archive")
    state = {
        "obj_name": obj_name,
        "md5": md5,
        "size": size,
        "get_url": get_url,
    }
    state_path = local_write_path(args.state_file, "upload state")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Signed GET verified; state saved to {state_path}")
    return obj_name, get_url


def send_action(api, args, language: str, url: str, md5: str, size: int) -> dict:
    meta = json.dumps({"md5": md5, "size": size}, separators=(",", ":"))
    payload = {
        "params": {
            "did": args.did,
            "siid": args.service_id,
            "aiid": args.install_action_id,
            "in": [language, url, meta],
        }
    }
    response = request_json(api, "/miotspec/action", args.country, payload)
    if response.get("result", {}).get("code") != 0:
        raise RuntimeError("device rejected voice action: " + json.dumps(response))
    return response


def relative_voice_url(url: str, archive_name: str = "ru.zip") -> str:
    split = urlsplit(url)
    if split.scheme and split.netloc:
        value = split.path + ("?" + split.query if split.query else "")
    else:
        value = url
    archive_name = archive_name or "ru.zip"
    if "#" not in value:
        value += f"#/{archive_name}"
    return value


def voice_status(api, args) -> dict:
    payload = {
        "params": {
            "did": args.did,
            "siid": args.service_id,
            "aiid": args.status_action_id,
            "in": [],
        }
    }
    response = request_json(api, "/miotspec/action", args.country, payload)
    result = response.get("result") or {}
    out = result.get("out")
    if not isinstance(out, list) or len(out) < 4:
        raise VoiceStatusUnavailable(
            "voice status response has no usable result.out: "
            + json.dumps(response, ensure_ascii=False)
        )
    return {
        "target": out[0],
        "current": out[1],
        "status": out[2],
        "progress": out[3],
    }


def wait_voice(api, args, target: str, timeout: int = 180) -> dict:
    deadline = time.time() + timeout
    last = None
    status_errors = 0
    while time.time() < deadline:
        try:
            current = voice_status(api, args)
        except VoiceStatusUnavailable as error:
            status_errors += 1
            if status_errors <= 3:
                print(f"Voice status temporarily unavailable, retrying: {error}")
            if last and last.get("current") == target and last.get("status") in (0, 4):
                return last
            time.sleep(2)
            continue

        status_errors = 0
        if current != last:
            print("Voice status: " + json.dumps(current, ensure_ascii=False))
            last = current
        if current["current"] == target and current["status"] in (0, 4):
            return current
        if current["status"] in (3, 5):
            raise RuntimeError("voice install failed: " + json.dumps(current, ensure_ascii=False))
        time.sleep(2)
    if last:
        print("Last voice status before timeout: " + json.dumps(last, ensure_ascii=False))
    raise TimeoutError(f"voice install did not finish in {timeout}s")


def install_pack(api, args, archive: Path, get_url: str, file_info) -> None:
    md5, size = file_info(archive)
    install_remote_pack(api, args, get_url, md5, size)


def install_remote_pack(api, args, get_url: str, md5: str, size: int) -> None:
    current = voice_status(api, args)
    if current["current"] == args.target_language and args.reset_language:
        print(f"Resetting voice to {args.reset_language} before custom install")
        send_action(
            api,
            args,
            args.reset_language,
            args.reset_url,
            args.reset_md5,
            0,
        )
        wait_voice(api, args, args.reset_language)

    archive_name = getattr(args, "remote_archive_name", "ru.zip")
    relative = relative_voice_url(get_url, archive_name)
    print("Installing custom pack remotely with Xiaomi Cloud MiOT action")
    if getattr(args, "debug_devices", False):
        print("Voice install URL: " + relative)
    send_action(api, args, args.target_language, relative, md5, size)
    wait_voice(api, args, args.target_language)
