<!-- LANG_START -->
🇷🇺 [Русская версия](README.md)
<!-- LANG_END -->

<div align="center">

<img src="resources/header.svg" alt="Xiaomi Voice Pack Tool" width="900"/>

</div>





<!-- STATS_START -->
<!-- auto-updated by GitHub Actions · 2026-07-10 07:02 UTC -->

[![Views local](https://img.shields.io/badge/Views_local-303-ff6900?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Views GitHub](https://img.shields.io/badge/Views_GitHub-276-ff6900?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Unique visitors](https://img.shields.io/badge/Unique-32-blue?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Clones](https://img.shields.io/badge/Clones-2660-purple?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Stars](https://img.shields.io/badge/Stars-1-yellow?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/stargazers)
[![Forks](https://img.shields.io/badge/Forks-0-green?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/network/members)
[![Downloads latest release](https://img.shields.io/badge/Downloads_latest_release-0-brightgreen?style=for-the-badge)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/releases/latest)
[![Downloads total assets](https://img.shields.io/badge/Downloads_total_assets-4-brightgreen?style=for-the-badge)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/releases)

<!-- STATS_END -->









<!-- GRAPH_START -->
<p align="center">
  <img src="./traffic-views.png" width="100%" alt="GitHub Traffic">
</p>
<!-- GRAPH_END -->








<!-- ISSUES_START -->
<!-- auto-updated by GitHub Actions · 2026-07-10 07:02 UTC -->

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





## Xiaomi Voice Pack Tool

Windows tool for working with robot vacuum cleaner voice packages
Xiaomi. Now the main focus is Xiaomi X20 Pro (`d102gl`) and X20 Max
(`d109gl`), but the code is already separated into providers and device families so that
gradually expand support for other Xiaomi models, and then others
manufacturers.

It imports Xiaomi authorization, builds a map of houses/rooms/devices,
converts old Roborock packages, collects new Xiaomi number packages,
checks archives, downloads official languages and installs the selected one
Voyspak.

Tested on:

- `xiaomi.vacuum.d109gl`
- `xiaomi.vacuum.d102gl`

## And also

- the list will be updated with all the vacuum cleaners I can get my hands on
- the current architecture is being prepared for a future renaming to
  `xiaomi-voicepack-tool` and then to `robot-voicepack-tool` when they appear
  other manufacturers.



## Features

- Interactive menu for Windows.
- Consecutive session import from Chrome, Firefox, Edge, Yandex, Chromium,
  Brave, Vivaldi, Opera, Opera GX and Tor Browser.
- Building `homes_map` from Xiaomi Cloud: regular houses, shared homes, rooms
  and devices inside rooms.
- Separate provider layer `providers/xiaomi`: inventory, compatibility,
  modern cloud voice and legacy miIO.
- List of compatible models and capabilities to help you choose the right method
  installations.
- Determining regional Xiaomi FDS endpoint from a session without sending a command
  to robot.
- Unpacking old encrypted Roborock `.pkg`.
- Recursive processing of ZIP/RAR with WAV, `.pkg` and mixed content.
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

Linux/macOS:

```bash
chmod +x run.sh
./run.sh
```

When you run it for the first time, select option 1. It will install the Python dependencies,
Playwright Chromium, `ffmpeg` and, if necessary, `ccrypt`.

## Menu

1. Prepare authorization and DID automatically
2. Build a map of houses and devices
3. Show compatible Xiaomi models
4. Preliminary check of the device
5. Convert all old packages from the old_voicepacks folder
6. Build a new custom ZIP for X20/Xiaomi Cloud
7. Build legacy PKG for Xiaomi/Roborock v1/S5
8. Install legacy PKG via python-miio
9. Check new ZIP voicepacks from the ready_voicepacks folder
10. Install the ZIP voicepack from the ready_voicepacks list
11. Download original d109gl/d102gl packages in all languages
12. Exit

## Folder structure

```text
old_voicepacks/             Старые .pkg, ZIP, RAR, WAV или подпапки
ready_voicepacks/           Готовые новые пакеты
custom_voicepack/
  audio/                    Числовые MP3 для ручной замены
  table_en.csv              Английская таблица 101 события
  table_ru.csv              Русская таблица 101 события
official_voicepacks/        Скачанные оригинальные пакеты
providers/                  Провайдеры роботов и методы установки
  xiaomi/
    inventory.py            Дома, комнаты, устройства Xiaomi
    compatibility.py        Список совместимых моделей и capabilities
    voice_modern_cloud.py   Новые Xiaomi через Cloud/MiOT
    voice_legacy_miio.py    Старые Xiaomi/Roborock через miIO
resources/                  Таблицы, кэш донора и служебные файлы
state/                      Локальная авторизация, homes_map и состояние
work/                       Временные файлы
```Авторизация, готовые сборки, скачанные оригиналы и временные файлы исключены из
Git.

Не храните большие голосовые архивы в Git. Для этого проекта в репозитории
должны оставаться код, таблицы и манифесты; `ready_voicepacks/`,
`official_voicepacks/`, `old_voicepacks/`, `cache/`, `work/` и `state/`
игнорируются.

## Конвертация старых пакетов

Поместите каждый исходник в `old_voicepacks` и выберите пункт 5. Поддерживаются:

- отдельный зашифрованный `.pkg`;
- ZIP/RAR с WAV;
- ZIP/RAR с одним или несколькими `.pkg`;
- ZIP/RAR, одновременно содержащий WAV и `.pkg`;
- подпапки с WAV, ZIP, RAR и `.pkg`;
- вложенные ZIP/RAR до четырёх уровней.

Отдельный WAV имеет приоритет над одноимённым файлом из вложенного пакета.
Небезопасные пути ZIP/RAR и архивы размером более 512 МиБ после распаковки
отклоняются.
Для RAR нужен установленный распаковщик в `PATH`, например `7z`, `unrar`,
`unar` или `bsdtar`; Python-пакет `rarfile` устанавливается автоматически.

Полный старый каталог содержит 97 голосовых событий. `sound.info` и
`sound.ver` являются служебными файлами и не считаются голосами.

## Скачать старые голосовые пакеты

https://4pda.to/forum/index.php?showtopic=881982

[https://www.google.com/search](https://www.google.com/webhp) -> xiaomi voice pack скачать

## Ручной кастомный пакет

Номера событий находятся в `custom_voicepack/table_ru.csv` и
`table_en.csv`. Положите изменённые числовые MP3, например `130.mp3`, в
`custom_voicepack/audio` и выберите пункт 6.

Отсутствующие события берутся из официального русского пакета, который
автоматически скачивается при первом использовании. Заменяемые файлы
нормализуются в mono, 16 kHz, 32 kbps без ID3 и Xing.

## Legacy PKG для Roborock v1/S5

Пункт 7 собирает зашифрованный `.pkg` для старых miIO-пылесосов:
Xiaomi Mi Robot Vacuum / Mijia 1C gen 1 (`rockrobo.vacuum.v1`) и Roborock
Sweep One S5/S50/S51/S55/S501 (`roborock.vacuum.s5`). Эти пакеты ставятся
не через Xiaomi Cloud, а локально:

```bash
pip install python-miio
mirobo discover --handshake true
mirobo --ip=192.168.8.1 --token=TOKEN install-sound ready_voicepacks/custom_roborock_v1_s5.pkg
```

Робот должен быть заряжен и стоять на док-станции. Для прошивки нужен IP и
локальный token; их можно получить через `mirobo discover --handshake true`
после подключения к сети `rockrobo-XXXX` или другим способом из вашей сети.

Профили сборки отличаются набором WAV:

```bash
python voicepack_manager.py build-legacy-pkg --legacy-profile gen1
python voicepack_manager.py build-legacy-pkg --legacy-profile gen2
python install_legacy_pkg.py --discover --status-first
```

`gen1` ориентирован на старый каталог 72 фраз, `gen2`/`s5` - на полный каталог
S5. Если нужны отсутствующие фразы, положите готовые старые `*.wav` с именами
Roborock в `custom_voicepack/audio`.

## Авторизация

Пункт 1 выполняет три шага: импортирует Xiaomi-сессию из установленного
браузера, строит карту домов/устройств и выполняет предварительную проверку.
Если импорт из браузера не получился, пункт 1 автоматически запускает
Xiaomi QR authorization: open the QR image or login page, confirm
Login to Xiaomi Home, after which the session will be saved in `state/cloud_auth.json`.

Point 2 can be run separately. It builds `state/homes_map.json` and
`state/devices.json` via Xiaomi Cloud. Regular houses are supported,
shared homes and devices located only in the rooms of a shared house. For
modern cloud devices are additionally determined by the regional FDS endpoint
via `genpresignedurl_v3`; This is a cloud request and it does not send a command to
robot Only the cleared host/base URL is saved in the state, without the signed URL
and query signatures. You can disable it using the `--no-resolve-fds` flag.

If the region is not specified, the tool tries Xiaomi Cloud endpoints automatically.
European countries, such as `cz`, `sk`, `pl`, `fr`, `it` or `eu`, for
old `api.io.mi.com` are converted to endpoint `de`. If in the old `.env`
the invalid `XIAOMI_COUNTRY=ru` is already written, temporarily override it:

```bash
./run.sh search-homes-devices --country auto
./run.sh search-homes-devices --country cz
```

For non-interactive selection use `--device-index`, `--device-ip`,
`--device-name` or `--did`.

Modern voice ZIP installation is done remotely via Xiaomi Cloud:
the archive is uploaded to Xiaomi FDS, then the MiOT action is sent to the robot
signed URL, md5 and size. These steps can be divided:

```bash
python voicepack_cycle.py upload --country de --did 1140953532
python voicepack_cycle.py remote-install --country de --did 1140953532
```

`upload` stores `state/latest_upload.json` and `remote-install` reads it and
sends a command to the robot without re-downloading the archive locally. You can also
pass the finished remote link manually:

```bash
python voicepack_cycle.py remote-install --remote-url URL --remote-md5 MD5 --remote-size SIZE
```

Through the Linux/macOS wrapper the same thing:

```bash
./run.sh upload --country de --did 1140953532
./run.sh remote-install --country de --did 1140953532
```

Modern Chrome
can use application-specific encryption cookie `v20`
(not tested). Before reading the cookie, point 1 makes a temporary copy
browser cookie and does not close browsers. If on a specific system
a copy of the blocked database is not readable, you can run the import with an explicit
flag `--close-browsers`.
After successfully accessing Xiaomi Cloud, a token is created
`state/cloud_auth.sha256`. If `cloud_auth.json` was changed manually, the token
will no longer match and will be updated after the next successful check.

The list of known compatible models can be displayed as follows:

```bash
python search-homes-devices.py --compatible-models
python search-homes-devices.py --compatible-models --family modern_cloud
python search-homes-devices.py --compatible-models --family legacy_miio
```

Local search uses UDP 54321 with a timeout of 1.5 seconds and 3 retries.
If the device responds slowly, increase `--scan-timeout` or
`XIAOMI_SCAN_TIMEOUT`, for example to `3`.

## Obtaining device information in MiHome

Go to MiHome -> vacuum cleaner -> ⋮ -> Cleaning history -> quickly press with three fingers -> total duration, total cleanings, total number of times

## Disclaimer

This is an independent project not associated with Xiaomi or Roborock.Installation of unofficial voicepacks is at your own risk and may void warranty service.

## Acknowledgments

Special thanks to [runassu](https://github.com/runassu) for the research and Chromium v20 cookie decryption techniques used in this project.
