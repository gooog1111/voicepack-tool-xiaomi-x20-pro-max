<!-- LANG_START -->
🇬🇧 [English version](README.en.md)
<!-- LANG_END -->

<div align="center">

<img src="resources/header.svg" alt="Xiaomi Voice Pack Tool" width="900"/>

</div>





<!-- STATS_START -->
<!-- auto-updated by GitHub Actions · 2026-06-28 04:23 UTC -->

[![Views local](https://img.shields.io/badge/Views_local-25-ff6900?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Views GitHub](https://img.shields.io/badge/Views_GitHub-0-ff6900?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Unique visitors](https://img.shields.io/badge/Unique-0-blue?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
[![Clones](https://img.shields.io/badge/Clones-0-purple?style=for-the-badge&logo=github)](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max)
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
<!-- auto-updated by GitHub Actions · 2026-06-28 04:23 UTC -->

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
- Рекурсивная обработка ZIP с WAV, `.pkg` и смешанным содержимым.
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

1. Импорт действующей Xiaomi-сессии из установленного браузера
2. Найти DID в локальной сети UDP 54321
3. Предварительная проверка устройства
4. Конвертировать все старые пакеты из папки old_voicepacks
5. Собрать новый кастомный войспак из папки custom_voicepack
6. Проверить новые войспаки из папки ready_voicepacks
7. Установить войспак из списка ready_voicepacks
8. Скачать оригинальные пакеты d109gl/d102gl на всех языках
9. Выход

## Структура папок

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

Авторизация, готовые сборки, скачанные оригиналы и временные файлы исключены из
Git.

## Конвертация старых пакетов

Поместите каждый исходник в `old_voicepacks` и выберите пункт 4. Поддерживаются:

- отдельный зашифрованный `.pkg`;
- ZIP с WAV;
- ZIP с одним или несколькими `.pkg`;
- ZIP, одновременно содержащий WAV и `.pkg`;
- подпапки с WAV, ZIP и `.pkg`;
- вложенные ZIP до четырёх уровней.

Отдельный WAV имеет приоритет над одноимённым файлом из вложенного пакета.
Небезопасные пути ZIP и архивы размером более 512 МиБ после распаковки
отклоняются.

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

## Авторизация

Пункт 1 последовательно проверяет установленные браузеры и прекращает поиск
после первой полной Xiaomi-сессии. Современный Chrome может использовать
привязанное к приложению шифрование cookie `v20` (не тестировплось).

### Получение информации об устройстве в MiHome

Зайдите в MiHome -> пылесос -> ⋮ -> История уборок -> тремя пальцами быстро нажимать на -> общая продолжительность, всего уборок, общее количество раз

## Отказ от ответственности

Это независимый проект, не связанный с Xiaomi или Roborock.
Установка неофициальных войспаков выполняется на ваш страх и риск, и может повлечь за собой отказ от гарантийного обслуживания.

## Благодарности

Отдельная благодарность [runassu](https://github.com/runassu) за исследование и методы расшифровки Chromium v20 cookie, использованные в этом проекте.
