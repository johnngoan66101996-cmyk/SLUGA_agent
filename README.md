# 🤖 SLUGA_agent: Автономный Инженер-Хирург ИИ

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![SQLite WAL](https://img.shields.io/badge/Memory-SQLite%20WAL-003B57.svg)](https://sqlite.org/)
[![Cloudflare Worker](https://img.shields.io/badge/Proxy-Cloudflare%20Worker-F38020.svg)](https://workers.cloudflare.com/)

---

## ⚡ Установка в 1 команду (Универсальный онлайн-инсталлятор)

> 💡 **Работает из любого места** (включая `System32` от администратора).  
> Скрипт сам предложит выбор и создаст безопасную папку (например, `C:\SLUGA_agent` или на Рабочем столе), клонирует проект, установит окружение и запустит мастера настройки.

### 🪟 Windows (PowerShell):
```powershell
irm https://raw.githubusercontent.com/johnngoan66101996-cmyk/SLUGA_agent/main/install.ps1 | iex
```

### 🐧 Linux / VPS (Bash):
```bash
curl -fsSL https://raw.githubusercontent.com/johnngoan66101996-cmyk/SLUGA_agent/main/install.sh | bash
```

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

## 🚀 Быстрый Старт (Установка в 1 команду)

### Способ 1: Установка в 1 команду через PowerShell (Windows)
> 💡 Работает из **любой** папки (включая System32). Скрипт сам предложит выбор (например, `C:\SLUGA_agent` или Рабочий стол) и всё настроит:
```powershell
irm https://raw.githubusercontent.com/johnngoan66101996-cmyk/SLUGA_agent/main/install.ps1 | iex
```

### Способ 2: Установка в 1 команду на Linux / VPS
```bash
curl -fsSL https://raw.githubusercontent.com/johnngoan66101996-cmyk/SLUGA_agent/main/install.sh | bash
```

---

### Способ 3: Ручное клонирование с GitHub
```bash
git clone https://github.com/johnngoan66101996-cmyk/SLUGA_agent.git
cd SLUGA_agent
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

# Резервный провайдер: Google AI Studio (https://aistudio.google.com/)
GOOGLE_AI_STUDIO_API_KEY=твой_ключ_google_ai_studio
# Для РФ укажите URL вашего Cloudflare Worker (с суффиксом /v1beta/openai/):
# Если сервер за рубежом — оставьте: https://generativelanguage.googleapis.com/v1beta/openai/
CF_GEMINI_PROXY_URL=https://your-worker-subdomain.workers.dev/v1beta/openai/
GOOGLE_GEMINI_MODEL=gemini-3.7-flash

# Telegram Бот (если используется):
TELEGRAM_BOT_TOKEN=твой_токен_бота
# Для РФ укажите URL вашего Cloudflare Worker (например: https://your-worker-subdomain.workers.dev/)
# Если сервер за рубежом — оставьте пустым для прямого подключения:
TELEGRAM_PROXY_URL=https://your-worker-subdomain.workers.dev/
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

## 🌐 Пошаговая инструкция: Создание своего Cloudflare Worker Proxy

Для обхода блокировок Google AI Studio и Telegram API на территории РФ используется собственный бесплатный прокси на базе Cloudflare Workers (тариф Free предоставляет 100,000 запросов в день бесплатно, без привязки банковской карты).

> **💡 Примечание:** Если ваш сервер или ПК находится за пределами РФ (или используется VPN), настраивать Cloudflare Worker **не требуется** — агент подключается к Google AI Studio и Telegram напрямую.

### Порядок действий (занимает 2 минуты):

1. **Регистрация в Cloudflare:**
   - Перейдите на [dash.cloudflare.com](https://dash.cloudflare.com/) и войдите или зарегистрируйтесь.
2. **Создание Worker:**
   - В левом меню выберите **Workers & Pages** (или **Compute (Workers)**).
   - Нажмите кнопку **Create Application** -> выберите вкладку **Workers** -> **Create Worker**.
   - Задайте имя воркера (например, `sluga-proxy`) и нажмите **Deploy**.
3. **Загрузка кода прокси:**
   - На открывшейся странице воркера нажмите кнопку **Edit code**.
   - Удалите стандартный шаблон кода и вставьте содержимое файла [`cloudflare_worker.js`](./cloudflare_worker.js) из этого репозитория.
   - Нажмите **Deploy** (или **Save and Deploy**).
4. **Получение URL вашего воркера:**
   - Скопируйте готовый адрес вашего воркера, он имеет вид:  
     `https://sluga-proxy.<твой-поддомен>.workers.dev`
5. **Указание в настройках агента (`.env` или через Мастер установки `wizard.py`):**
   - **Для Google Gemini API:** добавьте суффикс `/v1beta/openai/`:  
     `CF_GEMINI_PROXY_URL=https://sluga-proxy.<твой-поддомен>.workers.dev/v1beta/openai/`
   - **Для Telegram Bot API:** укажите базовый URL со слэшем на конце:  
     `TELEGRAM_PROXY_URL=https://sluga-proxy.<твой-поддомен>.workers.dev/`

### Ссылки на сервисы для ключей:
- **LiteAI (Claude Sonnet 4.6 / GPT-5.5 без VPN):** [https://liteai.tech/](https://liteai.tech/)
- **Google AI Studio (Бесплатные ключи Gemini 3.7):** [https://aistudio.google.com/](https://aistudio.google.com/)
- **Cloudflare Dashboard (Бесплатный воркер-прокси):** [https://dash.cloudflare.com/](https://dash.cloudflare.com/)
- **Telegram BotFather (Создание бота и токен):** [https://t.me/BotFather](https://t.me/BotFather)

---

## 🎮 Команды агента (CLI-терминал и Telegram)

| Команда | Описание |
|---|---|
| `/keys` | Показать текущие активные API-ключи (в маскированном виде) и выбранные модели |
| `/key liteai <ключ>` | Установить или сменить ключ LiteAI **на ходу** без перезапуска (сохраняется в `.env`) |
| `/key google <ключ>` | Установить или сменить ключ Google AI Studio **на ходу** |
| `/model <имя_модели>` | Переключить модель на лету (`claude-sonnet-4-6`, `gemini-3.6-flash`, `GPT-5.5` и др.) |
| `/setup` | Запустить интерактивный мастер настройки конфигурации |
| `/doctor` | Запустить экспресс-диагностику проекта (МРТ) |
| `/skills` | Просмотреть каталог доступных инженерных навыков (116 навыков) |
| `/status` | Состояние памяти SQLite (STM + LTM), сессий и активных модулей |
| `/reset` | Очистить контекст текущего диалога |

---

## 💡 Решение частых вопросов (Troubleshooting)

### ⚠️ Ошибка: `503 Service Unavailable` («This model is currently experiencing high demand»)
**Причина:** Ваш Cloudflare Worker и API-ключ работают исправно. Ошибка 503 означает, что в данный момент бесплатные серверы Google AI Studio временно перегружены запросами со всего мира.

**Что делать в этой ситуации:**
1. **Вариант 1 (Самый простой):** Подождать 15–30 секунд и повторить запрос (просто отправить сообщение в чат еще раз). Всплески нагрузки на серверах Google кратковременны.
2. **Вариант 2 (Переключиться на Gemini 3.6):**  
   Переключите модель на ходу командой:
   ```text
   /model gemini-3.6-flash
   ```
   Либо в файле `.env` укажите: `GOOGLE_GEMINI_MODEL=gemini-3.6-flash`. Модель 3.6 не испытывает очередей и отвечает моментально.
3. **Вариант 3 (Рекомендуется для боевой работы — LiteAI):**  
   Для круглосуточной стабильности без лимитов очередей подключите **LiteAI** (Claude Sonnet 4.6 / GPT-5.5) через [liteai.tech](https://liteai.tech/):
   - Введите прямо в чат команду:
     ```text
     /key liteai твой_ключ_liteai
     ```
   - Либо пропишите в `.env`: `LITEAI_API_KEY=твой_ключ_liteai`.
   - Агент автоматически начнет работать через стабильный шлюз Claude, а Gemini останется резервным каналом.

---

## 🗑️ Полное удаление и деинсталляция (Uninstallation)

Если вам необходимо полностью удалить агента SLUGA, его виртуальное окружение `.venv`, локальную базу SQLite и конфигурацию, выберите подходящий вариант:

### Способ 1: Удаление в 1 команду на Windows (PowerShell)
Запустите PowerShell и выполните команду онлайн-деинсталлятора:
```powershell
irm https://raw.githubusercontent.com/johnngoan66101996-cmyk/SLUGA_agent/main/uninstall.ps1 | iex
```
> 💡 *Скрипт автоматически обнаружит установку, корректно завершит процессы агента, запросит подтверждение и чисто удалит папку агента (по умолчанию `C:\SLUGA_agent` или на Рабочем столе).*

#### Ручное удаление в PowerShell:
```powershell
# 1. Завершить активные процессы агента:
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*SLUGA_agent*" -or $_.CommandLine -like "*main.py*" } | Stop-Process -Force

# 2. Удалить папку со всеми файлами (C:\SLUGA_agent или указанный вами путь):
Remove-Item -Path "C:\SLUGA_agent" -Recurse -Force
```

---

### Способ 2: Удаление в 1 команду на Linux / VPS (Bash)
Выполните команду онлайн-деинсталлятора в терминале:
```bash
curl -fsSL https://raw.githubusercontent.com/johnngoan66101996-cmyk/SLUGA_agent/main/uninstall.sh | bash
```

#### Ручное удаление в Linux:
```bash
# 1. Завершить процессы агента:
pkill -f "python.*main.py" || true

# 2. Удалить директорию агента:
rm -rf "$HOME/SLUGA_agent"
```

---

### Способ 3: Удаление при установке через Docker Compose
Если агент был развернут через Docker на сервере:
```bash
# 1. Перейти в папку проекта:
cd ~/SLUGA_agent

# 2. Остановить контейнеры, удалить сеть, тома и образы:
docker compose down -v --rmi all

# 3. Удалить файлы проекта:
cd ~ && rm -rf ~/SLUGA_agent
```
