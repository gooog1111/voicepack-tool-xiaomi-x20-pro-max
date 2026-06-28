#!/usr/bin/env python3
"""Convert an old Roborock WAV voice pack into a Xiaomi numeric MP3 ZIP."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path
from urllib.request import urlopen


PASSWORD = "r0ckrobo#23456"
HERE = Path(__file__).resolve().parent
MAX_RECURSION = 4
MAX_ZIP_ENTRIES = 5000
MAX_ZIP_UNCOMPRESSED = 512 * 1024 * 1024
CONTAINER_SUFFIXES = {".pkg", ".zip", ".rar"}
AUDIO_SUFFIXES = {".wav"}
SUPPORTED_INPUT_SUFFIXES = CONTAINER_SUFFIXES | AUDIO_SUFFIXES
OFFICIAL_DONOR_URL = (
    "https://ksyru0-fusion.fds.api.xiaomi.com/"
    "xiaomi-d109gl/audio/1104/ru.zip"
)


def find_program(name: str, explicit: str | None = None) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if path.is_file():
            return path
        raise FileNotFoundError(f"{name} not found: {path}")

    found = shutil.which(name)
    if found:
        return Path(found)

    if name == "ccrypt":
        bundled = (
            HERE
            / "resources"
            / "tools"
            / "windows"
            / "ccrypt.exe"
        )
        if bundled.is_file():
            return bundled

    raise FileNotFoundError(f"{name} not found in PATH")


def tool_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else HERE / path).resolve()


def run(command: list[str | Path]) -> None:
    process_env = os.environ.copy()
    process_env["CYGWIN"] = (
        process_env.get("CYGWIN", "") + " nodosfilewarning"
    ).strip()
    result = subprocess.run(
        [str(item) for item in command], check=False, env=process_env
    )
    if result.returncode:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: "
            + " ".join(str(item) for item in command)
        )


def extract_pkg(source: Path, destination: Path, work_dir: Path, ccrypt: Path) -> None:
    work_dir.mkdir(parents=True, exist_ok=True)
    encrypted = work_dir / "voicepack.pkg.cpt"
    decrypted = work_dir / "voicepack.pkg"
    shutil.copy2(source, encrypted)
    run([ccrypt, "-d", "-f", "-K", PASSWORD, encrypted])
    if not decrypted.is_file():
        raise RuntimeError("ccrypt did not create the decrypted package")

    with tarfile.open(decrypted, mode="r:*") as archive:
        members = [member for member in archive.getmembers() if member.isfile()]
        for member in members:
            if Path(member.name).suffix.lower() != ".wav":
                continue
            input_stream = archive.extractfile(member)
            if input_stream is None:
                continue
            target = destination / "audio" / Path(member.name).name
            target.parent.mkdir(parents=True, exist_ok=True)
            with input_stream, target.open("wb") as output_stream:
                shutil.copyfileobj(input_stream, output_stream)


def validate_zip(archive: zipfile.ZipFile, source: Path) -> list[zipfile.ZipInfo]:
    entries = [info for info in archive.infolist() if not info.is_dir()]
    if len(entries) > MAX_ZIP_ENTRIES:
        raise RuntimeError(f"Too many files in ZIP: {source}")
    if sum(info.file_size for info in entries) > MAX_ZIP_UNCOMPRESSED:
        raise RuntimeError(f"ZIP expands beyond 512 MiB: {source}")
    for info in entries:
        parts = Path(info.filename.replace("\\", "/")).parts
        if info.filename.startswith(("/", "\\")) or ".." in parts:
            raise RuntimeError(f"Unsafe ZIP entry: {info.filename}")
    return entries


def validate_archive_member(filename: str, source: Path) -> None:
    parts = Path(filename.replace("\\", "/")).parts
    if filename.startswith(("/", "\\")) or ".." in parts:
        raise RuntimeError(f"Unsafe archive entry in {source}: {filename}")


def validate_rar(archive, source: Path) -> list:
    entries = [info for info in archive.infolist() if not info.isdir()]
    if len(entries) > MAX_ZIP_ENTRIES:
        raise RuntimeError(f"Too many files in RAR: {source}")
    if sum(info.file_size for info in entries) > MAX_ZIP_UNCOMPRESSED:
        raise RuntimeError(f"RAR expands beyond 512 MiB: {source}")
    for info in entries:
        validate_archive_member(info.filename, source)
    return entries


def extract_rar_members(source: Path, destination: Path) -> list[Path]:
    try:
        import rarfile
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "RAR support requires the Python package 'rarfile'. "
            "Run requirements installation from run.ps1."
        ) from error

    seven_zip = find_archive_extractor()
    if seven_zip:
        rarfile.SEVENZIP_TOOL = str(seven_zip)

    extracted: list[Path] = []
    destination.mkdir(parents=True, exist_ok=True)
    try:
        with rarfile.RarFile(source) as archive:
            entries = validate_rar(archive, source)
            for index, info in enumerate(entries):
                suffix = Path(info.filename).suffix.lower()
                if suffix not in SUPPORTED_INPUT_SUFFIXES:
                    continue
                target = destination / f"{index:04d}" / Path(info.filename).name
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as input_stream, target.open("wb") as output:
                    shutil.copyfileobj(input_stream, output)
                extracted.append(target)
    except rarfile.RarCannotExec as error:
        raise RuntimeError(
            "RAR support needs an unpacker installed in PATH, for example "
            "7-Zip/7z, unrar, unar, or bsdtar."
        ) from error
    except rarfile.Error as error:
        raise RuntimeError(f"Cannot read RAR archive {source}: {error}") from error
    return extracted


def find_archive_extractor() -> Path | None:
    for name in ("7z", "7za", "unrar", "unar", "bsdtar"):
        found = shutil.which(name)
        if found:
            return Path(found)
    for path in (
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "7-Zip" / "7z.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "7-Zip" / "7z.exe",
    ):
        if path.is_file():
            return path
    return None


def copy_audio(source: Path, audio_dir: Path) -> None:
    audio_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, audio_dir / source.name)


def collect_source(
    source: Path,
    destination: Path,
    work_root: Path,
    ccrypt: Path | None,
    depth: int = 0,
) -> None:
    if depth > MAX_RECURSION:
        raise RuntimeError(f"Container nesting is deeper than {MAX_RECURSION}: {source}")

    audio_dir = destination / "audio"
    if source.is_dir():
        files = sorted(path for path in source.rglob("*") if path.is_file())
        for path in files:
            if path.suffix.lower() in CONTAINER_SUFFIXES:
                collect_source(path, destination, work_root, ccrypt, depth + 1)
        for path in files:
            if path.suffix.lower() == ".wav":
                copy_audio(path, audio_dir)
        return

    suffix = source.suffix.lower()
    if suffix == ".wav":
        copy_audio(source, audio_dir)
        return
    if suffix == ".pkg":
        if ccrypt is None:
            ccrypt = find_program("ccrypt")
        pkg_work = work_root / f"pkg-{depth}-{source.stem}-{len(list(work_root.iterdir()))}"
        extract_pkg(source, destination, pkg_work, ccrypt)
        return
    if suffix == ".rar":
        rar_work = work_root / f"rar-{depth}-{source.stem}-{len(list(work_root.iterdir()))}"
        extracted = extract_rar_members(source, rar_work)
        for path in extracted:
            if path.suffix.lower() in CONTAINER_SUFFIXES:
                collect_source(path, destination, work_root, ccrypt, depth + 1)
        for path in extracted:
            if path.suffix.lower() == ".wav":
                copy_audio(path, audio_dir)
        return
    if suffix != ".zip":
        raise ValueError(f"Unsupported source inside container: {source.name}")

    zip_work = work_root / f"zip-{depth}-{source.stem}-{len(list(work_root.iterdir()))}"
    zip_work.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as archive:
        entries = validate_zip(archive, source)
        extracted: list[Path] = []
        for index, info in enumerate(entries):
            suffix = Path(info.filename).suffix.lower()
            if suffix not in SUPPORTED_INPUT_SUFFIXES:
                continue
            target = zip_work / f"{index:04d}" / Path(info.filename).name
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as input_stream, target.open("wb") as output:
                shutil.copyfileobj(input_stream, output)
            extracted.append(target)

    # Nested containers are donors. WAV files placed next to them intentionally
    # override files with the same name from the nested package.
    for path in extracted:
        if path.suffix.lower() in CONTAINER_SUFFIXES:
            collect_source(path, destination, work_root, ccrypt, depth + 1)
    for path in extracted:
        if path.suffix.lower() == ".wav":
            copy_audio(path, audio_dir)


def read_mapping(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"old_file", "new_file", "confidence", "note"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Invalid mapping CSV: {path}")
    return rows


def create_zip(source_dir: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for mp3 in sorted(source_dir.glob("*.mp3"), key=lambda p: p.name):
            archive.write(mp3, mp3.name)


def write_report(report: Path, rows: list[dict[str, str]]) -> Path:
    fieldnames = ["old_file", "new_file", "confidence", "note", "status"]
    report.parent.mkdir(parents=True, exist_ok=True)
    try:
        with report.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return report
    except PermissionError:
        fallback = report.with_name(f"{report.stem}_{int(time.time())}{report.suffix}")
        with fallback.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(
            f"WARNING: report is locked, wrote fallback report: {fallback}",
            file=sys.stderr,
        )
        return fallback


def ensure_donor(base_dir: Path) -> None:
    existing = list(base_dir.glob("*.mp3"))
    if len(existing) == 101:
        return

    print(f"Downloading official donor: {OFFICIAL_DONOR_URL}")
    base_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="xiaomi-donor-") as temporary:
        archive_path = Path(temporary) / "ru.zip"
        with urlopen(OFFICIAL_DONOR_URL, timeout=60) as response:
            archive_path.write_bytes(response.read())
        with zipfile.ZipFile(archive_path) as archive:
            entries = [info for info in archive.infolist() if not info.is_dir()]
            if (
                len(entries) != 101
                or any(
                    "/" in info.filename
                    or "\\" in info.filename
                    or Path(info.filename).suffix.lower() != ".mp3"
                    for info in entries
                )
                or archive.testzip()
            ):
                raise RuntimeError("Unexpected official donor archive layout")
            for old_file in base_dir.glob("*.mp3"):
                old_file.unlink()
            for info in entries:
                with archive.open(info) as source, (base_dir / info.filename).open("wb") as output:
                    shutil.copyfileobj(source, output)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert an old Roborock .pkg, ZIP/RAR containing WAV files, or a "
            "WAV directory into a numeric Xiaomi MP3 voice pack."
        )
    )
    parser.add_argument("source", help="Old .pkg, .zip, .rar, .wav, or directory with WAV files")
    parser.add_argument(
        "--base-dir",
        default=HERE / "resources" / "official_voice_ru",
        type=Path,
        help="Unpacked official Xiaomi MP3 package used for missing events",
    )
    parser.add_argument(
        "--mapping",
        default=HERE / "resources" / "roborock_to_xiaomi_mapping.csv",
        type=Path,
    )
    parser.add_argument(
        "--output",
        default=HERE / "dist" / "converted_old_roborock.zip",
        type=Path,
    )
    parser.add_argument("--report", type=Path, help="Mapping report CSV path")
    parser.add_argument("--ffmpeg", help="Path to ffmpeg")
    parser.add_argument("--ccrypt", help="Path to ccrypt (needed for .pkg)")
    parser.add_argument("--bitrate-kbps", type=int, default=32)
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument(
        "--include-medium",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply medium-confidence mappings (default: enabled)",
    )
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    base_dir = tool_path(args.base_dir)
    mapping_path = tool_path(args.mapping)
    output = tool_path(args.output)
    report = (
        tool_path(args.report)
        if args.report
        else output.with_name(f"{output.stem}_report.csv")
    )

    if not source.exists():
        raise FileNotFoundError(f"Source not found: {source}")
    try:
        output.relative_to(HERE)
        report.relative_to(HERE)
    except ValueError as error:
        raise ValueError(
            f"Output and report must stay inside the tool directory: {HERE}"
        ) from error
    ensure_donor(base_dir)
    base_files = sorted(base_dir.glob("*.mp3"))
    if not base_files:
        raise FileNotFoundError(f"No donor MP3 files found in: {base_dir}")

    ffmpeg = find_program("ffmpeg", args.ffmpeg)
    rows = read_mapping(mapping_path)

    with tempfile.TemporaryDirectory(prefix="roborock-convert-") as temp_name:
        temp = Path(temp_name)
        audio_dir = temp / "audio"
        audio_dir.mkdir()
        work_root = temp / "containers"
        work_root.mkdir()
        ccrypt = None
        if args.ccrypt:
            ccrypt = find_program("ccrypt", args.ccrypt)
        collect_source(source, temp, work_root, ccrypt)

        wav_files = {
            path.name.lower(): path for path in audio_dir.glob("*.wav") if path.is_file()
        }
        if not wav_files:
            raise RuntimeError("No WAV files found in the source package")

        build_dir = temp / "build"
        build_dir.mkdir()
        for donor in base_files:
            shutil.copy2(donor, build_dir / donor.name)

        report_rows: list[dict[str, str]] = []
        replaced: set[str] = set()
        mapped_sources: set[str] = set()
        for row in rows:
            old_name = row["old_file"].strip()
            new_name = row["new_file"].strip()
            confidence = row["confidence"].strip().lower()
            source_wav = wav_files.get(old_name.lower())
            status = "missing_source"

            if source_wav and confidence == "medium" and not args.include_medium:
                status = "skipped_medium"
            elif source_wav:
                target = build_dir / new_name
                if not target.is_file():
                    status = "missing_target"
                else:
                    run(
                        [
                            ffmpeg,
                            "-hide_banner",
                            "-loglevel",
                            "error",
                            "-y",
                            "-nostdin",
                            "-i",
                            source_wav,
                            "-map_metadata",
                            "-1",
                            "-map_chapters",
                            "-1",
                            "-vn",
                            "-ac",
                            "1",
                            "-ar",
                            str(args.sample_rate),
                            "-c:a",
                            "libmp3lame",
                            "-b:a",
                            f"{args.bitrate_kbps}k",
                            "-write_xing",
                            "0",
                            "-id3v2_version",
                            "0",
                            target,
                        ]
                    )
                    status = "replaced"
                    replaced.add(new_name)
                    mapped_sources.add(old_name.lower())

            report_rows.append({**row, "status": status})

        known_names = {row["old_file"].strip().lower() for row in rows}
        full_list_path = HERE / "resources" / "roborock_v1_s5_full_filelist.csv"
        if full_list_path.is_file():
            with full_list_path.open("r", encoding="utf-8-sig", newline="") as handle:
                for full_row in csv.DictReader(handle):
                    old_name = full_row["filename"].strip()
                    if (
                        full_row.get("kind") == "voice"
                        and old_name.lower() not in known_names
                    ):
                        report_rows.append(
                            {
                                "old_file": old_name,
                                "new_file": "",
                                "confidence": "",
                                "note": "Нет надёжного аналога в новом пакете",
                                "status": (
                                    "unmapped"
                                    if old_name.lower() in wav_files
                                    else "not_in_source"
                                ),
                            }
                        )
                        known_names.add(old_name.lower())

        for name in sorted(wav_files):
            if name not in mapped_sources and name not in known_names:
                report_rows.append(
                    {
                        "old_file": wav_files[name].name,
                        "new_file": "",
                        "confidence": "",
                        "note": "Нет надёжного аналога в новом пакете",
                        "status": "unmapped",
                    }
                )

        create_zip(build_dir, output)
        report = write_report(report, report_rows)

    digest = hashlib.md5(output.read_bytes()).hexdigest()
    output.with_suffix(".md5").write_text(digest + "\n", encoding="ascii")
    output.with_suffix(".size").write_text(str(output.stat().st_size) + "\n", encoding="ascii")

    print(f"Created:  {output}")
    print(f"Report:   {report}")
    print(f"Replaced: {len(replaced)} of {len(base_files)} new voice events")
    print(f"Donor:    {len(base_files) - len(replaced)} unchanged voice events")
    print(f"MD5:      {digest}")
    print(f"Size:     {output.stat().st_size}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError, tarfile.TarError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
