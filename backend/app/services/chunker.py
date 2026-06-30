"""Разбиение текста на чанки (BE-05).

Извлечённый из документа текст разбивается на сегменты фиксированной
длины (по умолчанию 1000 символов) с перекрытием (по умолчанию 100
символов) между соседними чанками. Перекрытие сохраняет контекст на
границах сегментов и улучшает качество полнотекстового поиска.
"""

from dataclasses import dataclass

from app.core.config import settings
from app.services.parser import ParsedPage


@dataclass(frozen=True)
class TextChunk:
    """Сегмент текста документа, готовый к индексации.

    :param chunk_id: порядковый номер чанка в документе (с 0).
    :param page_number: номер страницы-источника.
    :param text: текст сегмента.
    """

    chunk_id: int
    page_number: int
    text: str


def chunk_text(
    text: str,
    page_number: int,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    start_index: int = 0,
) -> list[TextChunk]:
    """Разбить строку текста на перекрывающиеся чанки.

    :param text: исходный текст для разбиения.
    :param page_number: номер страницы, к которой относится текст.
    :param chunk_size: размер чанка в символах (по умолчанию из настроек).
    :param chunk_overlap: перекрытие в символах (по умолчанию из настроек).
    :param start_index: начальное значение идентификатора чанка.
    :return: список чанков; для пустого текста — пустой список.
    :raises ValueError: если ``chunk_overlap`` не меньше ``chunk_size``.
    """
    size = chunk_size if chunk_size is not None else settings.chunk_size
    overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap

    if size <= 0:
        raise ValueError("Размер чанка должен быть положительным числом.")
    if overlap < 0:
        raise ValueError("Перекрытие не может быть отрицательным.")
    if overlap >= size:
        raise ValueError("Перекрытие должно быть меньше размера чанка.")

    normalized = text.strip()
    if not normalized:
        return []

    chunks: list[TextChunk] = []
    step = size - overlap
    position = 0
    chunk_id = start_index

    while position < len(normalized):
        segment = normalized[position : position + size].strip()
        if segment:
            chunks.append(
                TextChunk(
                    chunk_id=chunk_id,
                    page_number=page_number,
                    text=segment,
                )
            )
            chunk_id += 1
        position += step

    return chunks


def chunk_pages(
    pages: list[ParsedPage],
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[TextChunk]:
    """Разбить на чанки список страниц документа со сквозной нумерацией.

    :param pages: страницы, полученные из :func:`parser.parse_document`.
    :param chunk_size: размер чанка в символах (по умолчанию из настроек).
    :param chunk_overlap: перекрытие в символах (по умолчанию из настроек).
    :return: общий список чанков с уникальными сквозными ``chunk_id``.
    """
    all_chunks: list[TextChunk] = []
    for page in pages:
        page_chunks = chunk_text(
            page.text,
            page.page_number,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            start_index=len(all_chunks),
        )
        all_chunks.extend(page_chunks)
    return all_chunks
