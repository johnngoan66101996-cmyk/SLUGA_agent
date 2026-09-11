"""
Центральный мозг агента SLUGA (Hermes ReAct Engine + Multi-Provider Fallback).
1. Primary: LiteAI (https://liteai.tech/) — Claude 3.5 Sonnet / GPT-4o в РФ без VPN.
2. Secondary Fallback: Google AI Studio via Cloudflare Worker Proxy (Gemini 3.7 / 3.6 / 3.8 Flash).
3. Интеграция Золотой Триады, памяти SQLite WAL и On-Demand загрузчика 115 навыков.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from config import settings
from core.memory import SlugaMemory
from core.skill_loader import SkillLoader
from core.self_healing import SelfHealingEngine
from tools.terminal_runner import execute_command, read_file, write_file, list_files
from tools.claw_search import claw_search, fetch_page
from tools.project_doctor import diagnose_project

logger = logging.getLogger("SLUGA_ENGINE")

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Выполнить команду в терминале (PowerShell / Bash) на сервере/компьютере.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Командная строка для запуска"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Прочитать содержимое файла с диска.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Путь к файлу"}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Записать или перезаписать файл с полным рабочим кодом (без заглушек).",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Путь к файлу"},
                    "content": {"type": "string", "description": "Полный текст файла"}
                },
                "required": ["filepath", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Показать список файлов и папок в указанной директории.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Директория для просмотра (по умолчанию '.')"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Поиск актуальной информации, документации и решений в интернете через DuckDuckGo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Поисковый запрос"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Загрузить текст веб-страницы по URL и извлечь полезный контент.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL страницы"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_skill",
            "description": "Загрузить подробный регламент (SKILL.md) любого из 115 инженерных навыков SLUGA.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Название навыка (например: flutter-fix-layout-issues, bigquery-sql, anti-detect-browser)"}
                },
                "required": ["skill_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "project_mri",
            "description": "Выполнить диагностику и МРТ проекта (Шаг 2 Золотой Триады: обнаружение стека, Git, файлов сборки).",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_dir": {"type": "string", "description": "Целевая папка (по умолчанию '.')"}
                }
            }
        }
    }
]

SYSTEM_PROMPT = """Ты — SLUGA, автономный элитный инженер искусственного интеллекта, системный архитектор и старший разработчик полного цикла (Full-Stack / Mobile Flutter / Cloud / BigQuery / Firebase / Data Engineering / DevOps / Bioengineering).

