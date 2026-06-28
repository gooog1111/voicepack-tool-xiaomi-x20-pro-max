param(
    [ValidateSet("menu", "setup", "existing-auth", "list-devices", "local-scan", "preflight", "convert-all", "build-custom", "verify-all", "install", "download-originals")]
    [string]$Command = "menu",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"

try {
    chcp 65001 > $null
    [Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
    $OutputEncoding = New-Object System.Text.UTF8Encoding $false
}
catch {
    # Кодировка консоли не критична для работы скрипта.
}

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $Here ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$EnvFile = Join-Path $Here ".env"
$RequirementsFile = Join-Path $Here "requirements.txt"
$RequirementsHashFile = Join-Path $Venv ".requirements.sha256"
$PlaywrightMarkerFile = Join-Path $Venv ".playwright.chromium.installed"

# Версия текущего пакета. Меняй при выпуске нового релиза.
# Значение должно совпадать с тегом GitHub Release, например: v1.0.0
$CurrentVersion = "v1.0.1-2"
$RepoUrl = "https://github.com/gooog1111/voicepack-tool-xiaomi-x20-pro-max"
$GitHubApiLatestRelease = "https://api.github.com/repos/gooog1111/voicepack-tool-xiaomi-x20-pro-max/releases/latest"

if (Test-Path $EnvFile) {
    Get-Content -LiteralPath $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $name, $value = $line.Split("=", 2)
            [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
        }
    }
}

function Get-FileSha256 {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return ""
    }

    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Get-CommandPath {
    param([Parameter(Mandatory = $true)]$CommandInfo)

    if ($CommandInfo.Source) {
        return $CommandInfo.Source
    }

    return $CommandInfo.Path
}

function Convert-VersionTagToComparableString {
    param([Parameter(Mandatory = $true)][string]$VersionTag)

    $normalized = $VersionTag.Trim()
    if ($normalized.StartsWith("v", [System.StringComparison]::OrdinalIgnoreCase)) {
        $normalized = $normalized.Substring(1)
    }

    return $normalized
}

function Test-NewVersionAvailable {
    try {
        $headers = @{
            "User-Agent" = "xiaomi-voicepack-tool"
            "Accept"     = "application/vnd.github+json"
        }

        $release = Invoke-RestMethod `
            -Uri $GitHubApiLatestRelease `
            -Headers $headers `
            -TimeoutSec 5 `
            -ErrorAction Stop

        $LatestVersion = [string]$release.tag_name
        if (-not $LatestVersion) {
            return
        }

        $latestComparable = Convert-VersionTagToComparableString $LatestVersion
        $currentComparable = Convert-VersionTagToComparableString $CurrentVersion

        $isNewer = $false
        try {
            $latestSemver = [version]$latestComparable
            $currentSemver = [version]$currentComparable
            $isNewer = $latestSemver -gt $currentSemver
        }
        catch {
            # Если тег не похож на SemVer, просто сравниваем строки.
            $isNewer = $LatestVersion -ne $CurrentVersion
        }

        if ($isNewer) {
            Write-Host ""
            Write-Host "Доступна новая версия: $LatestVersion" -ForegroundColor Yellow
            Write-Host "Текущая версия: $CurrentVersion" -ForegroundColor DarkGray
            Write-Host "Скачать: $RepoUrl/releases/latest" -ForegroundColor Cyan
            Write-Host ""
        }
    }
    catch {
        # Нет интернета, GitHub недоступен, release отсутствует или rate limit.
        # Проверка обновлений не критична, поэтому продолжаем без ошибки.
    }
}

function Ensure-PythonVenv {
    if (Test-Path -LiteralPath $Python) {
        return
    }

    $SystemPython = Get-Command python -ErrorAction SilentlyContinue
    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue

    if (-not $SystemPython -and -not $PyLauncher) {
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if (-not $winget) {
            throw "Python не найден, и winget недоступен. Установите Python 3.12 вручную или установите App Installer/winget."
        }

        Write-Host "Python не найден. Устанавливаю Python 3.12..." -ForegroundColor Yellow
        & (Get-CommandPath $winget) install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
        if ($LASTEXITCODE -ne 0) {
            throw "Не удалось установить Python через winget"
        }

        $SystemPython = Get-Command python -ErrorAction SilentlyContinue

        if (-not $SystemPython) {
            $candidate = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python" -Filter python.exe -Recurse -ErrorAction SilentlyContinue |
                Sort-Object FullName -Descending |
                Select-Object -First 1

            if ($candidate) {
                $SystemPython = $candidate
            }
        }

        $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    }

    Write-Host "Создаю виртуальное окружение .venv..." -ForegroundColor Yellow

    if ($SystemPython) {
        & (Get-CommandPath $SystemPython) -m venv $Venv
    }
    elseif ($PyLauncher) {
        & (Get-CommandPath $PyLauncher) -3 -m venv $Venv
    }
    else {
        throw "Python установлен, но не найден в PATH. Закройте и снова откройте PowerShell, затем запустите скрипт повторно."
    }

    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $Python)) {
        throw "Не удалось создать виртуальное окружение"
    }
}

