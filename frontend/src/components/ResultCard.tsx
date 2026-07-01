import type { SearchHit } from "../services/api";
import { HighlightedText } from "./HighlightedText";

/** Свойства карточки результата. */
interface ResultCardProps {
  /** Один результат поиска. */
  hit: SearchHit;
}

/**
 * Карточка одного результата поиска.
 * Показывает имя файла, номер страницы, фрагмент текста с подсветкой
 * и релевантность.
 *
 * @param props результат поиска hit
 */
export function ResultCard({ hit }: ResultCardProps) {
  return (
    <article className="result-card" data-testid="result-card">
      <header className="result-card__head">
        <span className="result-card__file" title={hit.file_name}>
          {hit.file_name}
        </span>
        <span className="result-card__page">Страница {hit.page}</span>
      </header>

      <p className="result-card__text">
        <HighlightedText highlight={hit.highlight} fallback={hit.text} />
      </p>

      <footer className="result-card__foot">
        <span className="result-card__score">
          Релевантность: {hit.score.toFixed(2)}
        </span>
      </footer>
    </article>
  );
}
