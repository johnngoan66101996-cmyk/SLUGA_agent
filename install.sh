#!/usr/bin/env bash
# ==============================================================================
# SLUGA_agent: Универсальный онлайн-установщик для Linux / macOS
# curl -fsSL https://raw.githubusercontent.com/johnngoan66101996-cmyk/SLUGA_agent/main/install.sh | bash
# ==============================================================================
set -e

echo "========================================================================"
echo "  🤖 УНИВЕРСАЛЬНЫЙ УСТАНОВЩИК SLUGA_agent (LINUX / VPS)"
echo "========================================================================"

TARGET_DIR="$HOME/SLUGA_agent"
echo "🎯 Установка в директорию: $TARGET_DIR"

mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

if command -v git &> /dev/null; then
    if [ ! -d ".git" ]; then
        echo "⬇️ Клонирование репозитория..."
        git clone https://github.com/johnngoan66101996-cmyk/SLUGA_agent.git .
    else
        echo "🔄 Обновление репозитория..."
        git pull origin main
    fi
else
    echo "⬇️ Скачивание архива с GitHub..."
    curl -fsSL https://github.com/johnngoan66101996-cmyk/SLUGA_agent/archive/refs/heads/main.tar.gz | tar -xz --strip-components=1
fi

chmod +x setup.sh
if [ -e /dev/tty ]; then
    ./setup.sh < /dev/tty
else
    ./setup.sh
fi
