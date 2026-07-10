<!-- LANG_START -->
🇷🇺 [Русская версия](README.md)
<!-- LANG_END -->

<div align="center">

<img src="resources/header.svg" alt="Xiaomi Voice Pack Tool" width="900"/>

</div>





<!-- STATS_START -->
<!-- auto-updated by GitHub Actions · 2026-07-10 10:01 UTC -->

[![Views local](https://img.shields.io/badge/Views_local-306-ff6900?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
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
<!-- auto-updated by GitHub Actions · 2026-07-10 10:01 UTC -->

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
```Authorization, finished assemblies, downloaded originals and temporary files are excluded from
Git.

Don't store large voice archives in Git. For this project in the repository
code, tables and manifests must remain; `ready_voicepacks/`,
`official_voicepacks/`, `old_voicepacks/`, `cache/`, `work/` and `state/`
are ignored.

## Converting old packages

Place each source in `old_voicepacks` and select option 5. Supported:

- separate encrypted `.pkg`;
- ZIP/RAR with WAV;
- ZIP/RAR with one or more `.pkg`;
- ZIP/RAR containing both WAV and `.pkg`;
- subfolders with WAV, ZIP, RAR and `.pkg`;
- nested ZIP/RAR up to four levels.

A separate WAV takes precedence over the file of the same name from the included package.
Unsafe ZIP/RAR paths and archives larger than 512 MiB after unpacking
are rejected.
RAR needs an installed unpacker in `PATH`, for example `7z`, `unrar`,
`unar` or `bsdtar`; The Python package `rarfile` is installed automatically.

The full old catalog contains 97 voice events. `sound.info` and
`sound.ver` are service files and are not considered votes.

## Download old voice packs

https://4pda.to/forum/index.php?showtopic=881982

[https://www.google.com/search](https://www.google.com/webhp) -> xiaomi voice pack download

## Manual custom package

Event numbers are in `custom_voicepack/table_ru.csv` and
`table_en.csv`. Put modified numeric MP3s, such as `130.mp3`, into
`custom_voicepack/audio` and select option 6.

Missing events are taken from the official Russian package, which
automatically downloaded the first time you use it. Replaceable files
normalized to mono, 16 kHz, 32 kbps without ID3 and Xing.

## Legacy PKG for Roborock v1/S5

Point 7 collects encrypted `.pkg` for old miIO vacuum cleaners:
Xiaomi Mi Robot Vacuum / Mijia 1C gen 1 (`rockrobo.vacuum.v1`) and Roborock
Sweep One S5/S50/S51/S55/S501 (`roborock.vacuum.s5`). These packages are installed
not via Xiaomi Cloud, but locally:

```bash
pip install python-miio
mirobo discover --handshake true
mirobo --ip=192.168.8.1 --token=TOKEN install-sound ready_voicepacks/custom_roborock_v1_s5.pkg
```

The robot must be charged and docked. For firmware you need IP and
local token; they can be obtained through `mirobo discover --handshake true`
after connecting to the `rockrobo-XXXX` network or otherwise from your network.

Build profiles differ in the WAV set:

```bash
python voicepack_manager.py build-legacy-pkg --legacy-profile gen1
python voicepack_manager.py build-legacy-pkg --legacy-profile gen2
python install_legacy_pkg.py --discover --status-first
```

`gen1` is focused on the old catalog of 72 phrases, `gen2`/`s5` - on the full catalog
S5. If you need missing phrases, put ready-made old `*.wav` with names
Roborock in `custom_voicepack/audio`.

## Authorization

Step 1 performs three steps: imports the Xiaomi session from the installed
browser, builds a map of houses/devices and performs a preliminary check.
If import from the browser fails, step 1 automatically startsQR-авторизацию Xiaomi: откройте QR-картинку или страницу входа, подтвердите
вход в Xiaomi Home, после чего сессия сохранится в `state/cloud_auth.json`.

Пункт 2 можно запускать отдельно. Он строит `state/homes_map.json` и
`state/devices.json` через Xiaomi Cloud. Поддерживаются обычные дома,
shared homes и устройства, лежащие только в комнатах shared-дома. Для
modern cloud устройств дополнительно определяется региональный FDS endpoint
через `genpresignedurl_v3`; это cloud-запрос и он не отправляет команду на
робот. В состояние сохраняется только очищенный host/base URL, без signed URL
и query-подписи. Отключить можно флагом `--no-resolve-fds`.

Если регион не указан, инструмент пробует Xiaomi Cloud endpoints автоматически.
Европейские страны, например `cz`, `sk`, `pl`, `fr`, `it` или `eu`, для
старого `api.io.mi.com` преобразуются в endpoint `de`. Если в старой `.env`
уже записан неверный `XIAOMI_COUNTRY=ru`, временно переопределите его:

```bash
./run.sh search-homes-devices --country auto
./run.sh search-homes-devices --country cz
```

Для неинтерактивного выбора используйте `--device-index`, `--device-ip`,
`--device-name` или `--did`.

Современная установка голосового ZIP выполняется удалённо через Xiaomi Cloud:
архив загружается в Xiaomi FDS, затем роботу отправляется MiOT action со
signed URL, md5 и размером. Эти шаги можно разделить:

```bash
python voicepack_cycle.py upload --country de --did 1140953532
python voicepack_cycle.py remote-install --country de --did 1140953532
```

`upload` сохраняет `state/latest_upload.json`, а `remote-install` читает его и
отправляет команду роботу без повторной локальной загрузки архива. Также можно
передать готовую удалённую ссылку вручную:

```bash
python voicepack_cycle.py remote-install --remote-url URL --remote-md5 MD5 --remote-size SIZE
```

Через Linux/macOS-обёртку то же самое:

```bash
./run.sh upload --country de --did 1140953532
./run.sh remote-install --country de --did 1140953532
```

Современный Chrome
может использовать привязанное к приложению шифрование cookie `v20`
(не тестировалось). Перед чтением cookie пункт 1 делает временную копию
cookie-базы браузера и не закрывает браузеры. Если на конкретной системе
копия заблокированной базы не читается, можно запустить импорт с явным
флагом `--close-browsers`.
После успешного обращения к Xiaomi Cloud создаётся маркер
`state/cloud_auth.sha256`. Если `cloud_auth.json` меняли вручную, маркер
перестанет совпадать и будет обновлён после следующей успешной проверки.

Список известных совместимых моделей можно вывести так:

```bash
python search-homes-devices.py --compatible-models
python search-homes-devices.py --compatible-models --family modern_cloud
python search-homes-devices.py --compatible-models --family legacy_miio
```

Локальный поиск использует UDP 54321 с таймаутом 1.5 секунды и 3 попытками.
Если устройство отвечает медленно, увеличьте `--scan-timeout` или
`XIAOMI_SCAN_TIMEOUT`, например до `3`.

## Получение информации об устройстве в MiHome

Зайдите в MiHome -> пылесос -> ⋮ -> История уборок -> тремя пальцами быстро нажимать на -> общая продолжительность, всего уборок, общее количество раз

## Отказ от ответственности

Это независимый проект, не связанный с Xiaomi или Roborock.
Installation of unofficial voicepacks is at your own risk and may void warranty service.

## Acknowledgments

Special thanks to [runassu](https://github.com/runassu) for the research and Chromium v20 cookie decryption techniques used in this project.
