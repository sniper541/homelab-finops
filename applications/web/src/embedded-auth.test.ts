import { afterEach, expect, it, vi } from "vitest";
import { embeddedCallback } from "./auth";
afterEach(() => vi.unstubAllGlobals());
it("accepts only the current frame, app origin and matching OAuth state", () => {
  const origin = "https://app.sniper541.com";
  vi.stubGlobal("window", { location: { origin } });
  const source = {} as Window;
  const event = { origin, source, data: { type: "finops-auth-callback", url: origin + "/#state=expected&code=opaque" } } as MessageEvent;
  expect(embeddedCallback(event, source, "expected")).toBe(event.data.url);
  expect(embeddedCallback(event, {} as Window, "expected")).toBeUndefined();
  expect(embeddedCallback(event, source, "wrong")).toBeUndefined();
  expect(embeddedCallback({ ...event, origin: "https://evil.invalid" } as MessageEvent, source, "expected")).toBeUndefined();
  for (const url of ["https://evil.invalid/#state=expected&code=x", origin + "/other#state=expected&code=x", origin + "/#state=expected&access_token=x", "invalid"]) {
    expect(embeddedCallback({ ...event, data: { ...event.data, url } } as MessageEvent, source, "expected")).toBeUndefined();
  }
});
