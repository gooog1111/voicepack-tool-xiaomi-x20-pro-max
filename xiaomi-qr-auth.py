#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import webbrowser
from pathlib import Path

import requests
import voicepack_cycle as cycle


HERE = Path(__file__).resolve().parent
ACCOUNT_LOGIN_URL = (
    "https://account.xiaomi.com/fe/service/login?sid=xiaomiio&_locale=en_GB&_snsNone=true"
)


def parse_xiaomi_json(text: str) -> dict:
    return json.loads(text.replace("&&&START&&&", "", 1))


class XiaomiQrLogin:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0"
        self.qr_image_url = ""
        self.login_url = ""
        self.long_polling_url = ""
        self.timeout_seconds = 120

    def prepare(self) -> None:
        params = {
            "_qrsize": "480",
            "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
            "callback": "https://sts.api.io.mi.com/sts",
            "_hasLogo": "false",
            "sid": "xiaomiio",
            "serviceParam": "",
            "_locale": "en_GB",
            "_dc": str(int(time.time() * 1000)),
        }
        response = self.session.get(
            "https://account.xiaomi.com/longPolling/loginUrl",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = parse_xiaomi_json(response.text)
        self.qr_image_url = str(data["qr"])
        self.login_url = str(data["loginUrl"])
        self.long_polling_url = str(data["lp"])
        self.timeout_seconds = int(data.get("timeout", 120))

    def save_qr_image(self) -> Path:
        response = self.session.get(self.qr_image_url, timeout=30)
        response.raise_for_status()
        fd, raw_path = tempfile.mkstemp(prefix="xiaomi-login-", suffix=".png")
        with os.fdopen(fd, "wb") as handle:
            handle.write(response.content)
        return Path(raw_path)

    def wait_for_scan(self) -> dict:
        started = time.time()
        while time.time() - started < self.timeout_seconds:
            remaining = max(0, int(self.timeout_seconds - (time.time() - started)))
            print(f"Ожидаю подтверждение QR в Xiaomi Home... осталось {remaining} сек.")
            try:
                response = self.session.get(self.long_polling_url, timeout=15)
            except requests.exceptions.Timeout:
                continue
            if response.status_code != 200:
                time.sleep(1)
                continue

            data = parse_xiaomi_json(response.text)
            location = data.get("location")
            if not location:
                time.sleep(1)
                continue

            token_response = self.session.get(location, timeout=30)
            token_response.raise_for_status()
            service_token = self.cookie_value("serviceToken")
            result = {
                "user_id": str(data.get("userId") or self.cookie_value("userId") or ""),
                "cuser_id": data.get("cUserId") or self.cookie_value("cUserId"),
                "pass_token": data.get("passToken") or self.cookie_value("passToken"),
                "ssecurity": data.get("ssecurity"),
                "service_token": service_token,
                "created_at": int(time.time()),
                "auth_method": "xiaomi-qr-login",
            }
            if all(result.get(key) for key in ("user_id", "ssecurity", "service_token")):
                return result
            raise RuntimeError("QR login succeeded, but Xiaomi did not return a complete session.")

        raise TimeoutError("QR login timed out. Scan the code and confirm login in Xiaomi Home.")

    def cookie_value(self, name: str) -> str | None:
        return next((cookie.value for cookie in self.session.cookies if cookie.name == name), None)


def open_file(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    elif sys.platform.startswith("linux"):
        subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        os.startfile(str(path))  # type: ignore[attr-defined]


def main() -> int:
    parser = argparse.ArgumentParser(description="Authorize Xiaomi Cloud with QR login")
    parser.add_argument("--output", type=Path, default=HERE / "state/cloud_auth.json")
    parser.add_argument("--no-open-browser", action="store_true", help="Do not open the Xiaomi login URL")
    parser.add_argument("--no-open-qr", action="store_true", help="Do not open the downloaded QR image")
    args = parser.parse_args()

    login = XiaomiQrLogin()
    print("Готовлю QR-авторизацию Xiaomi...")
    login.prepare()
    qr_path = login.save_qr_image()

    print(f"Login URL: {login.login_url or ACCOUNT_LOGIN_URL}")
    print(f"QR image: {qr_path}")
    if not args.no_open_browser:
        webbrowser.open(login.login_url or ACCOUNT_LOGIN_URL)
    if not args.no_open_qr:
        open_file(qr_path)

    result = login.wait_for_scan()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cycle.clear_auth_marker(args.output)
    try:
        os.chmod(args.output, 0o600)
    except OSError:
        pass
    print(f"Complete Xiaomi session imported by QR login: {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"QR AUTH ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
