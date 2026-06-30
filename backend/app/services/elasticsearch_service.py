"""Сервис индексации и поиска на базе Elasticsearch (BE-06..BE-09).

Создаёт индекс ``documents`` с русскоязычным анализатором, индексирует
чанки документов и выполняет полнотекстовый поиск ``multi_match`` по
полю ``text`` с подсветкой совпадений.
"""

from typing import Any

from elasticsearch import AsyncElasticsearch, NotFoundError

from app.core.logging import get_logger
from app.services.chunker import TextChunk

logger = get_logger(__name__)

# Настройки и маппинг индекса documents (BE-06).
#
# Русскоязычный анализатор строится на стандартном токенизаторе с
# фильтрами стоп-слов и стемминга русского языка. Дополнительно
# подключается lowercase. Анализатор `analysis-ru` реализован средствами
# встроенного в Elasticsearch функционала (плагин не требуется).
INDEX_SETTINGS: dict[str, Any] = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "filter": {
                "ru_stop": {"type": "stop", "stopwords": "_russian_"},
                "ru_stemmer": {"type": "stemmer", "language": "russian"},
                "en_stop": {"type": "stop", "stopwords": "_english_"},
                "en_stemmer": {"type": "stemmer", "language": "english"},
            },
            "analyzer": {
                # Основной анализатор для русского текста (с поддержкой
                # латиницы — полезно для смешанных технических текстов).
                "ru_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "ru_stop",
                        "ru_stemmer",
                        "en_stop",
                        "en_stemmer",
                    ],
                }
            },
        },
    },
    "mappings": {
        "properties": {
            "document_id": {"type": "keyword"},
            "chunk_id": {"type": "keyword"},
            "file_name": {
                "type": "text",
                "analyzer": "ru_analyzer",
                "fields": {"raw": {"type": "keyword"}},
            },
            "page_number": {"type": "integer"},
            "text": {"type": "text", "analyzer": "ru_analyzer"},
        }
    },
}


class ElasticsearchService:
    """Обёртка над клиентом Elasticsearch для индексации и поиска."""

    def __init__(self, client: AsyncElasticsearch, index_name: str) -> None:
        """Инициализировать сервис.

        :param client: асинхронный клиент Elasticsearch.
        :param index_name: имя индекса для документов.
        """
        self._client = client
        self._index = index_name

    @property
    def index_name(self) -> str:
        """Имя используемого индекса."""
        return self._index

    async def ensure_index(self) -> None:
        """Создать индекс ``documents`` с маппингом, если он отсутствует (BE-06)."""
        exists = await self._client.indices.exists(index=self._index)
        if exists:
            logger.info("Индекс '%s' уже существует.", self._index)
            return

        await self._client.indices.create(index=self._index, body=INDEX_SETTINGS)
        logger.info("Индекс '%s' создан.", self._index)

    async def index_chunks(
        self,
        document_id: str,
        file_name: str,
        chunks: list[TextChunk],
    ) -> int:
        """Проиндексировать чанки документа (BE-07).

        Каждый чанк сохраняется отдельным документом Elasticsearch с
        метаданными ``file_name``, ``page_number``, ``chunk_id`` и ``text``.
        Операция выполняется пакетно через bulk API.

        :param document_id: идентификатор исходного документа (UUID).
        :param file_name: имя файла-источника.
        :param chunks: список чанков для индексации.
        :return: количество успешно проиндексированных чанков.
        """
        if not chunks:
            return 0

        operations: list[dict[str, Any]] = []
        for chunk in chunks:
            doc_chunk_id = f"{document_id}_{chunk.chunk_id}"
            operations.append({"index": {"_index": self._index, "_id": doc_chunk_id}})
            operations.append(
                {
                    "document_id": document_id,
                    "chunk_id": doc_chunk_id,
                    "file_name": file_name,
                    "page_number": chunk.page_number,
                    "text": chunk.text,
                }
            )

        response = await self._client.bulk(operations=operations, refresh=True)
        if response.get("errors"):
            failed = [
                item
                for item in response["items"]
                if item.get("index", {}).get("status", 200) >= 300
            ]
            logger.error("Ошибки индексации %d чанков: %s", len(failed), failed[:3])
            return len(chunks) - len(failed)

        return len(chunks)

    async def delete_document(self, document_id: str) -> int:
        """Удалить все чанки документа из индекса.

        :param document_id: идентификатор документа.
        :return: количество удалённых чанков.
        """
        response = await self._client.delete_by_query(
            index=self._index,
            query={"term": {"document_id": document_id}},
            refresh=True,
            ignore_unavailable=True,
        )
        return int(response.get("deleted", 0))

    async def search(
        self,
        query: str,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:
        """Выполнить полнотекстовый поиск по чанкам (BE-08, BE-09).

        Используется ``multi_match`` по полю ``text`` (с повышенным весом)
        и ``file_name``. Совпадения подсвечиваются тегами ``<mark>`` (FE-06).

        :param query: текст поискового запроса.
        :param page: номер страницы результатов (с 1).
        :param page_size: количество результатов на странице.
        :return: словарь с ключами ``total``, ``took_ms`` и ``results``.
        """
        from_ = max(page - 1, 0) * page_size
        body: dict[str, Any] = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["text^3", "file_name"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            },
            "highlight": {
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],
                "fields": {"text": {"number_of_fragments": 1, "fragment_size": 300}},
            },
            "from": from_,
            "size": page_size,
        }

        response = await self._client.search(index=self._index, body=body)

        hits = response["hits"]
        total = hits["total"]["value"] if isinstance(hits["total"], dict) else hits["total"]

        results: list[dict[str, Any]] = []
        for hit in hits["hits"]:
            source = hit["_source"]
            highlight = None
            if "highlight" in hit and hit["highlight"].get("text"):
                highlight = hit["highlight"]["text"][0]
            results.append(
                {
                    "chunk_id": source["chunk_id"],
                    "document_id": source["document_id"],
                    "file_name": source["file_name"],
                    "page": source["page_number"],
                    "text": source["text"],
                    "score": hit["_score"] or 0.0,
                    "highlight": highlight,
                }
            )

        return {
            "total": total,
            "took_ms": response.get("took", 0),
            "results": results,
        }

    async def ping(self) -> bool:
        """Проверить доступность Elasticsearch.

        :return: ``True``, если кластер отвечает.
        """
        try:
            return bool(await self._client.ping())
        except Exception:  # noqa: BLE001
            return False

    async def document_exists(self, document_id: str) -> bool:
        """Проверить, есть ли в индексе хотя бы один чанк документа.

        :param document_id: идентификатор документа.
        :return: ``True``, если документ присутствует в индексе.
        """
        try:
            response = await self._client.count(
                index=self._index,
                query={"term": {"document_id": document_id}},
            )
            return int(response.get("count", 0)) > 0
        except NotFoundError:
            return False
