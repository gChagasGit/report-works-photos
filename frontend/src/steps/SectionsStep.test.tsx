import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { initialDraft, newSection, type ReportDraft } from "../domain/report";
import { strings } from "../strings/pt-BR";
import { TEMPLATE_SUMMARY } from "../test/mockApi";
import { renderWithProviders } from "../test/render";
import { SectionsStep } from "./SectionsStep";

function Harness({ start }: { start: ReportDraft }) {
  const [draft, setDraft] = useState(start);
  return (
    <SectionsStep
      workspaceId="ws"
      draft={draft}
      onDraft={setDraft}
      template={TEMPLATE_SUMMARY}
      counts={{ entorno: 5 }}
      onPhotosChanged={() => undefined}
    />
  );
}

const draftWith = (...sections: ReturnType<typeof newSection>[]): ReportDraft => ({
  ...initialDraft(),
  sections,
});

describe("SectionsStep", () => {
  it("mostra na hora que o título não existe no template", () => {
    renderWithProviders(
      <Harness start={draftWith(newSection({ id: "x", label: "Título inexistente" }))} />,
    );

    expect(screen.getByText(strings.sections.titleNotFound)).toBeInTheDocument();
  });

  it("não reclama de título que existe, mesmo com caixa e espaços diferentes", () => {
    renderWithProviders(
      <Harness start={draftWith(newSection({ id: "e", label: "  ENTORNO   da obra " }))} />,
    );

    expect(screen.queryByText(strings.sections.titleNotFound)).not.toBeInTheDocument();
  });

  it("avisa sobre título repetido no template", () => {
    renderWithProviders(
      <Harness start={draftWith(newSection({ id: "g", label: "Geral da obra" }))} />,
    );

    expect(screen.getByText(strings.sections.titleDuplicated(2))).toBeInTheDocument();
  });

  it("corrige o aviso ao editar o título", async () => {
    renderWithProviders(<Harness start={draftWith(newSection({ id: "x", label: "Errado" }))} />);
    const input = screen.getByRole("textbox", { name: strings.sections.label });

    await userEvent.clear(input);
    await userEvent.type(input, "Projetos/ARTs");

    expect(screen.queryByText(strings.sections.titleNotFound)).not.toBeInTheDocument();
  });

  it("valida o id da pasta e a contagem de fotos de cada seção", () => {
    renderWithProviders(
      <Harness
        start={draftWith(
          newSection({ id: "entorno", label: "Entorno da obra" }),
          newSection({ id: "Pasta Ruim", label: "Projetos/ARTs" }),
          newSection({ id: "vazia", label: "Projetos/ARTs" }),
        )}
      />,
    );

    expect(screen.getByText(strings.sections.invalidId)).toBeInTheDocument();
    expect(screen.getByText(strings.photos.photoCount(5))).toBeInTheDocument();
    expect(screen.getByText(strings.sections.folderEmpty)).toBeInTheDocument();
  });

  it("mostra o campo de fotos por grupo só em seções agrupadas e valida o texto", async () => {
    renderWithProviders(
      <Harness start={draftWith(newSection({ id: "p", label: "Projetos/ARTs" }))} />,
    );
    expect(screen.queryByLabelText(strings.sections.groupSizes)).not.toBeInTheDocument();

    await userEvent.click(screen.getByLabelText(strings.sections.grouped));
    expect(screen.getByText(strings.sections.invalidGroups)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(strings.sections.groupSizes), "4, 2");

    expect(screen.queryByText(strings.sections.invalidGroups)).not.toBeInTheDocument();
  });

  it("adiciona, remove e restaura as seções do exemplo", async () => {
    renderWithProviders(<Harness start={draftWith()} />);
    expect(screen.getByText(strings.sections.empty)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: strings.sections.add }));
    expect(screen.getAllByLabelText(strings.sections.folder)).toHaveLength(1);
    await userEvent.click(screen.getByRole("button", { name: strings.sections.remove }));
    expect(screen.getByText(strings.sections.empty)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: strings.sections.useExample }));
    expect(screen.getAllByLabelText(strings.sections.folder)).toHaveLength(6);
    const first = screen.getByTestId("section-entorno");
    expect(within(first).getByDisplayValue("Entorno da obra")).toBeInTheDocument();
  });
});
