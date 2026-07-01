import { useState, type KeyboardEvent } from "react";

/** Свойства строки поиска. */
interface SearchBarProps {
  /** Начальное значение запроса. */
  initialValue?: string;
  /** Колбэк запуска поиска с текстом запроса. */
  onSearch: (query: string) => void;
  /** Флаг выполнения поиска (блокирует кнопку). */
  loading: boolean;
}

/**
 * Строка поиска: текстовое поле и кнопка «Найти».
 * Поиск запускается по клику на кнопку и по нажатию Enter в поле.
 *
 * @param props initialValue, onSearch, loading
 */
export function SearchBar({
  initialValue = "",
  onSearch,
  loading,
}: SearchBarProps) {
  const [value, setValue] = useState(initialValue);

  /** Запускает поиск, если запрос непустой. */
  const trigger = () => {
    const trimmed = value.trim();
    if (trimmed.length > 0) {
      onSearch(trimmed);
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      trigger();
    }
  };

  return (
    <div className="search-bar">
      <input
        type="text"
        className="search-bar__input"
        data-testid="search-input"
        placeholder="Введите поисковый запрос..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        aria-label="Поисковый запрос"
      />
      <button
        type="button"
        className="btn btn--primary"
        data-testid="search-button"
        onClick={trigger}
        disabled={loading}
      >
        {loading ? "Поиск..." : "Найти"}
      </button>
    </div>
  );
}
