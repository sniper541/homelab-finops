import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
vi.mock("./auth", () => ({
  getAccessToken: vi.fn(), AuthenticationError: class AuthenticationError extends Error {}
}));
import { AuthenticationError, getAccessToken } from "./auth";
import { getDashboardData } from "./api";

describe("authenticated dashboard requests", () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    vi.resetAllMocks();
    vi.stubGlobal("fetch", fetchMock);
    vi.mocked(getAccessToken).mockResolvedValue("test-access-token");
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => [] });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("sends Bearer on every existing endpoint while preserving user_id=1", async () => {
    const result = await getDashboardData();
    expect(result.isFallback).toBe(false);
    expect(getAccessToken).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    for (const [url, options] of fetchMock.mock.calls) {
      expect(url).toContain("user_id=1");
      expect(options.headers).toEqual({ Accept: "application/json", Authorization: "Bearer test-access-token" });
    }
  });

  it("does not send API requests or show fallback when the session is invalid", async () => {
    vi.mocked(getAccessToken).mockRejectedValue(new AuthenticationError("expired"));
    await expect(getDashboardData()).rejects.toBeInstanceOf(AuthenticationError);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each([401, 403])("does not hide HTTP %s behind mock data", async (status) => {
    fetchMock.mockResolvedValue({ ok: false, status });
    await expect(getDashboardData()).rejects.toBeInstanceOf(AuthenticationError);
  });

  it("preserves the existing fallback on API outage", async () => {
    const warning = vi.spyOn(console, "warn").mockImplementation(() => {});
    fetchMock.mockRejectedValue(new Error("offline"));
    expect((await getDashboardData()).isFallback).toBe(true);
    warning.mockRestore();
  });
});
