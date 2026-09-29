import { useState } from "react";
import { ArrowUpRight, ChartNoAxesCombined, Wallet } from "lucide-react";
import { login } from "./auth";

export default function AuthScreen({ message }: { message: string }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  async function signIn() {
    setPending(true);
    setError("");
    try { await login(); }
    catch { setError("Не удалось открыть вход. Проверьте соединение и повторите попытку."); setPending(false); }
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
      <section className="welcome-auth" aria-labelledby="sign-in-title" aria-busy={pending}>
        <h2 id="sign-in-title">Всё начинается с входа</h2>
        <p className="welcome-auth-description">Одна учётная запись для сервисов Sniper541. Войдите на защищённой странице — и вернитесь к своим финансам.</p>
        {(error || message) && <p className="welcome-error" role="alert">{error || message}</p>}
        <button type="button" className="welcome-sign-in" disabled={pending} onClick={signIn}>{pending ? "Открываем вход…" : "Войти"}<ArrowUpRight aria-hidden="true" /></button>
        <button type="button" className="welcome-telegram" disabled>Войти через Telegram <span>Скоро</span></button>
      </section>
    </div>
    <footer className="welcome-bottom"><span>FinOps · Личный кабинет</span><span>Ваши данные — только для вас</span></footer>
  </main>;
}
