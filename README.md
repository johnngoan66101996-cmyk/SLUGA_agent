# 🤖 SLUGA_agent: Автономный Инженер-Хирург ИИ

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![SQLite WAL](https://img.shields.io/badge/Memory-SQLite%20WAL-003B57.svg)](https://sqlite.org/)
[![Cloudflare Worker](https://img.shields.io/badge/Proxy-Cloudflare%20Worker-F38020.svg)](https://workers.cloudflare.com/)

---

## ⚡ Особенности

1. **Без искусственных ограничений:** Полный карт-бланш на выполнение команд в терминале, рефакторинг, сборку и работу с файловой системой.
2. **Золотая Триада Первого Шага:**
   - 🛡️ **Шаг 1:** Стерильная изолированная среда (`finch-sandbox`).
   - 🔬 **Шаг 2:** Диагностика и МРТ проекта (`project-doctor`).
   - 🛑 **Шаг 3:** «Не навреди» — предотвращение потери данных (`accidental-data-loss-prevention`).
3. **116 офлайн-навыков в `./skills/`:** Динамический On-Demand загрузчик передает регламенты в контекст только при необходимости.
4. **Многопровайдерность с отказоустойчивостью:**
   - **Основная база:** [LiteAI](https://liteai.tech/) — доступ к Claude (Sonnet 4.6 / Opus 4.8 / Sonnet 5 / Opus 4.8[1m]), GPT-5.5 / 5.6-terra, OpenRouter в РФ без VPN.
   - **Резервная база:** Google AI Studio (Gemini 3.7 / 3.6 / 3.8 Flash) через Cloudflare Worker прокси (`cloudflare_worker.js`).
5. **Сверхнизкие системные требования:**
   - Потребление RAM: ~50–150 МБ (база SQLite WAL вместо тяжелых PostgreSQL/Redis).
   - Работает на самом бюджетном VPS (1 vCPU, 512 MB – 1 GB RAM).

---

## 📁 Структура Репозитория

```text
├── AGENTS.md               # Системное ядро, манифест и единый источник правды
├── cloudflare_worker.js    # Скрипт прокси для Cloudflare Worker (Telegram + Gemini)
├── config.py               # Валидация настроек окружения
├── main.py                 # Главная точка входа (CLI и Telegram Bot)
├── wizard.py               # Интерактивный мастер установки
├── requirements.txt        # Минимальные зависимости
├── Dockerfile              # Контейнеризация для VPS
├── docker-compose.yml      # Развертывание одной командой
├── setup.sh                # Автоустановка для Linux
├── setup.ps1               # Автоустановка для Windows
├── core/                   # Ядро агента
│   ├── engine.py           # ReAct Tool Loop с multi-provider fallback
│   ├── memory.py           # Двухуровневая память SQLite WAL (STM + LTM)
│   ├── self_healing.py     # Контур самоисцеления Actor-Critic
│   └── skill_loader.py     # On-Demand загрузчик 116 навыков
├── channels/               # Каналы связи
│   └── telegram_bot.py     # Telegram Bot на aiogram 3 с проксированием
├── daemons/                # Фоновые процессы
│   └── scheduler.py        # Heartbeat и фоновый планировщик задач
├── tools/                  # Инструменты хирурга
│   ├── terminal_runner.py  # Асинхронный терминал (Bash/PowerShell)
│   ├── claw_search.py      # DuckDuckGo HTML поисковик и парсер страниц
│   └── project_doctor.py   # МРТ проекта
└── skills/                 # Каталог 116 инженерных навыков
```

---

## 🚀 Быстрый Старт

### 1. Клонирование с GitHub
```bash
git clone <URL_ТВОЕГО_РЕПОЗИТОРИЯ>
cd <ПАПКА_РЕПОЗИТОРИЯ>
```

### 2. Настройка окружения
Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

Заполните ключевые переменные в `.env`:
```env
# Основной провайдер: LiteAI (https://liteai.tech/)
LITEAI_API_KEY=твой_ключ_liteai
LITEAI_BASE_URL=https://api.liteai.tech/v1
LITEAI_MODEL=claude-sonnet-4-6

# Резервный провайдер: Google AI Studio через твой Cloudflare Worker
GOOGLE_AI_STUDIO_API_KEY=твой_ключ_google_ai_studio
CF_GEMINI_PROXY_URL=https://hermes-proxy.johnngoan66101996.workers.dev/v1beta/openai/
GOOGLE_GEMINI_MODEL=gemini-3.7-flash

# Telegram Бот (если используется):
TELEGRAM_BOT_TOKEN=твой_токен_бота
TELEGRAM_PROXY_URL=https://hermes-proxy.johnngoan66101996.workers.dev/
TELEGRAM_ALLOWED_USERS=твой_telegram_id
```

### 3. Запуск

#### Вариант A: Docker Compose (Рекомендуется для VPS)
```bash
docker compose up -d
```

#### Вариант B: Нативный запуск (Linux VPS)
```bash
chmod +x setup.sh
./setup.sh
source .venv/bin/activate
python main.py bot
```

#### Вариант C: Windows
```powershell
.\setup.ps1
.venv\Scripts\python.exe main.py bot
```

#### Вариант D: Прямой CLI-режим (терминальный чат)
```bash
python main.py cli
```

---

## 🌐 Настройка Cloudflare Worker Proxy

Для обхода блокировок Google AI Studio и Telegram API в РФ используется Cloudflare Worker:
1. Откройте [dash.cloudflare.com](https://dash.cloudflare.com/) -> **Workers & Pages** -> **Create Application**.
2. Вставьте код из файла [`cloudflare_worker.js`](file:///c:/Users/sugat/OneDrive/Desktop/%D1%81%D0%BA%D0%B8%D0%BB%D1%8B/cloudflare_worker.js).
3. Нажмите **Deploy**. Полученный URL укажите в `CF_GEMINI_PROXY_URL` и `TELEGRAM_PROXY_URL`.

---

## 🎮 Команды в Telegram

- `/start` — Информация об агенте и статус подключения
- `/doctor` — МРТ текущего проекта и рекомендации безопасности
- `/skills` — Каталог доступных инженерных навыков
- `/status` — Состояние памяти SQLite, сессий и активных моделей
- `/reset` — Сброс контекста текущей сессии
