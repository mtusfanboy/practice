"""Pydantic-схемы документов для запросов и ответов API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    """Представление документа в ответах API.

    Используется как для ответа на загрузку (BE-01), так и для списка
    документов (FE-03).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Уникальный идентификатор документа (UUID)")
    file_name: str = Field(description="Имя загруженного файла")
    content_type: str = Field(description="MIME-тип файла")
    size_bytes: int = Field(description="Размер файла в байтах")
    status: DocumentStatus = Field(description="Статус обработки документа")
    page_count: int = Field(description="Количество страниц в документе")
    chunk_count: int = Field(description="Количество проиндексированных чанков")
    error_message: str | None = Field(
        default=None, description="Описание ошибки обработки, если она произошла"
    )
    uploaded_at: datetime = Field(description="Дата и время загрузки")
    indexed_at: datetime | None = Field(
        default=None, description="Дата и время завершения индексации"
    )


class DocumentListResponse(BaseModel):
    """Ответ со списком документов и общим количеством."""

    total: int = Field(description="Общее количество документов")
    items: list[DocumentResponse] = Field(description="Список документов")


class ErrorResponse(BaseModel):
    """Единый формат ответа об ошибке."""

    detail: str = Field(description="Человекочитаемое описание ошибки")
