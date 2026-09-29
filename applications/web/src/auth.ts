import Keycloak from "keycloak-js";

export const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL ?? "https://auth.sniper541.com",
  realm: "finops",
  clientId: "finops-web"
});

export class AuthenticationError extends Error {}

let initialization: Promise<boolean> | undefined;
const signedOutKey = "finops.signed-out";
export function initializeAuth() {
  // One initialization, including when React StrictMode mounts twice.
  return initialization ??= keycloak.init({
    // The adapter validates the authorization callback, state and PKCE.
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
