import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Конфигурация Vite.
 * В режиме разработки проксирует запросы `/api` на бэкенд (порт 8000),
 * чтобы фронтенд мог обращаться к API по относительным путям.
 */
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
