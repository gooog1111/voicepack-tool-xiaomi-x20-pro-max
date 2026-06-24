# Xiaomi Voice Pack Tool

<!-- STATS_START -->
<!-- auto-updated by GitHub Actions · 2026-06-24 08:26 UTC -->

[![Просмотры](https://hits.sh/gooog1111/voicepack-tool-xiaomi-x20-pro-max.svg?style=for-the-badge&label=👁+Просмотров&color=ff6900&labelColor=161b22)](https://hits.sh/gooog1111/voicepack-tool-xiaomi-x20-pro-max/)

| Показатель | Значение |
|---|---|
| 🏷️ Последний релиз | [`v1.0.0`](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/releases/latest) · 2026-06-23 |
| ⬇️ Скачиваний (релиз) | 0 |
| ⬇️ Скачиваний (всего) | 0 |
| ⭐ Звёзды | [0](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/stargazers) |
| 🍴 Форки | [0](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/network/members) |
| 🐛 Открытых задач | [0](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/issues) |
<!-- STATS_END -->

<!-- ISSUES_START -->
<!-- auto-updated by GitHub Actions · 2026-06-24 08:26 UTC -->

## 🐛 Открытые задачи

_Открытых задач нет — всё хорошо! 🎉_

> 💡 **[Создать новую задачу](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/issues/new/choose)** · [Все задачи](https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max/issues)
<!-- ISSUES_END -->

[English version](README.en.md)

Инструмент для Windows и Linux, предназначенный для работы с голосовыми
пакетами роботов-пылесосов Xiaomi. Он конвертирует старые пакеты Roborock,
собирает новые числовые пакеты Xiaomi, проверяет архивы, скачивает официальные
языки и устанавливает выбранный войспак.

Проверено на:

- `xiaomi.vacuum.d109gl`
- `xiaomi.vacuum.d102gl`

## Возможности

- Интерактивное меню для Windows и Linux.
- Авторизация Xiaomi во временном профиле браузера.
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

Linux:

```bash
chmod +x ./run.sh
./run.sh
```

При первом запуске выберите пункт 1. Он установит Python-зависимости,
Playwright Chromium, `ffmpeg` и, при необходимости, `ccrypt`.

## Меню

1. Установить необходимое ПО.
2. Авторизация Xiaomi во временном браузере.
3. Импорт действующей сессии из установленных браузеров.
4. Предварительная проверка устройства.
5. Конвертировать все старые пакеты.
6. Собрать новый кастомный войспак.
7. Проверить новые войспаки.
8. Установить войспак из списка.
9. Скачать оригинальные пакеты d109gl/d102gl на всех языках.
10. Выход.

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

Поместите каждый исходник в `old_voicepacks` и выберите пункт 5. Поддерживаются:

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

Пункт 2 открывает официальную страницу Xiaomi во временном профиле браузера.

Пункт 3 последовательно проверяет установленные браузеры и прекращает поиск
после первой полной Xiaomi-сессии. Современный Chrome может использовать
привязанное к приложению шифрование cookie `v20`; если Windows запрещает
перенос, используйте пункт 2.

Создайте `.env` на основе `.env.example` и укажите как минимум:

```text
XIAOMI_DID=YOUR_DEVICE_DID
```
### Получение XIAOMI_DID

Зайдите в MiHome -> пылесос -> ⋮ -> История уборок -> тремя пальцами быстро нажимать на -> общая продолжительность, всего уборок, общее количество раз

## Командная строка

```powershell
.\run.ps1 convert-all
.\run.ps1 build-custom
.\run.ps1 verify-all
.\run.ps1 install
.\run.ps1 download-originals
```

В Linux доступны те же команды через `./run.sh`.

## Отказ от ответственности

Это независимый проект, не связанный с Xiaomi или Roborock.
Установка неофициальных войспаков выполняется на ваш страх и риск, и может повлечь за собой отказ от гарантийного обслуживания.

## Лицензия

[MIT](LICENSE)


## Поддержать проект

Выберите удобный способ:

<p align="center">
  <a href="https://yoomoney.ru/fundraise/1IJBVM8MJMG.260624" target="_blank">
    <img src="https://img.shields.io/badge/ЮМоnеу-Сбор средств-yellow?style=for-the-badge&logo=YooMoney&logoColor=white" alt="ЮМоnеу">
  </a>
  <a href="https://t.tb.ru/c2c-qr-choose-bank?requisiteNumber=+79996363556&bankCode=100000000004" target="_blank">
    <img src="https://img.shields.io/badge/СБП-Т Банк | Sber-blue?style=for-the-badge&logo=none" alt="СБП">
  </a>
</p>

### USDT (TON)

Адрес для перевода:  
```bash
UQA73kPkNHudFD5yV7DuP-GuXO1ExTpqH0gNioQX8sY4fU6L
```
