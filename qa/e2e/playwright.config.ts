import { defineConfig, devices } from "@playwright/test";

/**
 * Конфигурация Playwright для E2E-тестов (QA-02).
 *
 * Базовый URL фронтенда задаётся переменной окружения E2E_BASE_URL
 * (по умолчанию http://localhost:3000 — порт фронтенда в docker-compose).
 * Тесты выполняются против поднятого полного стека (docker compose up).
 */
export default defineConfig({
  testDir: "./tests",
  // Сценарии последовательны: загрузка документа влияет на состояние поиска.
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
