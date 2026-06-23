# Xiaomi Voice Pack Tool

[![Stars](https://img.shields.io/github/stars/gooog1111/voicepack-tool-xiaomi-x20-pro-max?style=for-the-badge)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/stargazers)
[![Latest Release](https://img.shields.io/github/v/release/gooog1111/voicepack-tool-xiaomi-x20-pro-max?style=for-the-badge)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/gooog1111/voicepack-tool-xiaomi-x20-pro-max/total?style=for-the-badge)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/releases)
[![License](https://img.shields.io/github/license/gooog1111/voicepack-tool-xiaomi-x20-pro-max?style=for-the-badge)](LICENSE)

[![Visits](https://visitor-badge.laobi.icu/badge?page_id=gooog1111.voicepack-tool-xiaomi-x20-pro-max)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)

[Русская версия](README.ru.md)

Windows and Linux tool for Xiaomi robot vacuum voice packs. It converts old
Roborock packages, builds numeric Xiaomi voice packs, validates archives,
downloads official language packages, and installs a selected package.

Tested with:

- `xiaomi.vacuum.d109gl`
- `xiaomi.vacuum.d102gl`

## Features

- Interactive Windows and Linux menu.
- Temporary-browser Xiaomi authorization.
- Automatic session import from installed Chrome, Firefox, Edge, Yandex,
  Chromium, Brave, Vivaldi, Opera, Opera GX, and Tor Browser.
- Conversion of old encrypted Roborock `.pkg` files.
- Recursive ZIP processing for WAV, `.pkg`, and mixed archives.
- Batch conversion of every package in `old_voicepacks`.
- Manual package creation using Russian and English event tables.
- Exact validation of all 101 numeric MP3 events.
- Selection and installation of a package from `ready_voicepacks`.
- Downloading 20 official languages for d109gl and d102gl.

## Quick Start

```bash
git clone https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max.git
cd voicepack-tool-xiaomi-x20-pro-max
```

Windows:

```powershell
.\run.ps1
```

Linux:

```bash
chmod +x ./run.sh
./run.sh
```

Choose menu item 1 on first use. It installs the required Python packages,
Playwright Chromium, `ffmpeg`, and `ccrypt` where required.

## Menu

1. Install required software.
2. Authorize Xiaomi in a temporary browser.
3. Import an existing browser session.
4. Run a device preflight check.
5. Convert all old packages.
6. Build a custom voice pack.
7. Verify new voice packs.
8. Install a voice pack selected from a list.
9. Download all official d109gl/d102gl language packages.
10. Exit.

## Directory Layout

```text
old_voicepacks/             Old .pkg, ZIP, WAV files, or directories
ready_voicepacks/           Converted and manually built packages
custom_voicepack/
  audio/                    Numeric MP3 replacements
  table_en.csv              English reference for 101 events
  table_ru.csv              Russian reference for 101 events
official_voicepacks/        Downloaded official packages
resources/                  Mappings, donor cache, and runtime files
state/                      Local credentials and upload state
work/                       Temporary files
```

Credentials, generated packages, downloaded originals, and temporary files are
excluded from Git.

## Convert Old Packages

Place each input in `old_voicepacks` and choose menu item 5. Supported layouts:

- standalone encrypted `.pkg`;
- ZIP containing WAV files;
- ZIP containing one or more `.pkg` files;
- ZIP containing both WAV and `.pkg`;
- directories containing WAV, ZIP, and `.pkg`;
- nested ZIP archives up to four levels.

A loose WAV overrides a same-named file from a nested package. Unsafe ZIP paths
and archives expanding beyond 512 MiB are rejected.

The complete old catalog contains 97 voice events. `sound.info` and
`sound.ver` are metadata files and are not voice events.

## Download Old Package

https://4pda.to/forum/index.php?showtopic=881982

[https://www.google.com/search](https://www.google.com/webhp) -> xiaomi voice pack download

## Build a Custom Package

Use `custom_voicepack/table_ru.csv` and `table_en.csv` to find event numbers.
Put changed numeric MP3 files, such as `130.mp3`, in
`custom_voicepack/audio`, then choose menu item 6.

Missing events are taken from the official Russian donor package, downloaded
automatically on first use. Replacements are normalized to mono, 16 kHz,
32 kbps without ID3 or Xing metadata.

## Authorization

Menu item 2 opens the official Xiaomi account page in a temporary browser
profile.

Menu item 3 checks installed browsers sequentially and stops after finding the
first complete Xiaomi session. Modern Chrome may use application-bound `v20`
cookie encryption; use menu item 2 when Windows prevents cookie transfer.

Create `.env` from `.env.example` and set at least:

```text
XIAOMI_DID=YOUR_DEVICE_DID
```

Never publish `.env`, `state/*.json`, robot tokens, credentials, or signed
download URLs.

## Command Line

```powershell
.\run.ps1 convert-all
.\run.ps1 build-custom
.\run.ps1 verify-all
.\run.ps1 install
.\run.ps1 download-originals
```

Linux provides the same commands through `./run.sh`.

## Disclaimer

This is an independent community project and is not affiliated with Xiaomi or
Roborock. Installing unofficial voice packs is performed at your own risk.

## License

[MIT](LICENSE)
