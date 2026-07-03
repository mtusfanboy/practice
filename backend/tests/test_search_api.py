"""Интеграционные тесты эндпоинтов поиска (BE-08..10, QA-01)."""


from tests.conftest import read_fixture


async def _upload_sample(client) -> None:
    """Загрузить и проиндексировать образец документа для поиска."""
    files = {"file": ("sample_lecture.pdf", read_fixture("sample_lecture.pdf"), "application/pdf")}
    response = await client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201


async def test_search_returns_hits_with_required_fields(client) -> None:
    """Поиск возвращает результаты с обязательными полями (BE-09)."""
    await _upload_sample(client)

    response = await client.get("/api/v1/search", params={"q": "данных"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "данных"
    assert body["total"] >= 1
    hit = body["results"][0]
    # BE-09: обязательные поля результата.
    for field in ("chunk_id", "file_name", "page", "text", "score"):
        assert field in hit
    # FE-06: подсветка совпадений.
    assert "<mark>" in hit["highlight"]


async def test_search_empty_query_rejected(client) -> None:
    """Пустой поисковый запрос отклоняется валидацией (400)."""
    response = await client.get("/api/v1/search", params={"q": ""})
    assert response.status_code == 400


async def test_search_no_results_message_path(client) -> None:
    """Запрос без совпадений возвращает пустой список результатов (FE-08)."""
    await _upload_sample(client)

    response = await client.get("/api/v1/search", params={"q": "квантоваятелепортация"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["results"] == []


async def test_search_uses_cache_on_repeat(client) -> None:
    """Повторный одинаковый запрос обслуживается из кеша (BE-10)."""
    await _upload_sample(client)

    first = (await client.get("/api/v1/search", params={"q": "индекс"})).json()
    assert first["from_cache"] is False

    second = (await client.get("/api/v1/search", params={"q": "индекс"})).json()
    assert second["from_cache"] is True
    assert second["total"] == first["total"]


async def test_search_pagination_params(client) -> None:
    """Параметры пагинации принимаются и отражаются в ответе (FE-07)."""
    await _upload_sample(client)

    response = await client.get(
        "/api/v1/search", params={"q": "данных", "page": 1, "page_size": 5}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 5


async def test_search_saved_to_history(client) -> None:
    """Каждый поисковый запрос сохраняется в историю."""
    await _upload_sample(client)
    await client.get("/api/v1/search", params={"q": "нормализация"})

    history = (await client.get("/api/v1/search/history")).json()
    assert history["total"] >= 1
    assert any(item["query_text"] == "нормализация" for item in history["items"])


async def test_health_endpoints(client) -> None:
    """Эндпоинты здоровья отвечают корректно."""
    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = await client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["dependencies"]["elasticsearch"] == "up"
