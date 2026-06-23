#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMAND="${1:-menu}"
if [[ $# -gt 0 ]]; then shift; fi

if [[ -f "$HERE/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$HERE/.env"
  set +a
fi

if [[ "$COMMAND" == "menu" ]]; then
  printf '\nXiaomi Voice Pack\n=================\n'
  printf '1. Установить необходимое ПО\n'
  printf '2. Авторизация Xiaomi во временном браузере\n'
  printf '3. Импорт действующей Xiaomi-сессии из установленного браузера (Windows)\n'
  printf '4. Предварительная проверка устройства\n'
  printf '5. Конвертировать все старые пакеты из папки old_voicepacks\n'
  printf '6. Собрать новый кастомный войспак из папки custom_voicepack\n'
  printf '7. Проверить новые войспаки из папки ready_voicepacks\n'
  printf '8. Установить войспак из списка ready_voicepacks\n'
  printf '9. Скачать оригинальные пакеты d109gl/d102gl на всех языках\n'
  printf '10. Выход\n\n'
  read -r -p 'Выберите действие: ' choice
  case "$choice" in
    1) COMMAND="setup" ;;
    2) COMMAND="auth" ;;
    3) COMMAND="existing-auth" ;;
    4) COMMAND="preflight" ;;
    5) COMMAND="convert-all" ;;
    6) COMMAND="build-custom" ;;
    7) COMMAND="verify-all" ;;
    8) COMMAND="install" ;;
    9) COMMAND="download-originals" ;;
    10) exit 0 ;;
    *) echo "Неизвестный пункт меню: $choice" >&2; exit 2 ;;
  esac
fi

if [[ ! -x "$HERE/.venv/bin/python" ]]; then
  if ! command -v python3 >/dev/null 2>&1; then
    if [[ "$COMMAND" != "setup" ]]; then
      echo "Python 3 не найден. Сначала выберите пункт 1." >&2
      exit 1
    fi
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update && sudo apt-get install -y python3 python3-venv
    elif command -v dnf >/dev/null 2>&1; then
      sudo dnf install -y python3
    elif command -v pacman >/dev/null 2>&1; then
      sudo pacman -S --needed python
    elif command -v brew >/dev/null 2>&1; then
      brew install python
    else
      echo "Установите Python 3 через пакетный менеджер системы." >&2
      exit 1
    fi
  fi
  python3 -m venv "$HERE/.venv"
fi

if [[ "$COMMAND" == "setup" ]]; then
  "$HERE/.venv/bin/python" -m pip install --upgrade pip
  "$HERE/.venv/bin/python" -m pip install -r "$HERE/requirements.txt"
  "$HERE/.venv/bin/python" -m playwright install chromium
  if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ccrypt >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update && sudo apt-get install -y ffmpeg ccrypt
    elif command -v dnf >/dev/null 2>&1; then
      sudo dnf install -y ffmpeg ccrypt
    elif command -v pacman >/dev/null 2>&1; then
      sudo pacman -S --needed ffmpeg ccrypt
    elif command -v brew >/dev/null 2>&1; then
      brew install ffmpeg ccrypt
    else
      echo "Установите ffmpeg и ccrypt через пакетный менеджер системы." >&2
      exit 1
    fi
  fi
  echo "Необходимое ПО установлено."
  exit 0
fi

if [[ "$COMMAND" == "auth" ]]; then
  exec "$HERE/.venv/bin/python" "$HERE/browser-login.py" "$@"
fi
if [[ "$COMMAND" == "existing-auth" ]]; then
  exec "$HERE/.venv/bin/python" "$HERE/import-browser-session.py" "$@"
fi
if [[ "$COMMAND" == "convert-all" || "$COMMAND" == "build-custom" || "$COMMAND" == "verify-all" || "$COMMAND" == "install" || "$COMMAND" == "download-originals" ]]; then
  exec "$HERE/.venv/bin/python" "$HERE/voicepack_manager.py" "$COMMAND" "$@"
fi
exec "$HERE/.venv/bin/python" "$HERE/voicepack_cycle.py" "$COMMAND" "$@"
