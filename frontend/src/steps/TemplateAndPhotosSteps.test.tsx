import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { TemplateSummary } from "../api/endpoints";
import { initialDraft } from "../domain/report";
import { strings } from "../strings/pt-BR";
import { jsonResponse, mockApi, TEMPLATE_SUMMARY } from "../test/mockApi";
import { renderWithProviders } from "../test/render";
import { PhotosStep } from "./PhotosStep";
import { TemplateStep } from "./TemplateStep";

afterEach(() => vi.unstubAllGlobals());

const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

function fileInput(container: HTMLElement): HTMLInputElement {
  const input = container.querySelector('input[type="file"]');
  if (!(input instanceof HTMLInputElement)) throw new Error("campo de arquivo não encontrado");
  return input;
}

function TemplateHarness({ initial, target }: { initial?: TemplateSummary; target?: string }) {
  const [template, setTemplate] = useState<TemplateSummary | undefined>(initial);
  const draft = { ...initialDraft(), ...(target ? { target_sheet: target } : {}) };
  return (
    <TemplateStep
      workspaceId="ws"
      draft={draft}
      onDraft={() => undefined}
      template={template}
      onTemplate={setTemplate}
    />
  );
}

describe("TemplateStep", () => {
  it("envia o template e mostra a aba, a contagem e os títulos encontrados", async () => {
    const calls = mockApi({
      "PUT /api/workspaces/ws/template": () => jsonResponse(TEMPLATE_SUMMARY),
    });
    const { container } = renderWithProviders(<TemplateHarness />);

    await userEvent.upload(fileInput(container), new File(["x"], "model.xlsx", { type: XLSX }));

    expect(await screen.findByText(strings.template.titlesFound(4))).toBeInTheDocument();
    expect(screen.getByText("Projetos/ARTs")).toBeInTheDocument();
    expect(calls[0]?.search).toBe("?target_sheet=Relat%C3%B3rio%20fotogr%C3%A1fico");
  });

  it("mostra a mensagem em português quando o template é inválido", async () => {
    mockApi({
      "PUT /api/workspaces/ws/template": () =>
        jsonResponse({ detail: ["Não foi possível ler o template Excel: x"], issues: [] }, 422),
    });
    const { container } = renderWithProviders(<TemplateHarness />);

    await userEvent.upload(fileInput(container), new File(["x"], "m.xlsx", { type: XLSX }));

    expect(await screen.findByText(/Não foi possível ler o template Excel/)).toBeInTheDocument();
  });

  it("avisa quando a aba alvo não existe no template", () => {
    renderWithProviders(
      <TemplateHarness
        initial={{ ...TEMPLATE_SUMMARY, sheet_name: "Sheet1", target_found: false }}
        target="Outra"
      />,
    );

    expect(screen.getByText(strings.template.sheetMissing("Outra", "Sheet1"))).toBeInTheDocument();
  });
});

describe("PhotosStep", () => {
  it("envia o ZIP, mostra o resumo e avisa a tela para atualizar as contagens", async () => {
    mockApi({
      "POST /api/workspaces/ws/photos/archive": () =>
        jsonResponse({ sections: { entorno: 5, geral_obra: 2 }, skipped: 3 }),
    });
    const onChanged = vi.fn();
    const { container } = renderWithProviders(
      <PhotosStep workspaceId="ws" counts={{}} onChanged={onChanged} />,
    );

    await userEvent.upload(
      fileInput(container),
      new File(["x"], "fotos.zip", { type: "application/zip" }),
    );

    expect(await screen.findByText(/7 fotos recebidas/)).toBeInTheDocument();
    expect(screen.getByText(/3 arquivos ignorados/)).toBeInTheDocument();
    expect(onChanged).toHaveBeenCalled();
  });

  it("aceita um arquivo RAR", async () => {
    mockApi({
      "POST /api/workspaces/ws/photos/archive": () =>
        jsonResponse({ sections: { entorno: 2 }, skipped: 0 }),
    });
    const { container } = renderWithProviders(
      <PhotosStep workspaceId="ws" counts={{}} onChanged={() => undefined} />,
    );

    await userEvent.upload(fileInput(container), new File(["x"], "fotos.rar"));

    expect(await screen.findByText(/2 fotos recebidas/)).toBeInTheDocument();
  });

  it("envia uma pasta inteira com o caminho relativo de cada imagem", async () => {
    let sent: FormData | undefined;
    mockApi({
      "POST /api/workspaces/ws/photos/folder": (call) => {
        sent = call.body as FormData;
        return jsonResponse({ sections: { entorno: 1, geral_obra: 1 }, skipped: 0 });
      },
    });
    renderWithProviders(<PhotosStep workspaceId="ws" counts={{}} onChanged={() => undefined} />);
    const entorno = new File(["x"], "a.png", { type: "image/png" });
    const geral = new File(["x"], "b.jpg", { type: "image/jpeg" });
    const notes = new File(["x"], "leia.txt", { type: "text/plain" });
    Object.defineProperty(entorno, "webkitRelativePath", { value: "obra/entorno/a.png" });
    Object.defineProperty(geral, "webkitRelativePath", { value: "obra/geral_obra/b.jpg" });
    Object.defineProperty(notes, "webkitRelativePath", { value: "obra/entorno/leia.txt" });

    await userEvent.upload(screen.getByTestId("folder-input"), [entorno, geral, notes], {
      applyAccept: false,
    });

    expect(await screen.findByText(/2 fotos recebidas/)).toBeInTheDocument();
    expect(screen.getByText(/1 arquivo ignorado/)).toBeInTheDocument();
    expect(sent?.getAll("paths")).toEqual(["obra/entorno/a.png", "obra/geral_obra/b.jpg"]);
  });

  it("lista as pastas já recebidas com a quantidade de fotos", () => {
    renderWithProviders(
      <PhotosStep
        workspaceId="ws"
        counts={{ entorno: 5, pavimentos: 1 }}
        onChanged={() => undefined}
      />,
    );

    expect(screen.getByText("entorno")).toBeInTheDocument();
    expect(screen.getByText("5 fotos")).toBeInTheDocument();
    expect(screen.getByText("1 foto")).toBeInTheDocument();
  });

  it("explica quando ainda não há fotos", () => {
    renderWithProviders(<PhotosStep workspaceId="ws" counts={{}} onChanged={() => undefined} />);

    expect(screen.getByText(strings.photos.noFolders)).toBeInTheDocument();
  });
});
