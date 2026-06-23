from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD_DIR = HERE / "old_voicepacks"
READY_DIR = HERE / "ready_voicepacks"
CUSTOM_DIR = HERE / "custom_voicepack"
CUSTOM_AUDIO = CUSTOM_DIR / "audio"
OFFICIAL_DIR = HERE / "official_voicepacks"
RESOURCES = HERE / "resources"
DONOR_DIR = RESOURCES / "official_voice_ru"
with (CUSTOM_DIR / "table_en.csv").open("r", encoding="utf-8-sig", newline="") as handle:
    EXPECTED_NAMES = {row["file"] for row in csv.DictReader(handle)}


def ensure_layout() -> None:
    for path in (
        OLD_DIR,
        READY_DIR,
        CUSTOM_AUDIO,
        OFFICIAL_DIR / "d109gl",
        OFFICIAL_DIR / "d102gl",
        HERE / "state",
        HERE / "work",
    ):
        path.mkdir(parents=True, exist_ok=True)


def safe_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return cleaned or "voicepack"


def run(command: list[str | Path]) -> None:
    result = subprocess.run([str(item) for item in command], check=False)
    if result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): "
            + " ".join(str(item) for item in command)
        )


def conversion_inputs() -> list[tuple[str, Path]]:
    entries: list[tuple[str, Path]] = []
    loose_wavs = []
    for path in sorted(OLD_DIR.iterdir(), key=lambda item: item.name.lower()):
        if path.is_dir():
            entries.append((path.name, path))
        elif path.suffix.lower() in {".pkg", ".zip"}:
            entries.append((path.stem, path))
        elif path.suffix.lower() == ".wav":
            loose_wavs.append(path)
    if loose_wavs:
        loose_dir = HERE / "work" / "loose_wav_input"
        shutil.rmtree(loose_dir, ignore_errors=True)
        loose_dir.mkdir(parents=True)
        for path in loose_wavs:
            shutil.copy2(path, loose_dir / path.name)
        entries.append(("loose_wav_files", loose_dir))
    return entries


def convert_all(args) -> int:
    ensure_layout()
    entries = conversion_inputs()
    if not entries:
        print(f"No .pkg, .zip, WAV files, or subdirectories found in {OLD_DIR}")
        return 0

    success = 0
    failures: list[str] = []
    for name, source in entries:
        output = READY_DIR / f"{safe_name(name)}.zip"
        print(f"\nConverting: {source.name} -> {output.name}")
        command = [
            sys.executable,
            HERE / "convert_old_voicepack.py",
            source,
            "--output",
            output,
        ]
        if args.high_confidence_only:
            command.append("--no-include-medium")
        try:
            run(command)
            success += 1
        except Exception as error:
            failures.append(f"{source.name}: {error}")
            print(f"FAILED: {error}", file=sys.stderr)

    print(f"\nConverted: {success}; failed: {len(failures)}")
    for failure in failures:
        print(f"  {failure}", file=sys.stderr)
    return 1 if failures else 0


def build_custom(_args) -> int:
    ensure_layout()
    from convert_old_voicepack import ensure_donor

    ensure_donor(DONOR_DIR)
    output = READY_DIR / "custom_voicepack.zip"
    run(
        [
            sys.executable,
            HERE / "voicepack_cycle.py",
            "build",
            "--source-dir",
            CUSTOM_AUDIO,
            "--base-dir",
            DONOR_DIR,
            "--build-dir",
            HERE / "work" / "custom_normalized",
            "--archive",
            output,
        ]
    )
    return 0


