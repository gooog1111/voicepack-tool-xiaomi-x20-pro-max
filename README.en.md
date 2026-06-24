<div align="center">

<img src="resources/header.svg" alt="Xiaomi Voice Pack Tool" width="900"/>

</div>





<!-- STATS_START -->
<!-- auto-updated by GitHub Actions · 2026-06-24 10:45 UTC -->

[![Views local](https://img.shields.io/badge/Views_local-10-ff6900?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Views GitHub](https://img.shields.io/badge/Views_GitHub-0-ff6900?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Unique visitors](https://img.shields.io/badge/Unique-0-blue?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Clones](https://img.shields.io/badge/Clones-0-purple?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Stars](https://img.shields.io/badge/Stars-0-yellow?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/stargazers)
[![Forks](https://img.shields.io/badge/Forks-0-green?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/network/members)
[![Downloads release](https://img.shields.io/badge/Downloads_release-1-brightgreen?style=for-the-badge)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/releases/latest)
[![Downloads total](https://img.shields.io/badge/Downloads_total-1-brightgreen?style=for-the-badge)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/releases)

<!-- STATS_END -->









<!-- GRAPH_START -->
<p align="center">
  <img src="./traffic-views.png" width="100%" alt="GitHub Traffic">
</p>
<!-- GRAPH_END -->








<!-- ISSUES_START -->
<!-- auto-updated by GitHub Actions · 2026-06-24 10:45 UTC -->

##Open Issues

| # | Title | Date |
|---|-------|------|
| [`#1`](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/issues/1) | views-counter | 2026-06-24 |

> [Create new issue](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/issues/new/choose) · [All issues](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/issues)

<!-- ISSUES_END -->




[English version](README.en.md)

## Xiaomi Voce Pack Tool

A tool for Windows and Linux designed to work with voice
packages of Xiaomi robot vacuum cleaners. It converts old Roborock packages,
collects new Xiaomi numerical packages, checks archives, downloads official ones
languages and installs the selected voicepack.

Tested on:

- `xiaomi.vacuum.d109gl`
- `xiaomi.vacuum.d102gl`

## Features

- Interactive menu for Windows and Linux.
- Xiaomi authorization in a temporary browser profile.
- Consecutive session import from Chrome, Firefox, Edge, Yandex, Chromium,
  Brave, Vivaldi, Opera, Opera GX and Tor Browser.
- Unpacking old encrypted Roborock `.pkg`.
- Recursive processing of ZIP with WAV, `.pkg` and mixed content.
- Batch conversion of the entire `old_voicepacks` folder.
- Manual assembly using Russian and English event tables.
- Checking the exact set of 101 numeric MP3s.
- Select and install a package from `ready_voicepacks`.
- Download 20 official languages ​​for d109gl and d102gl.

## Quick start
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
When you run it for the first time, select option 1. It will install the Python dependencies,
Playwright Chromium, `ffmpeg` and, if necessary, `ccrypt`.

## Menu

1. Install the necessary software.
2. Xiaomi authorization in a temporary browser.
3. Import the current session from installed browsers.
4. Preliminary check of the device.
5. Convert all old packages.
6. Build a new custom voice pack.
7. Check new military packs.
8. Install a military pack from the list.
9. Download original d109gl/d102gl packages in all languages.
10. Exit.

## Folder structure
```text
old_voicepacks/             Старые .pkg, ZIP, WAV или подпапки
ready_voicepacks/           Готовые новые пакеты
custom_voicepack/
  audio/                    Числовые MP3 для ручной замены
  table_en.csv              Английская таблица 101 события
  table_ru.csv              Русская таблица 101 события
official_voicepacks/        Скачанные оригинальные пакеты
resources/                  Таблицы, кэш донора и служебные файлы
state/                      Локальная авторизация и состояние загрузки
work/                       Временные файлы
```
Authorization, finished assemblies, downloaded originals and temporary files are excluded from
Git.

## Converting old packages

Place each source in `old_voicepacks` and select option 5. Supported:

- separate encrypted `.pkg`;
- ZIP with WAV;
- ZIP with one or more `.pkg`;
- ZIP containing both WAV and `.pkg`;
- subfolders with WAV, ZIP and `.pkg`;
- nested ZIPs up to four levels.

A separate WAV takes precedence over the file of the same name from the included package.
Insecure ZIP paths and archives larger than 512 MiB after unpacking
are rejected.

The full old catalog contains 97 voice events. `sound.info` and
`sound.ver` are service files and are not considered voices.

## Download old voice packs

https://4pda.to/forum/index.php?showtopic=881982

[https://www.google.com/search](https://www.google.com/webhp) -> xiaomi voice pack download

## Manual custom package

Event numbers are in `custom_voicepack/table_en.csv` and
`table_en.csv`. Put modified numeric MP3s, such as `130.mp3`, into
`custom_voicepack/audio` and select item 6.

Missing events are taken from the official Russian package, which
automatically downloaded the first time you use it. Replaceable files
normalized to mono, 16 kHz, 32 kbps without ID3 and Xing.

## Authorization

Step 2 opens the official Xiaomi page in a temporary browser profile.

Step 3 sequentially checks installed browsers and stops searching
after the first full Xiaomi session. Modern Chrome can use
application-specific encryption cookie `v20`; if Windows prohibits
transfer, use point 2.

Create `.env` based on `.env.example` and specify at least:
```text
XIAOMI_DID=YOUR_DEVICE_DID
```
### Getting XIAOMI_DID

Go to MiHome -> vacuum cleaner -> ⋮ -> Cleaning history -> quickly press with three fingers -> total duration, total cleanings, total number of times

## Command line
```powershell
.\run.ps1 convert-all
.\run.ps1 build-custom
.\run.ps1 verify-all
.\run.ps1 install
.\run.ps1 download-originals
```
On Linux the same commands are available via `./run.sh`.

## Disclaimer

This is an independent project not associated with Xiaomi or Roborock.
Installation of unofficial voicepacks is at your own risk and may void warranty service.

## License

[MIT](LICENSE)


## Support the project

Choose a convenient method:

<p align="center">
  <a href="https://yoomoney.ru/fundraise/1IJBVM8MJMG.260624" target="_blank">
    <img src="https://img.shields.io/badge/YooMoney-Fundraising-yellow?style=for-the-badge&logo=YooMoney&logoColor=white" alt="YooMoney">
  </a>
  <a href="https://t.tb.ru/c2c-qr-choose-bank?requisiteNumber=+79996363556&bankCode=100000000004" target="_blank">
    <img src="https://img.shields.io/badge/SBP-T Bank | Sber-blue?style=for-the-badge&logo=none" alt="SBP">
  </a>
</p>

### USDT (TON)

Address for transfer:
```bash
UQA73kPkNHudFD5yV7DuP-GuXO1ExTpqH0gNioQX8sY4fU6L
```

