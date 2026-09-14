import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { initializeAuth } from "./auth";
import "./styles.css";
import "./brand.css";
import "./welcome.css";

const root = createRoot(document.getElementById("root")!);
root.render(<p role="status">Проверяем сессию…</p>);

// Initialize before React mounts, so callbacks and StrictMode cannot start a second flow.
initializeAuth().then(() => {
  root.render(<React.StrictMode><App /></React.StrictMode>);
}).catch(() => {
  root.render(
    <main>
      <p role="alert">Не удалось проверить сессию. Проверьте соединение и повторите попытку.</p>
      <button type="button" onClick={() => window.location.reload()}>Повторить</button>
    </main>
  );
});
