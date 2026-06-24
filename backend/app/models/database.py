"""Подключение к PostgreSQL через асинхронный SQLAlchemy."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Асинхронный движок SQLAlchemy. ``pool_pre_ping`` отбраковывает «мёртвые»
# соединения, что важно при перезапусках PostgreSQL в Docker Compose.
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    future=True,
)

# Фабрика асинхронных сессий. ``expire_on_commit=False`` позволяет
# обращаться к атрибутам объектов после commit без повторного запроса.
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Базовый декларативный класс для всех ORM-моделей."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-зависимость, отдающая сессию БД на время запроса.

    Сессия автоматически закрывается по завершении обработки запроса.

    :yield: активная асинхронная сессия SQLAlchemy.
    """
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    """Создать таблицы в БД, если они ещё не существуют.

    Вызывается при старте приложения. Для прототипа используется
    ``create_all`` вместо полноценных миграций (Alembic).
    """
    # Импорт моделей обязателен, чтобы они зарегистрировались в метаданных.
    from app.models import document  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
