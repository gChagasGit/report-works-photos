import { vi } from "vitest";

export type Call = {
  method: string;
  path: string;
  search: string;
  body: BodyInit | null | undefined;
};
type Handler = (call: Call) => Response | Promise<Response>;

/**
 * Substitui o `fetch` por rotas simuladas no formato "MÉTODO /caminho".
 * Rota desconhecida responde 500, o que faz o teste falhar de forma visível.
 */
export function mockApi(routes: Record<string, Handler>): Call[] {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(typeof input === "string" ? input : input.toString(), "http://localhost");
      const call: Call = {
        method: init?.method ?? "GET",
        path: url.pathname,
        search: url.search,
        body: init?.body,
      };
      calls.push(call);
      const handler = routes[`${call.method} ${call.path}`];
      return handler
        ? handler(call)
        : Response.json(
            { detail: [`sem rota simulada: ${call.method} ${call.path}`] },
            { status: 500 },
          );
    }),
  );
  return calls;
}

export const TEMPLATE_SUMMARY = {
  sheets: ["Sheet1", "Relatório fotográfico"],
  sheet_name: "Relatório fotográfico",
  target_found: true,
  max_row: 680,
  titles: [
    { row: 11, text: "Entorno da obra" },
    { row: 36, text: "Geral da obra" },
    { row: 38, text: "Geral da obra" },
    { row: 50, text: "Projetos/ARTs" },
  ],
};

export function jsonResponse(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}
