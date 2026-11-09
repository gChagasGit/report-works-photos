import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, requestJson } from "./client";

afterEach(() => vi.unstubAllGlobals());

describe("requestJson", () => {
  it("devolve o JSON de respostas bem-sucedidas", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(Response.json({ a: 1 }))),
    );

    expect(await requestJson<{ a: number }>("/x")).toEqual({ a: 1 });
  });

  it("transforma o erro da API em ApiError com as mensagens em português", async () => {
    const body = { detail: ["Área de trabalho não encontrada."], issues: [] };
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(Response.json(body, { status: 404 }))),
    );

    const error = await requestJson("/x").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(404);
    expect((error as ApiError).messages).toEqual(["Área de trabalho não encontrada."]);
  });

  it("usa uma mensagem padrão quando o corpo do erro não é JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response("falha", { status: 500 }))),
    );

    const error = (await requestJson("/x").catch((e: unknown) => e)) as ApiError;

    expect(error.messages).toEqual(["Ocorreu um erro inesperado."]);
  });
});
