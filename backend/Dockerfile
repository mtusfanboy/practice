# syntax=docker/dockerfile:1
# Dockerfile бэкенд-приложения (DO-01): Python + FastAPI.
# Многоступенчатая сборка для минимизации итогового образа.

# --- Этап сборки зависимостей ---
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Системные зависимости, необходимые для сборки некоторых пакетов.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

# --- Финальный образ ---
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Непривилегированный пользователь для запуска приложения.
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# Готовое виртуальное окружение из этапа сборки.
COPY --from=builder /opt/venv /opt/venv

# Исходный код приложения.
COPY app ./app

# Каталог для временных загрузок.
RUN mkdir -p /data/uploads && chown -R appuser:appuser /data /app

USER appuser

EXPOSE 8000

# Проверка работоспособности контейнера.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
