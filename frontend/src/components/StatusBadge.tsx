import type { DocumentStatus } from "../services/api";

/** Русские подписи статусов документа. */
const STATUS_LABELS: Record<DocumentStatus, string> = {
  uploaded: "Загружен",
  processing: "Обработка",
  indexed: "Готово",
  failed: "Ошибка",
};

/** Свойства бейджа статуса. */
interface StatusBadgeProps {
  /** Статус документа. */
  status: DocumentStatus;
}

/**
 * Цветной бейдж статуса документа.
 * @param props статус документа
 */
export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={`status-badge status-badge--${status}`}
      data-testid="document-status"
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
