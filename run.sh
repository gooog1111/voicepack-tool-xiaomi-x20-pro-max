#!/usr/bin/env bash
set -Eeuo pipefail

COMMAND="${1:-menu}"
if [[ $# -gt 0 ]]; then
  shift
fi
EXTRA_ARGS=("$@")

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HERE/.venv"
PYTHON="$VENV/bin/python"
ENV_FILE="$HERE/.env"
REQUIREMENTS_FILE="$HERE/requirements.txt"
REQUIREMENTS_HASH_FILE="$VENV/.requirements.sha256"
PLAYWRIGHT_MARKER_FILE="$VENV/.playwright.chromium.installed"
CURRENT_VERSION="v1.0.4-1"
REPO_URL="https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max"
GITHUB_API_LATEST_RELEASE="https://api.github.com/repos/gooog1111/voicepack-tool-xiaomi-x20-pro-max/releases/latest"

info() { printf '\033[36m%s\033[0m\n' "$*"; }
warn() { printf '\033[33m%s\033[0m\n' "$*" >&2; }
die() { printf '\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

load_env_file() {
  [[ -f "$ENV_FILE" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "$line" || "$line" == \#* || "$line" != *=* ]] && continue
    local name="${line%%=*}"
    local value="${line#*=}"
    name="${name//[[:space:]]/}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    export "$name=$value"
  done < "$ENV_FILE"
}

file_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

ensure_python_venv() {
  [[ -x "$PYTHON" ]] && return 0
  local system_python=""
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      system_python="$(command -v "$candidate")"
      break
    fi
  done
  [[ -n "$system_python" ]] || die "Python 3 не найден. Установите python3 и python3-venv."
  info "Создаю виртуальное окружение .venv..."
  "$system_python" -m venv "$VENV" || die "Не удалось создать .venv. На Debian/Ubuntu установите python3-venv."
  [[ -x "$PYTHON" ]] || die "Python в .venv не найден после создания окружения."
}

ensure_python_requirements() {
  [[ -f "$REQUIREMENTS_FILE" ]] || die "Не найден requirements.txt: $REQUIREMENTS_FILE"
  local current_hash saved_hash=""
  current_hash="$(file_sha256 "$REQUIREMENTS_FILE")"
  [[ -f "$REQUIREMENTS_HASH_FILE" ]] && saved_hash="$(<"$REQUIREMENTS_HASH_FILE")"
  [[ "$current_hash" == "$saved_hash" ]] && return 0

  info "Обновляю Python-зависимости из requirements.txt..."
  "$PYTHON" -m pip install --upgrade pip
  "$PYTHON" -m pip install -r "$REQUIREMENTS_FILE"
  printf '%s\n' "$current_hash" > "$REQUIREMENTS_HASH_FILE"
}

python_has_module() {
  "$PYTHON" -c "import $1" >/dev/null 2>&1
}

ensure_playwright_chromium() {
  python_has_module playwright || return 0
  local need_install=0
  [[ -f "$PLAYWRIGHT_MARKER_FILE" ]] || need_install=1
  if [[ "$need_install" -eq 0 ]]; then
    "$PYTHON" -c 'from playwright.sync_api import sync_playwright; p=sync_playwright().start(); p.chromium.launch(headless=True).close(); p.stop()' >/dev/null 2>&1 || need_install=1
  fi
  if [[ "$need_install" -eq 1 ]]; then
    info "Проверяю/устанавливаю Chromium для Playwright..."
    "$PYTHON" -m playwright install chromium
    date -Is > "$PLAYWRIGHT_MARKER_FILE"
  fi
}

ensure_optional_tools() {
  command -v ffmpeg >/dev/null 2>&1 || warn "ffmpeg не найден. Сборка/нормализация аудио не заработает, пока вы не установите ffmpeg."
  if ! command -v 7z >/dev/null 2>&1 && ! command -v unrar >/dev/null 2>&1 && ! command -v unar >/dev/null 2>&1 && ! command -v bsdtar >/dev/null 2>&1; then
    warn "Не найден 7z/unrar/unar/bsdtar. Распаковка RAR может не работать."
  fi
}

ensure_environment() {
  ensure_python_venv
  ensure_python_requirements
  if [[ "$COMMAND" == "setup" || "$COMMAND" == "existing-auth" ]]; then
    ensure_playwright_chromium
  fi
  ensure_optional_tools
}

test_new_version_available() {
  command -v curl >/dev/null 2>&1 || return 0
  local latest
  latest="$(curl -fsSL -H 'User-Agent: xiaomi-voicepack-tool' -H 'Accept: application/vnd.github+json' "$GITHUB_API_LATEST_RELEASE" 2>/dev/null | "$PYTHON" -c 'import json,sys; print((json.load(sys.stdin) or {}).get("tag_name",""))' 2>/dev/null || true)"
  [[ -z "$latest" || "$latest" == "$CURRENT_VERSION" ]] && return 0
  printf '\n'
  warn "Доступна новая версия: $latest"
  warn "Текущая версия: $CURRENT_VERSION"
  printf 'Скачать: %s/releases/latest\n\n' "$REPO_URL"
}

show_menu() {
  printf '\n'
  info "Xiaomi Voice Pack Tool"
  info "======================"
  printf 'Version: %s\n\n' "$CURRENT_VERSION"
  cat <<'MENU'
1. Подготовить авторизацию и DID автоматически
2. Построить карту домов и устройств
3. Показать совместимые модели Xiaomi
4. Предварительная проверка устройства
5. Конвертировать все старые пакеты из папки old_voicepacks
6. Собрать новый кастомный ZIP для X20/Xiaomi Cloud
7. Собрать legacy PKG для Xiaomi/Roborock v1/S5
8. Установить legacy PKG через python-miio
9. Проверить новые ZIP-войспаки из папки ready_voicepacks
10. Установить ZIP-войспак одним циклом
11. Скачать оригинальные пакеты d109gl/d102gl на всех языках
12. Загрузить ZIP в Xiaomi Cloud без установки
13. Установить уже загруженный ZIP удалённо
14. Выход

MENU
}

return_to_menu() {
  if [[ ! -t 0 ]]; then
    return 0
  fi
  printf '\n'
  read -r -p "Нажмите Enter для возврата в меню" _
  exec "$HERE/run.sh" menu
}

run_python() {
  "$PYTHON" "$@"
}

load_env_file

if [[ "$COMMAND" == "menu" ]]; then
  ensure_python_venv
  test_new_version_available
  show_menu
  read -r -p "Выберите действие: " choice
  case "$choice" in
    1) COMMAND="setup" ;;
    2) COMMAND="search-homes-devices" ;;
    3) COMMAND="compatible-models" ;;
    4) COMMAND="preflight" ;;
    5) COMMAND="convert-all" ;;
    6) COMMAND="build-custom" ;;
    7) COMMAND="build-legacy-pkg" ;;
    8) COMMAND="install-legacy-pkg" ;;
    9) COMMAND="verify-all" ;;
    10) COMMAND="install" ;;
    11) COMMAND="download-originals" ;;
    12) COMMAND="upload" ;;
    13) COMMAND="remote-install" ;;
    14) exit 0 ;;
    *) die "Неизвестный пункт меню: $choice" ;;
  esac
