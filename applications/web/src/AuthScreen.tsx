import { useState } from "react";
import { ArrowRight, BarChart3, Check, LockKeyhole, LogIn, Send, UserPlus, Wallet } from "lucide-react";
import { login, register } from "./auth";

const registrationEnabled = import.meta.env.VITE_REGISTRATION_ENABLED === "true";

export default function AuthScreen({ message }: { message: string }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const isRegistration = mode === "register";

  async function continueToAccount() {
    if (isRegistration && !registrationEnabled) return;
    setError("");
    setBusy(true);
    try { await (isRegistration ? register() : login()); }
    catch { setError("Не удалось открыть страницу входа. Попробуйте ещё раз."); }
    finally { setBusy(false); }
  }

  return (
    <main className="auth-shell finops-welcome">
      <section className="auth-hero" aria-labelledby="welcome-title">
        <a className="brand brand--auth" href="/" aria-label="FinOps — главная">
          <span className="brand__mark"><Wallet aria-hidden="true" /></span>
          <span className="welcome-brand-name">FinOps <small>Личные финансы</small></span>
        </a>
        <div className="auth-copy">
          <span className="welcome-eyebrow">БОЛЬШЕ ЯСНОСТИ. МЕНЬШЕ РУТИНЫ.</span>
          <h1 id="welcome-title">Ваши финансы.<br /><span>Ясная картина.</span></h1>
          <p>Доходы, расходы и привычки — в одном месте. Замечайте главное и планируйте следующий шаг.</p>
        </div>
        <div className="welcome-preview" aria-label="Демонстрационный обзор финансов">
          <div className="welcome-preview-heading"><span><BarChart3 aria-hidden="true" /> Обзор месяца</span><small>Пример</small></div>
          <div className="welcome-balance"><span>Свободный остаток</span><strong>48 200 <small>₽</small></strong></div>
          <div className="welcome-bars" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /><i /><i /></div>
          <div className="welcome-totals"><span>Доходы <strong>128 000 ₽</strong></span><span>Расходы <strong>79 800 ₽</strong></span></div>
        </div>
        <p className="welcome-caption"><Check aria-hidden="true" /> Всё важное — перед глазами</p>
      </section>

      <section className="auth-panel" aria-labelledby="account-title">
        <div className="auth-panel__header">
          <span className="welcome-eyebrow"><LockKeyhole aria-hidden="true" /> ЛИЧНЫЙ КАБИНЕТ</span>
          <h2 id="account-title">{isRegistration ? "Начнём знакомство" : "Вход в кабинет"}</h2>
          <p>{isRegistration ? "Один аккаунт для вашей финансовой картины." : "Рады видеть вас снова. Продолжим с того, на чём остановились."}</p>
        </div>
        <div className="auth-switch" role="group" aria-label="Вход или регистрация">
          <button type="button" aria-pressed={!isRegistration} className={!isRegistration ? "is-active" : ""} onClick={() => { setMode("login"); setError(""); }} disabled={busy}><LogIn aria-hidden="true" /> Войти</button>
          <button type="button" aria-pressed={isRegistration} className={isRegistration ? "is-active" : ""} onClick={() => { setMode("register"); setError(""); }} disabled={busy}><UserPlus aria-hidden="true" /> Регистрация</button>
        </div>
        <div className="welcome-account-step">
          <div className="welcome-step-icon"><LockKeyhole aria-hidden="true" /></div>
          <h3>{isRegistration ? (registrationEnabled ? "Создайте аккаунт FinOps" : "Регистрация пока закрыта") : "Ваш аккаунт FinOps"}</h3>
          <p>{isRegistration
            ? (registrationEnabled ? "Заполните данные на следующей странице и возвращайтесь в свой кабинет." : "Пока доступ есть у приглашённых пользователей. Если у вас уже есть аккаунт, выберите «Войти».")
            : "Введите логин и пароль на следующей странице. После входа вы вернётесь в свой кабинет."}</p>
          <button className="primary-button primary-button--wide" type="button" disabled={busy || (isRegistration && !registrationEnabled)} onClick={continueToAccount}>
            {busy ? "Переходим…" : isRegistration ? "Создать аккаунт" : "Войти в FinOps"}<ArrowRight aria-hidden="true" />
          </button>
        </div>
        <div className="welcome-divider"><span>Другие способы входа</span></div>
        <div className="welcome-telegram">
          <button className="telegram-button" type="button" disabled aria-describedby="telegram-note"><Send aria-hidden="true" /> Войти через Telegram <span className="welcome-soon">Скоро</span></button>
          <p id="telegram-note">Быстрый вход через Telegram появится позже.</p>
        </div>
        {(error || message) && <p className="auth-message" role="status">{error || message}</p>}
        <p className="welcome-footnote"><LockKeyhole aria-hidden="true" /> Единый аккаунт. Ваш личный кабинет.</p>
      </section>
    </main>
  );
}
