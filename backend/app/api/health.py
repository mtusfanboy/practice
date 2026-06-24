"""Эндпоинты проверки работоспособности сервиса и его зависимостей."""

from fastapi import APIRouter

from app.core.clients import clients
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Проверка жизнеспособности (liveness)")
async def health() -> dict[str, str]:
    """Базовая проверка того, что приложение запущено.

    :return: статус и версия приложения.
    """
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/health/ready", summary="Проверка готовности (readiness)")
async def readiness() -> dict[str, object]:
    """Проверка доступности внешних зависимостей.

    Опрашивает Elasticsearch и Redis. Возвращает агрегированный статус
    готовности, удобный для liveness/readiness-проб в оркестраторе.

    :return: словарь со статусом каждой зависимости и общим флагом ``ready``.
    """
    es_ok = await clients.es_service.ping() if clients.es_service else False
    redis_ok = await clients.cache_service.ping() if clients.cache_service else False

    return {
        "ready": bool(es_ok),  # ES критичен для поиска; Redis — опционален.
        "dependencies": {
            "elasticsearch": "up" if es_ok else "down",
            "redis": "up" if redis_ok else "down",
        },
    }
