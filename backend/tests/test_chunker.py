"""Юнит-тесты модуля разбиения текста на чанки (BE-05, QA-01)."""

import pytest
from app.services.chunker import chunk_pages, chunk_text
from app.services.parser import ParsedPage


def test_chunk_text_respects_size_and_overlap() -> None:
    """Чанки имеют заданный размер, а перекрытие сохраняет общий контекст."""
    text = "".join(str(i % 10) for i in range(2500))
    chunks = chunk_text(text, page_number=1, chunk_size=1000, chunk_overlap=100)

    # 2500 символов при шаге 900 → чанки на позициях 0, 900, 1800.
    assert len(chunks) == 3
    assert all(len(c.text) <= 1000 for c in chunks)
    # Перекрытие: конец первого чанка совпадает с началом второго.
    assert chunks[0].text[-100:] == chunks[1].text[:100]


def test_chunk_text_short_text_single_chunk() -> None:
    """Короткий текст помещается в один чанк."""
    chunks = chunk_text("Короткий текст.", page_number=3)

    assert len(chunks) == 1
    assert chunks[0].text == "Короткий текст."
    assert chunks[0].page_number == 3
    assert chunks[0].chunk_id == 0


def test_chunk_text_empty_returns_no_chunks() -> None:
    """Пустой или пробельный текст не порождает чанков."""
    assert chunk_text("", page_number=1) == []
    assert chunk_text("   \n  ", page_number=1) == []


def test_chunk_text_start_index_offsets_ids() -> None:
    """Идентификаторы чанков начинаются с переданного смещения."""
    text = "x" * 2500
    chunks = chunk_text(text, page_number=1, chunk_size=1000, chunk_overlap=100, start_index=5)

    assert chunks[0].chunk_id == 5
    assert chunks[-1].chunk_id == 5 + len(chunks) - 1


def test_chunk_text_invalid_overlap_raises() -> None:
    """Перекрытие не меньше размера чанка недопустимо."""
    with pytest.raises(ValueError, match="меньше размера"):
        chunk_text("любой текст", page_number=1, chunk_size=100, chunk_overlap=100)


def test_chunk_text_invalid_size_raises() -> None:
    """Неположительный размер чанка недопустим."""
    with pytest.raises(ValueError):
        chunk_text("любой текст", page_number=1, chunk_size=0)


def test_chunk_pages_continuous_ids() -> None:
    """Чанки нескольких страниц нумеруются сквозным образом."""
    pages = [
        ParsedPage(page_number=1, text="a" * 1500),
        ParsedPage(page_number=2, text="b" * 1500),
    ]
    chunks = chunk_pages(pages, chunk_size=1000, chunk_overlap=100)

    ids = [c.chunk_id for c in chunks]
    # Идентификаторы уникальны и идут по порядку без пропусков.
    assert ids == list(range(len(chunks)))
    # Присутствуют чанки обеих страниц.
    assert {c.page_number for c in chunks} == {1, 2}
