import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
vi.mock("./auth", () => ({ login: vi.fn() }));
import AuthScreen from "./AuthScreen";

describe("Central SSO entry", () => {
  it("offers SSO without collecting or embedding credentials", () => {
    const markup = renderToStaticMarkup(<AuthScreen message="" />);
    expect(markup).toContain(">Войти<");
    expect(markup).toContain("Войти через Telegram");
    expect(markup).not.toMatch(/<input|<form|<iframe/);
  });
  it("preserves session failure feedback", () => {
    const markup = renderToStaticMarkup(<AuthScreen message="Сессия истекла" />);
    expect(markup).toContain('role="alert"');
    expect(markup).toContain("Сессия истекла");
  });
});
