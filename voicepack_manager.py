from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
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
ROBOROCK_MAPPING = RESOURCES / "roborock_to_xiaomi_mapping.csv"
ROBOROCK_FULL_LIST = RESOURCES / "roborock_v1_s5_full_filelist.csv"
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
    process_env = os.environ.copy()
    process_env["CYGWIN"] = (
        process_env.get("CYGWIN", "") + " nodosfilewarning"
    ).strip()
    result = subprocess.run([str(item) for item in command], check=False, env=process_env)
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


def ffmpeg_to_legacy_wav(ffmpeg: str, source: Path, output: Path, sample_rate: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            source,
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-sample_fmt",
            "s16",
            output,
        ]
    )


def legacy_profile_files(profile: str) -> set[str]:
    if profile == "universal":
        return set()
    rows = list(csv.DictReader(ROBOROCK_FULL_LIST.open("r", encoding="utf-8-sig", newline="")))
    rows = [row for row in rows if row.get("kind", "voice") == "voice"]
    if profile == "gen1":
        return {row["filename"] for row in rows if row.get("present_in_old_72") == "True"}
    if profile in {"gen2", "s5"}:
        return {row["filename"] for row in rows}
    raise ValueError(f"Unknown legacy profile: {profile}")


def build_legacy_pkg(args) -> int:
    ensure_layout()
    from convert_old_voicepack import PASSWORD, ensure_donor, find_program

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required in PATH")

    ccrypt = find_program("ccrypt", args.ccrypt)
    ensure_donor(DONOR_DIR)

    output = Path(args.output).expanduser().resolve()
    build_dir = HERE / "work" / "legacy_pkg_wav"
    shutil.rmtree(build_dir, ignore_errors=True)
    build_dir.mkdir(parents=True)

    rows = list(csv.DictReader(ROBOROCK_MAPPING.open("r", encoding="utf-8-sig", newline="")))
    profile_files = legacy_profile_files(args.legacy_profile)
    if profile_files:
        rows = [row for row in rows if row["old_file"] in profile_files]

    built: list[str] = []
    missing: list[str] = []
    built_names: set[str] = set()
    skipped_medium = 0
    for row in rows:
        if row.get("confidence") == "medium" and not args.include_medium:
            skipped_medium += 1
            continue
        old_file = row["old_file"]
        new_file = row["new_file"]
        source = CUSTOM_AUDIO / old_file
        if not source.is_file():
            source = CUSTOM_AUDIO / new_file
        if not source.is_file():
            source = DONOR_DIR / new_file
        if not source.is_file():
            missing.append(f"{old_file} <- {new_file}")
            continue
        ffmpeg_to_legacy_wav(ffmpeg, source, build_dir / old_file, args.sample_rate)
        built.append(old_file)
        built_names.add(old_file)

    if profile_files:
        for source in sorted(CUSTOM_AUDIO.glob("*.wav")):
            if source.name in profile_files and source.name not in built_names:
                ffmpeg_to_legacy_wav(ffmpeg, source, build_dir / source.name, args.sample_rate)
                built.append(source.name)
                built_names.add(source.name)
        for old_file in sorted(profile_files - built_names):
            missing.append(old_file)

    if not built:
        raise RuntimeError("No legacy WAV files were built")
    if missing and args.strict_profile:
        raise RuntimeError("Legacy profile is incomplete: " + ", ".join(missing))

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="legacy-voicepack-", dir=str(HERE / "work")) as temp_name:
        temp_dir = Path(temp_name)
        tar_path = temp_dir / "voicepack.tar.gz"
        with tarfile.open(tar_path, "w:gz") as archive:
            for wav in sorted(build_dir.glob("*.wav")):
                archive.add(wav, arcname=wav.name)
        run([ccrypt, "-e", "-f", "-K", PASSWORD, tar_path])
        encrypted = tar_path.with_name(tar_path.name + ".cpt")
        if not encrypted.is_file():
            raise RuntimeError("ccrypt did not create encrypted package")
        shutil.copy2(encrypted, output)

    digest = hashlib.md5(output.read_bytes()).hexdigest()
    output.with_suffix(".md5").write_text(digest + "\n", encoding="ascii")
    print(
        f"Built legacy Roborock package: {output} "
        f"profile={args.legacy_profile} files={len(built)} "
        f"skipped_medium={skipped_medium} missing={len(missing)} md5={digest}"
    )
    if missing:
        print("Missing mapped files:")
        for item in missing:
            print("  " + item)
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
    run([
        sys.executable,
        HERE / "voicepack_cycle.py",
        "deploy",
        "--archive",
        archive,
        "--direct-scan",
        "--save-did",
    ])
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

    legacy = subparsers.add_parser("build-legacy-pkg")
    legacy.add_argument("--output", default=str(READY_DIR / "custom_roborock_v1_s5.pkg"))
    legacy.add_argument("--legacy-profile", choices=("universal", "gen1", "gen2", "s5"), default="universal")
    legacy.add_argument("--sample-rate", type=int, default=44100)
    legacy.add_argument("--ccrypt")
    legacy.add_argument("--strict-profile", action="store_true")
    legacy.add_argument("--no-include-medium", dest="include_medium", action="store_false")
    legacy.set_defaults(handler=build_legacy_pkg, include_medium=True)

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
