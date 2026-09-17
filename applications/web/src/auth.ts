import Keycloak from "keycloak-js";

export const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL ?? "https://auth.sniper541.com",
  realm: "finops",
  clientId: "finops-web"
});

export class AuthenticationError extends Error {}

let initialization: Promise<boolean> | undefined;
const signedOutKey = "finops.signed-out";
export function isSignedOut() {
  return window.sessionStorage.getItem(signedOutKey) === "true";
}

export function initializeAuth() {
  // One initialization, including when React StrictMode mounts twice.
  return initialization ??= keycloak.init({
    // The embedded native form returns here; the adapter validates state and PKCE.
    flow: "standard",
    pkceMethod: "S256",
    checkLoginIframe: false,
    redirectUri: window.location.origin + "/"
  });
}

export function createEmbeddedLoginUrl() {
  return keycloak.createLoginUrl({
    redirectUri: window.location.origin + "/",
    ...(isSignedOut() ? { prompt: "login" as const } : {})
  });
}

// Accept only our frame's same-origin callback for the flow we started.
export function embeddedCallback(event: MessageEvent, source: Window | null, state: string): string | undefined {
  if (!source || event.source !== source || event.origin !== window.location.origin ||
      event.data?.type !== "finops-auth-callback" || typeof event.data.url !== "string") return;
  try {
    const url = new URL(event.data.url);
    const params = new URLSearchParams(url.hash.slice(1));
    if (url.origin === window.location.origin && url.pathname === "/" && !url.search &&
        state && params.get("state") === state && (params.has("code") || params.has("error"))) return url.href;
  } catch { /* Ignore malformed messages. */ }
}

export function login() {
  window.sessionStorage.removeItem(signedOutKey);
  return keycloak.login({ redirectUri: window.location.origin + "/" });
}

export function register() {
  return keycloak.register({ redirectUri: window.location.origin + "/" });
}

export async function logout() {
  // A tab-local UX marker only, never a token or an authorization decision.
  window.sessionStorage.setItem(signedOutKey, "true");
  try {
    await keycloak.logout({ redirectUri: window.location.origin + "/" });
  } catch (error) {
    window.sessionStorage.removeItem(signedOutKey);
    throw error;
  }
}

export async function getAccessToken(): Promise<string> {
  if (!keycloak.authenticated) {
    throw new AuthenticationError("Войдите в аккаунт, чтобы загрузить данные.");
  }
  try {
    await keycloak.updateToken(30);
  } catch {
    keycloak.clearToken();
    throw new AuthenticationError("Сессия истекла. Войдите снова.");
  }
  if (!keycloak.token) {
    throw new AuthenticationError("Сессия истекла. Войдите снова.");
  }
  // Tokens stay in the adapter's memory, never localStorage/sessionStorage.
  return keycloak.token;
}
