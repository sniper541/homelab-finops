import Keycloak from "keycloak-js";

export const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL ?? "https://app.sniper541.com/auth",
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
  const callback = [window.location.search, window.location.hash.replace(/^#/, "?")]
    .some(value => {
      const params = new URLSearchParams(value);
      return params.has("error") || (params.has("code") && params.has("state"));
    });
  // One initialization, including when React StrictMode mounts twice.
  return initialization ??= keycloak.init({
    // Process callbacks once; errors and explicit logout require a deliberate retry.
    ...(!isSignedOut() && !callback ? { onLoad: "login-required" as const } : {}),
    flow: "standard",
    pkceMethod: "S256",
    checkLoginIframe: false,
    redirectUri: window.location.origin + "/"
  });
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
