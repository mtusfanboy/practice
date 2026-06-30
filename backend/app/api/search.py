"""Эндпоинты полнотекстового поиска и истории запросов (BE-08, BE-09, BE-10)."""

import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_cache_service, get_es_service
from app.core.logging import get_logger
from app.core.metrics import SEARCH_LATENCY_SECONDS, SEARCH_REQUESTS_TOTAL
from app.models.database import get_db
from app.models.document import SearchQuery
from app.schemas.search import (
    SearchHistoryItem,
    SearchHistoryResponse,
    SearchResponse,
)
from app.services.cache import CacheService
from app.services.elasticsearch_service import ElasticsearchService

logger = get_logger(__name__)

router = APIRouter(tags=["search"])


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Полнотекстовый поиск по документам",
)
async def search(
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
    page: int = Query(default=1, ge=1, description="Номер страницы (с 1)"),
    page_size: int = Query(default=10, ge=1, le=50, description="Результатов на странице"),
    es_service: ElasticsearchService = Depends(get_es_service),
    cache_service: CacheService = Depends(get_cache_service),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Выполнить полнотекстовый поиск по проиндексированным документам.

    Реализует требования BE-08 (поиск через ``multi_match``), BE-09
    (формат результатов) и BE-10 (кеширование в Redis с TTL = 5 минут).
    Каждый запрос сохраняется в историю поиска.

    :param q: текст поискового запроса.
    :param page: номер страницы результатов (пагинация, FE-07).
    :param page_size: количество результатов на странице.
    :return: результаты поиска с метаданными о времени и источнике ответа.
    """
    started = time.perf_counter()
    query_text = q.strip()

    # BE-10: проверяем кеш перед обращением к Elasticsearch.
    cached = await cache_service.get(query_text, page, page_size)
    if cached is not None:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        SEARCH_REQUESTS_TOTAL.labels(source="cache").inc()
        SEARCH_LATENCY_SECONDS.observe(time.perf_counter() - started)
        await _save_history(
            db, query_text, cached["total"], elapsed_ms, from_cache=True
        )
        return SearchResponse(
            query=query_text,
            total=cached["total"],
            page=page,
            page_size=page_size,
            took_ms=elapsed_ms,
            from_cache=True,
            results=cached["results"],
        )

    # Запрос к Elasticsearch (BE-08).
    outcome = await es_service.search(query_text, page=page, page_size=page_size)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    SEARCH_REQUESTS_TOTAL.labels(source="elasticsearch").inc()
    SEARCH_LATENCY_SECONDS.observe(time.perf_counter() - started)

    payload = {"total": outcome["total"], "results": outcome["results"]}
    await cache_service.set(query_text, page, page_size, payload)
    await _save_history(
        db, query_text, outcome["total"], elapsed_ms, from_cache=False
    )

    return SearchResponse(
        query=query_text,
        total=outcome["total"],
        page=page,
        page_size=page_size,
        took_ms=elapsed_ms,
        from_cache=False,
        results=outcome["results"],
    )


@router.get(
    "/search/history",
    response_model=SearchHistoryResponse,
    summary="История поисковых запросов",
)
async def search_history(
    limit: int = Query(default=20, ge=1, le=100, description="Размер выборки"),
    db: AsyncSession = Depends(get_db),
) -> SearchHistoryResponse:
    """Вернуть историю последних поисковых запросов.

    :param limit: максимальное количество записей истории.
    :return: список записей истории, отсортированный по убыванию времени.
    """
    total = await db.scalar(select(func.count()).select_from(SearchQuery)) or 0
    rows = await db.scalars(
        select(SearchQuery).order_by(SearchQuery.created_at.desc()).limit(limit)
    )
    return SearchHistoryResponse(
        total=int(total),
        items=[SearchHistoryItem.model_validate(row, from_attributes=True) for row in rows],
    )


async def _save_history(
    db: AsyncSession,
    query_text: str,
    results_count: int,
    took_ms: int,
    *,
    from_cache: bool,
) -> None:
    """Сохранить запись об одном поисковом запросе в историю.

    :param db: сессия БД.
    :param query_text: текст запроса.
    :param results_count: количество найденных результатов.
    :param took_ms: время выполнения в миллисекундах.
    :param from_cache: был ли ответ получен из кеша.
    """
    record = SearchQuery(
        query_text=query_text[:1024],
        results_count=results_count,
        took_ms=took_ms,
        from_cache=from_cache,
    )
    db.add(record)
    await db.commit()
