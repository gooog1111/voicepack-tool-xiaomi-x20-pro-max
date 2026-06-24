#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMAND="${1:-menu}"
if [[ $# -gt 0 ]]; then shift; fi

VENV_DIR="$HERE/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"

die() {
  echo "Ошибка: $*" >&2
  exit 1
}

info() {
  echo "[*] $*"
}

have() {
  command -v "$1" >/dev/null 2>&1
}

install_system_python() {
  info "Проверка системных Python-пакетов..."

  if have apt-get; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip curl
  elif have dnf; then
    sudo dnf install -y python3 python3-pip python3-virtualenv curl
  elif have pacman; then
    sudo pacman -S --needed python python-pip python-virtualenv curl
  elif have brew; then
    brew install python curl
  else
    die "Не найден поддерживаемый пакетный менеджер. Установите python3, venv, pip и curl вручную."
  fi
}

check_system_python() {
  if ! have python3; then
    [[ "$COMMAND" == "setup" ]] || die "Python 3 не найден. Сначала запустите: $0 setup"
    install_system_python
  fi

  python3 - <<'PY' || die "Python 3 запускается некорректно"
import sys
print("Python:", sys.version)
PY
}

venv_has_working_pip() {
  [[ -x "$PYTHON_BIN" ]] || return 1
  "$PYTHON_BIN" -m pip --version >/dev/null 2>&1
}

create_or_repair_venv() {
  check_system_python

  if [[ -x "$PYTHON_BIN" ]]; then
    if venv_has_working_pip; then
      info "venv найден, pip работает."
      return 0
    fi

    info "venv найден, но pip не работает. Пробую восстановить..."
    "$PYTHON_BIN" -m ensurepip --upgrade >/dev/null 2>&1 || true

    if venv_has_working_pip; then
      info "pip восстановлен через ensurepip."
      return 0
    fi

    info "venv повреждён. Пересоздаю $VENV_DIR..."
    rm -rf "$VENV_DIR"
  fi

  info "Создаю venv..."
  python3 -m venv "$VENV_DIR" || {
    info "Не удалось создать venv. Пробую установить системные зависимости..."
    install_system_python
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
  }

  [[ -x "$PYTHON_BIN" ]] || die "venv создан некорректно: нет $PYTHON_BIN"

  if ! venv_has_working_pip; then
    info "pip отсутствует в venv. Пробую ensurepip..."
    "$PYTHON_BIN" -m ensurepip --upgrade || true
  fi

  if ! venv_has_working_pip; then
    info "ensurepip не помог. Ставлю pip через get-pip.py..."
    have curl || install_system_python
    curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    "$PYTHON_BIN" /tmp/get-pip.py
  fi

  venv_has_working_pip || die "pip в venv всё ещё не работает"
  "$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel
}

install_system_tools() {
  if have ffmpeg && have ccrypt; then
    info "ffmpeg и ccrypt уже установлены."
    return 0
  fi

  info "Устанавливаю ffmpeg и ccrypt..."

  if have apt-get; then
    sudo apt-get update
    sudo apt-get install -y ffmpeg ccrypt
  elif have dnf; then
    sudo dnf install -y ffmpeg ccrypt
  elif have pacman; then
    sudo pacman -S --needed ffmpeg ccrypt
  elif have brew; then
    brew install ffmpeg ccrypt
  else
    die "Установите ffmpeg и ccrypt вручную."
  fi
}

show_menu() {
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
}

return_to_menu() {
  read -r -p 'Нажмите Enter для возврата в меню...'
  exec "$0" menu
}

if [[ -f "$HERE/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$HERE/.env"
  set +a
fi

if [[ "$COMMAND" == "menu" ]]; then
  show_menu
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
    *) die "Неизвестный пункт меню: $choice" ;;
  esac
fi

create_or_repair_venv

if [[ "$COMMAND" == "setup" ]]; then
  [[ -f "$HERE/requirements.txt" ]] || die "Не найден $HERE/requirements.txt"

  info "Устанавливаю Python-зависимости..."
  "$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel
  "$PYTHON_BIN" -m pip install -r "$HERE/requirements.txt"

  info "Устанавливаю Chromium для Playwright..."
  "$PYTHON_BIN" -m playwright install chromium

  install_system_tools

  echo "Необходимое ПО установлено."
  return_to_menu
fi

case "$COMMAND" in
  auth)
    "$PYTHON_BIN" "$HERE/browser-login.py" "$@"
    return_to_menu
    ;;
  existing-auth)
    "$PYTHON_BIN" "$HERE/import-browser-session.py" "$@"
    return_to_menu
    ;;
  convert-all|build-custom|verify-all|install|download-originals)
    "$PYTHON_BIN" "$HERE/voicepack_manager.py" "$COMMAND" "$@"
    return_to_menu
    ;;
  *)
    "$PYTHON_BIN" "$HERE/voicepack_cycle.py" "$COMMAND" "$@"
    return_to_menu
    ;;
esac
