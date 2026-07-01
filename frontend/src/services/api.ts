/**
 * Слой доступа к API бэкенда.
 * Содержит типы данных и функции для работы с документами и поиском.
 * Все запросы используют относительные пути с префиксом VITE_API_BASE.
 */

/** Базовый путь к API. Читается из переменной окружения, по умолчанию пустая строка. */
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

/** Статус обработки документа на бэкенде. */
export type DocumentStatus = "uploaded" | "processing" | "indexed" | "failed";

/** Описание загруженного документа. */
export interface DocumentResponse {
  id: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  status: DocumentStatus;
  page_count: number;
  chunk_count: number;
  error_message: string | null;
  uploaded_at: string;
  indexed_at: string | null;
}

/** Ответ со списком документов. */
export interface DocumentListResponse {
  total: number;
  items: DocumentResponse[];
}

/** Один результат (фрагмент) поиска. */
export interface SearchHit {
  chunk_id: string;
  document_id: string;
  file_name: string;
  page: number;
  text: string;
  score: number;
  /** HTML с подсветкой совпадений в тегах <mark>...</mark>, либо null. */
  highlight: string | null;
}

/** Ответ поискового запроса. */
export interface SearchResponse {
  query: string;
  total: number;
  page: number;
  page_size: number;
  took_ms: number;
  from_cache: boolean;
  results: SearchHit[];
}

/** Размер страницы выдачи поиска (фиксирован требованиями). */
export const SEARCH_PAGE_SIZE = 10;

/**
 * Извлекает человекочитаемое сообщение об ошибке из ответа сервера.
 * @param response объект Response неуспешного запроса
 * @returns текст ошибки из поля detail, либо стандартное сообщение
 */
async function extractError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string };
    if (data && typeof data.detail === "string") {
      return data.detail;
    }
  } catch {
    // тело не является JSON — игнорируем
  }
  return `Ошибка запроса (${response.status})`;
}

/**
 * Загружает один файл на сервер через XMLHttpRequest,
 * сообщая о прогрессе загрузки через колбэк.
 * Используется XHR (а не fetch), так как fetch не даёт прогресс отправки.
 *
 * @param file загружаемый файл
 * @param onProgress колбэк прогресса (0..100)
 * @returns промис с описанием созданного документа
 */
export function uploadDocument(
  file: File,
  onProgress: (percent: number) => void,
): Promise<DocumentResponse> {
  return new Promise<DocumentResponse>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append("file", file);

    xhr.open("POST", `${API_BASE}/api/v1/documents/upload`, true);

    xhr.upload.onprogress = (event: ProgressEvent) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        onProgress(percent);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as DocumentResponse);
        } catch {
          reject(new Error("Некорректный ответ сервера"));
        }
      } else {
        // пытаемся достать detail из тела ошибки
        let message = `Ошибка загрузки (${xhr.status})`;
        try {
          const data = JSON.parse(xhr.responseText) as { detail?: string };
          if (data && typeof data.detail === "string") {
            message = data.detail;
          }
        } catch {
          // тело не JSON — оставляем стандартное сообщение
        }
        reject(new Error(message));
      }
    };

    xhr.onerror = () => reject(new Error("Сетевая ошибка при загрузке"));
    xhr.send(form);
  });
}

/**
 * Получает список документов.
 * @param limit максимальное число элементов
 * @param offset смещение
 */
export async function listDocuments(
  limit = 100,
  offset = 0,
): Promise<DocumentListResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/documents?limit=${limit}&offset=${offset}`,
  );
  if (!response.ok) {
    throw new Error(await extractError(response));
  }
  return (await response.json()) as DocumentListResponse;
}

/**
 * Получает один документ по идентификатору (используется при опросе статуса).
 * @param id идентификатор документа
 */
export async function getDocument(id: string): Promise<DocumentResponse> {
  const response = await fetch(`${API_BASE}/api/v1/documents/${id}`);
  if (!response.ok) {
    throw new Error(await extractError(response));
  }
  return (await response.json()) as DocumentResponse;
}

/**
 * Удаляет документ по идентификатору.
 * @param id идентификатор документа
 */
export async function deleteDocument(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/documents/${id}`, {
    method: "DELETE",
  });
  if (!response.ok && response.status !== 204) {
    throw new Error(await extractError(response));
  }
}

/**
 * Выполняет поиск по базе знаний.
 * @param query поисковый запрос
 * @param page номер страницы (с 1)
 * @param pageSize размер страницы
 */
export async function search(
  query: string,
  page = 1,
  pageSize = SEARCH_PAGE_SIZE,
): Promise<SearchResponse> {
  const params = new URLSearchParams({
    q: query,
    page: String(page),
    page_size: String(pageSize),
  });
  const response = await fetch(`${API_BASE}/api/v1/search?${params.toString()}`);
  if (!response.ok) {
    throw new Error(await extractError(response));
  }
  return (await response.json()) as SearchResponse;
}
