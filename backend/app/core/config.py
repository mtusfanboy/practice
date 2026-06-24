"""Конфигурация приложения.

Все настройки читаются из переменных окружения (см. ``.env.example``).
Используется ``pydantic-settings`` для валидации и типизации параметров.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Контейнер настроек приложения.

    Атрибуты группируются по подсистемам: приложение, PostgreSQL,
    Elasticsearch, Redis и параметры загрузки документов.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Общие параметры приложения ---
    app_name: str = Field(default="University Knowledge Search")
    app_version: str = Field(default="1.0.0")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    api_v1_prefix: str = Field(default="/api/v1")
    # Список разрешённых источников для CORS (через запятую).
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:5173")

    # --- PostgreSQL ---
    postgres_host: str = Field(default="postgres")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="knowledge_base")
    postgres_user: str = Field(default="app")
    postgres_password: str = Field(default="app_password")

    # --- Elasticsearch ---
    elasticsearch_host: str = Field(default="elasticsearch")
    elasticsearch_port: int = Field(default=9200)
    elasticsearch_index: str = Field(default="documents")
    elasticsearch_scheme: str = Field(default="http")

    # --- Redis ---
    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    # Время жизни кеша поисковых запросов в секундах (BE-10: 5 минут).
    cache_ttl_seconds: int = Field(default=300)

    # --- Загрузка и обработка документов ---
    # Максимальный размер файла в байтах (BE-02: не более 20 МБ).
    max_upload_size_bytes: int = Field(default=20 * 1024 * 1024)
    allowed_extensions: str = Field(default="pdf,docx")
    upload_dir: str = Field(default="/data/uploads")
    # Параметры разбиения текста на чанки (BE-05).
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=100)

    @property
    def database_url(self) -> str:
        """Асинхронный URL подключения к PostgreSQL (asyncpg)."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def elasticsearch_url(self) -> str:
        """URL подключения к Elasticsearch."""
        return (
            f"{self.elasticsearch_scheme}://"
            f"{self.elasticsearch_host}:{self.elasticsearch_port}"
        )

    @property
    def redis_url(self) -> str:
        """URL подключения к Redis."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def allowed_extensions_set(self) -> set[str]:
        """Множество разрешённых расширений файлов в нижнем регистре."""
        return {
            ext.strip().lower()
            for ext in self.allowed_extensions.split(",")
            if ext.strip()
        }

    @property
    def cors_origins_list(self) -> list[str]:
        """Список разрешённых CORS-источников."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Вернуть закешированный экземпляр настроек.

    Использование ``lru_cache`` гарантирует, что настройки читаются из
    окружения только один раз за время жизни процесса.

    :return: единственный экземпляр :class:`Settings`.
    """
    return Settings()


settings = get_settings()
