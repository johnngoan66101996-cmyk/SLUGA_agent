# ==============================================================================
# Скрипт быстрого развертывания агента SLUGA на Windows
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "🚀 Развертывание автономного агента SLUGA (Windows)..." -ForegroundColor Cyan

# 1. Проверка Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python не найден в PATH. Установите Python 3.10+ с сайта python.org" -ForegroundColor Red
    exit 1
}

# 2. Создание виртуального окружения
if (-not (Test-Path ".venv")) {
    Write-Host "📦 Создание виртуального окружения .venv..." -ForegroundColor Yellow
    python -m venv .venv
}

# 3. Установка зависимостей
Write-Host "⬇️ Установка зависимостей из requirements.txt..." -ForegroundColor Yellow
& .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Проверка и запуск интерактивного мастера настройки
if (-not (Test-Path ".env")) {
    Write-Host "🧙 Запуск интерактивного мастера настройки..." -ForegroundColor Cyan
    & .venv\Scripts\python.exe wizard.py
} else {
    Write-Host "✅ Файл .env уже настроен." -ForegroundColor Green
    Write-Host "Для повторной настройки выполните: .venv\Scripts\python.exe wizard.py" -ForegroundColor Yellow
}

# 5. Папка данных
if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" | Out-Null
}

# 6. Регистрация глобальной команды 'sluga' в системе (как claude или hermes)
Write-Host "🔗 Регистрация глобальной команды 'sluga' в системе..." -ForegroundColor Yellow
$cmdContent = @"
@echo off
setlocal
"$PSScriptRoot\.venv\Scripts\python.exe" "$PSScriptRoot\main.py" %*
endlocal
"@
Set-Content -Path "$PSScriptRoot\sluga.cmd" -Value $cmdContent -Encoding ASCII

# Добавляем папку агента в User PATH, если еще не добавлено
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$PSScriptRoot*") {
    [Environment]::SetEnvironmentVariable("PATH", "$userPath;$PSScriptRoot", "User")
    $env:PATH += ";$PSScriptRoot"
}

# Копируем в WindowsApps для немедленной доступности в любых окнах терминала
$winApps = "$env:LOCALAPPDATA\Microsoft\WindowsApps"
if (Test-Path $winApps) {
    Set-Content -Path "$winApps\sluga.cmd" -Value $cmdContent -Encoding ASCII
}

Write-Host "✅ Развертывание завершено!" -ForegroundColor Green
Write-Host "`n🚀 ТЕПЕРЬ АГЕНТ ЗАПУСКАЕТСЯ ИЗ ЛЮБОЙ ПАПКИ КАК CLAUDE / HERMES:" -ForegroundColor Yellow
Write-Host "   sluga                   — запуск интерактивной консоли CLI" -ForegroundColor Green
Write-Host "   sluga `"задача`"          — выполнение разовой задачи" -ForegroundColor Green
Write-Host "   sluga bot               — запуск Telegram-демона" -ForegroundColor Green
Write-Host "   sluga doctor            — экспресс-диагностика проекта" -ForegroundColor Green
Write-Host "   sluga setup             — запуск мастера настройки" -ForegroundColor Green

