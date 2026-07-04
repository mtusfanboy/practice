import { test, expect } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";

/**
 * E2E-тест критического пользовательского сценария (QA-02):
 *   загрузка документа → индексация → поиск → отображение результатов.
 *
 * Требует поднятого полного стека (docker compose up) и доступного
 * фронтенда по E2E_BASE_URL. Использует тестовый PDF из набора фикстур
 * бэкенда (QA-03).
 */

// Путь к тестовому документу (переиспользуем фикстуру бэкенда).
const SAMPLE_PDF = path.resolve(
  __dirname,
  "../../../backend/tests/fixtures/sample_lecture.pdf",
);

test.beforeAll(() => {
  if (!fs.existsSync(SAMPLE_PDF)) {
    throw new Error(
      `Тестовый файл не найден: ${SAMPLE_PDF}. ` +
        "Сгенерируйте фикстуры: python backend/tests/fixtures/generate_fixtures.py",
    );
  }
});

test("загрузка документа, индексация и поиск по нему", async ({ page }) => {
  await page.goto("/");

  // Переходим на вкладку документов (если используется навигация вкладками).
  const documentsTab = page.getByTestId("tab-documents");
  if (await documentsTab.count()) {
    await documentsTab.click();
  }

  // FE-01: загрузка файла через скрытый input.
  await page.getByTestId("file-input").setInputFiles(SAMPLE_PDF);

  // FE-02: дожидаемся статуса «Готово» (документ проиндексирован).
  const uploadStatus = page.getByTestId("upload-status").first();
  await expect(uploadStatus).toContainText(/Готово/i, { timeout: 60_000 });

  // FE-03: документ появился в списке загруженных.
  const documentList = page.getByTestId("document-list");
  await expect(documentList.getByTestId("document-row").first()).toBeVisible();

  // Переходим к поиску.
  const searchTab = page.getByTestId("tab-search");
  if (await searchTab.count()) {
    await searchTab.click();
  }

  // FE-04: вводим запрос и запускаем поиск кнопкой «Найти».
  await page.getByTestId("search-input").fill("данных");
  await page.getByTestId("search-button").click();

  // FE-05/FE-06: появились карточки результатов с подсветкой совпадений.
  const results = page.getByTestId("search-results");
  await expect(results.getByTestId("result-card").first()).toBeVisible({
    timeout: 20_000,
  });
  await expect(results.locator("mark").first()).toBeVisible();
});

test("поиск без совпадений показывает сообщение об отсутствии результатов", async ({
  page,
}) => {
  await page.goto("/");

  const searchTab = page.getByTestId("tab-search");
  if (await searchTab.count()) {
    await searchTab.click();
  }

  // FE-08: запрос-бессмыслица не должен давать результатов.
  await page.getByTestId("search-input").fill("зюзьбляргквантумъ");
  await page.getByTestId("search-button").click();

  await expect(page.getByTestId("no-results")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("no-results")).toContainText(
    /ничего не найдено/i,
  );
});

test("поиск запускается по нажатию Enter", async ({ page }) => {
  await page.goto("/");

  const searchTab = page.getByTestId("tab-search");
  if (await searchTab.count()) {
    await searchTab.click();
  }

  // FE-04: поиск по клавише Enter.
  const input = page.getByTestId("search-input");
  await input.fill("данных");
  await input.press("Enter");

  // Должны отобразиться либо результаты, либо сообщение об их отсутствии.
  const results = page.getByTestId("search-results");
  const noResults = page.getByTestId("no-results");
  await expect(results.or(noResults)).toBeVisible({ timeout: 20_000 });
});
