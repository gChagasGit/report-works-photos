import { Alert, List } from "@mantine/core";
import { ApiError } from "../api/client";
import { strings } from "../strings/pt-BR";

/** Mostra as mensagens em português de um erro da API (ou a mensagem genérica). */
export function ErrorAlert({ error }: { error: unknown }) {
  if (!error) return null;
  const messages = error instanceof ApiError ? error.messages : [strings.errors.unexpected];
  return (
    <Alert color="red" role="alert">
      <List size="sm" listStyleType="none">
        {messages.map((message) => (
          <List.Item key={message}>{message}</List.Item>
        ))}
      </List>
    </Alert>
  );
}
