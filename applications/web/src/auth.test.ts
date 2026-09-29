import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

const adapter = vi.hoisted(() => ({
  init: vi.fn(), login: vi.fn(), register: vi.fn(), logout: vi.fn(), updateToken: vi.fn(),
  clearToken: vi.fn(), authenticated: true, token: "access-token"
}));
vi.mock("keycloak-js", () => ({ default: vi.fn(function () { return adapter; }) }));

describe("Keycloak session", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.stubGlobal("window", { location: { origin: "https://app.sniper541.com", search: "", hash: "" }, sessionStorage: { getItem: vi.fn().mockReturnValue(null), setItem: vi.fn(), removeItem: vi.fn() } });
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
      flow: "standard", pkceMethod: "S256"
    }));
    expect(adapter.init.mock.calls[0][0]).not.toHaveProperty("onLoad");
    expect(adapter.init.mock.calls[0][0]).not.toHaveProperty("silentCheckSsoRedirectUri");
  });

  it("does not restart authentication on an OAuth error callback", async () => {
    window.location.hash = "#error=access_denied&state=opaque";
    const { initializeAuth } = await import("./auth");
    await initializeAuth();
    expect(adapter.init.mock.calls[0][0]).not.toHaveProperty("onLoad");
  });

  it("keeps a new visitor on the app without invoking login", async () => {
    adapter.authenticated = false;
    adapter.init.mockResolvedValue(false);
    const { initializeAuth } = await import("./auth");
    expect(await initializeAuth()).toBe(false);
    expect(adapter.login).not.toHaveBeenCalled();
    expect(adapter.init.mock.calls[0][0]).not.toHaveProperty("onLoad");
  });

  it("processes authorization callbacks without initiating a second flow", async () => {
    window.location.search = "?code=opaque&state=opaque";
    const { initializeAuth } = await import("./auth");
    await initializeAuth();
    expect(adapter.init.mock.calls[0][0]).not.toHaveProperty("onLoad");
  });

  it("keeps an explicit signed-out tab on its landing page", async () => {
    vi.mocked(window.sessionStorage.getItem).mockReturnValue("true");
    const { initializeAuth, login } = await import("./auth");
    await initializeAuth();
    expect(adapter.init.mock.calls[0][0]).not.toHaveProperty("onLoad");
    await login();
    expect(window.sessionStorage.removeItem).toHaveBeenCalledWith("finops.signed-out");
  });

  it("marks logout before navigation and clears the marker on failure", async () => {
    adapter.logout.mockRejectedValueOnce(new Error("offline"));
    const { logout } = await import("./auth");
    await expect(logout()).rejects.toThrow("offline");
    expect(window.sessionStorage.setItem).toHaveBeenCalledWith("finops.signed-out", "true");
    expect(window.sessionStorage.removeItem).toHaveBeenCalledWith("finops.signed-out");
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

  it("delegates registration to the standard adapter without collecting credentials", async () => {
    const { register } = await import("./auth");
    await register();
    expect(adapter.register).toHaveBeenCalledWith({ redirectUri: "https://app.sniper541.com/" });
  });
});
