import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { strings } from "./strings/pt-BR";
import { jsonResponse, mockApi, TEMPLATE_SUMMARY } from "./test/mockApi";
import { renderWithProviders } from "./test/render";

const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

beforeEach(() => window.localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

function baseRoutes(validation: object) {
  return {
    "POST /api/workspaces": () => jsonResponse({ id: "ws" }, 201),
    "GET /api/workspaces/ws/photos": () => jsonResponse({ sections: { entorno: 5 } }),
    "GET /api/workspaces/ws/template": () =>
      jsonResponse({ detail: ["Envie o template Excel antes de continuar."], issues: [] }, 422),
    "PUT /api/workspaces/ws/template": () => jsonResponse(TEMPLATE_SUMMARY),
    "POST /api/workspaces/ws/validate": () => jsonResponse(validation),
  };
}

async function uploadTemplate(container: HTMLElement) {
  const input = container.querySelector('input[type="file"]');
  if (!(input instanceof HTMLInputElement)) throw new Error("campo de arquivo não encontrado");
  await userEvent.upload(input, new File(["x"], "model.xlsx", { type: XLSX }));
}

const next = () => screen.getByRole("button", { name: strings.nav.next });

describe("App", () => {
  it("começa pelo template e só avança depois de enviá-lo", async () => {
    mockApi(baseRoutes({ issues: [], blocking: false }));

    const { container } = renderWithProviders(<App />);

    expect(screen.getByRole("heading", { name: strings.app.title })).toBeInTheDocument();
    expect(next()).toBeDisabled();
    await uploadTemplate(container);
    await waitFor(() => expect(next()).toBeEnabled());
  });

  it("bloqueia o avanço quando um título de seção não existe no template", async () => {
    const issue = {
      code: "label_not_found",
      severity: "error",
      message:
        'O título "Pavimentos (INTERNAS DA TORRE)" não foi encontrado na coluna B da aba "X".',
      section_id: "pavimentos",
    };
    mockApi(baseRoutes({ issues: [issue], blocking: true }));
    const { container } = renderWithProviders(<App />);

    await uploadTemplate(container);
    await waitFor(() => expect(next()).toBeEnabled());
    await userEvent.click(next()); // fotos
    await userEvent.click(next()); // seções
    await userEvent.click(next()); // conferência

    expect(await screen.findByText(strings.validation.blocking)).toBeInTheDocument();
    expect(
      screen.getByText(/Pavimentos \(INTERNAS DA TORRE\)" não foi encontrado/),
    ).toBeInTheDocument();
    expect(next()).toBeDisabled();
  });

  it("libera a geração quando a conferência não encontra problemas", async () => {
    mockApi(baseRoutes({ issues: [], blocking: false }));
    const { container } = renderWithProviders(<App />);

    await uploadTemplate(container);
    await waitFor(() => expect(next()).toBeEnabled());
    await userEvent.click(next());
    await userEvent.click(next());
    await userEvent.click(next());

    expect(await screen.findByText(strings.validation.allGood)).toBeInTheDocument();
    await waitFor(() => expect(next()).toBeEnabled());
    await userEvent.click(next());
    expect(screen.getByRole("button", { name: strings.generate.start })).toBeEnabled();
  });

  it("reaproveita a área de trabalho e o template da sessão anterior", async () => {
    window.localStorage.setItem("report-works.workspace", "ws");
    const routes = baseRoutes({ issues: [], blocking: false });
    const calls = mockApi({
      ...routes,
      "GET /api/workspaces/ws/template": () => jsonResponse(TEMPLATE_SUMMARY),
    });

    renderWithProviders(<App />);

    await waitFor(() => expect(next()).toBeEnabled());
    expect(calls.some((call) => call.method === "POST" && call.path === "/api/workspaces")).toBe(
      false,
    );
  });

  it("avisa quando o servidor não responde", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new Error("rede"))),
    );

    renderWithProviders(<App />);

    expect(await screen.findByText(strings.server.offline)).toBeInTheDocument();
  });
});
