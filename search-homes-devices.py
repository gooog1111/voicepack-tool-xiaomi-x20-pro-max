from __future__ import annotations

import argparse
import json
import sys

import voicepack_cycle as cycle
from providers.xiaomi import compatibility
from providers.xiaomi import inventory as xiaomi_inventory
from providers.xiaomi import voice_modern_cloud


def add_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--country", default=cycle.env("XIAOMI_COUNTRY", cycle.DEFAULT_COUNTRY))
    parser.add_argument("--debug-devices", action="store_true", help="Print Xiaomi API probing diagnostics")
    parser.add_argument("--session-file", default=cycle.env("XIAOMI_SESSION_FILE", str(cycle.HERE / "state/captured_mihome_session.json")))
    parser.add_argument("--cloud-auth-file", default=cycle.env("XIAOMI_CLOUD_AUTH_FILE", str(cycle.HERE / "state/cloud_auth.json")))
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--devices-file", default=cycle.env("XIAOMI_DEVICES_FILE", str(cycle.HERE / "state/devices.json")))
    parser.add_argument("--homes-map-file", default=cycle.env("XIAOMI_HOMES_MAP_FILE", str(cycle.HERE / "state/homes_map.json")))
    parser.add_argument("--no-save-devices", dest="save_devices", action="store_false", help="Do not save homes/devices files")
    parser.set_defaults(save_devices=True)
    parser.add_argument("--did", default="", help=argparse.SUPPRESS)
    parser.add_argument("--model", default="", help=argparse.SUPPRESS)
    parser.add_argument("--device-name", default="", help=argparse.SUPPRESS)
    parser.add_argument("--device-ip", default="", help=argparse.SUPPRESS)
    parser.add_argument("--device-index", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--save-did", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--with-local-scan", action="store_true", help="Also scan local miIO UDP and merge matching devices into devices.json")
    parser.add_argument("--scan-subnet", default=cycle.env("XIAOMI_SCAN_SUBNET", ""), help="Local subnet for miIO UDP discovery, for example 192.168.1.0/24")
    parser.add_argument("--scan-host", default=cycle.env("XIAOMI_SCAN_HOST", cycle.env("XIAOMI_DEVICE_IP", "")), help="Probe one exact local IP with miIO hello")
    parser.add_argument("--scan-timeout", type=float, default=float(cycle.env("XIAOMI_SCAN_TIMEOUT", "1.5")))
    parser.add_argument("--scan-retries", type=int, default=int(cycle.env("XIAOMI_SCAN_RETRIES", "3")))
    parser.add_argument("--scan-workers", type=int, default=int(cycle.env("XIAOMI_SCAN_WORKERS", "96")))
    parser.add_argument("--direct-scan", action="store_true")
    parser.add_argument("--scan-common-subnets", action="store_true", help="Also try common private /24 subnets during local miIO scan")
    parser.add_argument("--mdns-scan", action="store_true", help="Also discover devices advertising _miio._udp.local via mDNS")
    parser.add_argument("--mdns-timeout", type=float, default=float(cycle.env("XIAOMI_MDNS_TIMEOUT", "5")))
    parser.add_argument("--raw-scan", action="store_true")
    parser.add_argument("--compatible-models", action="store_true", help="Print known Xiaomi voicepack-compatible models and exit")
    parser.add_argument("--family", default="", choices=("", "modern_cloud", "legacy_miio"), help="Filter --compatible-models by device family")
    parser.add_argument("--no-resolve-fds", dest="resolve_fds", action="store_false", help="Do not resolve regional Xiaomi FDS endpoint for cloud voice devices")
    parser.set_defaults(resolve_fds=True)


def print_homes_summary(homes_map: dict) -> None:
    print("Xiaomi homes map:")
    for region in xiaomi_inventory.iter_region_nodes(homes_map):
        print(
            "  "
            + json.dumps(
                {
                    "region": region.get("country", ""),
                    "homes": len(region.get("homes") or []),
                    "unassigned_devices": len(region.get("unassigned_devices") or []),
                },
                ensure_ascii=False,
            )
        )
        for home in region.get("homes", []):
            home_devices = len(home.get("devices") or [])
            rooms = home.get("rooms") or []
            print(
                "    "
                + json.dumps(
                    {
                        "id": home.get("id", ""),
                        "name": home.get("name", ""),
                        "source": home.get("source", ""),
                        "shareflag": home.get("shareflag"),
                        "permit_level": home.get("permit_level"),
                        "devices": home_devices,
                        "rooms": len(rooms),
                    },
                    ensure_ascii=False,
                )
            )
            for room in rooms:
                room_devices = room.get("devices") or []
                print(
                    "      "
                    + json.dumps(
                        {
                            "room_id": room.get("id", ""),
                            "room": room.get("name", ""),
                            "devices": [
                                {
                                    "name": item.get("name", ""),
                                    "did": item.get("did", ""),
                                    "model": item.get("model", ""),
                                    "ip": item.get("ip", ""),
                                    "fds_host": (item.get("fds") or {}).get("upload_host", ""),
                                    "online": item.get("online"),
                                }
                                for item in room_devices
                            ],
                        },
                        ensure_ascii=False,
                    )
                )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Xiaomi homes/devices map from saved authorization")
    add_args(parser)
    args = parser.parse_args()

    if args.compatible_models:
        print(json.dumps(compatibility.compatible_models(args.family), ensure_ascii=False, indent=2))
        return 0

    api = cycle.make_api(args)
    homes_map = xiaomi_inventory.build_homes_map(api, args)
    if args.resolve_fds:
        voice_modern_cloud.enrich_homes_map_fds(api, args, homes_map)
    devices = xiaomi_inventory.flatten_homes_map_devices(homes_map)
    local_devices = []

    if args.with_local_scan:
        known_hosts = [str(item.get("ip") or "") for item in devices if item.get("ip")]
        local_devices = cycle.local_miio_scan(args, known_hosts=known_hosts)
        devices = cycle.map_local_to_cloud_devices(devices, local_devices)

    xiaomi_inventory.save_homes_map(homes_map, args)
    cycle.save_device_inventory(devices + local_devices, args)
    cycle.mark_auth_verified(args.cloud_auth_file)
    print_homes_summary(homes_map)
    cycle.print_devices(devices)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
