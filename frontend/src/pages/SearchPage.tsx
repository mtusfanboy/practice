import { useCallback, useRef, useState } from "react";
import { search, type SearchResponse } from "../services/api";
import { SearchBar } from "../components/SearchBar";
import { SearchResults } from "../components/SearchResults";

/**
 * Страница поиска: строка поиска, результаты в виде карточек и пагинация.
 * Хранит текущий запрос, чтобы пагинация работала по тому же запросу.
 */
export function SearchPage() {
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Текущий активный запрос (для смены страниц).
  const currentQueryRef = useRef<string>("");

  /** Выполняет поиск по запросу и странице. */
  const runSearch = useCallback(async (query: string, page: number) => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await search(query, page);
      setResponse(data);
    } catch (error) {
      setResponse(null);
      setErrorMessage(
        error instanceof Error ? error.message : "Ошибка поиска",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  /** Обработчик запуска поиска: всегда начинает с первой страницы. */
  const handleSearch = useCallback(
    (query: string) => {
      currentQueryRef.current = query;
      void runSearch(query, 1);
    },
    [runSearch],
  );

  /** Обработчик смены страницы: повторяет поиск по сохранённому запросу. */
  const handlePageChange = useCallback(
    (page: number) => {
      if (currentQueryRef.current) {
        void runSearch(currentQueryRef.current, page);
      }
    },
    [runSearch],
  );

  return (
    <div className="search-page">
      <h2 className="section-title">Поиск по базе знаний</h2>
      <SearchBar onSearch={handleSearch} loading={loading} />

      {errorMessage ? <p className="error-text">{errorMessage}</p> : null}

      <SearchResults response={response} onPageChange={handlePageChange} />
    </div>
  );
}
