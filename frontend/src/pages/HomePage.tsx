import { useCallback, useEffect, useRef, useState } from "react";
import {
  deleteDocument,
  getDocument,
  listDocuments,
  uploadDocument,
  type DocumentResponse,
} from "../services/api";
import { DropZone } from "../components/DropZone";
import {
  UploadProgressList,
  type UploadItem,
} from "../components/UploadProgressList";
import { DocumentList } from "../components/DocumentList";

/** Интервал опроса статуса документа, мс. */
const POLL_INTERVAL_MS = 1500;
/** Максимальное число опросов перед прекращением. */
const MAX_POLLS = 40;

/** Генерирует локальный уникальный идентификатор строки загрузки. */
function makeUid(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * Главная страница: зона загрузки документов, прогресс загрузок
 * и список уже загруженных документов.
 */
export function HomePage() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [uploads, setUploads] = useState<UploadItem[]>([]);

  // Флаг монтирования: предотвращает обновление state после размонтирования.
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  /** Обновляет одну строку загрузки по uid. */
  const patchUpload = useCallback(
    (uid: string, patch: Partial<UploadItem>) => {
      if (!mountedRef.current) {
        return;
      }
      setUploads((prev) =>
        prev.map((item) => (item.uid === uid ? { ...item, ...patch } : item)),
      );
    },
    [],
  );

  /** Загружает список документов с бэкенда. */
  const refreshDocuments = useCallback(async () => {
    try {
      const data = await listDocuments(100, 0);
      if (mountedRef.current) {
        setDocuments(data.items);
      }
    } catch (error) {
      // тихо логируем — список просто не обновится
      console.error("Не удалось загрузить список документов:", error);
    } finally {
      if (mountedRef.current) {
        setLoadingDocs(false);
      }
    }
  }, []);

  // Первичная загрузка списка документов при монтировании.
  useEffect(() => {
    void refreshDocuments();
  }, [refreshDocuments]);

  /**
   * Опрашивает статус документа до перехода в indexed/failed
   * либо до исчерпания лимита опросов. Обновляет строку загрузки.
   */
  const pollDocument = useCallback(
    async (uid: string, documentId: string) => {
      for (let attempt = 0; attempt < MAX_POLLS; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
        if (!mountedRef.current) {
          return;
        }
        try {
          const doc = await getDocument(documentId);
          if (doc.status === "indexed") {
            patchUpload(uid, { phase: "done" });
            void refreshDocuments();
            return;
          }
          if (doc.status === "failed") {
            patchUpload(uid, {
              phase: "error",
              errorMessage: doc.error_message ?? "Не удалось обработать файл",
            });
            void refreshDocuments();
            return;
          }
          // uploaded / processing — продолжаем опрос, обновляем список
          void refreshDocuments();
        } catch (error) {
          patchUpload(uid, {
            phase: "error",
            errorMessage:
              error instanceof Error ? error.message : "Ошибка опроса статуса",
          });
          return;
        }
      }
      // лимит опросов исчерпан — оставляем в индексации, но снимаем неопределённость
      patchUpload(uid, {
        phase: "error",
        errorMessage: "Превышено время ожидания индексации",
      });
    },
    [patchUpload, refreshDocuments],
  );

  /**
   * Обрабатывает выбранные файлы: для каждого создаёт строку прогресса
   * и запускает параллельную загрузку с последующим опросом статуса.
   */
  const handleFiles = useCallback(
    (files: File[]) => {
      const newItems: UploadItem[] = files.map((file) => ({
        uid: makeUid(),
        fileName: file.name,
        sizeBytes: file.size,
        phase: "uploading",
        progress: 0,
      }));

      setUploads((prev) => [...newItems, ...prev]);

      // Запускаем N параллельных загрузок.
      files.forEach((file, index) => {
        const uid = newItems[index].uid;
        uploadDocument(file, (percent) => {
          patchUpload(uid, { progress: percent });
        })
          .then((doc) => {
            // сервер принял файл — переходим к индексации и опросу
            patchUpload(uid, { phase: "indexing", progress: 100 });
            void refreshDocuments();
            void pollDocument(uid, doc.id);
          })
          .catch((error: unknown) => {
            patchUpload(uid, {
              phase: "error",
              errorMessage:
                error instanceof Error ? error.message : "Ошибка загрузки",
            });
          });
      });
    },
    [patchUpload, pollDocument, refreshDocuments],
  );

  /** Удаляет документ и обновляет список. */
  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await deleteDocument(id);
        void refreshDocuments();
      } catch (error) {
        console.error("Не удалось удалить документ:", error);
      }
    },
    [refreshDocuments],
  );

  return (
    <div className="home-page">
      <section className="upload-section">
        <h2 className="section-title">Загрузка документов</h2>
        <DropZone onFiles={handleFiles} />
        <UploadProgressList items={uploads} />
      </section>

      <DocumentList
        documents={documents}
        loading={loadingDocs}
        onDelete={handleDelete}
      />
    </div>
  );
}
