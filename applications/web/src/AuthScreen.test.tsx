import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
vi.mock("./auth", () => ({ login: vi.fn(), register: vi.fn() }));
import AuthScreen from "./AuthScreen";

describe("FinOps welcome screen", () => {
  it("offers real OIDC entry points without a local credential form", () => {
    const markup = renderToStaticMarkup(<AuthScreen message="" />);
    expect(markup).toContain("Вход в кабинет");
    expect(markup).toContain("Регистрация");
    expect(markup).not.toMatch(/<input|<form|admin\/admin/);
    expect(markup).toMatch(/<button[^>]+disabled=""[^>]+aria-describedby="telegram-note"/);
    expect(markup).toContain("Скоро");
  });
});
