import { Badge, Container, Stack, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { getHealth } from "./api/client";
import { strings } from "./strings/pt-BR";

export function App() {
  const health = useQuery({ queryKey: ["health"], queryFn: getHealth, retry: false });

  const status = health.isPending
    ? { color: "gray", label: strings.server.checking }
    : health.isError
      ? { color: "red", label: strings.server.offline }
      : { color: "green", label: strings.server.online };

  return (
    <Container size="md" py="xl">
      <Stack gap="sm">
        <Title order={1}>{strings.app.title}</Title>
        <Text c="dimmed">{strings.app.subtitle}</Text>
        <Badge color={status.color} variant="light" w="fit-content">
          {status.label}
        </Badge>
      </Stack>
    </Container>
  );
}
