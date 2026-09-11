"""
Модуль конфигурации агента SLUGA.
Поддерживает многопровайдерность:
1. Основная база: LiteAI (https://liteai.tech/)
2. Резервная база: Google AI Studio (OpenAI-compatible) через Cloudflare Worker

Работает абсолютно из коробки:
- Если pydantic-settings установлен — использует строгую Pydantic-валидацию.
- Если pydantic-settings еще не установлен — использует чистый встроенный парсер Python.
"""

import os
from pathlib import Path
from typing import List, Optional

BASE_DIR = Path(__file__).resolve().parent

class ConfigMethodsMixin:
    @property
    def allowed_user_ids(self) -> List[int]:
        raw = getattr(self, "telegram_allowed_users", "")
        if not raw:
            return []
        ids = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                ids.append(int(part))
        return ids

    def update_key_runtime(self, provider: str, new_key: str) -> str:
        provider_lower = provider.lower()
        if "lite" in provider_lower or "claude" in provider_lower:
            self.liteai_api_key = new_key
            self._persist_env_var("LITEAI_API_KEY", new_key)
            return "LiteAI API ключ успешно обновлен на лету."
        elif "google" in provider_lower or "gemini" in provider_lower:
            self.google_ai_studio_api_key = new_key
            self._persist_env_var("GOOGLE_AI_STUDIO_API_KEY", new_key)
            return "Google AI Studio API ключ успешно обновлен на лету."
        else:
            self.liteai_api_key = new_key
            self._persist_env_var("LITEAI_API_KEY", new_key)
            return f"Ключ для {provider} обновлен."

    def update_model_runtime(self, new_model: str) -> str:
        if "gemini" in new_model.lower():
            self.google_gemini_model = new_model
            self._persist_env_var("GOOGLE_GEMINI_MODEL", new_model)
        else:
            self.liteai_model = new_model
            self._persist_env_var("LITEAI_MODEL", new_model)
        return f"Модель переключена на: {new_model}"

    def _persist_env_var(self, key_name: str, key_value: str):
        env_path = BASE_DIR / ".env"
        lines = []
        key_found = False
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith(f"{key_name}="):
                        lines.append(f"{key_name}={key_value}\n")
                        key_found = True
                    else:
                        lines.append(line)
        if not key_found:
            lines.append(f"{key_name}={key_value}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field

    class Settings(BaseSettings, ConfigMethodsMixin):
        model_config = SettingsConfigDict(
            env_file=str(BASE_DIR / ".env"),
            env_file_encoding="utf-8",
            extra="ignore"
        )

        # LiteAI (Primary Provider)
        liteai_api_key: Optional[str] = Field(default=None, alias="LITEAI_API_KEY")
        liteai_base_url: str = Field(default="https://api.liteai.tech/v1", alias="LITEAI_BASE_URL")
        liteai_model: str = Field(default="claude-sonnet-4-6", alias="LITEAI_MODEL")

        # Google AI Studio via Cloudflare Worker
        google_ai_studio_api_key: Optional[str] = Field(default=None, alias="GOOGLE_AI_STUDIO_API_KEY")
        cf_gemini_proxy_url: str = Field(
            default="https://hermes-proxy.johnngoan66101996.workers.dev/v1beta/openai/",
            alias="CF_GEMINI_PROXY_URL"
        )
        google_gemini_model: str = Field(default="gemini-3.7-flash", alias="GOOGLE_GEMINI_MODEL")

        # Telegram Bot
        telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
        telegram_proxy_url: Optional[str] = Field(
            default="https://hermes-proxy.johnngoan66101996.workers.dev/",
            alias="TELEGRAM_PROXY_URL"
        )
        telegram_allowed_users: str = Field(default="", alias="TELEGRAM_ALLOWED_USERS")

        # System parameters
        sqlite_db_path: str = Field(default="./data/sluga_memory.db", alias="SQLITE_DB_PATH")
        log_level: str = Field(default="INFO", alias="LOG_LEVEL")
        max_react_steps: int = Field(default=12, alias="MAX_REACT_STEPS")
        auto_healing_enabled: bool = Field(default=True, alias="AUTO_HEALING_ENABLED")

except ImportError:
    class Settings(ConfigMethodsMixin):
        def __init__(self):
            self.liteai_api_key = None
            self.liteai_base_url = "https://api.liteai.tech/v1"
            self.liteai_model = "claude-sonnet-4-6"
            self.google_ai_studio_api_key = None
            self.cf_gemini_proxy_url = "https://hermes-proxy.johnngoan66101996.workers.dev/v1beta/openai/"
            self.google_gemini_model = "gemini-3.7-flash"
            self.telegram_bot_token = None
            self.telegram_proxy_url = "https://hermes-proxy.johnngoan66101996.workers.dev/"
            self.telegram_allowed_users = ""
            self.sqlite_db_path = "./data/sluga_memory.db"
            self.log_level = "INFO"
            self.max_react_steps = 12
            self.auto_healing_enabled = True
            self._load_from_env()

        def _load_from_env(self):
            env_file = BASE_DIR / ".env"
            if env_file.exists():
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip()
                            attr = k.lower()
                            if hasattr(self, attr):
                                if attr == "auto_healing_enabled":
                                    setattr(self, attr, v.lower() in ("1", "true", "yes"))
                                elif attr == "max_react_steps":
                                    setattr(self, attr, int(v) if v.isdigit() else 12)
                                else:
                                    setattr(self, attr, v)

settings = Settings()
