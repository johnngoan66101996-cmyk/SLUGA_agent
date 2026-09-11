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

Write-Host "✅ Развертывание завершено!" -ForegroundColor Green
Write-Host "Для запуска в режиме консоли:   .venv\Scripts\python.exe main.py cli" -ForegroundColor Cyan
Write-Host "Для запуска Telegram-демона:    .venv\Scripts\python.exe main.py bot" -ForegroundColor Cyan
