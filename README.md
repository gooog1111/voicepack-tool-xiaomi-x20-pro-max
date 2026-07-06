<!-- LANG_START -->
🇬🇧 [English version](README.en.md)
<!-- LANG_END -->

<div align="center">

<img src="resources/header.svg" alt="Xiaomi Voice Pack Tool" width="900"/>

</div>





<!-- STATS_START -->
<!-- auto-updated by GitHub Actions · 2026-07-06 06:01 UTC -->

[![Views local](https://img.shields.io/badge/Views_local-207-ff6900?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Views GitHub](https://img.shields.io/badge/Views_GitHub-273-ff6900?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Unique visitors](https://img.shields.io/badge/Unique-32-blue?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Clones](https://img.shields.io/badge/Clones-1995-purple?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
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
<!-- auto-updated by GitHub Actions · 2026-07-06 06:01 UTC -->

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





## Xiaomi Voice Pack Tool

Инструмент для Windows для работы с голосовыми пакетами роботов-пылесосов
Xiaomi. Сейчас основной фокус - Xiaomi X20 Pro (`d102gl`) и X20 Max
(`d109gl`), но код уже разделён на провайдеры и семейства устройств, чтобы
постепенно расширять поддержку других моделей Xiaomi, а затем и других
производителей.

Он импортирует авторизацию Xiaomi, строит карту домов/комнат/устройств,
конвертирует старые пакеты Roborock, собирает новые числовые пакеты Xiaomi,
проверяет архивы, скачивает официальные языки и устанавливает выбранный
войспак.

Проверено на:

- `xiaomi.vacuum.d109gl`
- `xiaomi.vacuum.d102gl`

## А так же

- список будет пополняться всеми пылесосми, до которых смогу дотянуться
- текущая архитектура готовится к будущему переименованию в
  `xiaomi-voicepack-tool`, а затем в `robot-voicepack-tool`, когда появятся
  другие производители.



## Возможности

- Интерактивное меню для Windows.
- Последовательный импорт сессии из Chrome, Firefox, Edge, Яндекс, Chromium,
  Brave, Vivaldi, Opera, Opera GX и Tor Browser.
- Построение `homes_map` из Xiaomi Cloud: обычные дома, shared homes, комнаты
  и устройства внутри комнат.
- Отдельный слой провайдера `providers/xiaomi`: inventory, совместимость,
  modern cloud voice и legacy miIO.
- Список совместимых моделей и capabilities для выбора правильного метода
  установки.
- Определение регионального Xiaomi FDS endpoint из сессии без отправки команды
  на робот.
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

Linux/macOS:

```bash
chmod +x run.sh
./run.sh
```

При первом запуске выберите пункт 1. Он установит Python-зависимости,
Playwright Chromium, `ffmpeg` и, при необходимости, `ccrypt`.

## Меню

1. Подготовить авторизацию и DID автоматически
2. Построить карту домов и устройств
3. Показать совместимые модели Xiaomi
4. Предварительная проверка устройства
5. Конвертировать все старые пакеты из папки old_voicepacks
6. Собрать новый кастомный ZIP для X20/Xiaomi Cloud
7. Собрать legacy PKG для Xiaomi/Roborock v1/S5
8. Установить legacy PKG через python-miio
9. Проверить новые ZIP-войспаки из папки ready_voicepacks
10. Установить ZIP-войспак из списка ready_voicepacks
11. Скачать оригинальные пакеты d109gl/d102gl на всех языках
12. Выход

## Структура папок

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
```

Авторизация, готовые сборки, скачанные оригиналы и временные файлы исключены из
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
QR-авторизацию Xiaomi: откройте QR-картинку или страницу входа, подтвердите
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
Установка неофициальных войспаков выполняется на ваш страх и риск, и может повлечь за собой отказ от гарантийного обслуживания.

## Благодарности

Отдельная благодарность [runassu](https://github.com/runassu) за исследование и методы расшифровки Chromium v20 cookie, использованные в этом проекте.
