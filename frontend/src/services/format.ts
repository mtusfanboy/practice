/**
 * Вспомогательные функции форматирования и санитизации.
 */

/**
 * Форматирует ISO-дату в человекочитаемый вид (русская локаль).
 * @param iso строка даты в формате ISO 8601
 * @returns строка вида "23.06.2026, 18:11" либо исходная строка при ошибке
 */
export function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Форматирует размер файла в байтах в человекочитаемый вид.
 * @param bytes размер в байтах
 */
export function formatSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} Б`;
  }
  const units = ["КБ", "МБ", "ГБ"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

/**
 * Санитизирует строку подсветки: экранирует все символы `<` и `>`,
 * кроме разрешённых тегов `<mark>` и `</mark>`.
 * Результат безопасно передавать в dangerouslySetInnerHTML.
 *
 * @param raw строка от бэкенда, потенциально с произвольным HTML
 * @returns безопасная строка, содержащая только теги <mark>/</mark>
 */
export function sanitizeHighlight(raw: string): string {
  // Сначала полностью экранируем все угловые скобки и амперсанды,
  // затем возвращаем обратно только разрешённые теги <mark> и </mark>.
  const escaped = raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  return escaped
    .replace(/&lt;mark&gt;/g, "<mark>")
    .replace(/&lt;\/mark&gt;/g, "</mark>");
}
