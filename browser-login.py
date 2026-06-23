from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Response, sync_playwright


START_URL = "https://account.xiaomi.com/"
LOGIN_JSON_URL = (
    "https://account.xiaomi.com/pass/serviceLogin?"
    "sid=xiaomiio&_json=true&callback=https%3A%2F%2Fsts.api.io.mi.com%2Fsts"
)
SESSION_COOKIE_NAMES = {"serviceToken", "userId", "cUserId", "passToken"}


def parse_response(text: str) -> dict:
    return json.loads(text.replace("&&&START&&&", ""))


def save_private(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def find_browser() -> str:
    candidates: list[Path] = []
    if os.name == "nt":
        for root_name in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
            root = os.environ.get(root_name)
            if root:
                candidates.extend(
                    [
                        Path(root) / "Microsoft/Edge/Application/msedge.exe",
                        Path(root) / "Google/Chrome/Application/chrome.exe",
                    ]
                )
    else:
        for name in ("microsoft-edge", "google-chrome", "chromium", "chromium-browser"):
            found = shutil.which(name)
            if found:
                candidates.append(Path(found))
        candidates.extend(
            [
                Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            ]
        )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError("Microsoft Edge, Google Chrome, or Chromium was not found")


def cookie_value(cookies: list[dict], name: str) -> str | None:
    for cookie in cookies:
        if cookie.get("name") == name:
            return cookie.get("value")
    return None


def has_xiaomi_session_cookie(cookies: list[dict]) -> bool:
    return any(
        cookie.get("name") in SESSION_COOKIE_NAMES
        and ("xiaomi" in cookie.get("domain", "") or "mi.com" in cookie.get("domain", ""))
        for cookie in cookies
    )


def find_value(value, key: str):
    if isinstance(value, dict):
        if value.get(key) is not None:
            return value[key]
        for child in value.values():
            found = find_value(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_value(child, key)
            if found is not None:
                return found
    return None


def merge_auth_payload(captured: dict[str, object], data) -> bool:
    ssecurity = find_value(data, "ssecurity")
    if not ssecurity:
        return False
    mapping = {
        "userId": "userId",
        "cUserId": "cUserId",
        "passToken": "passToken",
        "ssecurity": "ssecurity",
        "location": "location",
    }
    for source, target in mapping.items():
        found = find_value(data, source)
        if found is not None:
            captured[target] = found
    return True


def recover_session_payload(context, captured: dict[str, object]) -> None:
    try:
        response = context.request.get(LOGIN_JSON_URL, timeout=30_000)
        data = parse_response(response.text())
    except Exception:
        return
    if not isinstance(data, dict) or not merge_auth_payload(captured, data):
        return
    location = captured.get("location")
    if location:
        try:
            context.request.get(location, timeout=30_000)
        except Exception:
            pass
    print("Xiaomi session payload recovered", flush=True)


def save_browser_session(context, path: Path) -> bool:
    try:
        state = context.storage_state()
    except Exception:
        return False
    cookies = state.get("cookies") or []
    xiaomi_cookies = [
        cookie
        for cookie in cookies
        if "xiaomi" in cookie.get("domain", "") or "mi.com" in cookie.get("domain", "")
    ]
    if not xiaomi_cookies:
        return False
    save_private(
        path,
        {
            "created_at": int(time.time()),
            "auth_method": "temporary-browser-profile",
            "note": (
                "Raw browser storage state. This is useful for diagnostics/import only; "
                "voicepack deployment uses cloud_auth.json when ssecurity is available."
            ),
            "cookies": xiaomi_cookies,
            "origins": state.get("origins") or [],
        },
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Xiaomi browser login diagnostic for xiaomiio"
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parent / "state/cloud_auth.json"),
    )
    parser.add_argument(
        "--session-output",
        default=str(Path(__file__).resolve().parent / "state/browser_session.json"),
    )
    parser.add_argument("--start-url", default=START_URL)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    deadline = time.time() + args.timeout
    executable = find_browser()
    captured: dict[str, object] = {}
    captured_endpoints: set[str] = set()
    flow = {"sts_reached_at": None}
    last_recover_attempt = 0.0
    browser_session_saved = False

    def capture_response(response: Response) -> None:
        if urlsplit(response.url).hostname == "sts.api.io.mi.com":
            flow["sts_reached_at"] = flow["sts_reached_at"] or time.time()
        if "xiaomi.com" not in response.url and "io.mi.com" not in response.url:
            return
        try:
            text = response.text()
            if "ssecurity" not in text and "passToken" not in text:
                return
            data = parse_response(text)
        except Exception:
            return
        if not isinstance(data, dict):
            return
        if merge_auth_payload(captured, data):
            captured_endpoints.add(response.url.split("?", 1)[0])
            print("Xiaomi login response captured", flush=True)

    print(f"Opening temporary Xiaomi browser profile in: {executable}")
    print(f"Start URL: {args.start_url}")
    print("Log in on the official Xiaomi page in that browser window.")
    print("The page is opened once and will not be refreshed by the script.")

    with tempfile.TemporaryDirectory(prefix="xiaomi_browser_auth_") as profile:
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                profile,
                executable_path=executable,
                headless=False,
                args=["--no-first-run", "--no-default-browser-check"],
            )
            context.on("response", capture_response)
            failure: str | None = None
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(args.start_url, wait_until="domcontentloaded", timeout=60_000)

                while time.time() < deadline:
                    try:
                        cookies = context.cookies()
                        current_host = urlsplit(page.url).hostname
                    except PlaywrightError:
                        failure = (
                            "The browser was closed before usable Mi Home credentials "
                            "were collected"
                        )
                        break
                    if current_host == "sts.api.io.mi.com":
                        flow["sts_reached_at"] = flow["sts_reached_at"] or time.time()
                    service_token = cookie_value(cookies, "serviceToken")
                    if service_token:
                        flow["sts_reached_at"] = flow["sts_reached_at"] or time.time()

                    now = time.time()
                    if not captured.get("ssecurity") and now - last_recover_attempt >= 5:
                        last_recover_attempt = now
                        recover_session_payload(context, captured)
                        try:
                            cookies = context.cookies()
                            service_token = cookie_value(cookies, "serviceToken")
                        except PlaywrightError:
                            failure = "The browser was closed while collecting Xiaomi cookies"
                            break

                    if not browser_session_saved and has_xiaomi_session_cookie(cookies):
                        browser_session_saved = save_browser_session(
                            context, Path(args.session_output)
                        )
                        if browser_session_saved:
                            print(f"Temporary browser session saved: {args.session_output}")

                    user_id = captured.get("userId") or cookie_value(cookies, "userId")
                    ssecurity = captured.get("ssecurity")
                    if service_token and user_id and ssecurity:
                        result = {
                            "user_id": str(user_id),
                            "cuser_id": captured.get("cUserId")
                            or cookie_value(cookies, "cUserId"),
                            "pass_token": captured.get("passToken")
                            or cookie_value(cookies, "passToken"),
                            "ssecurity": ssecurity,
                            "service_token": service_token,
                            "created_at": int(time.time()),
                            "auth_method": "browser",
                        }
                        output = Path(args.output)
                        save_private(output, result)
                        print(f"Browser login OK: {output}")
                        return 0

                    sts_reached_at = flow["sts_reached_at"]
                    if sts_reached_at and time.time() - sts_reached_at >= 8:
                        if service_token and not ssecurity:
                            failure = (
                                "Xiaomi web login completed, but it returned serviceToken "
                                "without ssecurity. Social login (including Google) cannot "
                                "currently create the RC4 credentials required by Mi Home. "
                                "Use a Xiaomi account password via XIAOMI_USER and "
                                "XIAOMI_PASSWORD, or an existing captured Mi Home session."
                            )
                        else:
                            failure = (
                                "Xiaomi STS completed, but no usable Mi Home credentials "
                                "were returned"
                            )
                        break

                    remaining = max(0, int(deadline - time.time()))
                    print(
                        "Waiting for Xiaomi login: "
                        f"serviceToken={'yes' if service_token else 'no'}, "
                        f"ssecurity={'yes' if ssecurity else 'no'}, "
                        f"remaining={remaining}s",
                        flush=True,
                    )
                    try:
                        page.wait_for_timeout(2_000)
                    except PlaywrightError:
                        failure = (
                            "The browser was closed before usable Mi Home credentials "
                            "were collected"
                        )
                        break
            finally:
                try:
                    context.close()
                except PlaywrightError:
                    pass

            if failure:
                raise RuntimeError(failure)

    details = ", ".join(sorted(captured_endpoints)) or "none"
    raise TimeoutError(
        f"Xiaomi browser login timed out after {args.timeout}s; "
        f"captured endpoints: {details}"
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"AUTH ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
