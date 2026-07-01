from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from providers.xiaomi import compatibility

HERE = Path(__file__).resolve().parents[2]
DEFAULT_COUNTRY = "auto"
DEFAULT_COUNTRY_CANDIDATES = (
    "de",
    "ru",
    "cn",
    "i2",
    "in",
    "sg",
    "us",
    "tw",
)
EU_COUNTRY_ALIASES = {
    "at", "be", "bg", "hr", "cy", "cz", "czech", "czechia", "dk", "ee",
    "eu", "europe", "fi", "fr", "gr", "hu", "ie", "it", "lv", "lt", "lu",
    "mt", "nl", "pl", "pt", "ro", "sk", "si", "es", "se", "uk", "gb",
}
COUNTRY_ALIASES = {
    **{name: "de" for name in EU_COUNTRY_ALIASES},
    "china": "cn",
    "mainland": "cn",
    "mainland_china": "cn",
    "india": "i2",
    "russia": "ru",
    "singapore": "sg",
    "taiwan": "tw",
    "usa": "us",
    "america": "us",
}


def normalize_country_code(value: str) -> str:
    token = str(value or "").strip().lower().replace("-", "_")
    return COUNTRY_ALIASES.get(token, token)


def parse_country_candidates(value: str | None) -> list[str]:
    if value is None:
        return list(DEFAULT_COUNTRY_CANDIDATES)

    text = str(value).strip()
    if not text:
        return list(DEFAULT_COUNTRY_CANDIDATES)
    if text.lower() in {"auto", "detect", "all"}:
        return list(DEFAULT_COUNTRY_CANDIDATES)

    parts: list[str] = []
    for chunk in text.replace(";", ",").split(","):
        for token in chunk.split():
            token = normalize_country_code(token)
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
            except Exception:
                continue
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


def request_json_any(api, paths: list[str], country: str, payload: dict) -> tuple[str, dict]:
    errors = []
    for path in paths:
        try:
            return path, request_json(api, path, country, payload)
        except Exception as exc:
            errors.append(f"{path}: {type(exc).__name__}: {exc}")
    raise RuntimeError("; ".join(errors))


def request_json_any_for_country_candidates(api, paths: list[str], args, payload: dict, country_candidates: list[str] | None = None) -> tuple[str, dict]:
    candidates = list(country_candidates or getattr(args, "country_candidates", []) or parse_country_candidates(getattr(args, "country", "")))
    errors: list[str] = []
    for country in candidates:
        try:
            path, response = request_json_any(api, paths, country, payload)
            args.country = country
            args.country_candidates = candidates
            return path, response
        except Exception as exc:
            errors.append(f"{country}: {type(exc).__name__}: {exc}")
    raise RuntimeError("; ".join(errors))


def local_write_path(value: str | Path, label: str) -> Path:
    path = Path(value).expanduser()
    path = (path if path.is_absolute() else HERE / path).resolve()
    try:
        path.relative_to(HERE)
    except ValueError as error:
        raise RuntimeError(f"{label} must stay inside {HERE}: {path}") from error
    return path


def first_present(raw: dict, names: tuple[str, ...], default=""):
    for name in names:
        value = raw.get(name)
        if value not in (None, ""):
            return value
    return default


def normalize_device(raw: dict, source: str = "", region: str = "") -> dict:
    did = str(first_present(raw, ("did", "deviceID", "device_id", "id"), ""))
    model = first_present(raw, ("model", "product_model", "modelName"), "")
    device = {
        "name": first_present(raw, ("name", "desc", "device_name", "nickname", "model"), ""),
        "did": did,
        "model": model,
        "ip": first_present(raw, ("localip", "localIp", "ip", "ip_address"), ""),
        "mac": first_present(raw, ("mac", "bssid"), ""),
        "online": raw.get("isOnline", raw.get("online", raw.get("is_online"))),
        "permit_level": raw.get("permitLevel", raw.get("permit_level")),
        "source": source,
        "region": region,
    }
    device.update(compatibility.classify_model(model))
    return device


