# ==============================================================================
# SLUGA_agent: Универсальный онлайн-установщик для Windows PowerShell
# Запуск из любой папки одной командой:
# irm https://raw.githubusercontent.com/johnngoan66101996-cmyk/SLUGA_agent/main/install.ps1 | iex
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  🤖 УНИВЕРСАЛЬНЫЙ УСТАНОВЩИК SLUGA_agent (WINDOWS POWERSHELL)" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# 1. Проверка защищенных системных папок (System32, Windows)
$currentDir = Get-Location
$isSystemDir = $currentDir.Path -like "*Windows\System32*" -or $currentDir.Path -like "*\Windows"

Write-Host "`n📁 Выбор директории для установки агента:" -ForegroundColor Yellow
$opt1 = "C:\SLUGA_agent (Рекомендуется, корень диска C:)"
$opt2 = "$HOME\Desktop\SLUGA_agent (Рабочий стол)"
$opt3 = "$HOME\SLUGA_agent (Домашняя папка пользователя)"
$opt4 = "Ввести свой путь вручную"

Write-Host "  [1] $opt1" -ForegroundColor Green
Write-Host "  [2] $opt2"
Write-Host "  [3] $opt3"
Write-Host "  [4] $opt4"

$targetDir = "C:\SLUGA_agent"
$choice = Read-Host "`n> Выберите папку установки [1-4] (Enter = 1)"

if ($choice -eq "2") {
    $targetDir = "$HOME\Desktop\SLUGA_agent"
} elseif ($choice -eq "3") {
    $targetDir = "$HOME\SLUGA_agent"
} elseif ($choice -eq "4") {
    $custom = Read-Host "> Введите полный путь к папке"
    if ($custom.Trim()) { $targetDir = $custom.Trim() }
} else {
    $targetDir = "C:\SLUGA_agent"
}

Write-Host "`n🎯 Целевая папка установки: $targetDir" -ForegroundColor Cyan

# 2. Создание папки, если ее нет
if (-not (Test-Path $targetDir)) {
    Write-Host "📦 Создаю директорию $targetDir..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

# 3. Скачивание репозитория
Set-Location $targetDir

if (Get-Command git -ErrorAction SilentlyContinue) {
    if (-not (Test-Path "$targetDir\.git")) {
        Write-Host "⬇️ Клонирование репозитория SLUGA_agent..." -ForegroundColor Yellow
        git clone https://github.com/johnngoan66101996-cmyk/SLUGA_agent.git .
    } else {
        Write-Host "🔄 Репозиторий уже существует. Обновление (git pull)..." -ForegroundColor Yellow
        git pull origin main
    }
} else {
    Write-Host "⬇️ Git не найден. Скачивание ZIP-архива с GitHub..." -ForegroundColor Yellow
    $zipUrl = "https://github.com/johnngoan66101996-cmyk/SLUGA_agent/archive/refs/heads/main.zip"
    $zipFile = "$targetDir\sluga.zip"
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipFile
    Expand-Archive -Path $zipFile -DestinationPath "$targetDir\temp_extract" -Force
    Copy-Item -Path "$targetDir\temp_extract\SLUGA_agent-main\*" -Destination $targetDir -Recurse -Force
    Remove-Item -Path $zipFile -Force
    Remove-Item -Path "$targetDir\temp_extract" -Recurse -Force
}

# 4. Запуск скрипта подготовки окружения setup.ps1
Write-Host "`n🚀 Запуск настройки окружения и интерактивного мастера..." -ForegroundColor Green
if (Test-Path "$targetDir\setup.ps1") {
    & "$targetDir\setup.ps1"
} else {
    Write-Host "❌ Ошибка: setup.ps1 не найден в $targetDir" -ForegroundColor Red
}
