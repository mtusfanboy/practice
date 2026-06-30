"""Управление жизненным циклом внешних клиентов (Elasticsearch, Redis).

Клиенты создаются один раз при старте приложения и переиспользуются на
протяжении его работы. Сервисы (Elasticsearch, кеш) строятся поверх этих
клиентов и предоставляются через FastAPI-зависимости.
"""

from elasticsearch import AsyncElasticsearch
from redis.asyncio import Redis

from app.core.config import settings
from app.core.logging import get_logger
from app.services.cache import CacheService
from app.services.elasticsearch_service import ElasticsearchService

logger = get_logger(__name__)


class Clients:
    """Контейнер общих клиентов и сервисов приложения."""

    def __init__(self) -> None:
        self.elasticsearch: AsyncElasticsearch | None = None
        self.redis: Redis | None = None
        self.es_service: ElasticsearchService | None = None
        self.cache_service: CacheService | None = None

    async def startup(self) -> None:
        """Создать клиентов и подготовить индекс Elasticsearch."""
        self.elasticsearch = AsyncElasticsearch(
            hosts=[settings.elasticsearch_url],
            request_timeout=30,
            retry_on_timeout=True,
            max_retries=3,
        )
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)

        self.es_service = ElasticsearchService(
            self.elasticsearch, settings.elasticsearch_index
        )
        self.cache_service = CacheService(self.redis, settings.cache_ttl_seconds)

        # Подготавливаем индекс. Ошибки на старте логируются, но не валят
        # приложение — Elasticsearch может подняться чуть позже.
        try:
            await self.es_service.ensure_index()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось подготовить индекс ES на старте: %s", exc)

    async def shutdown(self) -> None:
        """Корректно закрыть соединения клиентов."""
        if self.elasticsearch is not None:
            await self.elasticsearch.close()
        if self.redis is not None:
            await self.redis.aclose()


# Глобальный контейнер клиентов, инициализируемый в lifespan приложения.
clients = Clients()