def verify_archive(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        corrupt = archive.testzip()
    report = {
        "file": path.name,
        "count": len(names),
        "missing": sorted(EXPECTED_NAMES - set(names)),
        "extra": sorted(set(names) - EXPECTED_NAMES),
        "nested": sorted(name for name in names if "/" in name or "\\" in name),
        "duplicates": len(names) != len(set(names)),
        "corrupt": corrupt,
    }
    report["ok"] = not any(
        (
            report["missing"],
            report["extra"],
            report["nested"],
            report["duplicates"],
            report["corrupt"],
        )
    )
    return report


def verify_all(_args) -> int:
    ensure_layout()
    archives = sorted(READY_DIR.glob("*.zip"), key=lambda path: path.name.lower())
    if not archives:
        print(f"No ZIP voice packs found in {READY_DIR}")
        return 0
    failures = 0
    for path in archives:
        try:
            report = verify_archive(path)
        except (OSError, zipfile.BadZipFile) as error:
            report = {"file": path.name, "ok": False, "error": str(error)}
        print(json.dumps(report, ensure_ascii=False))
        failures += not report["ok"]
    print(f"Checked: {len(archives)}; valid: {len(archives) - failures}; invalid: {failures}")
    return 1 if failures else 0


def choose_archive() -> Path:
    archives = sorted(READY_DIR.glob("*.zip"), key=lambda path: path.name.lower())
    if not archives:
        raise RuntimeError(f"No ZIP voice packs found in {READY_DIR}")
    print("\nReady voice packs:")
    for index, path in enumerate(archives, 1):
        print(f"{index}. {path.name} ({path.stat().st_size} bytes)")
    raw = input("Select voice pack number: ").strip()
    if not raw.isdigit() or not 1 <= int(raw) <= len(archives):
        raise RuntimeError("Invalid voice pack number")
    return archives[int(raw) - 1]


def install_selected(args) -> int:
    ensure_layout()
    archive = Path(args.archive).expanduser().resolve() if args.archive else choose_archive()
    try:
        archive.relative_to(READY_DIR)
    except ValueError as error:
        raise RuntimeError(f"Voice pack must be inside {READY_DIR}") from error
    report = verify_archive(archive)
    if not report["ok"]:
        raise RuntimeError("Selected voice pack is invalid: " + json.dumps(report))
    run([sys.executable, HERE / "voicepack_cycle.py", "deploy", "--archive", archive])
    return 0


def safe_extract_mp3(archive_path: Path, destination: Path) -> int:
    with zipfile.ZipFile(archive_path) as archive:
        entries = [info for info in archive.infolist() if not info.is_dir()]
        if any(
            "/" in info.filename
            or "\\" in info.filename
            or Path(info.filename).suffix.lower() != ".mp3"
            for info in entries
        ):
            raise RuntimeError(f"Unexpected layout in {archive_path}")
        shutil.rmtree(destination, ignore_errors=True)
        destination.mkdir(parents=True)
        for info in entries:
            with archive.open(info) as source, (destination / info.filename).open("wb") as output:
                shutil.copyfileobj(source, output)
    return len(entries)


def download_originals(args) -> int:
    import requests

    ensure_layout()
    manifest = json.loads(
        (RESOURCES / "official_voice_manifest.json").read_text(encoding="utf-8")
    )
    models = args.models or manifest["models"]
    languages = {
        entry["code"]: entry["path"] for entry in manifest["languages"]
    }
    if args.languages:
        unknown = sorted(set(args.languages) - set(languages))
        if unknown:
            raise RuntimeError("Unknown language codes: " + ", ".join(unknown))
        languages = {code: languages[code] for code in args.languages}

    results = []
    for model in models:
        if model not in manifest["models"]:
            raise RuntimeError(f"Unknown model: {model}")
        for code, relative in languages.items():
            language_dir = OFFICIAL_DIR / model / code
            archive_path = language_dir / f"{code}.zip"
            url = f"{manifest['base_url']}/xiaomi-{model}/{relative}"
            language_dir.mkdir(parents=True, exist_ok=True)
            print(f"Downloading {model}/{code}: {url}")
            try:
                with requests.get(url, stream=True, timeout=60) as response:
                    response.raise_for_status()
                    with archive_path.open("wb") as output:
                        for chunk in response.iter_content(256 * 1024):
                            if chunk:
                                output.write(chunk)
                count = safe_extract_mp3(archive_path, language_dir / "audio")
                digest = hashlib.md5(archive_path.read_bytes()).hexdigest()
                metadata = {
                    "model": model,
                    "language": code,
                    "url": url,
                    "md5": digest,
                    "size": archive_path.stat().st_size,
                    "files": count,
                    "status": "ok",
                }
            except Exception as error:
                archive_path.unlink(missing_ok=True)
                metadata = {
                    "model": model,
                    "language": code,
                    "url": url,
                    "status": "error",
                    "error": str(error),
                }
            (language_dir / "metadata.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            results.append(metadata)
            print(f"  {metadata['status']}")

    summary = OFFICIAL_DIR / "download_report.csv"
    fields = ["model", "language", "status", "files", "size", "md5", "url", "error"]
    with summary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    failed = sum(item["status"] != "ok" for item in results)
    print(f"Downloaded: {len(results) - failed}; failed: {failed}; report: {summary}")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Xiaomi voice pack folder workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert = subparsers.add_parser("convert-all")
    convert.add_argument("--high-confidence-only", action="store_true")
    convert.set_defaults(handler=convert_all)

    build = subparsers.add_parser("build-custom")
    build.set_defaults(handler=build_custom)

    verify = subparsers.add_parser("verify-all")
    verify.set_defaults(handler=verify_all)

    install = subparsers.add_parser("install")
    install.add_argument("--archive")
    install.set_defaults(handler=install_selected)

    download = subparsers.add_parser("download-originals")
    download.add_argument("--models", nargs="+", choices=("d109gl", "d102gl"))
    download.add_argument("--languages", nargs="+")
    download.set_defaults(handler=download_originals)

    args = parser.parse_args()
    ensure_layout()
    return args.handler(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