def walk_devices(value, source: str, region: str = "") -> list[dict]:
    """Collect device-like dicts from Xiaomi cloud responses with varying layouts."""
    found: list[dict] = []
    if isinstance(value, dict):
        if any(key in value for key in ("did", "deviceID", "device_id")):
            item = normalize_device(value, source, region)
            if item["did"]:
                found.append(item)
        for child in value.values():
            found.extend(walk_devices(child, source, region))
    elif isinstance(value, list):
        for child in value:
            found.extend(walk_devices(child, source, region))
    return found


def merge_device_fields(existing: dict, item: dict) -> dict:
    for key, value in item.items():
        if key == "source":
            if value and value not in str(existing.get("source", "")):
                existing["source"] = (str(existing.get("source", "")) + "," + str(value)).strip(",")
        elif key in {"family", "display_model", "voice_install_method", "voice_pack_format"}:
            if value not in (None, "") and existing.get(key) in (None, "", "unknown"):
                existing[key] = value
        elif key == "supported":
            if value is True or existing.get(key) in (None, ""):
                existing[key] = value
        elif key == "capabilities":
            if value:
                merged = list(dict.fromkeys(list(existing.get(key) or []) + list(value)))
                existing[key] = merged
        elif value not in (None, "") and not existing.get(key):
            existing[key] = value
    return existing


def attach_home_context(item: dict, home: dict, room: dict | None = None) -> dict:
    item = dict(item)
    item.setdefault("region", home.get("region") or "")
    item.setdefault("home_id", home.get("id") or "")
    item.setdefault("home_name", home.get("name") or "")
    item.setdefault("home_source", home.get("source") or "")
    item.setdefault("home_shareflag", home.get("shareflag"))
    item.setdefault("home_permit_level", home.get("permit_level"))
    item.setdefault("home_uid", home.get("uid"))
    if room:
        item.setdefault("room_id", room.get("id") or "")
        item.setdefault("room_name", room.get("name") or "")
    return item


def add_device_to_container(container: dict, item: dict) -> None:
    did = str(item.get("did") or "")
    if not did:
        return
    devices = container.setdefault("devices", [])
    for existing in devices:
        if str(existing.get("did") or "") == did:
            merge_device_fields(existing, item)
            return
    devices.append(item)


def build_empty_homes_map() -> dict:
    return {
        "updated_at": "",
        "active_did": "",
        "regions": [],
        "errors": [],
    }


def get_or_add_region(homes_map: dict, country: str) -> dict:
    country = str(country or "")
    for region in homes_map.setdefault("regions", []):
        if str(region.get("country") or "") == country:
            region.setdefault("homes", [])
            region.setdefault("unassigned_devices", [])
            return region
    region = {"country": country, "homes": [], "unassigned_devices": []}
    homes_map.setdefault("regions", []).append(region)
    return region


def iter_region_nodes(homes_map: dict) -> list[dict]:
    regions = [
        region
        for region in homes_map.get("regions", [])
        if isinstance(region, dict) and ("homes" in region or "unassigned_devices" in region)
    ]
    if regions:
        return regions

    legacy_regions: dict[str, dict] = {}
    for home in homes_map.get("homes", []):
        country = str(home.get("region") or "")
        region = legacy_regions.setdefault(country, {"country": country, "homes": [], "unassigned_devices": []})
        region["homes"].append(home)
    for device in homes_map.get("unassigned_devices", []):
        country = str(device.get("region") or "")
        region = legacy_regions.setdefault(country, {"country": country, "homes": [], "unassigned_devices": []})
        region["unassigned_devices"].append(device)
    return list(legacy_regions.values())


def get_or_add_home(region_node: dict, raw_home: dict, source: str) -> dict:
    home_id = str(raw_home.get("id") or "")
    country = str(region_node.get("country") or "")
    for home in region_node.setdefault("homes", []):
        if str(home.get("id") or "") == home_id and home.get("source") == source:
            return home

    home = {
        "id": home_id,
        "name": raw_home.get("name") or "",
        "uid": raw_home.get("uid"),
        "source": source,
        "region": country,
        "shareflag": raw_home.get("shareflag"),
        "permit_level": raw_home.get("permit_level", raw_home.get("permitLevel")),
        "status": raw_home.get("status"),
        "devices": [],
        "rooms": [],
    }
    region_node.setdefault("homes", []).append(home)
    return home


