#!/usr/bin/env bash
# ==============================================================================
# Скрипт быстрого развертывания агента SLUGA на Linux VPS
# ==============================================================================
set -e

echo "🚀 Начинаем развертывание SLUGA_agent..."

# 1. Проверка Python 3 и автоматическая установка зависимостей при наличии apt
if ! command -v python3 &> /dev/null || ! python3 -m venv --help &> /dev/null; then
    if command -v apt &> /dev/null; then
        echo "📦 Доустановка Python3, venv и pip через apt..."
        if [ "$EUID" -eq 0 ]; then
            apt update -qq && apt install -y python3 python3-venv python3-pip git curl
        elif command -v sudo &> /dev/null; then
            sudo apt update -qq && sudo apt install -y python3 python3-venv python3-pip git curl
        fi
    fi
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.10+ (apt update && apt install -y python3 python3-venv python3-pip)"
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
    if [ -e /dev/tty ]; then
        python wizard.py < /dev/tty
    else
        python wizard.py
    fi
else
    echo "✅ Файл .env уже настроен. Для переконфигурации выполните: python wizard.py"
fi

# 5. Создание директории данных
mkdir -p data

# 6. Регистрация глобальной команды 'sluga' (как claude или hermes)
echo "🔗 Регистрация глобальной команды 'sluga' в системе..."
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
CURRENT_DIR="$(pwd)"

cat << EOF > "$BIN_DIR/sluga"
#!/usr/bin/env bash
"$CURRENT_DIR/.venv/bin/python" "$CURRENT_DIR/main.py" "\$@"
EOF
chmod +x "$BIN_DIR/sluga"

# 7. Автоматический запуск фонового демона 24/7
echo ""
echo "🚀 Запуск автономного демона SLUGA 24/7..."
"$CURRENT_DIR/.venv/bin/python" "$CURRENT_DIR/main.py" start

echo ""
echo "✅ Развертывание успешно завершено!"
echo "💡 Демон работает в фоне. Теперь можно закрывать терминал или отключать SSH."
echo ""
echo "Команды управления:"
echo "   sluga status            — статус демона (работает/остановлен, PID, логи)"
echo "   sluga stop              — остановка фонового демона"
echo "   sluga restart           — перезапуск фонового демона"
echo "   sluga logs              — просмотр свежих логов"
echo "   sluga start             — запуск демона"
echo "   sluga                   — запуск демона или статус"
echo "   sluga cli               — запуск интерактивной консоли CLI"
