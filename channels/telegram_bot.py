"""
Telegram-канал связи агента SLUGA.
Использует aiogram 3 с возможностью проксирования через Cloudflare Worker (/bot...).
Поддерживает whitelist пользователей и информирование о промежуточных шагах ReAct-петли.
"""

import logging
import io
import html
import json
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import Command
from config import settings, BASE_DIR
from core.engine import SlugaEngine
from tools.project_doctor import diagnose_project
from tools.voice_handler import transcribe_voice, synthesize_voice

logger = logging.getLogger("SLUGA_TELEGRAM")

# Персистентное хранилище настроек голосового ответа по чатам (сохраняется в data/voice_settings.json)
VOICE_SETTINGS_FILE = BASE_DIR / "data" / "voice_settings.json"

def get_voice_setting(chat_id: int) -> bool:
    try:
        if VOICE_SETTINGS_FILE.exists():
            with open(VOICE_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(str(chat_id), True)
    except Exception:
        pass
    return True

def set_voice_setting(chat_id: int, enabled: bool):
    try:
        data = {}
        if VOICE_SETTINGS_FILE.exists():
            with open(VOICE_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data[str(chat_id)] = enabled
        VOICE_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(VOICE_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Не удалось сохранить настройку голоса: {e}")

async def check_liteai_stats(api_key: str) -> dict:
    """Запрос статистики ключа и расхода токенов с сервиса LiteAI (liteai.tech/api/stats)"""
    clean_key = api_key.strip().strip("<>").strip()
    url = f"https://liteai.tech/api/stats?key={clean_key}"
    headers = {"User-Agent": "SLUGA_Agent/2.0"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 401:
            return {"error": "Ключ недействителен или не активен (401 Unauthorized)"}
        if not resp.is_success:
            return {"error": f"Ошибка сервиса LiteAI: HTTP {resp.status_code}"}
        return resp.json()

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Удобное меню быстрых кнопок агента SLUGA"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔬 МРТ проекта"), KeyboardButton(text="📊 Баланс токенов")],
            [KeyboardButton(text="🔐 Статус ключей"), KeyboardButton(text="🛠️ 116 Навыков")],
            [KeyboardButton(text="🧹 Очистить память"), KeyboardButton(text="🎙️ Голос (Вкл/Выкл)")],
            [KeyboardButton(text="🔽 Скрыть кнопки")]
        ],
        resize_keyboard=True
    )

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
            "  /balance — Проверка токенов и баланса LiteAI\n"
            "  /keys   — Статус активных ключей\n"
            "  /key    — Смена API-ключа на лету\n"
            "  /model  — Смена модели на лету\n"
            "  /doctor — МРТ текущего проекта\n"
            "  /skills — Каталог 116 навыков\n"
            "  /voice  — Управление голосовыми ответами\n"
            "  /reset  — Очистить текущий контекст диалога\n"
            "  /hide   — Скрыть кнопки под чатом\n\n"
            "Отправьте мне любую задачу — от анализа кода до автономного рефакторинга."
        )
        await msg.answer(welcome, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())

    @dp.message(Command("hide") | Command("clean"))
    async def cmd_hide(msg: types.Message):
        if not is_allowed(msg.from_user.id):
            return
        await msg.answer("🔽 Нижняя панель кнопок скрыта. Напишите /start, чтобы вернуть её в любой момент.", reply_markup=ReplyKeyboardRemove())

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
            "Смена на лету: `/key <новый_ключ>` или `/model <имя_модели>`\n"
            "📊 Проверить токены и баланс LiteAI: `/balance` или `/stats`"
        )
        await msg.answer(res, parse_mode="Markdown")

    @dp.message(Command("balance") | Command("stats"))
    async def cmd_stats(msg: types.Message):
        if not is_allowed(msg.from_user.id):
            return
        parts = msg.text.split(maxsplit=1)
        key_to_check = parts[1].strip().strip("<>").strip() if len(parts) > 1 else (settings.liteai_api_key or "").strip()
        if not key_to_check:
            await msg.answer(
                "❌ Ключ LiteAI не найден в конфигурации.\n\n"
                "Использование:\n"
                "• `/balance sk-bf-...` — проверить баланс по указанному ключу\n"
                "• `/key liteai sk-bf-...` — привязать ключ к боту",
                parse_mode="Markdown"
            )
            return

        status_msg = await msg.answer("⏳ Запрашиваю статистику и токены с LiteAI (liteai.tech/stats)...")
        try:
            data = await check_liteai_stats(key_to_check)
            if "error" in data:
                await status_msg.edit_text(f"❌ {data['error']}")
                return

            total_tokens = data.get("total_tokens", 0)
            total_requests = data.get("total_requests", 0)
            cost = data.get("cost", 0.0)

            # Форматирование токенов (миллионы / тысячи)
            if total_tokens >= 1_000_000:
                tokens_str = f"{total_tokens / 1_000_000:.2f}M"
            elif total_tokens >= 1_000:
                tokens_str = f"{total_tokens / 1_000:.1f}k"
            else:
                tokens_str = str(total_tokens)

            models_lines = []
            models = data.get("models", {})
            if models and isinstance(models, dict):
                sorted_models = sorted(models.items(), key=lambda x: x[1], reverse=True)
                for m, cnt in sorted_models[:5]:
                    models_lines.append(f"  • `{m}`: {cnt:,} токенов")

            models_block = ""
            if models_lines:
                models_block = "\n\n📊 **Расход по моделям:**\n" + "\n".join(models_lines)

            rate_limit = data.get("rate_limit")
            rate_block = f"\n⚡ **Лимит скорости:** `{rate_limit}`" if rate_limit else ""

            masked_key = f"{key_to_check[:7]}...{key_to_check[-4:]}" if len(key_to_check) > 11 else key_to_check

            res = (
                "📈 **Статистика и баланс токенов LiteAI:**\n"
                f"🔑 Ключ: `{masked_key}`\n\n"
                f"🪙 **Израсходовано токенов:** `{tokens_str}` ({total_tokens:,})\n"
                f"💬 **Всего запросов:** `{total_requests:,}`\n"
                f"💰 **Списано по тарифу:** `{cost:.2f} ₽`"
                f"{rate_block}"
                f"{models_block}\n\n"
                f"🌐 Веб-проверка: [liteai.tech/stats](https://liteai.tech/stats)"
            )
            await status_msg.edit_text(res, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception as e:
            await status_msg.edit_text(f"⚠️ Ошибка запроса к LiteAI: {e}")

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
            set_voice_setting(chat_id, False)
            await msg.answer("🔇 Голосовые ответы отключены. Агент будет отвечать только текстом.")
        elif len(parts) >= 2 and parts[1].lower() in ["on", "1", "true", "вкл"]:
            set_voice_setting(chat_id, True)
            await msg.answer("🎙️ Голосовые ответы включены. Агент будет озвучивать суть ответов.")
        else:
            cur = "включены" if get_voice_setting(chat_id) else "отключены"
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
            should_voice = get_voice_setting(msg.chat.id)
            if should_voice and is_voice_input:
                try:
                    await status_msg.edit_text("🎙️ Синтезирую голосовой ответ...")
                    voice_bytes = await synthesize_voice(response)
                    # Edge-TTS возвращает аудиопоток MP3. Пробуем answer_voice, при ошибке отправляем через answer_audio
                    voice_file = types.BufferedInputFile(voice_bytes, filename="sluga_voice.mp3")
                    try:
                        await msg.answer_voice(
                            voice=voice_file,
                            caption="🎙️ Голосовой ответ SLUGA"
                        )
                    except Exception as voice_err:
                        logger.warning(f"answer_voice сбой ({voice_err}), отправляю через answer_audio...")
                        audio_file = types.BufferedInputFile(voice_bytes, filename="sluga_voice.mp3")
                        await msg.answer_audio(
                            audio=audio_file,
                            title="Голосовой ответ SLUGA",
                            performer="SLUGA",
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

            # Безопасное отображение распознанного текста с защитой от Markdown-инъекций и ограничением длины
            display_text = user_prompt[:1000] + ("..." if len(user_prompt) > 1000 else "")
            safe_text = html.escape(display_text)

            await status_msg.edit_text(
                f"🗣️ <b>Вы сказали:</b> «<i>{safe_text}</i>»\n\n🧠 SLUGA принял задачу в обработку...",
                parse_mode="HTML"
            )

            await _process_and_reply(msg, session_id, user_prompt, status_msg, is_voice_input=True)

        except Exception as e:
            logger.exception("Ошибка обработки голосового сообщения")
            await status_msg.edit_text(f"❌ Не удалось обработать голосовое сообщение: {e}")

    # Обработчики быстрых кнопок клавиатуры SLUGA
    @dp.message(F.text == "🔬 МРТ проекта")
    async def btn_doctor(msg: types.Message):
        await cmd_doctor(msg)

    @dp.message(F.text.in_(["📊 Баланс токенов", "📊 Баланс", "Статистика токенов", "Баланс"]))
    async def btn_balance(msg: types.Message):
        await cmd_stats(msg)

    @dp.message(F.text == "🛠️ 116 Навыков")
    async def btn_skills(msg: types.Message):
        await cmd_skills(msg)

    @dp.message(F.text == "🔐 Статус ключей")
    async def btn_keys(msg: types.Message):
        await cmd_keys(msg)

    @dp.message(F.text == "🎙️ Голос (Вкл/Выкл)")
    async def btn_voice(msg: types.Message):
        chat_id = msg.chat.id
        current = get_voice_setting(chat_id)
        new_state = not current
        set_voice_setting(chat_id, new_state)
        status_text = "включены 🎙️" if new_state else "отключены 🔇"
        await msg.answer(f"Голосовые ответы теперь **{status_text}**.", parse_mode="Markdown")

    @dp.message(F.text == "🧹 Очистить память")
    async def btn_reset(msg: types.Message):
        await cmd_reset(msg)

    @dp.message(F.text == "🔽 Скрыть кнопки")
    async def btn_hide(msg: types.Message):
        await cmd_hide(msg)

    # Обработка устаревших кнопок от предыдущего бота (перехват и исправление клавиатуры)
    @dp.message(F.text == "👑 Google Gemini 3.7")
    async def legacy_gemini(msg: types.Message):
        status = settings.update_model_runtime("gemini-3.7-flash")
        await msg.answer(f"✅ {status}\n\nСтарые кнопки удалены, активна актуальная панель SLUGA:", reply_markup=get_main_keyboard())

    @dp.message(F.text == "⚡ LiteAI Claude Sonnet")
    async def legacy_claude(msg: types.Message):
        status = settings.update_model_runtime("claude-sonnet-4-6")
        await msg.answer(f"✅ {status}\n\nСтарые кнопки удалены, активна актуальная панель SLUGA:", reply_markup=get_main_keyboard())

    @dp.message(F.text == "⚙️ Статус")
    async def legacy_status(msg: types.Message):
        await cmd_keys(msg)
        await msg.answer("✅ Клавиатура обновлена на актуальную:", reply_markup=get_main_keyboard())

    @dp.message(F.text == "🔄 Сменить провайдера")
    async def legacy_switch_provider(msg: types.Message):
        await cmd_model(msg)

    @dp.message(F.text.in_(["🔼 Показать панель управления", "🔽 Скрыть панель кнопок"]))
    async def legacy_menu_toggle(msg: types.Message):
        if "Скрыть" in msg.text:
            await cmd_hide(msg)
        else:
            await msg.answer("✅ Панель управления SLUGA:", reply_markup=get_main_keyboard())

    # Обработчик текстовых сообщений
    @dp.message(F.text)
    async def handle_user_prompt(msg: types.Message):
        if not is_allowed(msg.from_user.id):
            return

        session_id = f"tg_{msg.chat.id}"
        status_msg = await msg.answer("🧠 SLUGA принял задачу в обработку...")
        await _process_and_reply(msg, session_id, msg.text, status_msg, is_voice_input=False)

