/** Свойства пагинации. */
interface PaginationProps {
  /** Текущая страница (с 1). */
  page: number;
  /** Общее количество результатов. */
  total: number;
  /** Размер страницы. */
  pageSize: number;
  /** Колбэк смены страницы. */
  onPageChange: (page: number) => void;
}

/**
 * Вычисляет компактный список номеров страниц для отображения.
 * Показывает первую, последнюю, текущую и соседние страницы,
 * заменяя пропуски многоточием (значение -1).
 *
 * @param current текущая страница
 * @param totalPages всего страниц
 */
function buildPageItems(current: number, totalPages: number): number[] {
  const pages = new Set<number>();
  pages.add(1);
  pages.add(totalPages);
  for (let p = current - 1; p <= current + 1; p += 1) {
    if (p >= 1 && p <= totalPages) {
      pages.add(p);
    }
  }
  const sorted = Array.from(pages).sort((a, b) => a - b);

  // вставляем -1 (многоточие) между несмежными номерами
  const result: number[] = [];
  let prev = 0;
  for (const p of sorted) {
    if (prev && p - prev > 1) {
      result.push(-1);
    }
    result.push(p);
    prev = p;
  }
  return result;
}

/**
 * Компонент пагинации: кнопки «Назад»/«Вперёд» и номера страниц.
 * Отрисовывается только при наличии более одной страницы.
 *
 * @param props page, total, pageSize, onPageChange
 */
export function Pagination({
  page,
  total,
  pageSize,
  onPageChange,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  if (totalPages <= 1) {
    return null;
  }

  const items = buildPageItems(page, totalPages);

  return (
    <nav className="pagination" data-testid="pagination" aria-label="Страницы">
      <button
        type="button"
        className="pagination__btn"
        data-testid="page-prev"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
      >
        ← Назад
      </button>

      <div className="pagination__pages">
        {items.map((p, index) =>
          p === -1 ? (
            <span className="pagination__ellipsis" key={`gap-${index}`}>
              …
            </span>
          ) : (
            <button
              type="button"
              key={p}
              className={`pagination__page${
                p === page ? " pagination__page--active" : ""
              }`}
              onClick={() => onPageChange(p)}
              aria-current={p === page ? "page" : undefined}
            >
              {p}
            </button>
          ),
        )}
      </div>

      <button
        type="button"
        className="pagination__btn"
        data-testid="page-next"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
      >
        Вперёд →
      </button>
    </nav>
  );
}
