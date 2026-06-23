from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import requests
from micloud import MiCloud, miutils


HERE = Path(__file__).resolve().parent
DEFAULT_ORIGINAL_URL = (
    "https://ksyru0-fusion.fds.api.xiaomi.com/"
    "xiaomi-d109gl/audio/1104/ru.zip"
)
DEFAULT_DID = ""
DEFAULT_COUNTRY = "ru"


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def file_info(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    return hashlib.md5(data).hexdigest(), len(data)


def local_write_path(value: str | Path, label: str) -> Path:
    path = Path(value).expanduser()
    path = (path if path.is_absolute() else HERE / path).resolve()
    try:
        path.relative_to(HERE)
    except ValueError as error:
        raise RuntimeError(f"{label} must stay inside {HERE}: {path}") from error
    return path


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
        digest = hashlib.md5()
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
    out = response["result"]["out"]
    return {
        "target": out[0],
        "current": out[1],
        "status": out[2],
        "progress": out[3],
    }


def wait_voice(api, args, target: str, timeout: int = 120) -> dict:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        current = voice_status(api, args)
        if current != last:
            print("Voice status: " + json.dumps(current, ensure_ascii=False))
            last = current
        if current["current"] == target and current["status"] in (0, 4):
            return current
        if current["status"] in (3, 5):
            raise RuntimeError("voice install failed: " + json.dumps(current))
        time.sleep(2)
    raise TimeoutError(f"voice install did not finish in {timeout}s")


def install_pack(api, args, archive: Path, get_url: str) -> None:
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

    split = urlsplit(get_url)
    relative = split.path + ("?" + split.query if split.query else "") + "#/ru.zip"
    md5, size = file_info(archive)
    print("Installing custom pack with relative signed GET and #/ru.zip")
    send_action(api, args, args.target_language, relative, md5, size)
    wait_voice(api, args, args.target_language)


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--country", default=env("XIAOMI_COUNTRY", DEFAULT_COUNTRY))
    parser.add_argument("--did", default=env("XIAOMI_DID", DEFAULT_DID))
    parser.add_argument("--model", default=env("XIAOMI_MODEL", "xiaomi.vacuum.d109gl"))
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
        choices=("preflight", "download", "build", "verify", "deploy", "all"),
    )
    parser.add_argument("--refresh-original", action="store_true")
    args = parser.parse_args()

    if args.command in {"preflight", "deploy", "all"} and (
        not args.did or args.did == "YOUR_DEVICE_DID"
    ):
        raise RuntimeError(
            "Device DID is required. Set XIAOMI_DID in .env or pass --did."
        )

    if args.command == "preflight":
        api = make_api(args)
        status = voice_status(api, args)
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

    api = make_api(args)
    _, get_url = generate_upload(api, args, archive)
    install_pack(api, args, archive, get_url)
    print("Custom voice cycle completed successfully")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
