"""ORM-модели документов и истории поиска."""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


def _utcnow() -> datetime:
    """Вернуть текущее время в UTC с таймзоной."""
    return datetime.now(UTC)


class DocumentStatus(str, enum.Enum):
    """Статус жизненного цикла документа.

    Значения соответствуют состояниям прогресс-бара на фронтенде (FE-02).
    """

    UPLOADED = "uploaded"      # Файл получен и сохранён.
    PROCESSING = "processing"  # Идёт извлечение текста и индексация.
    INDEXED = "indexed"        # Документ успешно проиндексирован (Готово).
    FAILED = "failed"          # Ошибка обработки (Ошибка).


class Document(Base):
    """Метаданные загруженного документа.

    Хранит информацию о файле и его статусе обработки. Содержимое
    (чанки) хранится отдельно в Elasticsearch.
    """

    __tablename__ = "documents"

    #: Уникальный идентификатор документа (BE-03, UUID).
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    #: Оригинальное имя файла.
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    #: MIME-тип файла.
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    #: Размер файла в байтах.
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    #: Текущий статус обработки.
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False, length=32),
        default=DocumentStatus.UPLOADED,
        nullable=False,
    )
    #: Количество страниц (заполняется после парсинга).
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Количество проиндексированных чанков.
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Текст ошибки, если обработка завершилась неудачно.
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Время загрузки.
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    #: Время завершения индексации.
    indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class SearchQuery(Base):
    """История поисковых запросов пользователей.

    Реализует требование «Сохранение истории поисковых запросов».
    """

    __tablename__ = "search_queries"

    #: Идентификатор записи истории.
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    #: Текст поискового запроса.
    query_text: Mapped[str] = mapped_column(String(1024), nullable=False)
    #: Количество найденных результатов.
    results_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Длительность выполнения запроса в миллисекундах.
    took_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Был ли ответ получен из кеша (BE-10).
    from_cache: Mapped[bool] = mapped_column(default=False, nullable=False)
    #: Время выполнения запроса.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
