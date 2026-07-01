import type { DocumentResponse } from "../services/api";
import { formatDate, formatSize } from "../services/format";
import { StatusBadge } from "./StatusBadge";

/** Свойства списка документов. */
interface DocumentListProps {
  /** Документы для отображения. */
  documents: DocumentResponse[];
  /** Флаг загрузки списка. */
  loading: boolean;
  /** Колбэк удаления документа по идентификатору. */
  onDelete: (id: string) => void;
}

/**
 * Таблица/список загруженных документов.
 * Показывает имя файла, дату загрузки, размер и бейдж статуса.
 * Адаптивна: на широких экранах — таблица, на узких — карточки.
 *
 * @param props документы, флаг загрузки, колбэк удаления
 */
export function DocumentList({
  documents,
  loading,
  onDelete,
}: DocumentListProps) {
  return (
    <section className="document-section">
      <h2 className="section-title">Загруженные документы</h2>

      {loading ? (
        <p className="muted">Загрузка списка...</p>
      ) : documents.length === 0 ? (
        <p className="muted">Пока нет загруженных документов.</p>
      ) : (
        <div className="document-list" data-testid="document-list">
          <div className="document-row document-row--header">
            <span className="document-cell document-cell--name">Имя файла</span>
            <span className="document-cell document-cell--date">
              Дата загрузки
            </span>
            <span className="document-cell document-cell--size">Размер</span>
            <span className="document-cell document-cell--status">Статус</span>
            <span className="document-cell document-cell--actions" />
          </div>

          {documents.map((doc) => (
            <div
              className="document-row"
              data-testid="document-row"
              key={doc.id}
            >
              <span
                className="document-cell document-cell--name"
                title={doc.file_name}
              >
                <span className="document-cell__label">Имя файла:</span>
                {doc.file_name}
              </span>
              <span className="document-cell document-cell--date">
                <span className="document-cell__label">Дата:</span>
                {formatDate(doc.uploaded_at)}
              </span>
              <span className="document-cell document-cell--size">
                <span className="document-cell__label">Размер:</span>
                {formatSize(doc.size_bytes)}
              </span>
              <span className="document-cell document-cell--status">
                <span className="document-cell__label">Статус:</span>
                <StatusBadge status={doc.status} />
              </span>
              <span className="document-cell document-cell--actions">
                <button
                  type="button"
                  className="btn btn--danger btn--small"
                  onClick={() => onDelete(doc.id)}
                  aria-label={`Удалить ${doc.file_name}`}
                >
                  Удалить
                </button>
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
