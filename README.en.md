<!-- LANG_START -->
🇷🇺 [Русская версия](README.md)
<!-- LANG_END -->

<div align="center">

<img src="resources/header.svg" alt="Xiaomi Voice Pack Tool" width="900"/>

</div>





<!-- STATS_START -->
<!-- auto-updated by GitHub Actions · 2026-06-28 17:01 UTC -->

[![Views local](https://img.shields.io/badge/Views_local-28-ff6900?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Views GitHub](https://img.shields.io/badge/Views_GitHub-33-ff6900?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Unique visitors](https://img.shields.io/badge/Unique-7-blue?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Clones](https://img.shields.io/badge/Clones-617-purple?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Stars](https://img.shields.io/badge/Stars-0-yellow?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/stargazers)
[![Forks](https://img.shields.io/badge/Forks-0-green?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/network/members)
[![Downloads latest release](https://img.shields.io/badge/Downloads_latest_release-0-brightgreen?style=for-the-badge)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/releases/latest)
[![Downloads total assets](https://img.shields.io/badge/Downloads_total_assets-3-brightgreen?style=for-the-badge)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/releases)

<!-- STATS_END -->









<!-- GRAPH_START -->
<p align="center">
  <img src="./traffic-views.png" width="100%" alt="GitHub Traffic">
</p>
<!-- GRAPH_END -->








<!-- ISSUES_START -->
<!-- auto-updated by GitHub Actions · 2026-06-28 17:01 UTC -->

## Issues

<p>
  <a href="https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/issues">
    <img alt="Open issues" src="https://img.shields.io/badge/Open_issues-0-blue?style=for-the-badge&logo=github">
  </a>
  <a href="https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/issues/new/choose">
    <img alt="Create issue" src="https://img.shields.io/badge/Create_issue-new-success?style=for-the-badge&logo=github">
  </a>
</p>

<details open>
<summary><b>Open issues</b></summary>


<p align="center">
  <b>No open issues.</b><br>
  <sub>The service issue <code>views-counter</code> is hidden from the list.</sub>
</p>


</details>

<p>
  <a href="https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/issues/new/choose">Create new issue</a> ·
  <a href="https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/issues">All issues</a>
</p>

<!-- ISSUES_END -->





## Xiaomi Voce Pack Tool

A tool for Windows designed to work with voice
packages (voices) of the Xiaomi x20 pro (d102gl) and x20 max (d109gl) robot vacuum cleaners. It converts old Roborock packages,
collects new Xiaomi numerical packages, checks archives, downloads official ones
languages and installs the selected voicepack.

Tested on:

- `xiaomi.vacuum.d109gl`
- `xiaomi.vacuum.d102gl`

## And also

- the list will be updated with all the vacuum cleaners I can get my hands on



## Features

- Interactive menu for Windows.
- Consecutive session import from Chrome, Firefox, Edge, Yandex, Chromium,
  Brave, Vivaldi, Opera, Opera GX and Tor Browser.
- Unpacking old encrypted Roborock `.pkg`.
- Recursive processing of ZIP with WAV, `.pkg` and mixed content.
- Batch conversion of the entire `old_voicepacks` folder.
- Manual assembly using Russian and English event tables.
- Checking the exact set of 101 numeric MP3s.
- Selecting and installing a package from `ready_voicepacks`.
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

When you run it for the first time, select option 1. It will install the Python dependencies,
Playwright Chromium, `ffmpeg` and, if necessary, `ccrypt`.

## Menu

1. Prepare authorization and DID automatically
2. Preliminary check of the device
3. Convert all old packages from the old_voicepacks folder
4. Collect a new custom voicepack from the custom_voicepack folder
5. Check new voicepacks from the ready_voicepacks folder
6. Install a voicepack from the ready_voicepacks list
7. Download original d109gl/d102gl packages in all languages
8. Exit

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

Place each source in `old_voicepacks` and select option 4. Supported:

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
`sound.ver` are service files and are not considered votes.

## Download old voice packs

https://4pda.to/forum/index.php?showtopic=881982

[https://www.google.com/search](https://www.google.com/webhp) -> xiaomi voice pack download

## Manual custom package

Event numbers are in `custom_voicepack/table_ru.csv` and
`table_en.csv`. Put modified numeric MP3s, such as `130.mp3`, into`custom_voicepack/audio` and select option 6.

Missing events are taken from the official Russian package, which
automatically downloaded the first time you use it. Replaceable files
normalized to mono, 16 kHz, 32 kbps without ID3 and Xing.

## Authorization

Step 1 sequentially imports the Xiaomi session from the installed browser,
searches for devices via Mi Cloud and local network UDP 54321, saves everything
found devices in `state/devices.json`, prompts you to select active
vacuum cleaner when there are multiple matches and performs a preliminary check.
For non-interactive selection use `--device-index`, `--device-ip`,
`--device-name` or `--did`.
Modern Chrome
can use application-specific encryption cookie `v20`
(not tested). Before reading cookie, item 1 automatically closes
found browsers so that their databases are not blocked.

Local search uses UDP 54321 with a timeout of 1.5 seconds and 3 retries.
If the device responds slowly, increase `--scan-timeout` or
`XIAOMI_SCAN_TIMEOUT`, for example up to `3`.

## Obtaining device information in MiHome

Go to MiHome -> vacuum cleaner -> ⋮ -> Cleaning history -> quickly press with three fingers -> total duration, total cleanings, total number of times

## Disclaimer

This is an independent project not associated with Xiaomi or Roborock.
Installation of unofficial voicepacks is at your own risk and may void warranty service.

## Acknowledgments

Special thanks to [runassu](https://github.com/runassu) for the research and Chromium v20 cookie decryption techniques used in this project.
