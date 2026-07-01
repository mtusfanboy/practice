import { formatSize } from "../services/format";

/** Фаза жизненного цикла загрузки одного файла. */
export type UploadPhase =
  | "uploading" // идёт отправка файла (XHR в полёте)
  | "indexing" // сервер принял, идёт обработка/индексация
  | "done" // статус документа стал indexed
  | "error"; // ошибка загрузки/обработки

/** Состояние загрузки одного файла. */
export interface UploadItem {
  /** Локальный уникальный идентификатор строки. */
  uid: string;
  /** Имя файла. */
  fileName: string;
  /** Размер файла в байтах. */
  sizeBytes: number;
  /** Текущая фаза. */
  phase: UploadPhase;
  /** Прогресс отправки в процентах (0..100). */
  progress: number;
  /** Текст ошибки, если phase === "error". */
  errorMessage?: string;
}

/** Сопоставление фазы и точной русской подписи статуса. */
const PHASE_LABELS: Record<UploadPhase, string> = {
  uploading: "Загрузка...",
  indexing: "Индексация...",
  done: "Готово",
  error: "Ошибка",
};

/** Свойства списка прогресса загрузок. */
interface UploadProgressListProps {
  /** Текущие элементы загрузки. */
  items: UploadItem[];
}

/**
 * Список строк прогресса загрузки файлов.
 * Для каждого файла отображает имя, прогресс-бар и текстовый статус.
 *
 * @param props массив items
 */
export function UploadProgressList({ items }: UploadProgressListProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="upload-list">
      {items.map((item) => {
        const label = PHASE_LABELS[item.phase];
        // Во время отправки показываем реальный процент; иначе — заполненный бар.
        const barPercent = item.phase === "uploading" ? item.progress : 100;

        return (
          <div className="upload-item" data-testid="upload-item" key={item.uid}>
            <div className="upload-item__head">
              <span className="upload-item__name" title={item.fileName}>
                {item.fileName}
              </span>
              <span className="upload-item__size">
                {formatSize(item.sizeBytes)}
              </span>
            </div>
            <div className="upload-item__bar">
              <div
                className={`upload-item__fill upload-item__fill--${item.phase}`}
                style={{ width: `${barPercent}%` }}
              />
            </div>
            <div className="upload-item__footer">
              <span
                className={`upload-item__status upload-item__status--${item.phase}`}
                data-testid="upload-status"
              >
                {label}
                {item.phase === "uploading" ? ` ${item.progress}%` : ""}
              </span>
              {item.phase === "error" && item.errorMessage ? (
                <span className="upload-item__error" title={item.errorMessage}>
                  {item.errorMessage}
                </span>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
