# QA — тестирование и контроль качества

Каталог содержит инструменты тестирования системы. Юнит-тесты бэкенда
(QA-01) находятся в `backend/tests`, а набор тестовых документов (QA-03) —
в `backend/tests/fixtures` (генерируется скриптом
`backend/tests/fixtures/generate_fixtures.py`).

## Состав

| Подкаталог    | Требование | Назначение                                            |
|---------------|------------|-------------------------------------------------------|
| `e2e/`        | QA-02      | E2E-тесты критических сценариев (Playwright)           |
| `load/`       | QA-04      | Нагрузочные тесты (Locust, 50 пользователей)           |
| `evaluation/` | QA-05      | Оценка качества поиска (Precision@3)                   |

## QA-02. E2E-тесты (Playwright)

Требуется поднятый полный стек (`docker compose up`).

```bash
cd qa/e2e
npm install
npm run install:browsers          # установка Chromium
E2E_BASE_URL=http://localhost:3000 npm test
```

Сценарий: загрузка документа → индексация → поиск → отображение
результатов, а также проверки пустой выдачи и запуска поиска по Enter.

## QA-04. Нагрузочные тесты (Locust)

Требуется работающий бэкенд с проиндексированными документами
(см. `init.sh`).

```bash
pip install -r qa/requirements.txt
locust -f qa/load/locustfile.py \
    --host http://localhost:8000 \
    --users 50 --spawn-rate 10 --run-time 1m \
    --headless --csv qa/load/report
```

Отчёт о времени отклика сохраняется в `qa/load/report_stats.csv`.

## QA-05. Precision@3

Требуется работающий бэкенд с проиндексированными документами.

```bash
pip install -r qa/requirements.txt
python qa/evaluation/precision_at_3.py \
    --host http://localhost:8000 \
    --output qa/evaluation/precision_report.md
```

Эталонные запросы задаются в `qa/evaluation/reference_queries.json`
и при необходимости адаптируются под загруженный корпус.
