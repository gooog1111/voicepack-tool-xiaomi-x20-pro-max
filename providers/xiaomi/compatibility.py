from __future__ import annotations

from dataclasses import dataclass, field


PROVIDER_ID = "xiaomi"


@dataclass(frozen=True)
class XiaomiDeviceProfile:
    model: str
    family: str
    display_name: str
    voice_install_method: str
    voice_pack_format: str
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    aliases: tuple[str, ...] = field(default_factory=tuple)


MODERN_CLOUD_VOICE_CAPABILITIES = (
    "cloud_inventory",
    "miot_voice_status",
    "miot_voice_install",
    "cloud_voicepack_upload",
)

LEGACY_MIIO_VOICE_CAPABILITIES = (
    "miio_local_discovery",
    "miio_install_sound",
    "legacy_pkg_voicepack",
)


DEVICE_PROFILES: dict[str, XiaomiDeviceProfile] = {
    "xiaomi.vacuum.d109gl": XiaomiDeviceProfile(
        model="xiaomi.vacuum.d109gl",
        family="modern_cloud",
        display_name="Xiaomi Robot Vacuum X20 Max",
        voice_install_method="cloud_miot",
        voice_pack_format="xiaomi_cloud_zip",
        capabilities=MODERN_CLOUD_VOICE_CAPABILITIES,
        aliases=("d109gl", "x20 max"),
    ),
    "xiaomi.vacuum.d102gl": XiaomiDeviceProfile(
        model="xiaomi.vacuum.d102gl",
        family="modern_cloud",
        display_name="Xiaomi Robot Vacuum X20 Pro",
        voice_install_method="cloud_miot",
        voice_pack_format="xiaomi_cloud_zip",
        capabilities=MODERN_CLOUD_VOICE_CAPABILITIES,
        aliases=("d102gl", "x20 pro"),
    ),
    "rockrobo.vacuum.v1": XiaomiDeviceProfile(
        model="rockrobo.vacuum.v1",
        family="legacy_miio",
        display_name="Xiaomi Mi Robot Vacuum",
        voice_install_method="miio_install_sound",
        voice_pack_format="legacy_encrypted_pkg",
        capabilities=LEGACY_MIIO_VOICE_CAPABILITIES,
        aliases=("gen1",),
    ),
    "roborock.vacuum.s5": XiaomiDeviceProfile(
        model="roborock.vacuum.s5",
        family="legacy_miio",
        display_name="Roborock Sweep One S5/S50/S51/S55/S501",
        voice_install_method="miio_install_sound",
        voice_pack_format="legacy_encrypted_pkg",
        capabilities=LEGACY_MIIO_VOICE_CAPABILITIES,
        aliases=("s5", "s50", "s51", "s55", "s501"),
    ),
}


UNKNOWN_CAPABILITIES = (
    "cloud_inventory",
)


def profile_for_model(model: str) -> XiaomiDeviceProfile | None:
    return DEVICE_PROFILES.get((model or "").strip())


def classify_model(model: str) -> dict:
    profile = profile_for_model(model)
    if profile:
        return {
            "provider": PROVIDER_ID,
            "vendor": "xiaomi",
            "family": profile.family,
            "display_model": profile.display_name,
            "voice_install_method": profile.voice_install_method,
            "voice_pack_format": profile.voice_pack_format,
            "capabilities": list(profile.capabilities),
            "supported": True,
        }
    return {
        "provider": PROVIDER_ID,
        "vendor": "xiaomi",
        "family": "unknown",
        "display_model": model or "",
        "voice_install_method": "",
        "voice_pack_format": "",
        "capabilities": list(UNKNOWN_CAPABILITIES),
        "supported": False,
    }


def compatible_models(family: str = "") -> list[dict]:
    profiles = DEVICE_PROFILES.values()
    if family:
        profiles = [profile for profile in profiles if profile.family == family]
    return [
        {
            "provider": PROVIDER_ID,
            "model": profile.model,
            "family": profile.family,
            "display_name": profile.display_name,
            "voice_install_method": profile.voice_install_method,
            "voice_pack_format": profile.voice_pack_format,
            "capabilities": list(profile.capabilities),
            "aliases": list(profile.aliases),
        }
        for profile in profiles
    ]