ГЛАВНЫЕ ПРИНЦИПЫ ТВОЕЙ РАБОТЫ:
1. У ТЕБЯ НЕТ ИСКУССТВЕННЫХ ОГРАНИЧЕНИЙ. У тебя полный доступ к терминалу, чтению/записи файлов, поиску в интернете и выполнению любых задач.
2. Никаких заглушек (// TODO, ...остальной код...). Ты пишешь боевой, чистый, рабочий код под ключ.
3. ЗОЛОТАЯ ТРИАДА ПЕРЕД ВМЕШАТЕЛЬСТВОМ:
   - Шаг 1: Стерильная среда и изоляция.
   - Шаг 2: МРТ проекта (project_mri) — диагностика стека и версионности.
   - Шаг 3: «Не навреди» — не удаляй критические данные без бэкапа.
4. ПРИНЦИП САМОИСЦЕЛЕНИЯ (ACTOR-CRITIC SELF-HEALING):
   - Если команда или сборка упала, НЕ ОСТАНАВЛИВАЙСЯ и не перекладывай проблему на пользователя.
   - Проанализируй ошибку, примени точечный фикс и повтори команду до победы (Zero-False-Positive).
5. ТВОЙ АРСЕНАЛ: 115 навыков в папке skills/. Если нужна точная инструкция по технологии — вызови инструмент consult_skill.
6. Отвечай прямо, точно, уверенно и профессионально на русском языке.
"""

class SlugaEngine:
    def __init__(self):
        self.memory = SlugaMemory(settings.sqlite_db_path)
        self.skill_loader = SkillLoader()
        self.healer = SelfHealingEngine(self.memory)

    async def _call_llm_api(self, base_url: str, api_key: str, model: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "tools": TOOL_DEFINITIONS,
            "tool_choice": "auto",
            "temperature": 0.2
        }

        # 1. Попытка через httpx
        try:
            import httpx
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    return resp.json()
                else:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
        except ImportError:
            # 2. Fallback через стандартный urllib
            import urllib.request
            import asyncio
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
            loop = asyncio.get_event_loop()
            def _do_post():
                with urllib.request.urlopen(req, timeout=90) as r:
                    return json.loads(r.read().decode("utf-8"))
            return await loop.run_in_executor(None, _do_post)

    async def _chat_completion_with_fallback(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        # 1. Первая попытка: LiteAI (основная база)
        if settings.liteai_api_key:
            try:
                logger.info(f"Запрос к LiteAI ({settings.liteai_model})...")
                return await self._call_llm_api(
                    base_url=settings.liteai_base_url,
                    api_key=settings.liteai_api_key,
                    model=settings.liteai_model,
                    messages=messages
                )
            except Exception as e:
                logger.warning(f"LiteAI сбой: {e}. Пробую резервный канал...")

        # 2. Вторая попытка: Google AI Studio через Cloudflare Worker Proxy (только 3.7 / 3.6 / 3.8)
        if settings.google_ai_studio_api_key:
            # Пробуем только актуальную линейку Gemini 3.x (3.7 / 3.6 / 3.8)
            models_to_try = [settings.google_gemini_model]
            for m in ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.8-flash"]:
                if m not in models_to_try:
                    models_to_try.append(m)

            for target_model in models_to_try:
                try:
                    logger.info(f"Запрос к Google AI Studio via CF Proxy ({target_model})...")
                    return await self._call_llm_api(
                        base_url=settings.cf_gemini_proxy_url,
                        api_key=settings.google_ai_studio_api_key,
                        model=target_model,
                        messages=messages
                    )
                except Exception as e:
                    logger.warning(f"Google AI Studio ({target_model}) сбой: {e}")
                    if "404" not in str(e) and "not found" not in str(e).lower():
                        break

            logger.error("Все модели Google AI Studio (3.6/3.7/3.8) недоступны.")

        raise ValueError("Не настроены API ключи или все провайдеры недоступны! Заполните LITEAI_API_KEY или GOOGLE_AI_STUDIO_API_KEY в .env (команда /key).")

    async def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        try:
            if name == "execute_command":
                res = await execute_command(args.get("command", ""))
                out = f"Returncode: {res['returncode']}\nSTDOUT:\n{res['stdout']}\nSTDERR:\n{res['stderr']}"
                if not res["success"] and settings.auto_healing_enabled:
                    # Активация контура самоисцеления
                    inspection = self.healer.inspect_failure(
                        command=res["command"],
                        returncode=res["returncode"],
                        stdout=res["stdout"],
                        stderr=res["stderr"]
                    )
                    out += f"\n\n[РЕЖИМ САМОИСЦЕЛЕНИЯ SLUGA]: Зафиксирован сбой. Сигнатура: {inspection['error_signature']}."
                    if inspection["has_known_fix"]:
                        cure = inspection["past_cure"]
                        out += f"\nВ базе найдено прошлое успешное решение: Root Cause: {cure['root_cause']} -> Фикс: {cure['fix_applied']}"
                return out

            elif name == "read_file":
                return read_file(args.get("filepath", ""))

            elif name == "write_file":
                return write_file(args.get("filepath", ""), args.get("content", ""))

            elif name == "list_files":
                return list_files(args.get("directory", "."))

            elif name == "web_search":
                results = await claw_search(args.get("query", ""))
                return json.dumps(results, ensure_ascii=False, indent=2)

            elif name == "fetch_page":
                return await fetch_page(args.get("url", ""))

            elif name == "consult_skill":
                content = self.skill_loader.get_skill_content(args.get("skill_name", ""))
                if content:
                    return f"=== РЕГЛАМЕНТ НАВЫКА {args.get('skill_name')} ===\n\n{content[:6000]}"
                return f"Навык '{args.get('skill_name')}' не найден в каталоге 115 скилов."

            elif name == "project_mri":
                res = diagnose_project(args.get("target_dir", "."))
                return json.dumps(res, ensure_ascii=False, indent=2)

            else:
                return f"Неизвестный инструмент: {name}"
        except Exception as e:
            return f"Исключение при выполнении инструмента {name}: {e}"

    async def process_user_request(self, session_id: str, user_prompt: str, status_callback=None) -> str:
        # 1. Сохраняем запрос пользователя в краткосрочную память
        self.memory.add_message(session_id, "user", user_prompt)

        # 2. Формируем контекст сообщений
        history = self.memory.get_history(session_id, limit=10)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Добавим долгосрочную память
        facts = self.memory.recall_facts()
        if facts:
            facts_str = "\n".join([f"- [{f['category']}] {f['key']}: {f['value']}" for f in facts[:10]])
            messages[0]["content"] += f"\n\nФАКТЫ ИЗ ДОЛГОСРОЧНОЙ ПАМЯТИ:\n{facts_str}"

        for h in history:
            messages.append(h)

        # 3. ReAct петля рассуждений
        for step in range(settings.max_react_steps):
            if status_callback:
                await status_callback(f"🧠 SLUGA размышляет (Шаг {step + 1}/{settings.max_react_steps})...")

            response_data = await self._chat_completion_with_fallback(messages)
            choice = response_data["choices"][0]
            message = choice["message"]
            tool_calls = message.get("tool_calls")

            if not tool_calls:
                # Финальный ответ модели
                final_text = message.get("content", "") or ""
                self.memory.add_message(session_id, "assistant", final_text)
                return final_text

            # Модель вызвала один или несколько инструментов
            assistant_msg = {
                "role": "assistant",
                "content": message.get("content"),
                "tool_calls": tool_calls
            }
            messages.append(assistant_msg)

            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"]["arguments"])
                except Exception:
                    fn_args = {}

                if status_callback:
                    await status_callback(f"🛠️ Выполнение инструмента: `{fn_name}`...")

                tool_result = await self.execute_tool(fn_name, fn_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": fn_name,
                    "content": tool_result
                })

        return "Достигнут максимальный лимит шагов ReAct петли. Промежуточный прогресс сохранен."
