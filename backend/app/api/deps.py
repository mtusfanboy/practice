"""FastAPI-зависимости для доступа к сервисам приложения."""

from fastapi import HTTPException, status

from app.core.clients import clients
from app.services.cache import CacheService
from app.services.elasticsearch_service import ElasticsearchService


def get_es_service() -> ElasticsearchService:
    """Вернуть сервис Elasticsearch.

    :return: инициализированный :class:`ElasticsearchService`.
    :raises HTTPException: 503, если сервис ещё не инициализирован.
    """
    if clients.es_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис поиска недоступен.",
        )
    return clients.es_service


def get_cache_service() -> CacheService:
    """Вернуть сервис кеширования.

    :return: инициализированный :class:`CacheService`.
    :raises HTTPException: 503, если сервис ещё не инициализирован.
    """
    if clients.cache_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис кеширования недоступен.",
        )
    return clients.cache_service