fi

case "$COMMAND" in
  menu|setup|existing-auth|search-homes-devices|compatible-models|list-devices|local-scan|preflight|convert-all|build-custom|build-legacy-pkg|install-legacy-pkg|verify-all|install|download-originals|upload|remote-install|deploy|all|download|build|verify)
    ;;
  *)
    die "Неизвестная команда: $COMMAND"
    ;;
esac

ensure_environment

case "$COMMAND" in
  setup)
    cloud_auth_file="$HERE/state/cloud_auth.json"
    info "Шаг 1/3: импортирую Xiaomi-сессию из браузера..."
    if ! run_python "$HERE/import-browser-session.py" --output "$cloud_auth_file"; then
      warn "Импорт из браузера не получился. Запускаю QR-авторизацию Xiaomi..."
      run_python "$HERE/xiaomi-qr-auth.py" --output "$cloud_auth_file"
    fi

    info "Шаг 2/3: строю карту домов и устройств..."
    run_python "$HERE/search-homes-devices.py" "${EXTRA_ARGS[@]}"

    info "Шаг 3/3: выбираю DID и проверяю доступ к устройству..."
    run_python "$HERE/voicepack_cycle.py" preflight --save-did --did= --model= --device-name= --device-ip= "${EXTRA_ARGS[@]}"
    return_to_menu
    ;;
  search-homes-devices)
    run_python "$HERE/search-homes-devices.py" "${EXTRA_ARGS[@]}"
    return_to_menu
    ;;
  compatible-models)
    run_python "$HERE/search-homes-devices.py" --compatible-models "${EXTRA_ARGS[@]}"
    return_to_menu
    ;;
  existing-auth)
    run_python "$HERE/import-browser-session.py" "${EXTRA_ARGS[@]}"
    return_to_menu
    ;;
  convert-all|build-custom|build-legacy-pkg|verify-all|install|download-originals)
    run_python "$HERE/voicepack_manager.py" "$COMMAND" "${EXTRA_ARGS[@]}"
    return_to_menu
    ;;
  install-legacy-pkg)
    run_python "$HERE/install_legacy_pkg.py" "${EXTRA_ARGS[@]}"
    return_to_menu
    ;;
  *)
    run_python "$HERE/voicepack_cycle.py" "$COMMAND" "${EXTRA_ARGS[@]}"
    return_to_menu
    ;;
esac
