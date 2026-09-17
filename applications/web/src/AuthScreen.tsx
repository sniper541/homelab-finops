import { useState } from "react";
import { ArrowRight, ArrowUpRight, ChartNoAxesCombined, LockKeyhole, Send, Wallet } from "lucide-react";
import { isSignedOut, login, register } from "./auth";

export default function AuthScreen({ message }: { message: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const signedOut = isSignedOut();
  async function enter() {
    setBusy(true);
    setError("");
    try { await (mode === "login" ? login() : register()); }
    catch { setError("Не удалось открыть вход. Проверьте соединение и попробуйте ещё раз."); }
    finally { setBusy(false); }
  }
  return <main className="welcome-page">
    <div className="access-scene" aria-hidden="true"><i /><i /><i /></div>
    <header className="welcome-header">
      <a className="welcome-logo" href="/" aria-label="FinOps — главная"><Wallet /><span>FinOps<span className="welcome-logo-dot">.</span></span></a>
      <span className="welcome-owner">by Sniper541</span>
    </header>
    <div className="welcome-layout">
      <section className="welcome-story" aria-labelledby="welcome-title">
        <h1 id="welcome-title">Ваши финансы.<br /><span>В ясной картине.</span></h1>
        <p>Баланс, динамика и привычки — в одном пространстве. Вводите операции в Telegram, а здесь смотрите, как складывается месяц.</p>
        <div className="welcome-ledger" aria-label="Возможности FinOps">
          <div><Wallet aria-hidden="true" /><span>Баланс</span><span>Всё под контролем</span></div>
          <div><ChartNoAxesCombined aria-hidden="true" /><span>Аналитика</span><span>Видеть главное</span></div>
          <div><ArrowUpRight aria-hidden="true" /><span>История</span><span>Каждая операция</span></div>
        </div>
      </section>
      <section className="welcome-card" aria-labelledby={mode === "login" ? "session-title" : "register-title"} data-mode={mode}>
        <div className="welcome-card-edge" aria-hidden="true" />
        <div className="welcome-tabs" aria-label="Способ входа">
          <button type="button" aria-pressed={mode === "login"} onClick={() => setMode("login")} disabled={busy}>Вход</button>
          <button type="button" aria-pressed={mode === "register"} onClick={() => setMode("register")} disabled={busy}>Регистрация</button>
        </div>
        <div className="welcome-card-content">
          <span className="welcome-lock"><LockKeyhole aria-hidden="true" /></span>
          <div className="welcome-panes">
            <div className="welcome-pane" data-active={mode === "login"} aria-hidden={mode !== "login"}>
              <h2 id="session-title">{signedOut ? "До новой встречи." : "С возвращением."}</h2>
              <p>{signedOut ? "Вы вышли из аккаунта. Ваши данные останутся здесь до следующего входа." : "Войдите в своё пространство. Всё важное уже под рукой."}</p>
            </div>
            <div className="welcome-pane" data-active={mode === "register"} aria-hidden={mode !== "register"}>
              <h2 id="register-title">Начните с себя.</h2>
              <p>Создайте аккаунт, чтобы собрать свои финансы в одном месте.</p>
            </div>
          </div>
        </div>
        {(error || message) && <p className="welcome-error" role="alert">{error || message}</p>}
        <button className="welcome-submit" type="button" disabled={busy} onClick={enter}>
          <span>{busy ? "Открываем вход…" : mode === "register" ? "Создать аккаунт" : signedOut ? "Войти снова" : "Войти"}</span><ArrowRight aria-hidden="true" />
        </button>
        <div className="welcome-divider"><span>или</span></div>
        <button className="welcome-telegram" type="button" disabled aria-describedby="telegram-soon">
          <Send aria-hidden="true" /><span>Войти через Telegram</span><small>Скоро</small>
        </button>
        <p id="telegram-soon" className="welcome-hint">Вход через Telegram появится позже.</p>
        <footer className="welcome-card-footer"><LockKeyhole aria-hidden="true" /> Один аккаунт. Ваше пространство.</footer>
      </section>
    </div>
    <footer className="welcome-bottom"><span>FinOps · Личный кабинет</span><span>Ваши данные — только для вас</span></footer>
  </main>;
}
