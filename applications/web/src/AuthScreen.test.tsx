import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
vi.mock("./auth", () => ({ login: vi.fn(), createEmbeddedLoginUrl: vi.fn(), embeddedCallback: vi.fn() }));
import AuthScreen from "./AuthScreen";

describe("Embedded sign-in shell", () => {
  it("announces form loading without collecting credentials in React", () => {
    const markup = renderToStaticMarkup(<AuthScreen message="" />);
    expect(markup).toContain("Загружаем защищённую форму");
    expect(markup).not.toMatch(/<input|<form/);
  });
  it("preserves session failure feedback", () => {
    const markup = renderToStaticMarkup(<AuthScreen message="Сессия истекла" />);
    expect(markup).toContain('role="alert"');
    expect(markup).toContain("Сессия истекла");
  });
});
