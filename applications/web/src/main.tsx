import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { initializeAuth } from "./auth";
import "./styles.css";
import "./brand.css";
import "./welcome.css";

const root = createRoot(document.getElementById("root")!);
if (window.parent !== window && /(?:^#|&)(?:code|error)=/.test(window.location.hash)) {
  // Do not initialize a second adapter or consume the parent's PKCE callback state.
  window.parent.postMessage({ type: "finops-auth-callback", url: window.location.href }, window.location.origin);
  root.render(<main className="session-loading"><p role="status">Завершаем вход…</p></main>);
} else {
  root.render(<main className="session-loading"><span>FinOps.</span><p role="status">Проверяем сессию…</p></main>);

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
}
