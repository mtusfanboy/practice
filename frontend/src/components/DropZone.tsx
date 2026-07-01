import { useRef, useState, type DragEvent, type ChangeEvent } from "react";

/** Допустимые расширения файлов. */
const ACCEPTED_EXTENSIONS = [".pdf", ".docx"];
const ACCEPT_ATTR = ACCEPTED_EXTENSIONS.join(",");

/** Свойства зоны загрузки. */
interface DropZoneProps {
  /** Колбэк, вызываемый со списком выбранных/перетащенных файлов. */
  onFiles: (files: File[]) => void;
}

/**
 * Проверяет, что имя файла имеет допустимое расширение (.pdf или .docx).
 * @param name имя файла
 */
function hasAcceptedExtension(name: string): boolean {
  const lower = name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

/**
 * Зона Drag-and-Drop для загрузки нескольких файлов.
 * Поддерживает перетаскивание и клик (открывает скрытый input).
 * Принимает только файлы .pdf и .docx.
 *
 * @param props колбэк onFiles
 */
export function DropZone({ onFiles }: DropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  /** Отбирает только допустимые файлы и передаёт их наверх. */
  const handleFiles = (fileList: FileList | null) => {
    if (!fileList) {
      return;
    }
    const accepted = Array.from(fileList).filter((f) =>
      hasAcceptedExtension(f.name),
    );
    if (accepted.length > 0) {
      onFiles(accepted);
    }
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    handleFiles(event.dataTransfer.files);
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
  };

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    handleFiles(event.target.files);
    // сбрасываем значение, чтобы можно было выбрать тот же файл повторно
    event.target.value = "";
  };

  const openFileDialog = () => inputRef.current?.click();

  return (
    <div
      className={`dropzone${isDragging ? " dropzone--active" : ""}`}
      data-testid="dropzone"
      onClick={openFileDialog}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          openFileDialog();
        }
      }}
    >
      <div className="dropzone__icon" aria-hidden="true">
        ⬆
      </div>
      <p className="dropzone__title">
        Перетащите файлы сюда или нажмите для выбора
      </p>
      <p className="dropzone__hint">Поддерживаются форматы PDF и DOCX</p>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPT_ATTR}
        data-testid="file-input"
        className="dropzone__input"
        onChange={handleInputChange}
      />
    </div>
  );
}
