#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_PKG = HERE / "ready_voicepacks/custom_roborock_v1_s5.pkg"


def local_script(name: str) -> Path | None:
    scripts_dir = Path(sys.executable).resolve().parent
    candidates = [
        scripts_dir / name,
        scripts_dir / f"{name}.exe",
        scripts_dir / f"{name}.cmd",
        scripts_dir / f"{name}.bat",
    ]
    return next((path for path in candidates if path.is_file()), None)


def find_mirobo(explicit: str = "") -> str:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if path.is_file():
            return str(path)
        raise FileNotFoundError(f"mirobo not found: {path}")

    local = local_script("mirobo")
    if local:
        return str(local)

    found = shutil.which("mirobo")
    if found:
        return found

    raise FileNotFoundError("mirobo not found. Install python-miio: pip install python-miio")


def run(command: list[str | Path], dry_run: bool = False) -> subprocess.CompletedProcess:
    printable = " ".join(str(item) for item in command)
    print("+ " + printable)
    if dry_run:
        return subprocess.CompletedProcess(command, 0, "", "")
    return subprocess.run([str(item) for item in command], text=True, capture_output=True, check=False)


def parse_discover(output: str) -> tuple[str, str]:
    pattern = re.compile(
        r"(?P<ip>\d{1,3}(?:\.\d{1,3}){3}).*?token:\s*b?['\"](?P<token>[0-9a-fA-F]+)['\"]",
        re.IGNORECASE,
    )
    match = pattern.search(output)
    if not match:
        raise RuntimeError("Could not parse IP/token from mirobo discover output")
    return match.group("ip"), match.group("token")


def discover(mirobo: str, dry_run: bool = False) -> tuple[str, str]:
    completed = run([mirobo, "discover", "--handshake", "true"], dry_run=dry_run)
    if dry_run:
        return "", ""
    output = (completed.stdout or "") + "\n" + (completed.stderr or "")
    if completed.returncode:
        raise RuntimeError(output.strip() or f"mirobo discover failed: {completed.returncode}")
    print(output.strip())
    return parse_discover(output)


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
        raise FileNotFoundError(f"Voice package not found: {pkg}")

    mirobo = find_mirobo(args.mirobo)
    ip = args.ip
    token = args.token
    if args.discover or not (ip and token):
        found_ip, found_token = discover(mirobo, dry_run=args.dry_run)
        ip = ip or found_ip
        token = token or found_token

    if not ip or not token:
        raise RuntimeError("Provide --ip and --token, or use --discover")

    base = [mirobo, f"--ip={ip}", f"--token={token}"]
    if args.status_first:
        status = run(base + ["status"], dry_run=args.dry_run)
        if status.returncode:
            raise RuntimeError((status.stdout or "") + (status.stderr or ""))
        print((status.stdout or "").strip())

    install = run(base + ["install-sound", pkg], dry_run=args.dry_run)
    if args.dry_run:
        print("Dry run complete; package was not installed.")
        return 0
    if install.returncode:
        raise RuntimeError((install.stdout or "") + (install.stderr or ""))
    print((install.stdout or "").strip())
    print("Legacy voice package installation started.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
