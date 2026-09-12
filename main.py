"""
Главная точка входа автономного агента SLUGA.
Поддерживает два режима работы:
1. Автономный демон Telegram: `python main.py` или `python main.py bot`
2. Прямой терминальный CLI-режим: `python main.py cli`
"""

from __future__ import annotations

import sys
import asyncio
import logging

# Обеспечение корректного вывода UTF-8 (включая эмодзи) на Windows-терминалах
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import settings

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SLUGA_MAIN")

def mask_key(k: str) -> str:
    if not k:
        return "[НЕ ЗАДАН]"
    if len(k) <= 8:
        return "***"
    return f"{k[:5]}...{k[-4:]}"

async def run_cli_mode(engine):
    print("=" * 70)
    print("🤖 АВТОНОМНЫЙ АГЕНТ-ХИРУРГ SLUGA (CLI MODE)")
    print("=" * 70)
    print("💡 Команды на лету:")
    print("   /keys            — статус и ключи в рантайме")
    print("   /key <значение>  — горячая замена ключа на лету")
    print("   /model <имя>     — горячее переключение модели")
    print("   /setup           — запуск интерактивного мастера")
    print("   doctor           — МРТ текущего проекта")
    print("   exit             — выход")
    print("=" * 70)

    session_id = "local_cli_session"

    while True:
        try:
            prompt = input("\n👤 ВЫ > ").strip()
            if not prompt:
                continue
            if prompt.lower() in ["exit", "quit"]:
                print("Завершение сеанса SLUGA.")
                break

            # 1. Просмотр ключей на лету
            if prompt.lower() == "/keys":
                print("\n🔑 ТЕКУЩИЕ КЛЮЧИ И МОДЕЛИ:")
                print(f"  • LiteAI Ключ: {mask_key(settings.liteai_api_key)} | Модель: {settings.liteai_model}")
                print(f"  • Google AI Studio: {mask_key(settings.google_ai_studio_api_key)} | Модель: {settings.google_gemini_model}")
                print(f"  • CF Proxy: {settings.cf_gemini_proxy_url}")
                continue

            # 2. Горячая смена ключа на лету: /key liteai sk-bf-... или /key sk-bf-...
            if prompt.lower().startswith("/key"):
                parts = prompt.split()
                if len(parts) == 2:
                    new_val = parts[1].strip()
                    provider = "liteai" if new_val.startswith("sk-") else "google"
                    res = settings.update_key_runtime(provider, new_val)
                    print(f"✅ {res}")
                elif len(parts) >= 3:
                    provider = parts[1].strip()
                    new_val = parts[2].strip()
                    res = settings.update_key_runtime(provider, new_val)
                    print(f"✅ {res}")
                else:
                    new_val = input("🔑 Введите новый API-ключ LiteAI (sk-bf-...): ").strip()
                    if new_val:
                        res = settings.update_key_runtime("liteai", new_val)
                        print(f"✅ {res}")
                continue

            # 3. Горячее переключение модели: /model claude-opus-4-8
            if prompt.lower().startswith("/model"):
                parts = prompt.split(maxsplit=1)
                if len(parts) == 2:
                    new_m = parts[1].strip()
                    res = settings.update_model_runtime(new_m)
                    print(f"✅ {res}")
                else:
                    print("\nПопулярные модели LiteAI:")
                    print("  claude-sonnet-4-6, claude-opus-4-8, claude-opus-4-8[1m], claude-sonnet-5, GPT-5.5")
                    new_m = input("Введите имя модели: ").strip()
                    if new_m:
                        res = settings.update_model_runtime(new_m)
                        print(f"✅ {res}")
                continue

            # 4. Запуск мастера настроек
            if prompt.lower() in ["/setup", "setup"]:
                import wizard
                wizard.run_wizard()
                continue

            if prompt.lower() == "doctor":
                from tools.project_doctor import diagnose_project
                import json
                print("\n🩺 МРТ Проекта:")
                print(json.dumps(diagnose_project("."), ensure_ascii=False, indent=2))
                continue

            print("\n⚙️ Обработка задачи агентом...")
            async def cli_status(text):
                print(f"  {text}")

            try:
                result = await engine.process_user_request(
                    session_id=session_id,
                    user_prompt=prompt,
                    status_callback=cli_status
                )
                print(f"\n🤖 SLUGA:\n{result}")
            except Exception as req_err:
                err_str = str(req_err)
                # Перехват ошибки исчерпания токенов / недействительного ключа (401 / 429)
                if "401" in err_str or "429" in err_str or "unauthorized" in err_str.lower() or "quota" in err_str.lower():
                    print(f"\n⚠️ СБОЙ АВТОРИЗАЦИИ / ИСЧЕРПАН ЛИМИТ: {err_str}")
                    print("🔄 Агент не сбрасывает контекст! Введите новый ключ LiteAI прямо сейчас:")
                    new_key = input("🔑 Новый ключ LiteAI (или Enter для отмены) > ").strip()
                    if new_key:
                        settings.update_key_runtime("liteai", new_key)
                        print("🔁 Повторяю запрос с новым ключом...")
                        result = await engine.process_user_request(
                            session_id=session_id,
                            user_prompt=prompt,
                            status_callback=cli_status
                        )
                        print(f"\n🤖 SLUGA:\n{result}")
                    else:
                        print("Запрос отменен.")
                elif "Не настроены API ключи" in err_str:
                    print(f"\n❌ {err_str}")
                else:
                    raise req_err

        except (KeyboardInterrupt, EOFError):
            print("\nСеанс прерван.")
            break
        except Exception as e:
            if "Не настроены API ключи" not in str(e):
                logger.exception("Ошибка в CLI режиме")
            print(f"\n❌ {e}")

