"""Prometheus-метрики приложения (DO-06).

Помимо стандартных метрик HTTP, собираемых через
``prometheus-fastapi-instrumentator``, здесь определяются специализированные
метрики поиска: количество поисковых запросов и время их выполнения.
"""

from prometheus_client import Counter, Histogram

# Общее количество выполненных поисковых запросов с разбивкой по источнику
# ответа (``cache`` — ответ из Redis, ``elasticsearch`` — реальный запрос).
SEARCH_REQUESTS_TOTAL = Counter(
    "search_requests_total",
    "Общее количество поисковых запросов к /api/v1/search",
    labelnames=("source",),
)

# Время выполнения поискового запроса в секундах.
SEARCH_LATENCY_SECONDS = Histogram(
    "search_latency_seconds",
    "Время обработки поискового запроса в секундах",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Количество загруженных документов с разбивкой по итоговому статусу.
DOCUMENTS_UPLOADED_TOTAL = Counter(
    "documents_uploaded_total",
    "Количество загруженных документов",
    labelnames=("status",),
)

# Количество проиндексированных чанков.
CHUNKS_INDEXED_TOTAL = Counter(
    "chunks_indexed_total",
    "Количество проиндексированных в Elasticsearch чанков",
)
