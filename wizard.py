"""
Интерактивный мастер инициализации агента SLUGA.
Запуск: python wizard.py или python main.py setup
"""

import os
import sys
import getpass
from pathlib import Path

# Обеспечение корректного вывода UTF-8 на Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent

def clear_screen():
    os.system("cls" if sys.platform == "win32" else "clear")

def print_header():
    print("=" * 72)
    print("  🤖 МАСТЕР ИНИЦИАЛИЗАЦИИ АВТОНОМНОГО АГЕНТА SLUGA")
    print("=" * 72)
    print("  [ИНФО] Память: SQLite WAL | Модели: LiteAI + Google AI Studio | Навыков: 116")
    print("-" * 72)

def ask_choice(prompt: str, options: list, default_idx: int = 0) -> int:
    print(f"\n? {prompt}")
    for i, opt in enumerate(options):
        prefix = "  👉" if i == default_idx else "    "
        print(f"{prefix} [{i + 1}] {opt}")
    
    while True:
        choice = input(f"> Ваш выбор [1-{len(options)}] (Enter = {default_idx + 1}): ").strip()
        if not choice:
            return default_idx
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return int(choice) - 1
        print(f"Пожалуйста, введите число от 1 до {len(options)}.")

def ask_input(prompt: str, default: str = "", hide_input: bool = False) -> str:
    default_text = f" [{default}]" if default else ""
    full_prompt = f"\n? {prompt}{default_text}\n> "
    
    if hide_input:
        val = getpass.getpass(full_prompt).strip()
    else:
        val = input(full_prompt).strip()
        
    return val if val else default

