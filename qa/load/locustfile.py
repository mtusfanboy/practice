"""Нагрузочное тестирование поиска (QA-04).

Имитирует одновременную работу пользователей, выполняющих поисковые
запросы к системе, и собирает отчёт о времени отклика.

Запуск (50 одновременных пользователей в течение 1 минуты)::

    locust -f qa/load/locustfile.py \\
        --host http://localhost:8000 \\
        --users 50 --spawn-rate 10 --run-time 1m \\
        --headless --csv qa/load/report

По завершении формируются файлы ``report_stats.csv`` и
``report_stats_history.csv`` с распределением времени отклика.
"""

import random

from locust import HttpUser, between, task

# Набор поисковых запросов, имитирующих реальные обращения к базе знаний.
SEARCH_TERMS = [
    "нейронные сети",
    "трансформер",
    "градиентный спуск",
    "механизм внимания",
    "обучение модели",
    "классификация изображений",
    "рекуррентная сеть",
    "функция потерь",
    "регуляризация",
    "векторное представление",
    "attention",
    "convolution",
    "optimization",
    "language model",
]


class SearchUser(HttpUser):
    """Виртуальный пользователь, выполняющий поисковые запросы."""

    # Пауза между запросами одного пользователя (1–3 секунды).
    wait_time = between(1, 3)

    @task(5)
    def search(self) -> None:
        """Выполнить поисковый запрос со случайным термином и страницей."""
        term = random.choice(SEARCH_TERMS)
        page = random.randint(1, 3)
        with self.client.get(
            "/api/v1/search",
            params={"q": term, "page": page, "page_size": 10},
            name="/api/v1/search",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Неожиданный статус: {response.status_code}")

    @task(1)
    def list_documents(self) -> None:
        """Периодически запрашивать список документов."""
        self.client.get(
            "/api/v1/documents",
            params={"limit": 20, "offset": 0},
            name="/api/v1/documents",
        )
