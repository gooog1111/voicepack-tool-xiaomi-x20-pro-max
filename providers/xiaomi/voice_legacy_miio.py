from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path


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


def install_sound(
    pkg: Path,
    ip: str = "",
    token: str = "",
    mirobo_path: str = "",
    discover_first: bool = False,
    status_first: bool = False,
    dry_run: bool = False,
) -> None:
    if not pkg.is_file():
        raise FileNotFoundError(f"Voice package not found: {pkg}")

    mirobo = find_mirobo(mirobo_path)
    if discover_first or not (ip and token):
        found_ip, found_token = discover(mirobo, dry_run=dry_run)
        ip = ip or found_ip
        token = token or found_token

    if not ip or not token:
        raise RuntimeError("Provide --ip and --token, or use --discover")

    base = [mirobo, f"--ip={ip}", f"--token={token}"]
    if status_first:
        status = run(base + ["status"], dry_run=dry_run)
        if status.returncode:
            raise RuntimeError((status.stdout or "") + (status.stderr or ""))
        print((status.stdout or "").strip())

    install = run(base + ["install-sound", pkg], dry_run=dry_run)
    if dry_run:
        print("Dry run complete; package was not installed.")
        return
    if install.returncode:
        raise RuntimeError((install.stdout or "") + (install.stderr or ""))
    print((install.stdout or "").strip())
    print("Legacy voice package installation started.")
