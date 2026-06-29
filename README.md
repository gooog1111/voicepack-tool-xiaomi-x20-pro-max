<!-- LANG_START -->
🇬🇧 [English version](README.en.md)
<!-- LANG_END -->

<div align="center">

<img src="resources/header.svg" alt="Xiaomi Voice Pack Tool" width="900"/>

</div>





<!-- STATS_START -->
<!-- auto-updated by GitHub Actions · 2026-06-29 13:01 UTC -->

[![Views local](https://img.shields.io/badge/Views_local-48-ff6900?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Views GitHub](https://img.shields.io/badge/Views_GitHub-57-ff6900?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Unique visitors](https://img.shields.io/badge/Unique-27-blue?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Clones](https://img.shields.io/badge/Clones-834-purple?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Stars](https://img.shields.io/badge/Stars-0-yellow?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/stargazers)
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
<!-- auto-updated by GitHub Actions · 2026-06-29 13:01 UTC -->

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
<summary><b>Открытые issues</b></summary>


<p align="center">
  <b>Открытых issues нет.</b><br>
  <sub>Служебный issue <code>views-counter</code> скрыт из списка.</sub>
</p>


</details>

<p>
  <a href="https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/issues/new/choose">Создать issue</a> ·
  <a href="https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/issues">Все issues</a>
</p>

<!-- ISSUES_END -->





## Xiaomi Voce Pack Tool

Инструмент для Windows, предназначенный для работы с голосовыми
пакетами (озвучками) роботов-пылесосов Xiaomi x20 pro (d102gl) и x20 max (d109gl). Он конвертирует старые пакеты Roborock,
собирает новые числовые пакеты Xiaomi, проверяет архивы, скачивает официальные
языки и устанавливает выбранный войспак.

Проверено на:

- `xiaomi.vacuum.d109gl`
- `xiaomi.vacuum.d102gl`

## А так же

- список будет пополняться всеми пылесосми, до которых смогу дотянуться



## Возможности

- Интерактивное меню для Windows.
- Последовательный импорт сессии из Chrome, Firefox, Edge, Яндекс, Chromium,
  Brave, Vivaldi, Opera, Opera GX и Tor Browser.
- Распаковка старых зашифрованных Roborock `.pkg`.
- Рекурсивная обработка ZIP/RAR с WAV, `.pkg` и смешанным содержимым.
- Пакетная конвертация всей папки `old_voicepacks`.
- Ручная сборка по русской и английской таблицам событий.
- Проверка точного набора из 101 числового MP3.
- Выбор и установка пакета из `ready_voicepacks`.
- Скачивание 20 официальных языков для d109gl и d102gl.

## Быстрый старт

```bash
git clone https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max.git
cd voicepack-tool-xiaomi-x20-pro-max
```

Windows:

```powershell
.\run.ps1
```

При первом запуске выберите пункт 1. Он установит Python-зависимости,
Playwright Chromium, `ffmpeg` и, при необходимости, `ccrypt`.

## Меню

1. Подготовить авторизацию и DID автоматически
2. Предварительная проверка устройства
3. Конвертировать все старые пакеты из папки old_voicepacks
4. Собрать новый кастомный ZIP для X20/Xiaomi Cloud
5. Собрать legacy PKG для Xiaomi/Roborock v1/S5
6. Установить legacy PKG через python-miio
7. Проверить новые ZIP-войспаки из папки ready_voicepacks
8. Установить ZIP-войспак из списка ready_voicepacks
9. Скачать оригинальные пакеты d109gl/d102gl на всех языках
10. Выход

## Структура папок

```text
old_voicepacks/             Старые .pkg, ZIP, RAR, WAV или подпапки
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

Авторизация, готовые сборки, скачанные оригиналы и временные файлы исключены из
Git.

## Конвертация старых пакетов

Поместите каждый исходник в `old_voicepacks` и выберите пункт 3. Поддерживаются:

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
`custom_voicepack/audio` и выберите пункт 4.

Отсутствующие события берутся из официального русского пакета, который
автоматически скачивается при первом использовании. Заменяемые файлы
нормализуются в mono, 16 kHz, 32 kbps без ID3 и Xing.

## Legacy PKG для Roborock v1/S5

Пункт 5 собирает зашифрованный `.pkg` для старых miIO-пылесосов:
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

Пункт 1 последовательно импортирует Xiaomi-сессию из установленного браузера,
ищет устройства через Mi Cloud и локальную сеть UDP 54321, сохраняет все
найденные устройства в `state/devices.json`, предлагает выбрать активный
пылесос при нескольких совпадениях и выполняет предварительную проверку.
Если импорт из браузера не получился, пункт 1 автоматически запускает
QR-авторизацию Xiaomi: откройте QR-картинку или страницу входа, подтвердите
вход в Xiaomi Home, после чего сессия сохранится в `state/cloud_auth.json`.
Для неинтерактивного выбора используйте `--device-index`, `--device-ip`,
`--device-name` или `--did`.
Современный Chrome
может использовать привязанное к приложению шифрование cookie `v20`
(не тестировалось). Перед чтением cookie пункт 1 автоматически закрывает
найденные браузеры, чтобы их базы данных не были заблокированы.
После успешного обращения к Xiaomi Cloud создаётся маркер
`state/cloud_auth.sha256`. Если `cloud_auth.json` меняли вручную, маркер
перестанет совпадать и будет обновлён после следующей успешной проверки.

Локальный поиск использует UDP 54321 с таймаутом 1.5 секунды и 3 попытками.
Если устройство отвечает медленно, увеличьте `--scan-timeout` или
`XIAOMI_SCAN_TIMEOUT`, например до `3`.

## Получение информации об устройстве в MiHome

Зайдите в MiHome -> пылесос -> ⋮ -> История уборок -> тремя пальцами быстро нажимать на -> общая продолжительность, всего уборок, общее количество раз

## Отказ от ответственности

Это независимый проект, не связанный с Xiaomi или Roborock.
Установка неофициальных войспаков выполняется на ваш страх и риск, и может повлечь за собой отказ от гарантийного обслуживания.

## Благодарности

Отдельная благодарность [runassu](https://github.com/runassu) за исследование и методы расшифровки Chromium v20 cookie, использованные в этом проекте.
