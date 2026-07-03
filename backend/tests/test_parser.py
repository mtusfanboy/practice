"""Юнит-тесты модуля извлечения текста (BE-04, QA-01, QA-03)."""

import pytest
from app.services.parser import DocumentParsingError, parse_document

from tests.conftest import read_fixture


def test_parse_pdf_extracts_text_per_page() -> None:
    """Корректный PDF разбирается постранично, текст не пустой."""
    pages = parse_document(read_fixture("sample_lecture.pdf"), "sample_lecture.pdf")

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2
    assert "базы данных" in pages[0].text.lower()
    assert "индекс" in pages[1].text.lower()


def test_parse_pdf_with_custom_font() -> None:
    """PDF с нестандартным шрифтом всё равно отдаёт извлекаемый текст."""
    pages = parse_document(read_fixture("custom_font.pdf"), "custom_font.pdf")

    assert len(pages) >= 1
    assert pages[0].text.strip()


def test_parse_docx_extracts_paragraphs_and_tables() -> None:
    """Корректный DOCX отдаёт текст абзацев и таблиц на одной странице."""
    pages = parse_document(read_fixture("sample_lecture.docx"), "sample_lecture.docx")

    assert len(pages) == 1
    assert pages[0].page_number == 1
    text = pages[0].text.lower()
    assert "конспект лекций" in text
    # Содержимое таблицы также должно попасть в текст.
    assert "структура для ускорения поиска" in text


def test_parse_unsupported_extension_raises() -> None:
    """Неподдерживаемое расширение приводит к ошибке парсинга."""
    with pytest.raises(DocumentParsingError, match="Неподдерживаемый формат"):
        parse_document(b"plain text", "notes.txt")


def test_parse_empty_pdf_raises() -> None:
    """PDF без извлекаемого текста считается ошибкой."""
    with pytest.raises(DocumentParsingError):
        parse_document(read_fixture("empty.pdf"), "empty.pdf")


def test_parse_empty_docx_raises() -> None:
    """Пустой DOCX приводит к ошибке парсинга."""
    with pytest.raises(DocumentParsingError, match="не содержит текста"):
        parse_document(read_fixture("empty.docx"), "empty.docx")


def test_parse_corrupted_pdf_raises() -> None:
    """Битый PDF приводит к контролируемой ошибке, а не падению."""
    with pytest.raises(DocumentParsingError):
        parse_document(read_fixture("corrupted.pdf"), "corrupted.pdf")


def test_parse_corrupted_docx_raises() -> None:
    """Битый DOCX приводит к контролируемой ошибке парсинга."""
    with pytest.raises(DocumentParsingError):
        parse_document(read_fixture("corrupted.docx"), "corrupted.docx")
