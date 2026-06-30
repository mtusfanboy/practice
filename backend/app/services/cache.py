"""Кеширование поисковых запросов через Redis (BE-10).

Повторные одинаковые запросы обслуживаются из кеша с TTL = 5 минут,
что снижает нагрузку на Elasticsearch. При недоступности Redis сервис
деградирует «мягко»: запросы выполняются напрямую, без кеширования.
"""

import hashlib
import json
from typing import Any

from redis.asyncio import Redis

from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """Обёртка над Redis для кеширования результатов поиска."""

    _PREFIX = "search:"

    def __init__(self, client: Redis, ttl_seconds: int) -> None:
        """Инициализировать сервис кеша.

        :param client: асинхронный клиент Redis.
        :param ttl_seconds: время жизни записи кеша в секундах.
        """
        self._client = client
        self._ttl = ttl_seconds

    @staticmethod
    def _make_key(query: str, page: int, page_size: int) -> str:
        """Построить детерминированный ключ кеша для параметров запроса.

        :param query: текст поискового запроса.
        :param page: номер страницы.
        :param page_size: размер страницы.
        :return: строковый ключ кеша.
        """
        normalized = query.strip().lower()
        raw = f"{normalized}|{page}|{page_size}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"{CacheService._PREFIX}{digest}"

    async def get(self, query: str, page: int, page_size: int) -> dict[str, Any] | None:
        """Получить закешированный ответ на поисковый запрос.

        :param query: текст поискового запроса.
        :param page: номер страницы.
        :param page_size: размер страницы.
        :return: словарь с результатами или ``None``, если кеш пуст
            либо Redis недоступен.
        """
        key = self._make_key(query, page, page_size)
        try:
            raw = await self._client.get(key)
        except Exception as exc:  # noqa: BLE001 — мягкая деградация
            logger.warning("Redis недоступен при чтении кеша: %s", exc)
            return None

        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    async def set(
        self,
        query: str,
        page: int,
        page_size: int,
        value: dict[str, Any],
    ) -> None:
        """Сохранить ответ на поисковый запрос в кеш с TTL.

        :param query: текст поискового запроса.
        :param page: номер страницы.
        :param page_size: размер страницы.
        :param value: сериализуемый словарь с результатами поиска.
        """
        key = self._make_key(query, page, page_size)
        try:
            await self._client.set(
                key,
                json.dumps(value, ensure_ascii=False),
                ex=self._ttl,
            )
        except Exception as exc:  # noqa: BLE001 — мягкая деградация
            logger.warning("Redis недоступен при записи кеша: %s", exc)

    async def ping(self) -> bool:
        """Проверить доступность Redis.

        :return: ``True``, если Redis отвечает.
        """
        try:
            return bool(await self._client.ping())
        except Exception:  # noqa: BLE001
            return False
