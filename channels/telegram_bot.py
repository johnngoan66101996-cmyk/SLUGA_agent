"""
Telegram-канал связи агента SLUGA.
Использует aiogram 3 с возможностью проксирования через Cloudflare Worker (/bot...).
Поддерживает whitelist пользователей и информирование о промежуточных шагах ReAct-петли.
"""

import logging
import io
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import Command
from config import settings
from core.engine import SlugaEngine
from tools.project_doctor import diagnose_project
from tools.voice_handler import transcribe_voice, synthesize_voice

logger = logging.getLogger("SLUGA_TELEGRAM")

# Хранилище настроек голосового ответа по чатам (по умолчанию включен)
chat_voice_settings = {}

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

    @dp.message(Command("voice"))
    async def cmd_voice(msg: types.Message):
        if not is_allowed(msg.from_user.id):
            return
        parts = msg.text.split()
        chat_id = msg.chat.id
        if len(parts) >= 2 and parts[1].lower() in ["off", "0", "false", "выкл"]:
            chat_voice_settings[chat_id] = False
            await msg.answer("🔇 Голосовые ответы отключены. Агент будет отвечать только текстом.")
        elif len(parts) >= 2 and parts[1].lower() in ["on", "1", "true", "вкл"]:
            chat_voice_settings[chat_id] = True
            await msg.answer("🎙️ Голосовые ответы включены. Агент будет озвучивать суть ответов.")
        else:
            cur = "включены" if chat_voice_settings.get(chat_id, True) else "отключены"
            await msg.answer(
                f"🎙️ Статус голосовых ответов: **{cur}**.\n\n"
                "Управление:\n"
                "• `/voice on` — включить голосовые ответы\n"
                "• `/voice off` — выключить голосовые ответы",
                parse_mode="Markdown"
            )

    async def _process_and_reply(msg: types.Message, session_id: str, prompt_text: str, status_msg: types.Message, is_voice_input: bool = False):
        async def notify_progress(status_text: str):
            try:
                await status_msg.edit_text(status_text)
            except Exception:
                pass

        try:
            response = await engine.process_user_request(
                session_id=session_id,
                user_prompt=prompt_text,
                status_callback=notify_progress
            )

            # Голосовой ответ при включенном режиме
            should_voice = chat_voice_settings.get(msg.chat.id, True)
            if should_voice and is_voice_input:
                try:
                    await status_msg.edit_text("🎙️ Синтезирую голосовой ответ...")
                    voice_bytes = await synthesize_voice(response)
                    await msg.answer_voice(
                        voice=types.BufferedInputFile(voice_bytes, filename="sluga_voice.mp3"),
                        caption="🎙️ Голосовой ответ SLUGA"
                    )
                except Exception as ve:
                    logger.warning(f"Ошибка синтеза речи Edge-TTS: {ve}")

            # Отправка подробного текстового отчета с кодом
            if len(response) > 4000:
                parts = [response[i:i+3800] for i in range(0, len(response), 3800)]
                await status_msg.edit_text(parts[0])
                for part in parts[1:]:
                    await msg.answer(part)
            else:
                await status_msg.edit_text(response)

        except Exception as e:
            logger.exception("Ошибка обработки запроса")
            await status_msg.edit_text(f"❌ Сбой выполнения задачи: {e}")

    # Обработчик голосовых сообщений (войсов)
    @dp.message(F.voice | F.audio)
    async def handle_voice_message(msg: types.Message):
        if not is_allowed(msg.from_user.id):
            return

        session_id = f"tg_{msg.chat.id}"
        status_msg = await msg.answer("🎙️ Загружаю голосовое сообщение...")

        try:
            voice_obj = msg.voice or msg.audio
            file_info = await msg.bot.get_file(voice_obj.file_id)
            audio_stream = io.BytesIO()
            await msg.bot.download_file(file_info.file_path, audio_stream)
            audio_bytes = audio_stream.getvalue()

            await status_msg.edit_text("🔄 Распознаю речь (STT)...")
            mime_type = getattr(voice_obj, 'mime_type', 'audio/ogg') or 'audio/ogg'
            user_prompt = await transcribe_voice(audio_bytes, mime_type=mime_type)

            await status_msg.edit_text(f"🗣️ **Вы сказали:** «_{user_prompt}_»\n\n🧠 SLUGA принял задачу в обработку...", parse_mode="Markdown")

            await _process_and_reply(msg, session_id, user_prompt, status_msg, is_voice_input=True)

        except Exception as e:
            logger.exception("Ошибка обработки голосового сообщения")
            await status_msg.edit_text(f"❌ Не удалось обработать голосовое сообщение: {e}")

    # Обработчик текстовых сообщений
    @dp.message(F.text)
    async def handle_user_prompt(msg: types.Message):
        if not is_allowed(msg.from_user.id):
            return

        session_id = f"tg_{msg.chat.id}"
        status_msg = await msg.answer("🧠 SLUGA принял задачу в обработку...")
        await _process_and_reply(msg, session_id, msg.text, status_msg, is_voice_input=False)
