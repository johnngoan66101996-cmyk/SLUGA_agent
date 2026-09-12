#!/usr/bin/env bash
# ==============================================================================
# SLUGA_agent: Онлайн-деинсталлятор для Linux / VPS
# Запуск одной командой:
# curl -fsSL https://raw.githubusercontent.com/johnngoan66101996-cmyk/SLUGA_agent/main/uninstall.sh | bash
# ==============================================================================

echo "========================================================================"
echo "  🗑️ ДЕИНСТАЛЛЯЦИЯ АВТОНОМНОГО АГЕНТА SLUGA (LINUX / VPS)"
echo "========================================================================"

TARGET_DIR="${1:-$HOME/SLUGA_agent}"

if [ ! -d "$TARGET_DIR" ]; then
    echo "⚠️ Директория $TARGET_DIR не найдена. Возможно, агент уже удален."
    exit 0
fi

echo "⚠️ ВНИМАНИЕ: Будет полностью удалена папка:"
echo "   $TARGET_DIR"
echo "   (Включая виртуальное окружение .venv, базу данных SQLite и конфигурацию .env)"
read -p "Подтвердите удаление [y/N]: " confirm
case "$confirm" in
    [yY][eE][sS]|[yY]|[дД])
        ;;
    *)
        echo "❌ Деинсталляция отменена."
        exit 0
        ;;
esac

echo "🛑 Остановка запущенных процессов и контейнеров..."
# Если использовался Docker Compose
if [ -f "$TARGET_DIR/docker-compose.yml" ] && command -v docker &> /dev/null; then
    cd "$TARGET_DIR" && docker compose down -v --rmi all 2>/dev/null || true
fi

# Остановка нативных процессов python main.py
pkill -f "python.*main.py" 2>/dev/null || true
sleep 1

echo "🧹 Удаление файлов и виртуального окружения..."
rm -rf "$TARGET_DIR"

echo "✅ Агент SLUGA успешно и полностью удален с системы!"
