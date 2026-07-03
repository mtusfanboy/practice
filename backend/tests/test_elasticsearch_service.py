"""Юнит-тесты построения запросов Elasticsearch (BE-06..09, QA-01).

Реальный клиент Elasticsearch подменяется заглушкой, что позволяет
проверить структуру индексирующих и поисковых запросов без поднятия
кластера.
"""

from typing import Any

from app.services.chunker import TextChunk
from app.services.elasticsearch_service import INDEX_SETTINGS, ElasticsearchService


class FakeIndices:
    """Заглушка пространства имён indices клиента Elasticsearch."""

    def __init__(self) -> None:
        self.created: dict[str, Any] = {}
        self._exists = False

    async def exists(self, index: str) -> bool:
        return self._exists

    async def create(self, index: str, body: dict[str, Any]) -> dict[str, Any]:
        self.created[index] = body
        self._exists = True
        return {"acknowledged": True}


class FakeESClient:
    """Минимальная заглушка AsyncElasticsearch для проверки запросов."""

    def __init__(self) -> None:
        self.indices = FakeIndices()
        self.last_bulk: list[dict[str, Any]] | None = None
        self.last_search: dict[str, Any] | None = None

    async def bulk(self, operations, refresh=False):
        self.last_bulk = operations
        return {"errors": False, "items": []}

    async def search(self, index, body):
        self.last_search = body
        return {
            "took": 7,
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_score": 4.2,
                        "_source": {
                            "chunk_id": "doc_0",
                            "document_id": "doc",
                            "file_name": "lecture.pdf",
                            "page_number": 3,
                            "text": "Полнотекстовый поиск по базе знаний.",
                        },
                        "highlight": {"text": ["<mark>поиск</mark> по базе"]},
                    }
                ],
            },
        }


def test_index_settings_have_russian_analyzer() -> None:
    """Маппинг индекса использует русскоязычный анализатор (BE-06)."""
    analyzers = INDEX_SETTINGS["settings"]["analysis"]["analyzer"]
    assert "ru_analyzer" in analyzers
    assert "ru_stemmer" in analyzers["ru_analyzer"]["filter"]
    assert INDEX_SETTINGS["mappings"]["properties"]["text"]["analyzer"] == "ru_analyzer"


async def test_ensure_index_creates_with_settings() -> None:
    """ensure_index создаёт индекс с заданным маппингом, если его нет."""
    client = FakeESClient()
    service = ElasticsearchService(client, "documents")

    await service.ensure_index()
    assert "documents" in client.indices.created
    assert client.indices.created["documents"] == INDEX_SETTINGS


async def test_index_chunks_builds_bulk_with_metadata() -> None:
    """index_chunks формирует bulk-запрос с метаданными чанков (BE-07)."""
    client = FakeESClient()
    service = ElasticsearchService(client, "documents")

    chunks = [
        TextChunk(chunk_id=0, page_number=1, text="первый чанк"),
        TextChunk(chunk_id=1, page_number=2, text="второй чанк"),
    ]
    count = await service.index_chunks("doc-uuid", "lecture.pdf", chunks)

    assert count == 2
    # Каждый чанк — пара «action / source», итого 4 элемента.
    assert len(client.last_bulk) == 4
    source = client.last_bulk[1]
    assert source["document_id"] == "doc-uuid"
    assert source["file_name"] == "lecture.pdf"
    assert source["page_number"] == 1
    assert source["chunk_id"] == "doc-uuid_0"


async def test_search_builds_multi_match_with_highlight() -> None:
    """search использует multi_match по text и подсветку (BE-08, BE-09, FE-06)."""
    client = FakeESClient()
    service = ElasticsearchService(client, "documents")

    outcome = await service.search("поиск", page=1, page_size=10)

    body = client.last_search
    assert "multi_match" in body["query"]
    assert "text^3" in body["query"]["multi_match"]["fields"]
    assert body["highlight"]["pre_tags"] == ["<mark>"]

    assert outcome["total"] == 1
    assert outcome["took_ms"] == 7
    hit = outcome["results"][0]
    assert hit["chunk_id"] == "doc_0"
    assert hit["page"] == 3
    assert hit["score"] == 4.2
    assert "<mark>" in hit["highlight"]


async def test_index_empty_chunks_returns_zero() -> None:
    """Индексация пустого списка чанков не обращается к клиенту."""
    client = FakeESClient()
    service = ElasticsearchService(client, "documents")
    assert await service.index_chunks("doc", "f.pdf", []) == 0
    assert client.last_bulk is None
