import Keycloak from "keycloak-js";

export const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL ?? "https://app.sniper541.com/auth",
  realm: "finops",
  clientId: "finops-web"
});

export class AuthenticationError extends Error {}

let initialization: Promise<boolean> | undefined;
export function initializeAuth() {
  // One initialization, including when React StrictMode mounts twice.
  return initialization ??= keycloak.init({
    onLoad: "check-sso",
    flow: "standard",
    pkceMethod: "S256",
    checkLoginIframe: false,
    redirectUri: window.location.origin + "/"
  });
}

export function login() {
  return keycloak.login({ redirectUri: window.location.origin + "/" });
}

export function register() {
  return keycloak.register({ redirectUri: window.location.origin + "/" });
}

export function logout() {
  return keycloak.logout({ redirectUri: window.location.origin + "/" });
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
