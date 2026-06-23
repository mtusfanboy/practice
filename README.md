# Интеллектуальная поисковая система по внутренней базе знаний университета

Полнофункциональное веб-приложение для загрузки документов (PDF/DOCX) и
полнотекстового поиска по ним с ранжированием и подсветкой совпадений.
Проект построен на микросервисной архитектуре и разворачивается одной
командой через Docker Compose.

## Содержание

- [Возможности](#возможности)
- [Архитектура](#архитектура)
- [Технологический стек](#технологический-стек)
- [Структура репозитория](#структура-репозитория)
- [Быстрый старт](#быстрый-старт)
- [Локальная разработка](#локальная-разработка)
- [API](#api)
- [Тестирование](#тестирование)
- [Мониторинг](#мониторинг)
- [Наполнение тестовыми данными](#наполнение-тестовыми-данными)
- [Переменные окружения](#переменные-окружения)
- [Соответствие требованиям](#соответствие-требованиям)

## Возможности

- **Загрузка документов** PDF и DOCX через Drag-and-Drop с множественным
  выбором и индикацией прогресса загрузки и индексации.
- **Извлечение текста** (pdfplumber / python-docx) и разбиение на чанки по
  1000 символов с перекрытием 100 символов.
- **Полнотекстовый поиск** через Elasticsearch с русскоязычным анализатором,
  ранжированием по релевантности и подсветкой совпадений.
- **Кеширование** частых запросов в Redis (TTL = 5 минут).
- **История** поисковых запросов.
- **Мониторинг** метрик (Prometheus + Grafana).
- **Документация API** через OpenAPI 3.0 (Swagger UI).

## Архитектура

Система состоит из независимых сервисов, объединённых в одну Docker-сеть:

```
                ┌─────────────┐
   Браузер ───▶ │   front     │  React (статика) + Nginx
                │  (Nginx)    │  проксирует /api ─┐
                └─────────────┘                   │
                                                  ▼
                                          ┌─────────────┐
                                          │     app     │  FastAPI (Python)
                                          │  (FastAPI)  │
                                          └──────┬──────┘
                          ┌──────────────────────┼──────────────────────┐
                          ▼                       ▼                      ▼
                  ┌─────────────┐        ┌─────────────────┐     ┌────────────┐
                  │  postgres   │        │  elasticsearch  │     │   redis    │
                  │ (метаданные)│        │ (индекс чанков) │     │   (кеш)    │
                  └─────────────┘        └─────────────────┘     └────────────┘

   Наблюдаемость:  prometheus  ◀── /metrics ── app        grafana ◀── prometheus
```

- **Загрузка**: `front` → `app` (`POST /api/v1/documents/upload`) → метаданные
  в `postgres`, файл парсится и чанки индексируются в `elasticsearch`
  (асинхронно, в фоне). Статус отслеживается через список документов.
- **Поиск**: `front` → `app` (`GET /api/v1/search`) → проверка кеша в `redis`,
  при промахе — запрос к `elasticsearch`, ответ кешируется, запрос пишется в
  историю в `postgres`.

## Технологический стек

| Слой         | Технологии                                                   |
|--------------|--------------------------------------------------------------|
| Backend      | Python 3.12, FastAPI, SQLAlchemy (async), Pydantic v2        |
| Поиск/кеш    | Elasticsearch 8, Redis 7                                     |
| БД           | PostgreSQL 16                                                |
| Frontend     | TypeScript, React 18, Vite 5, Nginx                          |
| Парсинг      | pdfplumber, python-docx                                      |
| DevOps       | Docker, Docker Compose, GitHub Actions                       |
| Мониторинг   | Prometheus, Grafana                                          |
| Тестирование | pytest, Playwright, Locust                                   |

## Структура репозитория

```
.
├── backend/                  # Бэкенд (FastAPI)
│   ├── app/
│   │   ├── api/              # Эндпоинты (documents, search, health)
│   │   ├── core/            # Конфигурация, логирование, метрики, клиенты
│   │   ├── models/          # SQLAlchemy-модели + подключение к БД
│   │   ├── schemas/         # Pydantic-схемы (контракт API)
│   │   ├── services/        # Парсинг, чанкинг, индексация, кеш
│   │   └── main.py          # Точка входа FastAPI
│   ├── tests/               # Юнит- и интеграционные тесты (QA-01)
│   │   └── fixtures/        # Тестовые документы и их генератор (QA-03)
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pyproject.toml       # Конфигурация ruff / pytest / coverage
│   └── Dockerfile
├── frontend/                 # Фронтенд (React + TypeScript + Vite)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/        # Запросы к API
│   │   └── App.tsx
│   ├── package.json
│   ├── nginx.conf
│   └── Dockerfile
├── monitoring/               # Конфигурация Prometheus и Grafana
├── qa/                       # E2E (Playwright), нагрузка (Locust), Precision@3
├── docker-compose.yml        # Оркестрация всех сервисов
├── .env.example              # Шаблон переменных окружения
├── .github/workflows/ci.yml  # CI/CD (линтеры, тесты, сборка образов)
├── init.sh                   # Наполнение системы тестовыми PDF
└── README.md
```

## Быстрый старт

Требования: установленные **Docker** и **Docker Compose**.

```bash
# 1. Скопировать шаблон переменных окружения и при желании изменить пароли
cp .env.example .env

# 2. Собрать и запустить весь стек
docker compose up --build

# 3. (Опционально) наполнить систему тестовыми PDF-лекциями
./init.sh
```

После запуска доступны:

| Сервис             | URL                              |
|--------------------|----------------------------------|
| Веб-интерфейс      | http://localhost:3000            |
| API (Swagger UI)   | http://localhost:8000/docs       |
| API (ReDoc)        | http://localhost:8000/redoc      |
| Prometheus         | http://localhost:9090            |
| Grafana            | http://localhost:3001 (admin/admin) |

> Первый запуск Elasticsearch занимает 30–60 секунд — дождитесь состояния
> `healthy` у контейнера `ks-elasticsearch`.

## Локальная разработка

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# Для локального запуска нужны PostgreSQL, Elasticsearch и Redis
# (можно поднять только их: docker compose up postgres elasticsearch redis)
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (проксирует /api на :8000)
```

## API

Все эндпоинты задокументированы по стандарту OpenAPI 3.0 и доступны в
Swagger UI (`/docs`).

| Метод    | Путь                              | Назначение                          |
|----------|-----------------------------------|-------------------------------------|
| `POST`   | `/api/v1/documents/upload`        | Загрузка документа (PDF/DOCX)       |
| `GET`    | `/api/v1/documents`               | Список документов и их статусы      |
| `GET`    | `/api/v1/documents/{id}`          | Метаданные документа                |
| `DELETE` | `/api/v1/documents/{id}`          | Удаление документа                  |
| `GET`    | `/api/v1/search?q=...`            | Полнотекстовый поиск                |
| `GET`    | `/api/v1/search/history`          | История поисковых запросов          |
| `GET`    | `/health`, `/health/ready`        | Проверка работоспособности          |
| `GET`    | `/metrics`                        | Метрики Prometheus                  |

Коды ответов: `200/201` — успех, `400` — ошибка валидации, `404` — не
найдено, `500` — внутренняя ошибка.

## Тестирование

```bash
# Юнит- и интеграционные тесты бэкенда с покрытием (QA-01)
cd backend && pytest

# E2E-тесты (требуется запущенный стек) (QA-02)
cd qa/e2e && npm install && npm run install:browsers && npm test

# Нагрузочное тестирование, 50 пользователей (QA-04)
pip install -r qa/requirements.txt
locust -f qa/load/locustfile.py --host http://localhost:8000 \
    --users 50 --spawn-rate 10 --run-time 1m --headless --csv qa/load/report

# Оценка качества поиска Precision@3 (QA-05)
python qa/evaluation/precision_at_3.py --host http://localhost:8000
```

Подробности — в [`qa/README.md`](qa/README.md). Текущее покрытие бэкенда
тестами — **более 80 %** (требование — не менее 50 %).

## Мониторинг

Бэкенд экспонирует метрики Prometheus по `/metrics`, включая
специализированные:

- `search_requests_total{source}` — количество поисковых запросов;
- `search_latency_seconds` — время выполнения поиска;
- `documents_uploaded_total{status}` — загруженные документы по статусу.

В Grafana автоматически подключается источник Prometheus и дашборд
**«Knowledge Search — Overview»** (число запросов к поиску, среднее время
ответа и др.).

## Наполнение тестовыми данными

Скрипт `init.sh` скачивает 10 общедоступных PDF и загружает их в систему:

```bash
./init.sh                                  # бэкенд на localhost:8000
BACKEND_URL=http://localhost:8000 ./init.sh
```

## Переменные окружения

Все секреты вынесены в `.env` (см. `.env.example`). Ключевые параметры:
порты сервисов, учётные данные PostgreSQL, индекс и память Elasticsearch,
TTL кеша, максимальный размер загружаемого файла, доступ к Grafana.

## Авторизация

Согласно техническому заданию, для прототипа авторизация может
отсутствовать. В текущей версии система работает без авторизации; при
необходимости упрощённая схема логин/пароль может быть добавлена на уровне
бэкенда (middleware) и фронтенда без изменения остальной архитектуры.

## Соответствие требованиям

<details>
<summary>Backend (BE-01 … BE-10)</summary>

| ID    | Реализация                                                                 |
|-------|----------------------------------------------------------------------------|
| BE-01 | `app/api/documents.py` → `POST /api/v1/documents/upload`                    |
| BE-02 | `_validate_upload` (формат PDF/DOCX, размер ≤ 20 МБ, HTTP 400)              |
| BE-03 | UUID документа (`app/models/document.py`, `uuid.uuid4`)                     |
| BE-04 | `app/services/parser.py` (pdfplumber, python-docx)                         |
| BE-05 | `app/services/chunker.py` (1000 символов, перекрытие 100)                  |
| BE-06 | `app/services/elasticsearch_service.py` (`ru_analyzer`, индекс `documents`) |
| BE-07 | `index_chunks` (метаданные file_name, page_number, chunk_id, text)         |
| BE-08 | `GET /api/v1/search` (`multi_match` по `text`)                              |
| BE-09 | JSON-результаты с chunk_id, file_name, page, text, score                    |
| BE-10 | `app/services/cache.py` (Redis, TTL = 300 с)                               |
</details>

<details>
<summary>Frontend (FE-01 … FE-09)</summary>

| ID    | Реализация                                                                 |
|-------|----------------------------------------------------------------------------|
| FE-01 | `components/DropZone.tsx` (Drag-and-Drop, множественная загрузка)           |
| FE-02 | `components/UploadProgressList.tsx` (прогресс: Загрузка/Индексация/Готово/Ошибка) |
| FE-03 | `components/DocumentList.tsx` (название, дата, статус)                      |
| FE-04 | `components/SearchBar.tsx` (кнопка «Найти» + Enter)                         |
| FE-05 | `components/ResultCard.tsx` (файл, страница, фрагмент, релевантность)       |
| FE-06 | `components/HighlightedText.tsx` (подсветка `<mark>`, жёлтый фон)           |
| FE-07 | `components/Pagination.tsx` (по 10 результатов)                            |
| FE-08 | Сообщение «По вашему запросу ничего не найдено…»                            |
| FE-09 | Адаптивная вёрстка 320–1920px (`styles/index.css`)                          |
</details>

<details>
<summary>DevOps (DO-01 … DO-07)</summary>

| ID    | Реализация                                                                 |
|-------|----------------------------------------------------------------------------|
| DO-01 | `backend/Dockerfile` (Python + FastAPI, multi-stage)                       |
| DO-02 | `frontend/Dockerfile` (Node build → Nginx)                                 |
| DO-03 | `docker-compose.yml` (app, front, postgres, elasticsearch, redis)          |
| DO-04 | `.env` / `.env.example` (секреты через переменные окружения)               |
| DO-05 | `.github/workflows/ci.yml` (линтеры, тесты, сборка образов)                 |
| DO-06 | `monitoring/` (Prometheus + Grafana, дашборд)                              |
| DO-07 | `init.sh` (скачивание и загрузка 10 PDF)                                    |
</details>

<details>
<summary>QA (QA-01 … QA-06)</summary>

| ID    | Реализация                                                                 |
|-------|----------------------------------------------------------------------------|
| QA-01 | `backend/tests/` (pytest, покрытие > 50 %)                                  |
| QA-02 | `qa/e2e/` (Playwright, сценарий загрузка→индексация→поиск)                  |
| QA-03 | `backend/tests/fixtures/` (корректные, пустые, битые, нестандартный шрифт)  |
| QA-04 | `qa/load/locustfile.py` (50 одновременных пользователей)                    |
| QA-05 | `qa/evaluation/precision_at_3.py` (Precision@3, Markdown-таблица)           |
| QA-06 | Руководство пользователя — готовится отдельно (отчётность)                  |
</details>
