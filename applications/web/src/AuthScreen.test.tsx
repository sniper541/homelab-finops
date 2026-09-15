import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
const state = vi.hoisted(() => ({ signedOut: true }));
vi.mock("./auth", () => ({ login: vi.fn(), isSignedOut: () => state.signedOut }));
import AuthScreen from "./AuthScreen";

describe("Session recovery screen", () => {
  it("shows an explicit logout landing without a credential form", () => {
    const markup = renderToStaticMarkup(<AuthScreen message="" />);
    expect(markup).toContain("Вы вышли из аккаунта");
    expect(markup).toContain("Войти снова");
    expect(markup).not.toMatch(/<input|<form|Войти в FinOps|на следующей странице/);
  });
  it("shows an authentication error without automatic navigation", () => {
    state.signedOut = false;
    const markup = renderToStaticMarkup(<AuthScreen message="Сессия истекла" />);
    expect(markup).toContain("Вход не завершён");
    expect(markup).toContain("Сессия истекла");
  });
});
