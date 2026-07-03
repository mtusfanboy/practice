"""Юнит-тесты сервиса кеширования поисковых запросов (BE-10, QA-01)."""

from typing import Any

from app.services.cache import CacheService


class FakeRedis:
    """Заглушка асинхронного клиента Redis на основе словаря."""

    def __init__(self, *, fail: bool = False) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self._fail = fail

    async def get(self, key: str) -> str | None:
        if self._fail:
            raise ConnectionError("redis down")
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        if self._fail:
            raise ConnectionError("redis down")
        self.store[key] = value
        if ex is not None:
            self.ttls[key] = ex

    async def ping(self) -> bool:
        if self._fail:
            raise ConnectionError("redis down")
        return True


def test_cache_key_is_deterministic_and_normalized() -> None:
    """Ключ кеша одинаков для запросов, различающихся регистром и пробелами."""
    key_a = CacheService._make_key("  Базы Данных ", 1, 10)
    key_b = CacheService._make_key("базы данных", 1, 10)
    assert key_a == key_b
    # Разные параметры пагинации дают разные ключи.
    assert key_a != CacheService._make_key("базы данных", 2, 10)


async def test_set_then_get_roundtrip() -> None:
    """Сохранённое значение читается обратно из кеша с TTL."""
    redis = FakeRedis()
    cache = CacheService(redis, ttl_seconds=300)
    payload: dict[str, Any] = {"total": 2, "results": [{"text": "пример"}]}

    await cache.set("запрос", 1, 10, payload)
    restored = await cache.get("запрос", 1, 10)

    assert restored == payload
    # TTL установлен в соответствии с настройкой (BE-10: 5 минут).
    assert set(redis.ttls.values()) == {300}


async def test_get_miss_returns_none() -> None:
    """Отсутствующий в кеше запрос возвращает None."""
    cache = CacheService(FakeRedis(), ttl_seconds=300)
    assert await cache.get("неизвестный", 1, 10) is None


async def test_cache_degrades_gracefully_on_failure() -> None:
    """При недоступности Redis сервис не выбрасывает исключений."""
    cache = CacheService(FakeRedis(fail=True), ttl_seconds=300)
    # Ни get, ни set не должны падать.
    assert await cache.get("запрос", 1, 10) is None
    await cache.set("запрос", 1, 10, {"total": 0, "results": []})
    assert await cache.ping() is False
