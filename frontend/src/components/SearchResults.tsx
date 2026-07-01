import type { SearchResponse } from "../services/api";
import { ResultCard } from "./ResultCard";
import { Pagination } from "./Pagination";

/** Свойства блока результатов поиска. */
interface SearchResultsProps {
  /** Ответ поиска, либо null если поиск ещё не выполнялся. */
  response: SearchResponse | null;
  /** Колбэк смены страницы. */
  onPageChange: (page: number) => void;
}

/**
 * Блок отображения результатов поиска.
 * Показывает метаинформацию, карточки результатов и пагинацию.
 * При пустой выдаче выводит сообщение об отсутствии результатов.
 *
 * @param props response, onPageChange
 */
export function SearchResults({ response, onPageChange }: SearchResultsProps) {
  if (!response) {
    return null;
  }

  if (response.total === 0) {
    return (
      <p className="no-results" data-testid="no-results">
        По вашему запросу ничего не найдено. Попробуйте изменить формулировку
      </p>
    );
  }

  return (
    <div className="search-results-wrap">
      <p className="search-meta">
        Найдено результатов: <strong>{response.total}</strong> · время:{" "}
        {response.took_ms} мс
        {response.from_cache ? " · из кэша" : ""}
      </p>

      <div className="search-results" data-testid="search-results">
        {response.results.map((hit) => (
          <ResultCard hit={hit} key={hit.chunk_id} />
        ))}
      </div>

      <Pagination
        page={response.page}
        total={response.total}
        pageSize={response.page_size}
        onPageChange={onPageChange}
      />
    </div>
  );
}
