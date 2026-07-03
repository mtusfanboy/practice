"""Юнит-тесты конфигурации приложения (QA-01)."""

from app.core.config import Settings


def test_database_url_built_from_parts() -> None:
    """URL БД корректно собирается из компонентов настроек."""
    settings = Settings(
        postgres_user="u",
        postgres_password="p",
        postgres_host="h",
        postgres_port=5433,
        postgres_db="db",
    )
    assert settings.database_url == "postgresql+asyncpg://u:p@h:5433/db"


def test_allowed_extensions_parsed_to_set() -> None:
    """Список расширений разбирается в множество в нижнем регистре."""
    settings = Settings(allowed_extensions="PDF, Docx ,")
    assert settings.allowed_extensions_set == {"pdf", "docx"}


def test_cors_origins_parsed_to_list() -> None:
    """CORS-источники разбираются в список без пустых элементов."""
    settings = Settings(cors_origins="http://a, http://b ,")
    assert settings.cors_origins_list == ["http://a", "http://b"]


def test_redis_and_es_urls() -> None:
    """URL-адреса Redis и Elasticsearch формируются корректно."""
    settings = Settings(
        redis_host="r",
        redis_port=6380,
        redis_db=2,
        elasticsearch_host="es",
        elasticsearch_port=9201,
        elasticsearch_scheme="http",
    )
    assert settings.redis_url == "redis://r:6380/2"
    assert settings.elasticsearch_url == "http://es:9201"
