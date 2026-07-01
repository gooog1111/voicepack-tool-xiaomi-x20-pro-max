import unittest

import voicepack_cycle
from providers.xiaomi import voice_modern_cloud


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
