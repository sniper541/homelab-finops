import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, ChartNoAxesCombined, Wallet } from "lucide-react";
import { createEmbeddedLoginUrl, embeddedCallback, login } from "./auth";

export default function AuthScreen({ message }: { message: string }) {
  const frame = useRef<HTMLIFrameElement>(null);
  const [url, setUrl] = useState("");
  const [height, setHeight] = useState(690);
  const [mode, setMode] = useState("login");
  const [switching, setSwitching] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    let state = "";
    let authOrigin = "";
    const timer = window.setTimeout(() => {
      if (active) setError("Форма загружается дольше обычного. Можно открыть защищённый вход отдельно.");
    }, 15000);
    const receive = (event: MessageEvent) => {
      const callback = embeddedCallback(event, frame.current?.contentWindow ?? null, state);
      if (callback) {
        window.sessionStorage.removeItem("finops.signed-out");
        // A fragment-only location.replace does not reload or reinitialize the adapter.
        window.history.replaceState(null, "", callback);
        window.location.reload();
      }
      if (event.source !== frame.current?.contentWindow || event.origin !== authOrigin) return;
      if (event.data?.type === "finops-auth-transition") { setSwitching(true); return; }
      if (event.data?.type !== "finops-auth-layout") return;
      const size = event.data.height;
      if (typeof size !== "number" || !Number.isFinite(size) || size < 200 || size > 2400) return;
      setHeight(Math.ceil(size));
      setMode(event.data.mode === "register" ? "register" : "login");
      setReady(true);
      setSwitching(false);
      setError("");
      window.clearTimeout(timer);
    };
    window.addEventListener("message", receive);
    createEmbeddedLoginUrl().then(value => {
      if (!active) return;
      const auth = new URL(value);
      state = auth.searchParams.get("state") ?? "";
      authOrigin = auth.origin;
      setUrl(value);
    }).catch(() => { if (active) setError("Не удалось загрузить форму. Проверьте соединение и повторите попытку."); });
    return () => { active = false; window.clearTimeout(timer); window.removeEventListener("message", receive); };
  }, []);
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
      <section className="welcome-auth" data-mode={mode} data-switching={switching} aria-label="Вход в личный кабинет" aria-busy={!ready && !error}>
        {!ready && !error && <p className="welcome-loading" role="status">Загружаем защищённую форму…</p>}
        {url && <iframe ref={frame} className="welcome-frame" title="Вход и регистрация — Keycloak" src={url} style={{ height }} onLoad={() => frame.current?.contentWindow?.postMessage({ type: "finops-auth-host" }, new URL(url).origin)} allow="publickey-credentials-get; publickey-credentials-create" />}
        {(error || message) && <p className="welcome-error" role="alert">{error || message}</p>}
        {error && <button className="welcome-fallback" onClick={() => login().catch(() => setError("Не удалось открыть вход. Проверьте соединение."))}>Открыть защищённый вход</button>}
      </section>
    </div>
    <footer className="welcome-bottom"><span>FinOps · Личный кабинет</span><span>Ваши данные — только для вас</span></footer>
  </main>;
}
