"""Юнит-тесты валидации загружаемых файлов (BE-02, QA-01)."""

from types import SimpleNamespace

import pytest
from app.api.documents import _validate_upload
from app.core.config import settings
from fastapi import HTTPException


def _fake_file(filename: str) -> SimpleNamespace:
    """Создать заглушку UploadFile с нужным именем файла."""
    return SimpleNamespace(filename=filename, content_type="application/octet-stream")


def test_valid_pdf_passes() -> None:
    """Корректный PDF допустимого размера проходит валидацию."""
    _validate_upload(_fake_file("lecture.pdf"), size_bytes=1024)


def test_valid_docx_passes() -> None:
    """Корректный DOCX допустимого размера проходит валидацию."""
    _validate_upload(_fake_file("lecture.docx"), size_bytes=1024)


def test_unsupported_extension_rejected() -> None:
    """Неподдерживаемое расширение отклоняется с кодом 400."""
    with pytest.raises(HTTPException) as exc:
        _validate_upload(_fake_file("notes.txt"), size_bytes=1024)
    assert exc.value.status_code == 400
    assert "Недопустимый формат" in exc.value.detail


def test_no_extension_rejected() -> None:
    """Файл без расширения отклоняется."""
    with pytest.raises(HTTPException) as exc:
        _validate_upload(_fake_file("noextension"), size_bytes=1024)
    assert exc.value.status_code == 400


def test_empty_file_rejected() -> None:
    """Пустой файл (0 байт) отклоняется."""
    with pytest.raises(HTTPException) as exc:
        _validate_upload(_fake_file("lecture.pdf"), size_bytes=0)
    assert exc.value.status_code == 400
    assert "пуст" in exc.value.detail.lower()


def test_oversized_file_rejected() -> None:
    """Файл больше максимального размера отклоняется."""
    too_big = settings.max_upload_size_bytes + 1
    with pytest.raises(HTTPException) as exc:
        _validate_upload(_fake_file("lecture.pdf"), size_bytes=too_big)
    assert exc.value.status_code == 400
    assert "превышает" in exc.value.detail.lower()


def test_extension_case_insensitive() -> None:
    """Расширение в верхнем регистре также допустимо."""
    _validate_upload(_fake_file("LECTURE.PDF"), size_bytes=1024)
