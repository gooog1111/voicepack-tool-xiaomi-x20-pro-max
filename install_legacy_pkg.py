#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from providers.xiaomi import voice_legacy_miio


HERE = Path(__file__).resolve().parent
DEFAULT_PKG = HERE / "ready_voicepacks/custom_roborock_v1_s5.pkg"


def main() -> int:
    parser = argparse.ArgumentParser(description="Install a legacy Roborock/Xiaomi .pkg voice pack via python-miio")
    parser.add_argument("pkg", nargs="?", default=str(DEFAULT_PKG), help="Legacy encrypted .pkg voice pack")
    parser.add_argument("--ip", default="", help="Vacuum local IP")
    parser.add_argument("--token", default="", help="Vacuum local token")
    parser.add_argument("--discover", action="store_true", help="Run mirobo discover --handshake true before installing")
    parser.add_argument("--mirobo", default="", help="Path to mirobo executable")
    parser.add_argument("--status-first", action="store_true", help="Run mirobo status before install-sound")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    pkg = Path(args.pkg).expanduser().resolve()
    if not pkg.is_file():
        raise FileNotFoundError(
            f"Legacy voice package not found: {pkg}. "
            "Build it first with menu item 7 / build-legacy-pkg."
        )

    voice_legacy_miio.install_sound(
        pkg=pkg,
        ip=args.ip,
        token=args.token,
        mirobo_path=args.mirobo,
        discover_first=args.discover,
        status_first=args.status_first,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
