import { sanitizeHighlight } from "../services/format";

/** Свойства компонента подсветки текста. */
interface HighlightedTextProps {
  /** HTML-строка с подсветкой (теги <mark>), либо null. */
  highlight: string | null;
  /** Запасной чистый текст, если подсветка отсутствует. */
  fallback: string;
}

/**
 * Рендерит текст найденного фрагмента с подсветкой совпадений.
 * Если есть поле highlight — санитизирует и выводит его как HTML
 * (остаются только теги <mark>). Иначе выводит обычный текст.
 *
 * @param props highlight и fallback
 */
export function HighlightedText({ highlight, fallback }: HighlightedTextProps) {
  if (highlight && highlight.trim().length > 0) {
    return (
      <span
        className="highlighted-text"
        // Строка предварительно санитизирована: допустимы только <mark>/</mark>.
        dangerouslySetInnerHTML={{ __html: sanitizeHighlight(highlight) }}
      />
    );
  }
  return <span className="highlighted-text">{fallback}</span>;
}
