"""Pydantic-схемы API."""

from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    ErrorResponse,
)
from app.schemas.search import (
    SearchHistoryItem,
    SearchHistoryResponse,
    SearchHit,
    SearchResponse,
)

__all__ = [
    "DocumentListResponse",
    "DocumentResponse",
    "ErrorResponse",
    "SearchHistoryItem",
    "SearchHistoryResponse",
    "SearchHit",
    "SearchResponse",
]
