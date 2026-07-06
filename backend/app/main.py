"""Точка входа FastAPI-приложения.

Собирает приложение: настраивает логирование, CORS, метрики Prometheus
(DO-06), подключает роутеры и инициализирует внешних клиентов в lifespan.
Документация OpenAPI 3.0 доступна по ``/docs`` (Swagger UI) и ``/redoc``.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.api import documents, health, search
from app.core.clients import clients
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.models.database import init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения.

    На старте: инициализирует БД и внешних клиентов (Elasticsearch, Redis).
    На остановке: корректно закрывает соединения.
    """
    configure_logging()
    logger.info("Запуск приложения '%s' v%s", settings.app_name, settings.app_version)

    try:
        await init_db()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось инициализировать БД на старте: %s", exc)

    await clients.startup()
    yield
    await clients.shutdown()
    logger.info("Приложение остановлено.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Интеллектуальная поисковая система по внутренней базе знаний "
        "университета. Загрузка PDF/DOCX, полнотекстовый поиск через "
        "Elasticsearch с подсветкой совпадений и кешированием в Redis."
    ),
    openapi_version="3.0.2",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS (DO-04/интеграция с фронтендом).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus-инструментирование: экспонирует /metrics (DO-06).
Instrumentator(
    should_group_status_codes=True,
    excluded_handlers=["/metrics", "/health", "/health/ready"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Преобразовать ошибки валидации запроса в ответ 400 Bad Request.

    По умолчанию FastAPI возвращает 422; для соответствия требованиям к
    API (400 — ошибка валидации) приводим формат к единому виду.
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Ошибка валидации запроса.", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Преобразовать необработанные исключения в ответ 500.

    Скрывает детали внутренней ошибки от клиента, но логирует их полностью.
    """
    logger.exception("Необработанная ошибка при обработке %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Внутренняя ошибка сервера."},
    )


# Подключение роутеров под префиксом /api/v1.
app.include_router(health.router)
app.include_router(documents.router, prefix=settings.api_v1_prefix)
app.include_router(search.router, prefix=settings.api_v1_prefix)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Корневой эндпоинт со ссылкой на документацию."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }
