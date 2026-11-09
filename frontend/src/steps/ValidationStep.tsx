import { Alert, Loader, Stack, Text } from "@mantine/core";
import type { UseQueryResult } from "@tanstack/react-query";
import type { ValidationOut } from "../api/endpoints";
import { ErrorAlert } from "../components/ErrorAlert";
import { strings } from "../strings/pt-BR";

type Props = {
  validation: UseQueryResult<ValidationOut>;
  hasTemplate: boolean;
};

export function ValidationStep({ validation, hasTemplate }: Props) {
  if (!hasTemplate) return <Alert color="yellow">{strings.validation.needTemplate}</Alert>;
  if (validation.isError) return <ErrorAlert error={validation.error} />;
  if (!validation.data) {
    return (
      <Stack align="center" gap="xs">
        <Loader size="sm" />
        <Text size="sm">{strings.validation.checking}</Text>
      </Stack>
    );
  }
  const { issues, blocking } = validation.data;
  return (
    <Stack>
      {validation.isFetching && (
        <Text size="sm" c="dimmed">
          {strings.validation.checking}
        </Text>
      )}
      {issues.length === 0 ? (
        <Alert color="green">{strings.validation.allGood}</Alert>
      ) : (
        <>
          {blocking && (
            <Alert color="red" role="alert">
              {strings.validation.blocking}
            </Alert>
          )}
          {issues.map((issue) => (
            <Alert
              key={`${issue.code}-${issue.section_id ?? ""}-${issue.message}`}
              color={issue.severity === "error" ? "red" : "yellow"}
              title={
                issue.severity === "error"
                  ? strings.validation.errorTitle
                  : strings.validation.warningTitle
              }
            >
              {issue.message}
            </Alert>
          ))}
        </>
      )}
    </Stack>
  );
}
