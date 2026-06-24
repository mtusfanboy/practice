"""Pydantic-схемы поиска для запросов и ответов API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    """Один результат поиска (BE-09).

    Поля соответствуют требуемому формату JSON: ``chunk_id``,
    ``file_name``, ``page``, ``text``, ``score``. Дополнительно
    отдаётся ``highlight`` для подсветки совпадений на фронтенде (FE-06).
    """

    chunk_id: str = Field(description="Идентификатор чанка")
    document_id: str = Field(description="Идентификатор документа-источника")
    file_name: str = Field(description="Имя файла-источника")
    page: int = Field(description="Номер страницы, где найден фрагмент")
    text: str = Field(description="Текст найденного фрагмента")
    score: float = Field(description="Оценка релевантности (Elasticsearch score)")
    highlight: str | None = Field(
        default=None,
        description="Фрагмент с HTML-разметкой совпадений (<mark>...</mark>)",
    )


class SearchResponse(BaseModel):
    """Ответ на поисковый запрос (BE-08)."""

    query: str = Field(description="Исходный поисковый запрос")
    total: int = Field(description="Общее количество найденных результатов")
    page: int = Field(description="Номер текущей страницы (с 1)")
    page_size: int = Field(description="Количество результатов на странице")
    took_ms: int = Field(description="Время выполнения запроса в миллисекундах")
    from_cache: bool = Field(description="Получен ли ответ из кеша Redis")
    results: list[SearchHit] = Field(description="Список найденных фрагментов")


class SearchHistoryItem(BaseModel):
    """Элемент истории поисковых запросов."""

    id: uuid.UUID = Field(description="Идентификатор записи истории")
    query_text: str = Field(description="Текст запроса")
    results_count: int = Field(description="Количество найденных результатов")
    took_ms: int = Field(description="Время выполнения в миллисекундах")
    from_cache: bool = Field(description="Был ли ответ из кеша")
    created_at: datetime = Field(description="Время выполнения запроса")


class SearchHistoryResponse(BaseModel):
    """Ответ с историей поисковых запросов."""

    total: int = Field(description="Общее количество записей в истории")
    items: list[SearchHistoryItem] = Field(description="Список запросов")
