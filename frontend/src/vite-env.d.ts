/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Базовый путь к API. По умолчанию пустая строка (относительные пути). */
  readonly VITE_API_BASE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
