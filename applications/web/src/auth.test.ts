import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

const adapter = vi.hoisted(() => ({
  init: vi.fn(), login: vi.fn(), logout: vi.fn(), updateToken: vi.fn(),
  clearToken: vi.fn(), authenticated: true, token: "access-token"
}));
vi.mock("keycloak-js", () => ({ default: vi.fn(function () { return adapter; }) }));

describe("Keycloak session", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.stubGlobal("window", { location: { origin: "https://app.sniper541.com" } });
    adapter.authenticated = true;
    adapter.token = "access-token";
    adapter.init.mockResolvedValue(true);
    adapter.updateToken.mockResolvedValue(false);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("initializes only once with standard flow and PKCE S256", async () => {
    const { initializeAuth } = await import("./auth");
    await Promise.all([initializeAuth(), initializeAuth()]);
    expect(adapter.init).toHaveBeenCalledTimes(1);
    expect(adapter.init).toHaveBeenCalledWith(expect.objectContaining({
      flow: "standard", pkceMethod: "S256", onLoad: "check-sso"
    }));
  });

  it("uses the refreshed access token", async () => {
    adapter.updateToken.mockImplementationOnce(async () => { adapter.token = "fresh-token"; return true; });
    const { getAccessToken } = await import("./auth");
    await expect(getAccessToken()).resolves.toBe("fresh-token");
    expect(adapter.updateToken).toHaveBeenCalledWith(30);
  });

  it("rejects expired sessions and clears tokens when refresh fails", async () => {
    adapter.updateToken.mockRejectedValueOnce(new Error("expired"));
    const { getAccessToken, AuthenticationError } = await import("./auth");
    await expect(getAccessToken()).rejects.toBeInstanceOf(AuthenticationError);
    expect(adapter.clearToken).toHaveBeenCalledOnce();
  });

  it("rejects unauthenticated requests", async () => {
    adapter.authenticated = false;
    const { getAccessToken, AuthenticationError } = await import("./auth");
    await expect(getAccessToken()).rejects.toBeInstanceOf(AuthenticationError);
    expect(adapter.updateToken).not.toHaveBeenCalled();
  });

  it("delegates login and logout to Keycloak with an allowed return URL", async () => {
    const { login, logout } = await import("./auth");
    await login();
    await logout();
    const options = { redirectUri: "https://app.sniper541.com/" };
    expect(adapter.login).toHaveBeenCalledWith(options);
    expect(adapter.logout).toHaveBeenCalledWith(options);
  });
});
