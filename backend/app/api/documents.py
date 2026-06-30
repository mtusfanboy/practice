"""Эндпоинты загрузки и просмотра документов (BE-01, BE-02, BE-03, FE-03)."""

import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_es_service
from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import DOCUMENTS_UPLOADED_TOTAL
from app.models.database import async_session_factory, get_db
from app.models.document import Document, DocumentStatus
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    ErrorResponse,
)
from app.services.document_service import DocumentProcessor, list_documents
from app.services.elasticsearch_service import ElasticsearchService

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def _validate_upload(file: UploadFile, size_bytes: int) -> None:
    """Проверить формат и размер загружаемого файла (BE-02).

    :param file: загружаемый файл.
    :param size_bytes: фактический размер файла в байтах.
    :raises HTTPException: 400, если формат или размер не соответствуют
        требованиям.
    """
    file_name = file.filename or ""
    extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""

    if extension not in settings.allowed_extensions_set:
        allowed = ", ".join(sorted(settings.allowed_extensions_set)).upper()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Недопустимый формат файла '.{extension}'. "
                f"Разрешены только: {allowed}."
            ),
        )

    if size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл пуст.",
        )

    if size_bytes > settings.max_upload_size_bytes:
        max_mb = settings.max_upload_size_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Размер файла превышает допустимый предел в {max_mb} МБ.",
        )


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Загрузить документ",
    responses={400: {"model": ErrorResponse, "description": "Ошибка валидации файла"}},
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Файл PDF или DOCX (не более 20 МБ)"),
    db: AsyncSession = Depends(get_db),
    es_service: ElasticsearchService = Depends(get_es_service),
) -> DocumentResponse:
    """Загрузить документ для индексации (BE-01).

    Выполняет валидацию файла (BE-02), генерирует UUID (BE-03), сохраняет
    метаданные в БД и запускает фоновую обработку (парсинг и индексацию).
    Клиент отслеживает прогресс через список документов (FE-02, FE-03).

    :param file: загружаемый файл PDF или DOCX.
    :return: метаданные созданного документа со статусом ``uploaded``.
    """
    content = await file.read()
    _validate_upload(file, len(content))

    document = Document(
        id=uuid.uuid4(),
        file_name=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        status=DocumentStatus.UPLOADED,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    DOCUMENTS_UPLOADED_TOTAL.labels(status="uploaded").inc()

    # Обработка (парсинг + индексация) выполняется в фоне, чтобы быстро
    # вернуть ответ и не блокировать клиента (FE-02: статусы прогресса).
    processor = DocumentProcessor(async_session_factory, es_service)
    background_tasks.add_task(
        processor.process, document.id, content, document.file_name
    )

    logger.info("Документ %s ('%s') принят в обработку.", document.id, document.file_name)
    return DocumentResponse.model_validate(document)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="Список загруженных документов",
)
async def get_documents(
    limit: int = Query(default=100, ge=1, le=500, description="Размер выборки"),
    offset: int = Query(default=0, ge=0, description="Смещение выборки"),
) -> DocumentListResponse:
    """Вернуть список загруженных документов с их статусами (FE-03).

    :param limit: максимальное количество документов в ответе.
    :param offset: смещение для постраничной выборки.
    :return: список документов и их общее количество.
    """
    total, items = await list_documents(async_session_factory, limit, offset)
    return DocumentListResponse(
        total=total,
        items=[DocumentResponse.model_validate(item) for item in items],
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Получить документ по идентификатору",
    responses={404: {"model": ErrorResponse, "description": "Документ не найден"}},
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Вернуть метаданные документа по его идентификатору.

    :param document_id: идентификатор документа (UUID).
    :return: метаданные документа.
    :raises HTTPException: 404, если документ не найден.
    """
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден.",
        )
    return DocumentResponse.model_validate(document)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить документ",
    responses={404: {"model": ErrorResponse, "description": "Документ не найден"}},
)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    es_service: ElasticsearchService = Depends(get_es_service),
) -> None:
    """Удалить документ из БД и его чанки из индекса Elasticsearch.

    :param document_id: идентификатор документа (UUID).
    :raises HTTPException: 404, если документ не найден.
    """
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден.",
        )

    await es_service.delete_document(str(document_id))
    await db.delete(document)
    await db.commit()
    logger.info("Документ %s удалён.", document_id)
