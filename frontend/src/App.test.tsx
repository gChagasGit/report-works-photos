import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { strings } from "./strings/pt-BR";
import { renderWithProviders } from "./test/render";

afterEach(() => vi.unstubAllGlobals());

function stubFetch(response: Response | Error) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => (response instanceof Error ? Promise.reject(response) : Promise.resolve(response))),
  );
}

describe("App", () => {
  it("mostra o título e que o servidor está conectado", async () => {
    stubFetch(Response.json({ status: "ok" }));

    renderWithProviders(<App />);

    expect(screen.getByRole("heading", { name: strings.app.title })).toBeInTheDocument();
    expect(await screen.findByText(strings.server.online)).toBeInTheDocument();
  });

  it("avisa quando o servidor não responde", async () => {
    stubFetch(new Error("rede"));

    renderWithProviders(<App />);

    expect(await screen.findByText(strings.server.offline)).toBeInTheDocument();
  });
});