def get_or_add_room(home: dict, raw_room: dict) -> dict:
    room_id = str(raw_room.get("id") or "")
    for room in home["rooms"]:
        if str(room.get("id") or "") == room_id:
            return room
    room = {
        "id": room_id,
        "name": raw_room.get("name") or "",
        "parentid": str(raw_room.get("parentid") or ""),
        "shareflag": raw_room.get("shareflag"),
        "region": home.get("region") or "",
        "devices": [],
    }
    home["rooms"].append(room)
    return room


def add_home_ref_device(container: dict, did: str, source: str, region: str = "") -> None:
    add_device_to_container(container, {
        "name": "",
        "did": str(did),
        "model": "",
        "ip": "",
        "mac": "",
        "online": None,
        "source": source,
        "region": region,
        **compatibility.classify_model(""),
    })


def add_homes_from_response(homes_map: dict, response: dict, source: str, region: str = "") -> None:
    result = response.get("result") if isinstance(response, dict) else None
    if not isinstance(result, dict):
        return

    region_node = get_or_add_region(homes_map, region)
    for home_list_name in ("homelist", "home_list", "share_home_list"):
        homes = result.get(home_list_name) or []
        if not isinstance(homes, list):
            continue
        for raw_home in homes:
            if not isinstance(raw_home, dict):
                continue
            home = get_or_add_home(region_node, raw_home, home_list_name)
            for did in raw_home.get("dids") or []:
                add_home_ref_device(home, str(did), source, region)
            for raw_room in raw_home.get("roomlist") or []:
                if not isinstance(raw_room, dict):
                    continue
                room = get_or_add_room(home, raw_room)
                for did in raw_room.get("dids") or []:
                    add_home_ref_device(room, str(did), source, region)


def iter_home_device_refs(homes_map: dict) -> list[tuple[dict, dict | None, dict]]:
    refs: list[tuple[dict, dict | None, dict]] = []
    for region in iter_region_nodes(homes_map):
        for home in region.get("homes", []):
            home.setdefault("region", region.get("country") or "")
            for device in home.get("devices", []):
                device.setdefault("region", home.get("region") or "")
                refs.append((home, None, device))
            for room in home.get("rooms", []):
                room.setdefault("region", home.get("region") or "")
                for device in room.get("devices", []):
                    device.setdefault("region", room.get("region") or home.get("region") or "")
                    refs.append((home, room, device))
    return refs


def enrich_homes_map_devices(api, args, homes_map: dict) -> None:
    for region in iter_region_nodes(homes_map):
        for home in region.get("homes", []):
            refs = [
                (room, device)
                for room in ([None] + list(home.get("rooms", [])))
                for device in (home.get("devices", []) if room is None else room.get("devices", []))
                if device.get("did")
            ]
            dids = sorted({str(device["did"]) for _, device in refs})
            home_id = str(home.get("id") or "")
            if not home_id or not dids:
                continue

            payload = {
                "home_id": home_id,
                "dids": dids,
                "getVirtualModel": False,
                "getHuamiDevices": 0,
                "limit": max(300, len(dids)),
            }
            try:
                country = str(home.get("region") or region.get("country") or getattr(args, "country", ""))
                path, response = request_json_any(
                    api,
                    ["/v2/home/device_list_page", "/home/device_list_page"],
                    country,
                    payload,
                )
            except Exception as exc:
                if getattr(args, "debug_devices", False):
                    print(f"DEBUG homes_map device details failed home_id={home_id}: {type(exc).__name__}: {exc}", file=sys.stderr)
                continue

            details_by_did = {
                str(item.get("did") or ""): item
                for item in walk_devices(response.get("result") or response, path, country)
                if item.get("did")
            }
            for room, device in refs:
                detail = details_by_did.get(str(device.get("did") or ""))
                if not detail:
                    continue
                merge_device_fields(device, detail)
                merge_device_fields(device, attach_home_context(detail, home, room))
            if getattr(args, "debug_devices", False):
                print(f"DEBUG {path}: homes_map home_id={home_id} requested_dids={len(dids)} details={len(details_by_did)}")


