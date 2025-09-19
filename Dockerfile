FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ✅ копіюємо правильний requirements.txt
COPY chatbot_project/backend/requirements.txt /app/requirements.txt

# Встановлюємо залежності (сюди входить і openpyxl, якщо він у файлі)
RUN python -m pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.txt \
 && pip install --no-cache-dir gunicorn

# Далі — увесь код
COPY . /app

# Робочий каталог із manage.py (далі його перевизначаєш у compose для web/bot)
WORKDIR /app/chatbot_project
