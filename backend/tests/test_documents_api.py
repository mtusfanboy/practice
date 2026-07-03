"""Интеграционные тесты эндпоинтов документов (BE-01..03, FE-03, QA-01)."""


from tests.conftest import read_fixture


async def test_upload_pdf_then_indexed(client) -> None:
    """Загрузка корректного PDF создаёт документ и индексирует его."""
    files = {"file": ("sample_lecture.pdf", read_fixture("sample_lecture.pdf"), "application/pdf")}
    response = await client.post("/api/v1/documents/upload", files=files)

    assert response.status_code == 201
    body = response.json()
    assert body["file_name"] == "sample_lecture.pdf"
    # Фоновая обработка завершается синхронно в рамках тестового клиента.
    assert body["status"] in {"uploaded", "indexed"}

    # После обработки документ должен иметь статус indexed и чанки.
    list_response = await client.get("/api/v1/documents")
    assert list_response.status_code == 200
    docs = list_response.json()
    assert docs["total"] == 1
    document = docs["items"][0]
    assert document["status"] == "indexed"
    assert document["chunk_count"] > 0
    assert document["page_count"] == 2


async def test_upload_docx_indexed(client) -> None:
    """Загрузка корректного DOCX успешно индексируется."""
    files = {
        "file": (
            "sample_lecture.docx",
            read_fixture("sample_lecture.docx"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    response = await client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201

    docs = (await client.get("/api/v1/documents")).json()
    assert docs["items"][0]["status"] == "indexed"


async def test_upload_invalid_extension_returns_400(client) -> None:
    """Загрузка файла неподдерживаемого формата возвращает 400."""
    files = {"file": ("notes.txt", b"plain text content", "text/plain")}
    response = await client.post("/api/v1/documents/upload", files=files)

    assert response.status_code == 400
    assert "формат" in response.json()["detail"].lower()


async def test_upload_empty_file_returns_400(client) -> None:
    """Загрузка пустого файла возвращает 400."""
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    response = await client.post("/api/v1/documents/upload", files=files)

    assert response.status_code == 400


async def test_upload_corrupted_pdf_marks_failed(client) -> None:
    """Битый PDF принимается, но переводится в статус failed с ошибкой."""
    files = {"file": ("corrupted.pdf", read_fixture("corrupted.pdf"), "application/pdf")}
    response = await client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201

    docs = (await client.get("/api/v1/documents")).json()
    document = docs["items"][0]
    assert document["status"] == "failed"
    assert document["error_message"]


async def test_get_document_by_id(client) -> None:
    """Документ можно получить по его идентификатору."""
    files = {"file": ("sample_lecture.pdf", read_fixture("sample_lecture.pdf"), "application/pdf")}
    created = (await client.post("/api/v1/documents/upload", files=files)).json()

    response = await client.get(f"/api/v1/documents/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_missing_document_returns_404(client) -> None:
    """Запрос несуществующего документа возвращает 404."""
    response = await client.get("/api/v1/documents/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_delete_document(client) -> None:
    """Документ можно удалить, после чего он исчезает из списка."""
    files = {"file": ("sample_lecture.pdf", read_fixture("sample_lecture.pdf"), "application/pdf")}
    created = (await client.post("/api/v1/documents/upload", files=files)).json()

    delete_response = await client.delete(f"/api/v1/documents/{created['id']}")
    assert delete_response.status_code == 204

    docs = (await client.get("/api/v1/documents")).json()
    assert docs["total"] == 0