function Ensure-PythonRequirements {
    if (-not (Test-Path -LiteralPath $RequirementsFile)) {
        throw "Не найден requirements.txt: $RequirementsFile"
    }

    $CurrentHash = Get-FileSha256 $RequirementsFile
    $SavedHash = ""

    if (Test-Path -LiteralPath $RequirementsHashFile) {
        $SavedHash = (Get-Content -LiteralPath $RequirementsHashFile -Raw).Trim()
    }

    if ($CurrentHash -eq $SavedHash) {
        return
    }

    Write-Host "Обновляю Python-зависимости из requirements.txt..." -ForegroundColor Yellow

    & $Python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "pip upgrade failed"
    }

    & $Python -m pip install -r $RequirementsFile
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed"
    }

    Set-Content -LiteralPath $RequirementsHashFile -Value $CurrentHash -Encoding ASCII
}

function Test-PythonModule {
    param([Parameter(Mandatory = $true)][string]$ModuleName)

    & $Python -c "import $ModuleName" 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Ensure-PlaywrightChromium {
    $NeedInstall = $false

    if (-not (Test-PythonModule "playwright")) {
        return
    }

    if (-not (Test-Path -LiteralPath $PlaywrightMarkerFile)) {
        $NeedInstall = $true
    }
    else {
        & $Python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); p.chromium.launch(headless=True).close(); p.stop()" 2>$null
        if ($LASTEXITCODE -ne 0) {
            $NeedInstall = $true
        }
    }

    if ($NeedInstall) {
        Write-Host "Проверяю/устанавливаю Chromium для Playwright..." -ForegroundColor Yellow
        & $Python -m playwright install chromium
        if ($LASTEXITCODE -ne 0) {
            throw "Playwright Chromium installation failed"
        }
        Set-Content -LiteralPath $PlaywrightMarkerFile -Value (Get-Date).ToString("s") -Encoding ASCII
    }
}

function Ensure-Ffmpeg {
    if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
        return
    }

    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Warning "ffmpeg не найден, а winget недоступен. Если конвертация аудио не работает, установите ffmpeg вручную."
        return
    }

    Write-Host "ffmpeg не найден. Устанавливаю ffmpeg..." -ForegroundColor Yellow
    & (Get-CommandPath $winget) install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "ffmpeg installation failed"
    }
}

function Ensure-Environment {
    Ensure-PythonVenv
    Ensure-PythonRequirements
    Ensure-PlaywrightChromium
    Ensure-Ffmpeg
}

function Show-Menu {
    Write-Host ""
    Write-Host "Xiaomi Voice Pack Tool" -ForegroundColor Cyan
    Write-Host "=================" -ForegroundColor Cyan
    Write-Host "Version: $CurrentVersion" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "1. Подготовить авторизацию и DID автоматически"
    Write-Host "2. Найти DID в локальной сети UDP 54321"
    Write-Host "3. Предварительная проверка устройства"
    Write-Host "4. Конвертировать все старые пакеты из папки old_voicepacks"
    Write-Host "5. Собрать новый кастомный войспак из папки custom_voicepack"
    Write-Host "6. Проверить новые войспаки из папки ready_voicepacks"
    Write-Host "7. Установить войспак из списка ready_voicepacks"
    Write-Host "8. Скачать оригинальные пакеты d109gl/d102gl на всех языках"
    Write-Host "9. Выход"
    Write-Host ""
}

function Return-ToMenu {
    Write-Host ""
    Read-Host "Нажмите Enter для возврата в меню"
    & $PSCommandPath menu
}

if ($Command -eq "menu") {
    Test-NewVersionAvailable
    Show-Menu
    $choice = Read-Host "Выберите действие"
    $selectedCommand = switch ($choice) {
        "1" { "setup" }
        "2" { "local-scan" }
        "3" { "preflight" }
        "4" { "convert-all" }
        "5" { "build-custom" }
        "6" { "verify-all" }
        "7" { "install" }
        "8" { "download-originals" }
        "9" { exit 0 }
        default {
            Write-Error "Неизвестный пункт меню: $choice"
            exit 2
        }
    }
    $Command = $selectedCommand
    if ($choice -eq "2" -and (-not $ExtraArgs -or $ExtraArgs.Count -eq 0)) {
        $ExtraArgs = @("--direct-scan", "--save-did")
    }
}

Ensure-Environment

if ($Command -eq "setup") {
    $CloudAuthFile = Join-Path $Here "state\cloud_auth.json"
    Write-Host ""
    Write-Host "Шаг 1/2: импортирую Xiaomi-сессию из браузера..." -ForegroundColor Cyan
    & $Python (Join-Path $Here "import-browser-session.py") --output $CloudAuthFile
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        Return-ToMenu
        exit $code
    }

    Write-Host ""
    Write-Host "Шаг 2/2: ищу DID и проверяю доступ к устройству..." -ForegroundColor Cyan
    $SetupArgs = @("--direct-scan", "--save-did")
    if ($ExtraArgs) {
        $SetupArgs += $ExtraArgs
    }
    & $Python (Join-Path $Here "voicepack_cycle.py") preflight @SetupArgs
    $code = $LASTEXITCODE
    Return-ToMenu
    exit $code
}

if ($Command -eq "existing-auth") {
    & $Python (Join-Path $Here "import-browser-session.py") @ExtraArgs
    $code = $LASTEXITCODE
    Return-ToMenu
    exit $code
}

if ($Command -in @("convert-all", "build-custom", "verify-all", "install", "download-originals")) {
    & $Python (Join-Path $Here "voicepack_manager.py") $Command @ExtraArgs
    $code = $LASTEXITCODE
    Return-ToMenu
    exit $code
}

& $Python (Join-Path $Here "voicepack_cycle.py") $Command @ExtraArgs
$code = $LASTEXITCODE
Return-ToMenu
exit $code
