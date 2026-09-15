import { useState } from "react";
import { isSignedOut, login } from "./auth";

// Recovery only: normal visitors enter the OIDC flow before React mounts.
export default function AuthScreen({ message }: { message: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function retry() {
    setBusy(true);
    setError("");
    try { await login(); }
    catch { setError("Не удалось открыть вход. Проверьте соединение и попробуйте ещё раз."); }
    finally { setBusy(false); }
  }
  return <main className="auth-shell" style={{ display: "grid", placeItems: "center", minHeight: "100vh" }}>
    <section className="auth-panel" aria-labelledby="session-title">
      <p className="welcome-eyebrow">FinOps · Личный кабинет</p>
      <h1 id="session-title">{isSignedOut() ? "Вы вышли из аккаунта" : "Вход не завершён"}</h1>
      <p role="status">{error || message || (isSignedOut() ? "Сессия завершена. До встречи!" : "Повторите вход, чтобы открыть свои данные.")}</p>
      <button className="primary-button" type="button" disabled={busy} onClick={retry}>
        {busy ? "Открываем вход…" : "Войти снова"}
      </button>
    </section>
  </main>;
}
