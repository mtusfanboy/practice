import { useState } from "react";
import { HomePage } from "./pages/HomePage";
import { SearchPage } from "./pages/SearchPage";

/** Доступные вкладки приложения. */
type Tab = "documents" | "search";

/**
 * Корневой компонент приложения.
 * Реализует простое переключение между вкладками «Документы» и «Поиск».
 */
export function App() {
  const [tab, setTab] = useState<Tab>("documents");

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__inner">
          <h1 className="app-title">База знаний университета</h1>
          <nav className="tabs" aria-label="Разделы">
            <button
              type="button"
              className={`tab${tab === "documents" ? " tab--active" : ""}`}
              data-testid="tab-documents"
              onClick={() => setTab("documents")}
            >
              Документы
            </button>
            <button
              type="button"
              className={`tab${tab === "search" ? " tab--active" : ""}`}
              data-testid="tab-search"
              onClick={() => setTab("search")}
            >
              Поиск
            </button>
          </nav>
        </div>
      </header>

      <main className="app-main">
        {tab === "documents" ? <HomePage /> : <SearchPage />}
      </main>

      <footer className="app-footer">
        <p>Система поиска по базе знаний · {new Date().getFullYear()}</p>
      </footer>
    </div>
  );
}
