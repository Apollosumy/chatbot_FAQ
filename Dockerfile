FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Копіюємо лише requirements на ранньому етапі для кешу
WORKDIR /app
COPY chatbot_project/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt && \
    pip install --no-cache-dir gunicorn

# Далі — увесь код
COPY . /app

# Робоча директорія = ваша папка з manage.py та bot/
WORKDIR /app/chatbot_project

# (Якщо в Django використовується STATIC_ROOT, він керуватиме місцем для статики)
