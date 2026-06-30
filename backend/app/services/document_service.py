"""Оркестрация обработки документов.

Связывает воедино парсинг (BE-04), чанкинг (BE-05) и индексацию (BE-07),
обновляя статус документа в PostgreSQL на каждом этапе. Используется
фоновой задачей после загрузки файла.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.logging import get_logger
from app.core.metrics import CHUNKS_INDEXED_TOTAL, DOCUMENTS_UPLOADED_TOTAL
from app.models.document import Document, DocumentStatus
from app.services.chunker import chunk_pages
from app.services.elasticsearch_service import ElasticsearchService
from app.services.parser import DocumentParsingError, parse_document

logger = get_logger(__name__)


class DocumentProcessor:
    """Обрабатывает загруженный документ: парсинг → чанкинг → индексация."""

    def __init__(
        self,
        session_factory: async_sessionmaker,
        es_service: ElasticsearchService,
    ) -> None:
        """Инициализировать обработчик.

        :param session_factory: фабрика асинхронных сессий БД (фоновой
            задаче нужна собственная сессия, не связанная с запросом).
        :param es_service: сервис индексации Elasticsearch.
        """
        self._session_factory = session_factory
        self._es = es_service

    async def process(
        self,
        document_id: uuid.UUID,
        content: bytes,
        file_name: str,
    ) -> None:
        """Полностью обработать документ и обновить его статус в БД.

        Метод не выбрасывает исключений наружу: любая ошибка фиксируется
        в поле ``error_message`` и переводит документ в статус ``FAILED``.

        :param document_id: идентификатор документа в БД.
        :param content: бинарное содержимое файла.
        :param file_name: имя файла.
        """
        await self._set_status(document_id, DocumentStatus.PROCESSING)

        try:
            pages = parse_document(content, file_name)
            chunks = chunk_pages(pages)
            indexed = await self._es.index_chunks(
                str(document_id), file_name, chunks
            )
            CHUNKS_INDEXED_TOTAL.inc(indexed)

            await self._mark_indexed(
                document_id,
                page_count=len(pages),
                chunk_count=indexed,
            )
            DOCUMENTS_UPLOADED_TOTAL.labels(status="indexed").inc()
            logger.info(
                "Документ %s проиндексирован: %d страниц, %d чанков.",
                document_id,
                len(pages),
                indexed,
            )
        except DocumentParsingError as exc:
            await self._mark_failed(document_id, str(exc))
            DOCUMENTS_UPLOADED_TOTAL.labels(status="failed").inc()
            logger.warning("Ошибка парсинга документа %s: %s", document_id, exc)
        except Exception as exc:  # noqa: BLE001 — фиксируем любую ошибку индексации
            await self._mark_failed(document_id, f"Ошибка индексации: {exc}")
            DOCUMENTS_UPLOADED_TOTAL.labels(status="failed").inc()
            logger.exception("Непредвиденная ошибка обработки документа %s", document_id)

    async def _set_status(
        self, document_id: uuid.UUID, status: DocumentStatus
    ) -> None:
        """Обновить статус документа."""
        async with self._session_factory() as session:
            document = await session.get(Document, document_id)
            if document is not None:
                document.status = status
                await session.commit()

    async def _mark_indexed(
        self, document_id: uuid.UUID, page_count: int, chunk_count: int
    ) -> None:
        """Перевести документ в статус INDEXED и записать метрики."""
        async with self._session_factory() as session:
            document = await session.get(Document, document_id)
            if document is not None:
                document.status = DocumentStatus.INDEXED
                document.page_count = page_count
                document.chunk_count = chunk_count
                document.indexed_at = datetime.now(UTC)
                document.error_message = None
                await session.commit()

    async def _mark_failed(self, document_id: uuid.UUID, message: str) -> None:
        """Перевести документ в статус FAILED с описанием ошибки."""
        async with self._session_factory() as session:
            document = await session.get(Document, document_id)
            if document is not None:
                document.status = DocumentStatus.FAILED
                document.error_message = message[:2000]
                await session.commit()


async def list_documents(
    session_factory: async_sessionmaker,
    limit: int,
    offset: int,
) -> tuple[int, list[Document]]:
    """Вернуть список документов с пагинацией и их общее количество (FE-03).

    :param session_factory: фабрика асинхронных сессий БД.
    :param limit: максимальное количество документов.
    :param offset: смещение выборки.
    :return: кортеж ``(total, items)``.
    """
    from sqlalchemy import func

    async with session_factory() as session:
        total = await session.scalar(select(func.count()).select_from(Document)) or 0
        result = await session.scalars(
            select(Document)
            .order_by(Document.uploaded_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return int(total), list(result)
