FROM python:3.11-slim

# Установка системных утилит (Git, curl, sqlite)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    sqlite3 \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копирование зависимостей и установка
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода агента и каталога навыков
COPY . .

# Создание директории данных
RUN mkdir -p /app/data

# Переменные по умолчанию
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py", "bot"]
