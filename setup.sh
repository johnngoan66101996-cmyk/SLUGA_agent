#!/usr/bin/env bash
# ==============================================================================
# Скрипт быстрого развертывания агента SLUGA на Linux VPS
# ==============================================================================
set -e

echo "🚀 Начинаем развертывание SLUGA_agent..."

# 1. Проверка Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.10+ (например, apt update && apt install -y python3 python3-venv python3-pip)"
    exit 1
fi

# 2. Создание виртуального окружения
if [ ! -d ".venv" ]; then
    echo "📦 Создание виртуального окружения .venv..."
    python3 -m venv .venv
fi

# 3. Активация и установка зависимостей
echo "⬇️ Установка зависимостей из requirements.txt..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Проверка и запуск интерактивного мастера настройки
if [ ! -f ".env" ]; then
    echo "🧙 Запуск интерактивного мастера настройки..."
    python wizard.py
else
    echo "✅ Файл .env уже настроен. Для переконфигурации выполните: python wizard.py"
fi

# 5. Создание директории данных
mkdir -p data

echo "✅ Развертывание успешно завершено!"
echo "Для запуска в фоновом режиме Telegram-бота выполните:"
echo "   source .venv/bin/activate && python main.py bot"
echo "Или через Docker: docker compose up -d"