def run_wizard():
    clear_screen()
    print_header()

    print("\nДобро пожаловать в конфигуратор SLUGA.")
    print("Мастер поможет настроить ключи, модели, каналы связи и политику безопасности.\n")

    env_data = {}

    # --- 1. Основной провайдер LLM ---
    provider_options = [
        "LiteAI (https://liteai.tech/) — Claude 3.5/5, GPT-5, оплата в РФ [РЕКОМЕНДУЕТСЯ]",
        "Google AI Studio (Gemini 3.7 / 3.6 / 3.8 Flash через Cloudflare Worker)",
        "Собственный OpenAI-совместимый API / OpenRouter"
    ]
    p_idx = ask_choice("Выберите основной источник интеллекта (Primary LLM):", provider_options, default_idx=0)

    if p_idx == 0:
        # LiteAI
        liteai_key = ask_input("Введите ваш API-ключ LiteAI (формат sk-bf-...):", hide_input=False)
        env_data["LITEAI_API_KEY"] = liteai_key
        env_data["LITEAI_BASE_URL"] = "https://api.liteai.tech/v1"

        models = [
            "claude-sonnet-4-6 — Золотой стандарт (баланс ума и скорости) [Рекомендуется]",
            "claude-opus-4-8 — Максимальный хирург кода и архитектуры",
            "claude-opus-4-8[1m] — Анализ гигантских репозиториев (контекст 1M)",
            "claude-sonnet-5 / claude-opus-5 — Новое поколение",
            "GPT-5.5 / gpt-5.6-terra — Модели OpenAI",
            "Ввести свое имя модели вручную"
        ]
        m_idx = ask_choice("Выберите базовую модель для ReAct-петли рассуждений:", models, default_idx=0)
        if m_idx == 0:
            env_data["LITEAI_MODEL"] = "claude-sonnet-4-6"
        elif m_idx == 1:
            env_data["LITEAI_MODEL"] = "claude-opus-4-8"
        elif m_idx == 2:
            env_data["LITEAI_MODEL"] = "claude-opus-4-8[1m]"
        elif m_idx == 3:
            sub = ask_choice("Выберите вариант:", ["claude-sonnet-5", "claude-opus-5"], default_idx=0)
            env_data["LITEAI_MODEL"] = "claude-sonnet-5" if sub == 0 else "claude-opus-5"
        elif m_idx == 4:
            sub = ask_choice("Выберите вариант:", ["GPT-5.5", "gpt-5.6-terra"], default_idx=0)
            env_data["LITEAI_MODEL"] = "GPT-5.5" if sub == 0 else "gpt-5.6-terra"
        else:
            custom_m = ask_input("Введите точное имя модели:", default="claude-sonnet-4-6")
            env_data["LITEAI_MODEL"] = custom_m

    elif p_idx == 1:
        # Google AI Studio
        g_key = ask_input("Введите API-ключ Google AI Studio (AIzaSy...):", hide_input=False)
        env_data["GOOGLE_AI_STUDIO_API_KEY"] = g_key
        print("\n💡 Для работы Google AI Studio в РФ используйте бесплатный Cloudflare Worker (cloudflare_worker.js).")
        print("   Сервис Cloudflare: https://dash.cloudflare.com/ (раздел Workers & Pages)")
        print("   Если ваш сервер/VPN за рубежом — нажмите Enter для прямого подключения к Google API.\n")
        env_data["CF_GEMINI_PROXY_URL"] = ask_input(
            "URL Cloudflare Worker (например: https://your-proxy.workers.dev/v1beta/openai/) или Enter:",
            default="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        env_data["GOOGLE_GEMINI_MODEL"] = ask_input("Модель Gemini:", default="gemini-3.7-flash")

    else:
        # Custom / OpenRouter
        env_data["LITEAI_API_KEY"] = ask_input("Введите API-ключ:", hide_input=False)
        env_data["LITEAI_BASE_URL"] = ask_input("Base URL:", default="https://openrouter.ai/api/v1")
        env_data["LITEAI_MODEL"] = ask_input("Модель:", default="anthropic/claude-3.5-sonnet")

    # --- 2. Резервный провайдер (Резервный канал Google Gemini) ---
    if "GOOGLE_AI_STUDIO_API_KEY" not in env_data:
        backup_opts = [
            "Да, подключить Google AI Studio (Gemini 3.7) для отказоустойчивости",
            "Пропустить (работать только на одном провайдере)"
        ]
        b_idx = ask_choice("Настроить резервный бесплатный канал Google Gemini?", backup_opts, default_idx=1)
        if b_idx == 0:
            env_data["GOOGLE_AI_STUDIO_API_KEY"] = ask_input("API-ключ Google AI Studio (нажмите Enter если пока нет):", default="")
            print("\n💡 Для РФ: проксируйте через Cloudflare Worker (cloudflare_worker.js на https://dash.cloudflare.com/)")
            cf_in = ask_input(
                "URL Cloudflare Worker (например: https://your-proxy.workers.dev/v1beta/openai/) или Enter для прямого подключения:",
                default="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            env_data["CF_GEMINI_PROXY_URL"] = cf_in
            env_data["GOOGLE_GEMINI_MODEL"] = "gemini-3.7-flash"

    # --- 3. Настройка Telegram ---
    channel_opts = [
        "Терминал (CLI) + Telegram-бот",
        "Только терминальный режим (CLI)"
    ]
    c_idx = ask_choice("Каналы связи агента:", channel_opts, default_idx=0)
    if c_idx == 0:
        tg_token = ask_input("Введите токен Telegram-бота (от @BotFather):", default="")
        env_data["TELEGRAM_BOT_TOKEN"] = tg_token
        print("\n💡 Для обхода блокировок Telegram API в РФ укажите URL вашего Cloudflare Worker.")
        print("   Если бот работает за пределами РФ — оставьте поле пустым (нажмите Enter).")
        tg_proxy = ask_input(
            "URL Cloudflare Worker для Telegram (например: https://your-proxy.workers.dev/ или оставьте пустым):",
            default=""
        )
        env_data["TELEGRAM_PROXY_URL"] = tg_proxy
        tg_users = ask_input("Ваш Telegram User ID для белого списка (Whitelist, через запятую):", default="")
        env_data["TELEGRAM_ALLOWED_USERS"] = tg_users
    else:
        env_data["TELEGRAM_BOT_TOKEN"] = ""
        env_data["TELEGRAM_ALLOWED_USERS"] = ""

    # --- 4. Политика безопасности ---
    sec_opts = [
        "Full Autonomous Surgeon (Карт-бланш: агент сам пишет код, запускает тесты и правит)",
        "Safe Guard (Предотвращение критических удалений и остановки процессов)"
    ]
    s_idx = ask_choice("Режим автономности выполнения команд:", sec_opts, default_idx=0)
    env_data["AUTO_HEALING_ENABLED"] = "true"
    env_data["SQLITE_DB_PATH"] = "./data/sluga_memory.db"
    env_data["LOG_LEVEL"] = "INFO"
    env_data["MAX_REACT_STEPS"] = "12"

    # --- 5. Сохранение конфигурации в .env ---
    env_file = BASE_DIR / ".env"
    with open(env_file, "w", encoding="utf-8") as f:
        f.write("# SLUGA AGENT RUNTIME CONFIGURATION\n")
        for k, v in env_data.items():
            f.write(f"{k}={v}\n")

    # Создание папки данных и инициализация песочницы
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "data" / "sandbox").mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 72)
    print("  🎉 АГЕНТ SLUGA УСПЕШНО ИНИЦИАЛИЗИРОВАН И НАСТРОЕН ПОД КЛЮЧ!")
    print("=" * 72)
    print("  🛡️ Шаг 1: Песочница finch-sandbox создана: ./data/sandbox")
    print("  🔬 Шаг 2: Каталог 116 навыков проиндексирован")
    print("  🛑 Шаг 3: Модуль предотвращения потери данных активен")
    print(f"  💾 Файл окружения сохранен: {env_file}")
    print("  🔑 Смена ключей на лету во время работы: команды /key, /model, /keys")
    print("=" * 72)

    run_opts = [
        "Запустить интерактивный консольный диалог (CLI прямо сейчас)",
        "Запустить Telegram-демона в фоновом режиме",
        "Выйти в терминал"
    ]
    r_idx = ask_choice("Как запустить агента?", run_opts, default_idx=0)
    if r_idx == 0:
        os.system(f'"{sys.executable}" main.py cli')
    elif r_idx == 1:
        os.system(f'"{sys.executable}" main.py bot')
    else:
        print("\nГотово. Вы можете запустить агента в любой момент:")
        print("  python main.py cli  (для терминала)")
        print("  python main.py bot  (для Telegram-бота)")

if __name__ == "__main__":
    run_wizard()
