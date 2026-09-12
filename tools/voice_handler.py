"""
Модуль голосового взаимодействия агента SLUGA (STT + TTS).
1. STT (Speech-to-Text): Распознавание голосовых сообщений из Telegram через Gemini Multimodal Audio или Whisper API.
2. TTS (Text-to-Speech): Высококачественный синтез реалистичной русской речи через Microsoft Edge-TTS (без API ключей, бесплатно).
"""

import re
import io
import base64
import logging
import httpx

from config import settings

logger = logging.getLogger("SLUGA_VOICE")

# По умолчанию используется качественный русский мужской голос
DEFAULT_VOICE = "ru-RU-DmitryNeural"
# Дополнительный женский голос: "ru-RU-SvetlanaNeural"

def prepare_text_for_speech(text: str, max_chars: int = 500) -> str:
    """
    Очищает текст от блоков кода Markdown и ссылок для комфортного восприятия на слух.
    """
    # Удаляем блоки кода ```...```
    cleaned = re.sub(r'```[\s\S]*?```', '', text)
    # Удаляем инлайн-код `...`
    cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)
    # Удаляем Markdown заголовки и жирный шрифт
    cleaned = re.sub(r'[#*_~>]+', '', cleaned)
    # Удаляем ссылки [text](url) -> text
    cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)
    # Удаляем эмодзи и служебные спецсимволы
    cleaned = re.sub(r'[🤖🛠️🧠🩺✅❌⚠️💡📁🚀]', '', cleaned)
    
    # Сжимаем повторяющиеся переносы строк и пробелы
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    if not cleaned:
        return "Задача выполнена. Подробный отчет и код отправлены в сообщении выше."

    if len(cleaned) > max_chars:
        # Обрезаем по последнему предложению до max_chars
        truncated = cleaned[:max_chars]
        last_dot = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
        if last_dot > 100:
            cleaned = truncated[:last_dot + 1]
        else:
            cleaned = truncated
        cleaned += " Полный отчет и детали в сообщении выше."

    return cleaned


async def transcribe_voice(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """
    Распознает речь из переданных аудио-байтов в текст.
    Приоритет:
    1. Whisper через LiteAI (быстро, стабильно, без блокировок и очередей)
    2. Google Gemini Multimodal (резервный канал при наличии ключа)
    """
    # Проверка на пустой или поврежденный поток
    if not audio_bytes or len(audio_bytes) < 100:
        raise ValueError("Голосовой файл пустой или повреждён (размер < 100 байт).")

    # 1. Основной канал: LiteAI / Whisper API
    if settings.liteai_api_key:
        try:
            logger.info("Распознавание речи через LiteAI Whisper API...")
            whisper_url = f"{settings.liteai_base_url.rstrip('/')}/audio/transcriptions"
            headers = {"Authorization": f"Bearer {settings.liteai_api_key}"}
            
            # Корректное расширение в зависимости от реального mime_type
            ext_map = {
                "audio/ogg": "voice.ogg",
                "audio/opus": "voice.ogg",
                "audio/mpeg": "voice.mp3",
                "audio/mp3": "voice.mp3",
                "audio/mp4": "voice.m4a",
                "audio/x-m4a": "voice.m4a",
                "audio/wav": "voice.wav",
                "audio/x-wav": "voice.wav",
                "audio/webm": "voice.webm",
            }
            file_name = ext_map.get(mime_type.lower(), "voice.ogg")

            files = {
                "file": (file_name, audio_bytes, mime_type)
            }
            data = {
                "model": "whisper-1",
                "language": "ru"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(whisper_url, headers=headers, files=files, data=data)
                if resp.status_code == 200:
                    recognized = resp.json().get("text", "").strip()
                    if recognized:
                        logger.info(f"Речь успешно расшифрована (Whisper): '{recognized[:50]}...'")
                        return recognized
                else:
                    logger.warning(f"LiteAI Whisper вернул HTTP {resp.status_code}: {resp.text[:150]}")
        except Exception as e:
            logger.warning(f"Сбой расшифровки через LiteAI Whisper: {e}")

    # 2. Резервный канал: Google AI Studio (Gemini 3.7 / 3.6 / Flash)
    if settings.google_ai_studio_api_key:
        try:
            logger.info("Резервное распознавание речи через Google Gemini Multimodal Audio...")
            b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
            
            base_url = settings.cf_gemini_proxy_url.rstrip('/')
            if base_url.endswith("/openai"):
                base_url = base_url[:-7]
            if not base_url.endswith("/v1beta"):
                base_url = f"{base_url}/v1beta"

            target_model = settings.google_gemini_model or "gemini-3.7-flash"
            url = f"{base_url}/models/{target_model}:generateContent?key={settings.google_ai_studio_api_key}"

            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": b64_audio
                                }
                            },
                            {
                                "text": "Транскрибируй эту голосовую запись на русском языке в точный текст. Выведи ТОЛЬКО расшифрованный текст без лишних пояснений, вступительных фраз и кавычек."
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1
                }
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            recognized = parts[0].get("text", "").strip()
                            if recognized:
                                logger.info(f"Речь успешно расшифрована (Gemini): '{recognized[:50]}...'")
                                return recognized
                else:
                    logger.warning(f"Gemini Audio STT вернул HTTP {resp.status_code}: {resp.text[:150]}")
        except Exception as e:
            logger.warning(f"Сбой расшифровки через Gemini: {e}")

    raise RuntimeError("Не удалось распознать голосовое сообщение. Убедитесь, что настроен LITEAI_API_KEY (https://liteai.tech/) или проверьте баланс токенов (/balance).")


async def synthesize_voice(text: str, voice: str = DEFAULT_VOICE) -> bytes:
    """
    Преобразует текст ответа агента в аудио-файл (.ogg / .mp3) через Microsoft Edge-TTS.
    Работает абсолютно бесплатно, без API ключей и лимитов.
    """
    import edge_tts

    spoken_text = prepare_text_for_speech(text)
    logger.info(f"Синтез речи (Edge-TTS, голос {voice}): '{spoken_text[:60]}...'")

    communicate = edge_tts.Communicate(spoken_text, voice=voice)
    
    audio_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])

    audio_bytes = audio_buffer.getvalue()
    if not audio_bytes:
        raise RuntimeError("Не удалось сгенерировать аудиопоток Edge-TTS.")

    return audio_bytes
