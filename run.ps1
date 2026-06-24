param(
    [ValidateSet("menu", "setup", "auth", "existing-auth", "preflight", "convert-all", "build-custom", "verify-all", "install", "download-originals")]
    [string]$Command = "menu",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $Here ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$EnvFile = Join-Path $Here ".env"

if (Test-Path $EnvFile) {
    Get-Content -LiteralPath $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $name, $value = $line.Split("=", 2)
            [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
        }
    }
}

function Show-Menu {
    Write-Host ""
    Write-Host "Xiaomi Voice Pack" -ForegroundColor Cyan
    Write-Host "=================" -ForegroundColor Cyan
    Write-Host "1. Установить необходимое ПО"
    Write-Host "2. Авторизация Xiaomi во временном браузере"
    Write-Host "3. Импорт действующей Xiaomi-сессии из установленного браузера"
    Write-Host "4. Предварительная проверка устройства"
    Write-Host "5. Конвертировать все старые пакеты из папки old_voicepacks"
    Write-Host "6. Собрать новый кастомный войспак из папки custom_voicepack"
    Write-Host "7. Проверить новые войспаки из папки ready_voicepacks"
    Write-Host "8. Установить войспак из списка ready_voicepacks"
    Write-Host "9. Скачать оригинальные пакеты d109gl/d102gl на всех языках"
    Write-Host "10. Выход"
    Write-Host ""
}

function Return-ToMenu {
    Write-Host ""
    Read-Host "Нажмите Enter для возврата в меню"
    & $PSCommandPath menu
}

if ($Command -eq "menu") {
    Show-Menu
    $choice = Read-Host "Выберите действие"
    $selectedCommand = switch ($choice) {
        "1" { "setup" }
        "2" { "auth" }
        "3" { "existing-auth" }
        "4" { "preflight" }
        "5" { "convert-all" }
        "6" { "build-custom" }
        "7" { "verify-all" }
        "8" { "install" }
        "9" { "download-originals" }
        "10" { exit 0 }
        default {
            Write-Error "Неизвестный пункт меню: $choice"
            exit 2
        }
    }
    $Command = $selectedCommand
}

if (-not (Test-Path $Python)) {
    $SystemPython = Get-Command python -ErrorAction SilentlyContinue
    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $SystemPython -and -not $PyLauncher -and $Command -eq "setup") {
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if (-not $winget) { throw "Python не найден, и winget недоступен" }
        & $winget.Source install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
        if ($LASTEXITCODE -ne 0) { throw "Не удалось установить Python" }
        $candidate = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python" -Filter python.exe -Recurse -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($candidate) { $SystemPython = $candidate }
    }
    if ($SystemPython) {
        $SystemPythonPath = if ($SystemPython.Source) { $SystemPython.Source } else { $SystemPython.FullName }
        & $SystemPythonPath -m venv $Venv
    }
    elseif ($PyLauncher) {
        & $PyLauncher.Source -3 -m venv $Venv
    }
    else {
        throw "Python 3 не найден. Сначала выберите пункт 1."
    }
}

if ($Command -eq "setup") {
    & $Python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
    & $Python -m pip install -r (Join-Path $Here "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
    & $Python -m playwright install chromium
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if (-not $winget) { throw "ffmpeg not found and winget is unavailable" }
        & $winget.Source install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
        if ($LASTEXITCODE -ne 0) { throw "ffmpeg installation failed" }
    }
    Write-Host "Необходимое ПО установлено." -ForegroundColor Green
    Return-ToMenu
    exit 0
}

if ($Command -eq "auth") {
    & $Python (Join-Path $Here "browser-login.py") @ExtraArgs
    Return-ToMenu
    exit $LASTEXITCODE
}

if ($Command -eq "existing-auth") {
    & $Python (Join-Path $Here "import-browser-session.py") @ExtraArgs
    Return-ToMenu
    exit $LASTEXITCODE
}

if ($Command -in @("convert-all", "build-custom", "verify-all", "install", "download-originals")) {
    & $Python (Join-Path $Here "voicepack_manager.py") $Command @ExtraArgs
    Return-ToMenu
    exit $LASTEXITCODE
}

& $Python (Join-Path $Here "voicepack_cycle.py") $Command @ExtraArgs
Return-ToMenu
exit $LASTEXITCODE
