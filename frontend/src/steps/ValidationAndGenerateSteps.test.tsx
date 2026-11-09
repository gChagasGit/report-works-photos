import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { UseQueryResult } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { IssueOut, JobOut, ValidationOut } from "../api/endpoints";
import { initialDraft, toConfig } from "../domain/report";
import { strings } from "../strings/pt-BR";
import { jsonResponse, mockApi } from "../test/mockApi";
import { renderWithProviders } from "../test/render";
import { GenerateStep } from "./GenerateStep";
import { ValidationStep } from "./ValidationStep";

afterEach(() => vi.unstubAllGlobals());

const issue = (patch: Partial<IssueOut>): IssueOut => ({
  code: "x",
  severity: "error",
  message: "mensagem",
  section_id: null,
  ...patch,
});

function query(data: ValidationOut | undefined, extra: object = {}): UseQueryResult<ValidationOut> {
  return { data, isError: false, isFetching: false, ...extra } as UseQueryResult<ValidationOut>;
}

describe("ValidationStep", () => {
  it("pede o template quando ainda não foi enviado", () => {
    renderWithProviders(<ValidationStep validation={query(undefined)} hasTemplate={false} />);

    expect(screen.getByText(strings.validation.needTemplate)).toBeInTheDocument();
  });

  it("mostra que está conferindo enquanto não há resultado", () => {
    renderWithProviders(<ValidationStep validation={query(undefined)} hasTemplate />);

    expect(screen.getByText(strings.validation.checking)).toBeInTheDocument();
  });

  it("confirma quando nada impede a geração", () => {
    renderWithProviders(
      <ValidationStep validation={query({ issues: [], blocking: false })} hasTemplate />,
    );

    expect(screen.getByText(strings.validation.allGood)).toBeInTheDocument();
  });

  it("separa o que impede a geração do que é só aviso", () => {
    const issues = [
      issue({
        code: "label_not_found",
        message: 'O título "X" não foi encontrado na coluna B da aba "Y".',
      }),
      issue({
        code: "fewer_photos",
        severity: "warning",
        message: "Prevê 5 fotos, mas a pasta tem 3.",
      }),
    ];

    renderWithProviders(
      <ValidationStep validation={query({ issues, blocking: true })} hasTemplate />,
    );

    expect(screen.getByText(strings.validation.blocking)).toBeInTheDocument();
    expect(screen.getByText(/não foi encontrado na coluna B/)).toBeInTheDocument();
    expect(screen.getByText(strings.validation.errorTitle)).toBeInTheDocument();
    expect(screen.getByText(strings.validation.warningTitle)).toBeInTheDocument();
  });

  it("mostra a mensagem da API quando a conferência falha", () => {
    const failed = query(undefined, {
      isError: true,
      error: new Error("falha"),
    });

    renderWithProviders(<ValidationStep validation={failed} hasTemplate />);

    expect(screen.getByRole("alert")).toHaveTextContent(strings.errors.unexpected);
  });
});

const job = (patch: Partial<JobOut>): JobOut => ({
  id: "j1",
  workspace_id: "ws",
  state: "running",
  done: 0,
  total: 5,
  percent: 0,
  message: "",
  failures: [],
  issues: [],
  errors: [],
  download_url: null,
  ...patch,
});

describe("GenerateStep", () => {
  const config = toConfig(initialDraft());

  it("não deixa gerar enquanto há problemas bloqueantes", () => {
    renderWithProviders(<GenerateStep workspaceId="ws" config={config} blocked />);

    expect(screen.getByText(strings.generate.blocked)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: strings.generate.start })).toBeDisabled();
  });

  it("gera, acompanha o andamento e oferece o download", async () => {
    let polls = 0;
    const calls = mockApi({
      "POST /api/jobs": () => jsonResponse(job({}), 202),
      "GET /api/jobs/j1": () => {
        polls += 1;
        return jsonResponse(
          polls < 2
            ? job({ done: 2, percent: 0.4, message: "Entorno da obra: foto 2 de 5" })
            : job({
                state: "done",
                done: 5,
                percent: 1,
                message: "Relatório concluído.",
                download_url: "/api/jobs/j1/download",
                failures: ["Não foi possível inserir a foto 3.png em D13: x"],
              }),
        );
      },
    });
    renderWithProviders(<GenerateStep workspaceId="ws" config={config} blocked={false} />);

    await userEvent.click(screen.getByRole("button", { name: strings.generate.start }));

    const link = await screen.findByRole(
      "link",
      { name: strings.generate.download },
      { timeout: 4000 },
    );
    expect(link).toHaveAttribute("href", "/api/jobs/j1/download");
    expect(screen.getByText(strings.generate.photoFailures(1))).toBeInTheDocument();
    expect(screen.getByText(/foto 3.png em D13/)).toBeInTheDocument();
    expect(JSON.parse(String(calls[0]?.body))).toMatchObject({ workspace_id: "ws" });
  });

  it("mostra os motivos quando a geração falha", async () => {
    mockApi({
      "POST /api/jobs": () => jsonResponse(job({}), 202),
      "GET /api/jobs/j1": () =>
        jsonResponse(
          job({
            state: "failed",
            errors: ["Há problemas que impedem a geração do relatório."],
            issues: [issue({ code: "folder_missing", message: "A pasta não existe" })],
          }),
        ),
    });
    renderWithProviders(<GenerateStep workspaceId="ws" config={config} blocked={false} />);

    await userEvent.click(screen.getByRole("button", { name: strings.generate.start }));

    expect(await screen.findByText(strings.generate.failed)).toBeInTheDocument();
    expect(
      screen.getByText("Há problemas que impedem a geração do relatório."),
    ).toBeInTheDocument();
    expect(screen.getByText("A pasta não existe")).toBeInTheDocument();
  });
});
