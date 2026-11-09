import type { components } from "./schema";
import { strings } from "../strings/pt-BR";

export type Health = { status: string };
export type ErrorBody = components["schemas"]["ErrorOut"];

/** Erro da API com as mensagens em português já prontas para exibir. */
export class ApiError extends Error {
  readonly status: number;
  readonly messages: string[];
  readonly issues: ErrorBody["issues"];

  constructor(status: number, body: Partial<ErrorBody>) {
    const messages =
      body.detail && body.detail.length > 0 ? body.detail : [strings.errors.unexpected];
    super(messages.join("; "));
    this.status = status;
    this.messages = messages;
    this.issues = body.issues ?? [];
  }
}

/** Lê a resposta como JSON; respostas de erro viram `ApiError`. */
export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as Partial<ErrorBody>;
    throw new ApiError(response.status, body);
  }
  return (await response.json()) as T;
}

export function getHealth(): Promise<Health> {
  return requestJson<Health>("/api/health");
}