def add_unassigned_devices_to_homes_map(homes_map: dict, devices: list[dict], region: str = "") -> None:
    mapped_dids = {str(device.get("did") or "") for _, _, device in iter_home_device_refs(homes_map)}
    region_node = get_or_add_region(homes_map, region)
    for item in devices:
        did = str(item.get("did") or "")
        if did and did not in mapped_dids:
            item.setdefault("region", region)
            for existing in region_node.setdefault("unassigned_devices", []):
                if str(existing.get("did") or "") == did:
                    merge_device_fields(existing, item)
                    break
            else:
                region_node.setdefault("unassigned_devices", []).append(item)


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


def flatten_homes_map_devices(homes_map: dict) -> list[dict]:
    devices: list[dict] = []
    for home, room, device in iter_home_device_refs(homes_map):
        devices.append(attach_home_context(device, home, room))
    for region in iter_region_nodes(homes_map):
        for device in region.get("unassigned_devices", []):
            item = dict(device)
            item.setdefault("region", region.get("country") or "")
            devices.append(item)
    return unique_devices(devices)


def build_homes_map(api, args) -> dict:
    """
    Build a full home-centric inventory first, then let callers flatten/select.
    This handles owned homes, shared homes, room-only DID references, and plain
    device lists using the same structure.
    """
    attempts: list[tuple[str, dict]] = [
        ("/v2/home/device_list", {"getVirtualModel": False, "getHuamiDevices": 0}),
        ("/home/device_list", {"getVirtualModel": False, "getHuamiDevices": 0}),
        ("/v2/home/device_list", {}),
        ("/home/device_list", {}),
        ("/v2/home/device_list_page", {"getVirtualModel": False, "getHuamiDevices": 0, "limit": 300}),
        ("/home/device_list_page", {"getVirtualModel": False, "getHuamiDevices": 0, "limit": 300}),
        ("/v2/homeroom/gethome", {"fetch_share": True, "fetch_share_dev": True, "limit": 300}),
        ("/homeroom/gethome", {"fetch_share": True, "fetch_share_dev": True, "limit": 300}),
        ("/v2/homeroom/gethome", {"fetch_share": 1, "fetch_share_dev": 1, "limit": 300}),
        ("/homeroom/gethome", {"fetch_share": 1, "fetch_share_dev": 1, "limit": 300}),
    ]
    homes_map = build_empty_homes_map()
    direct_devices_by_region: dict[str, list[dict]] = {}
    country_candidates = resolve_country_candidates(
        api,
        args,
        probe_paths=[path for path, _ in attempts[:4]],
        payload={"getVirtualModel": False, "getHuamiDevices": 0},
    )
    for country in country_candidates:
        get_or_add_region(homes_map, country)

    for country in country_candidates:
        args.country = country
        region_devices = direct_devices_by_region.setdefault(country, [])
        for path, payload in attempts:
            try:
                response = request_json(api, path, country, payload)
                devices = walk_devices(response.get("result") or response, path, country)
                add_homes_from_response(homes_map, response, path, country)
                region_devices.extend(devices)
                if getattr(args, "debug_devices", False):
                    refs_count = len(iter_home_device_refs(homes_map))
                    homes_count = len(get_or_add_region(homes_map, country).get("homes", []))
                    print(f"DEBUG {path}: devices={len(devices)} homes={homes_count} home_dids={refs_count} country={country}")
            except Exception as exc:
                homes_map["errors"].append(f"{country} {path}: {type(exc).__name__}: {exc}")
                if getattr(args, "debug_devices", False):
                    print(f"DEBUG {country} {path} failed: {type(exc).__name__}: {exc}", file=sys.stderr)

    enrich_homes_map_devices(api, args, homes_map)
    for country, devices in direct_devices_by_region.items():
        add_unassigned_devices_to_homes_map(homes_map, devices, country)
    homes_map["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S %z")
    return homes_map


def save_homes_map(homes_map: dict, args, active_did: str = "") -> None:
    if not getattr(args, "save_devices", False):
        return

    path = local_write_path(args.homes_map_file, "homes map file")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dict(homes_map)
    data["active_did"] = active_did or data.get("active_did") or ""
    if not data.get("updated_at"):
        data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S %z")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved homes map to {path}")
