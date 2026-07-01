import unittest
import importlib.util
import sys
from pathlib import Path

try:
    from Crypto.Cipher import AES
except ImportError:
    AES = None

import voicepack_cycle
from providers.xiaomi import voice_modern_cloud

import_browser_session = None
if AES is not None:
    IMPORT_BROWSER_SESSION_PATH = Path(__file__).resolve().parents[1] / "import-browser-session.py"
    spec = importlib.util.spec_from_file_location("import_browser_session", IMPORT_BROWSER_SESSION_PATH)
    import_browser_session = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["import_browser_session"] = import_browser_session
    spec.loader.exec_module(import_browser_session)


class CountryAndScanHelpersTest(unittest.TestCase):
    def test_parse_country_candidates_parses_csv_and_defaults(self) -> None:
        self.assertEqual(voicepack_cycle.parse_country_candidates("ru, us ,de"), ["ru", "us", "de"])
        self.assertEqual(voicepack_cycle.parse_country_candidates(""), list(voicepack_cycle.DEFAULT_COUNTRY_CANDIDATES))
        self.assertEqual(voicepack_cycle.parse_country_candidates("cz"), ["de"])
        self.assertEqual(voicepack_cycle.parse_country_candidates("eu,ru"), ["de", "ru"])

    def test_build_scan_subnets_prefers_local_range(self) -> None:
        subnets = voicepack_cycle.build_scan_subnets("", "192.168.31.55")
        self.assertIn("192.168.31.0/24", subnets)
        self.assertNotIn("192.168.0.0/24", subnets)
        self.assertNotIn("192.168.1.0/24", subnets)

    def test_build_scan_subnets_can_include_common_ranges(self) -> None:
        subnets = voicepack_cycle.build_scan_subnets("", "192.168.31.55", include_common=True)
        self.assertIn("192.168.0.0/24", subnets)
        self.assertIn("192.168.1.0/24", subnets)

    def test_relative_voice_url_keeps_relative_and_converts_absolute(self) -> None:
        self.assertEqual(
            voice_modern_cloud.relative_voice_url("https://host.example/a/b.zip?sig=1", "ru.zip"),
            "/a/b.zip?sig=1#/ru.zip",
        )
        self.assertEqual(
            voice_modern_cloud.relative_voice_url("/xiaomi-d109gl/audio/it.zip", ""),
            "/xiaomi-d109gl/audio/it.zip#/ru.zip",
        )

    def test_linux_chromium_fallback_cookie_decrypt(self) -> None:
        if AES is None or import_browser_session is None:
            self.skipTest("pycryptodome is not installed")
        plain = b"service-token"
        padding = 16 - len(plain) % 16
        key = import_browser_session.hashlib.pbkdf2_hmac("sha1", b"peanuts", b"saltysalt", 1, dklen=16)
        encrypted = b"v10" + AES.new(key, AES.MODE_CBC, iv=b" " * 16).encrypt(plain + bytes([padding]) * padding)
        self.assertEqual(import_browser_session.decrypt_linux_chromium_fallback(encrypted), plain)