async def run_bot_mode(engine):
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN не задан в .env! Переключение в CLI-режим...")
        await run_cli_mode(engine)
        return

    from aiogram import Dispatcher
    from channels.telegram_bot import create_bot, setup_router
    from daemons.scheduler import SlugaDaemon

    logger.info("Инициализация Telegram бота и фонового демона...")
    bot = create_bot()
    dp = Dispatcher()
    setup_router(dp, engine)

    daemon = SlugaDaemon(engine.memory)
    daemon.start()

    logger.info("SLUGA успешно запущен и готов к приему команд в Telegram!")
    try:
        await dp.start_polling(bot)
    finally:
        daemon.stop()
        await bot.session.close()

async def run_single_prompt(engine, prompt: str):
    print(f"\n⚙️ Обработка задачи: {prompt}\n")
    async def cli_status(text):
        print(f"  {text}")
    try:
        result = await engine.process_user_request(
            session_id="single_cli_run",
            user_prompt=prompt,
            status_callback=cli_status
        )
        print(f"\n🤖 SLUGA:\n{result}\n")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}\n")

def main():
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else ""

    if cmd in ["setup", "wizard"]:
        import wizard
        wizard.run_wizard()
        return

    if cmd == "doctor":
        from tools.project_doctor import diagnose_project
        import json
        print("\n🩺 МРТ Проекта:")
        print(json.dumps(diagnose_project("."), ensure_ascii=False, indent=2))
        return

    # Управление фоновым демоном 24/7 (по аналогии с Hermes / PM2)
    if cmd == "start":
        from daemons.daemon_manager import start_daemon
        start_daemon()
        return

    if cmd == "stop":
        from daemons.daemon_manager import stop_daemon
        stop_daemon()
        return

    if cmd == "restart":
        from daemons.daemon_manager import restart_daemon
        restart_daemon()
        return

    if cmd in ["status", "ps"]:
        from daemons.daemon_manager import status_daemon
        status_daemon()
        return

    if cmd in ["logs", "log"]:
        from daemons.daemon_manager import show_logs
        lines = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 40
        show_logs(lines)
        return

    # 1. По умолчанию при запуске без параметров: запуск фонового демона 24/7
    if not cmd and settings.telegram_bot_token:
        from daemons.daemon_manager import start_daemon
        start_daemon()
        return

    from core.engine import SlugaEngine
    engine = SlugaEngine()

    # 2. Запуск Telegram бота в текущем терминале: sluga bot
    if cmd in ["bot", "daemon"]:
        asyncio.run(run_bot_mode(engine))
    # 3. Интерактивный терминал: sluga cli или запуск без токена
    elif cmd in ["cli", ""]:
        asyncio.run(run_cli_mode(engine))
    # 4. Вызов разовой команды: sluga "напиши калькулятор"
    else:
        prompt = " ".join(sys.argv[1:])
        asyncio.run(run_single_prompt(engine, prompt))

if __name__ == "__main__":
    main()
