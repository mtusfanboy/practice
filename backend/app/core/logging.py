"""Настройка структурированного логирования приложения."""

import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    """Сконфигурировать корневой логгер приложения.

    Уровень логирования зависит от флага ``debug``: ``DEBUG`` для
    режима разработки и ``INFO`` для остальных окружений. Логи выводятся
    в ``stdout`` в едином человекочитаемом формате.
    """
    level = logging.DEBUG if settings.debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Понижаем шум от сторонних библиотек.
    for noisy in ("elastic_transport", "elasticsearch", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Вернуть именованный логгер.

    :param name: имя логгера, обычно ``__name__`` модуля.
    :return: настроенный экземпляр :class:`logging.Logger`.
    """
    return logging.getLogger(name)
