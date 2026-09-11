"""
Telegram-канал связи агента SLUGA.
Использует aiogram 3 с возможностью проксирования через Cloudflare Worker (/bot...).
Поддерживает whitelist пользователей и информирование о промежуточных шагах ReAct-петли.
"""

import logging
from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import Command
from config import settings
from core.engine import SlugaEngine
from tools.project_doctor import diagnose_project

logger = logging.getLogger("SLUGA_TELEGRAM")

def create_bot() -> Bot:
    session = None
    if settings.telegram_proxy_url:
        # Маршрутизируем запросы через Cloudflare Worker
        base_proxy = settings.telegram_proxy_url.rstrip('/')
        server = TelegramAPIServer(
            base=f"{base_proxy}/bot{{token}}/{{method}}",
            file=f"{base_proxy}/file/bot{{token}}/{{path}}"
        )
        session = AiohttpSession(api=server)

    return Bot(token=settings.telegram_bot_token, session=session)

def setup_router(dp: Dispatcher, engine: SlugaEngine):
    def is_allowed(user_id: int) -> bool:
        allowed = settings.allowed_user_ids
        if not allowed:
            return True # Если белый список не задан, доступ открыт
        return user_id in allowed

    @dp.message(Command("start"))
    async def cmd_start(msg: types.Message):
        if not is_allowed(msg.from_user.id):
            await msg.answer("⛔ Доступ ограничен. Ваш ID отсутствует в белом списке.")
            return

        welcome = (
            "🤖 **SLUGA — Автономный Агент-Хирург ИИ**\n\n"
            "База моделей:\n"
            "  • Primary: **LiteAI** (Claude / GPT-5)\n"
            "  • Secondary: **Google AI Studio** (Gemini 3.7 / 3.6 / 3.8 Flash)\n\n"
            "Доступные команды:\n"
            "  /doctor — МРТ текущего проекта\n"
            "  /skills — Каталог 116 навыков\n"
            "  /key — Смена ключа на лету\n"
            "  /model — Смена модели на лету\n"
            "  /keys — Статус активных ключей\n"
            "  /reset — Очистить текущий контекст диалога\n"
            "  /status — Статус системы и памяти\n\n"
            "Отправьте мне любую задачу — от анализа кода до автономного рефакторинга."
        )
        await msg.answer(welcome, parse_mode="Markdown")

    @dp.message(Command("doctor"))
    async def cmd_doctor(msg: types.Message):
        if not is_allowed(msg.from_user.id):
            return
        status_msg = await msg.answer("🔬 Провожу диагностику МРТ проекта...")
        mri = diagnose_project(".")
        res = (
            f"🩺 **Результаты МРТ Проекта:**\n"
            f"• Папка: `{mri['project_root']}`\n"
            f"• Git: {'✅ Инициализирован' if mri['has_git_vcs'] else '❌ Отсутствует'}\n"
            f"• Стек: {', '.join(mri['detected_stack'])}\n"
            f"• Манифесты: {', '.join(mri['manifests_detected']) or 'Нет'}\n\n"
            f"{mri['safety_recommendation']}"
        )
        await status_msg.edit_text(res, parse_mode="Markdown")

    @dp.message(Command("skills"))
    async def cmd_skills(msg: types.Message):
        if not is_allowed(msg.from_user.id):
            return
        skills = engine.skill_loader.list_skills()
        text = f"📚 **Доступно {len(skills)} навыков SLUGA (Золотая Триада + Профильные):**\n\n"
        for s in skills[:15]:
            text += f"• **{s['name']}**: {s['description'][:70]}...\n"
        text += f"\n_...и еще {len(skills) - 15} навыков в папке ./skills/_"
        await msg.answer(text, parse_mode="Markdown")

    @dp.message(Command("reset"))
    async def cmd_reset(msg: types.Message):
        if not is_allowed(msg.from_user.id):
            return
        session_id = f"tg_{msg.chat.id}"
        engine.memory.clear_history(session_id)
        await msg.answer("🧹 Краткосрочная память сессии очищена.")

    @dp.message(Command("keys"))
    async def cmd_keys(msg: types.Message):
        if not is_allowed(msg.from_user.id):
            return
        def mask(k):
            return f"{k[:5]}...{k[-4:]}" if k and len(k) > 8 else "[НЕ ЗАДАН]"
        res = (
            "🔑 **Текущие ключи и модели (Рантайм):**\n"
            f"• LiteAI: `{mask(settings.liteai_api_key)}` | Модель: `{settings.liteai_model}`\n"
            f"• Google AI Studio: `{mask(settings.google_ai_studio_api_key)}` | Модель: `{settings.google_gemini_model}`\n\n"
            "Смена на лету: `/key <новый_ключ>` или `/model <имя_модели>`"
        )
        await msg.answer(res, parse_mode="Markdown")

    @dp.message(Command("key"))
    async def cmd_key(msg: types.Message):
        if not is_allowed(msg.from_user.id):
            return
        parts = msg.text.split()
        if len(parts) >= 2:
            new_k = parts[1].strip()
            provider = "liteai" if new_k.startswith("sk-") else "google"
            status = settings.update_key_runtime(provider, new_k)
            await msg.answer(f"✅ {status}\nНовый ключ активен и сохранен в `.env`.")
        else:
            await msg.answer("Использование: `/key sk-bf-...` для смены ключа LiteAI на лету.", parse_mode="Markdown")

    @dp.message(Command("model"))
    async def cmd_model(msg: types.Message):
        if not is_allowed(msg.from_user.id):
            return
        parts = msg.text.split(maxsplit=1)
        if len(parts) == 2:
            new_m = parts[1].strip()
            status = settings.update_model_runtime(new_m)
            await msg.answer(f"✅ {status}\nМодель переключена без перезапуска бота.")
        else:
            await msg.answer(
                "Использование: `/model <имя_модели>`\n\n"
                "Доступные модели LiteAI:\n"
                "• `claude-sonnet-4-6`\n"
                "• `claude-opus-4-8`\n"
                "• `claude-opus-4-8[1m]`\n"
                "• `claude-sonnet-5`\n"
                "• `GPT-5.5`\n"
                "• `gemini-3.7-flash` (Google AI Studio)\n"
                "• `gemini-3.6-flash` (Google AI Studio)\n"
                "• `gemini-3.8-flash` (Google AI Studio)",
                parse_mode="Markdown"
            )

    @dp.message()
    async def handle_user_prompt(msg: types.Message):
        if not is_allowed(msg.from_user.id):
            return

        session_id = f"tg_{msg.chat.id}"
        status_msg = await msg.answer("🧠 SLUGA принял задачу в обработку...")

        async def notify_progress(status_text: str):
            try:
                await status_msg.edit_text(status_text)
            except Exception:
                pass

        try:
            response = await engine.process_user_request(
                session_id=session_id,
                user_prompt=msg.text,
                status_callback=notify_progress
            )

            # Telegram лимит 4096 символов на сообщение
            if len(response) > 4000:
                parts = [response[i:i+3800] for i in range(0, len(response), 3800)]
                await status_msg.edit_text(parts[0])
                for part in parts[1:]:
                    await msg.answer(part)
            else:
                await status_msg.edit_text(response)
        except Exception as e:
            logger.exception("Ошибка обработки сообщения")
            await status_msg.edit_text(f"❌ Сбой выполнения задачи: {e}")
