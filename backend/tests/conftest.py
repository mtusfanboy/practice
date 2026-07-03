"""Общие фикстуры pytest для тестов бэкенда.

Поднимает изолированную in-memory SQLite-базу, подменяет внешние сервисы
(Elasticsearch, Redis) их тестовыми двойниками и предоставляет HTTP-клиент
для интеграционных тестов API.
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from app.api.deps import get_cache_service, get_es_service
from app.main import app
from app.models.database import Base, get_db
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.fixtures.generate_fixtures import generate_all

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def ensure_fixtures() -> dict[str, Path]:
    """Гарантировать наличие тестовых документов перед запуском тестов."""
    return generate_all()


def read_fixture(name: str) -> bytes:
    """Прочитать содержимое тестового файла по имени.

    :param name: имя файла в каталоге ``tests/fixtures``.
    :return: бинарное содержимое файла.
    """
    return (FIXTURES_DIR / name).read_bytes()


class FakeESService:
    """Тестовый двойник :class:`ElasticsearchService`.

    Хранит «проиндексированные» чанки в памяти и реализует простой
    подстрочный поиск, достаточный для проверки логики API.
    """

    def __init__(self) -> None:
        self.documents: dict[str, list[dict[str, Any]]] = {}

    async def ensure_index(self) -> None:
        return None

    async def index_chunks(self, document_id, file_name, chunks) -> int:
        self.documents[document_id] = [
            {
                "chunk_id": f"{document_id}_{c.chunk_id}",
                "document_id": document_id,
                "file_name": file_name,
                "page": c.page_number,
                "text": c.text,
            }
            for c in chunks
        ]
        return len(chunks)

    async def delete_document(self, document_id) -> int:
        return len(self.documents.pop(document_id, []))

    async def search(self, query, *, page=1, page_size=10) -> dict[str, Any]:
        needle = query.lower()
        hits: list[dict[str, Any]] = []
        for chunks in self.documents.values():
            for chunk in chunks:
                if needle in chunk["text"].lower():
                    hits.append(
                        {
                            **chunk,
                            "score": 1.0,
                            "highlight": chunk["text"].replace(
                                query, f"<mark>{query}</mark>"
                            ),
                        }
                    )
        start = (page - 1) * page_size
        return {
            "total": len(hits),
            "took_ms": 1,
            "results": hits[start : start + page_size],
        }

    async def ping(self) -> bool:
        return True

    async def document_exists(self, document_id) -> bool:
        return document_id in self.documents


class FakeCacheService:
    """Тестовый двойник :class:`CacheService` на основе словаря в памяти."""

    def __init__(self) -> None:
        self.store: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _key(query: str, page: int, page_size: int) -> str:
        return f"{query.strip().lower()}|{page}|{page_size}"

    async def get(self, query, page, page_size):
        return self.store.get(self._key(query, page, page_size))

    async def set(self, query, page, page_size, value) -> None:
        self.store[self._key(query, page, page_size)] = value

    async def ping(self) -> bool:
        return True


@pytest_asyncio.fixture
async def test_engine():
    """Создать изолированный движок SQLite в памяти и схему БД."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def fake_es() -> FakeESService:
    """Тестовый сервис Elasticsearch."""
    return FakeESService()


@pytest_asyncio.fixture
async def fake_cache() -> FakeCacheService:
    """Тестовый сервис кеша."""
    return FakeCacheService()


@pytest_asyncio.fixture
async def client(test_engine, fake_es, fake_cache):
    """HTTP-клиент с подменёнными зависимостями приложения.

    Подменяет сессию БД на SQLite, а сервисы ES/кеша — на тестовые двойники.
    Фоновая обработка документов выполняется синхронно благодаря
    ``DocumentProcessor``, использующему ``async_session_factory``,
    который здесь также указывает на тестовую БД.
    """
    test_session_factory = async_sessionmaker(
        bind=test_engine, expire_on_commit=False, autoflush=False
    )

    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    # Подменяем глобальную фабрику сессий, используемую фоновой задачей,
    # и клиентов ES/кеша.
    import app.api.documents as documents_module
    import app.models.database as db_module
    from app.core import clients as clients_module

    original_factory = documents_module.async_session_factory
    documents_module.async_session_factory = test_session_factory
    db_module.async_session_factory = test_session_factory

    clients_module.clients.es_service = fake_es
    clients_module.clients.cache_service = fake_cache

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_es_service] = lambda: fake_es
    app.dependency_overrides[get_cache_service] = lambda: fake_cache

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    documents_module.async_session_factory = original_factory
    db_module.async_session_factory = original_factory


@pytest.fixture(scope="session")
def event_loop():
    """Единый событийный цикл на сессию тестов."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
