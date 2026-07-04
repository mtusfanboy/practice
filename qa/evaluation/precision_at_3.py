"""Оценка качества поиска по метрике Precision@3 (QA-05).

Для каждого эталонного запроса проверяется, входит ли нужный документ
(идентифицируемый по характерной подстроке ``signature``) в топ-3 выдачи.
Результаты оформляются в виде Markdown-таблицы и сохраняются в файл.

Запуск (требуется работающий бэкенд с проиндексированными документами)::

    python qa/evaluation/precision_at_3.py \\
        --host http://localhost:8000 \\
        --reference qa/evaluation/reference_queries.json \\
        --output qa/evaluation/precision_report.md

Зависимости: requests (``pip install requests``).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import requests

TOP_K = 3


@dataclass
class QueryResult:
    """Результат проверки одного эталонного запроса.

    :param query: текст запроса.
    :param signature: ожидаемая подстрока релевантного документа.
    :param hit: найден ли нужный документ в топ-3.
    :param top_files: имена файлов из топ-3 выдачи.
    """

    query: str
    signature: str
    hit: bool
    top_files: list[str]


def evaluate_query(host: str, query: str, signature: str) -> QueryResult:
    """Выполнить запрос и проверить наличие нужного документа в топ-3.

    :param host: базовый URL бэкенда.
    :param query: текст поискового запроса.
    :param signature: характерная подстрока релевантного документа.
    :return: результат проверки запроса.
    """
    response = requests.get(
        f"{host}/api/v1/search",
        params={"q": query, "page": 1, "page_size": TOP_K},
        timeout=30,
    )
    response.raise_for_status()
    results = response.json().get("results", [])[:TOP_K]

    needle = signature.lower()
    hit = any(needle in hit_item.get("text", "").lower() for hit_item in results)
    top_files = [hit_item.get("file_name", "—") for hit_item in results]
    return QueryResult(query=query, signature=signature, hit=hit, top_files=top_files)


def build_markdown_report(results: list[QueryResult], precision: float) -> str:
    """Сформировать Markdown-отчёт с таблицей результатов.

    :param results: результаты по всем запросам.
    :param precision: итоговое значение Precision@3.
    :return: текст отчёта в формате Markdown.
    """
    lines = [
        "# Отчёт об оценке качества поиска (Precision@3)",
        "",
        f"Эталонных запросов: **{len(results)}**  ",
        f"**Precision@3 = {precision:.2f}** "
        f"({sum(r.hit for r in results)} из {len(results)} запросов попали в топ-3)",
        "",
        "| № | Запрос | Сигнатура | Нужный документ в топ-3 | Топ-3 файлов |",
        "|---|--------|-----------|:----------------------:|--------------|",
    ]
    for index, result in enumerate(results, start=1):
        mark = "✅ да" if result.hit else "❌ нет"
        files = ", ".join(result.top_files) if result.top_files else "—"
        lines.append(
            f"| {index} | {result.query} | `{result.signature}` | {mark} | {files} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """Точка входа: выполнить оценку и сохранить отчёт."""
    parser = argparse.ArgumentParser(description="Оценка Precision@3 (QA-05)")
    parser.add_argument("--host", default="http://localhost:8000", help="URL бэкенда")
    parser.add_argument(
        "--reference",
        default=str(Path(__file__).with_name("reference_queries.json")),
        help="JSON с эталонными запросами",
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).with_name("precision_report.md")),
        help="Путь к итоговому Markdown-отчёту",
    )
    args = parser.parse_args()

    reference = json.loads(Path(args.reference).read_text(encoding="utf-8"))
    queries = reference["queries"]

    results: list[QueryResult] = []
    for item in queries:
        try:
            result = evaluate_query(args.host, item["query"], item["signature"])
        except requests.RequestException as exc:
            print(f"Ошибка запроса '{item['query']}': {exc}", file=sys.stderr)
            result = QueryResult(item["query"], item["signature"], False, [])
        status = "найден" if result.hit else "НЕ найден"
        print(f"[{status:>9}] {result.query}")
        results.append(result)

    precision = sum(r.hit for r in results) / len(results) if results else 0.0
    report = build_markdown_report(results, precision)
    Path(args.output).write_text(report, encoding="utf-8")

    print(f"\nPrecision@3 = {precision:.2f}")
    print(f"Отчёт сохранён: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
