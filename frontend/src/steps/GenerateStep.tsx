import { Alert, Button, List, Progress, Stack, Text } from "@mantine/core";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { createJob, getJob, type ReportConfig } from "../api/endpoints";
import { ErrorAlert } from "../components/ErrorAlert";
import { strings } from "../strings/pt-BR";

const POLL_MS = 500;

type Props = {
  workspaceId: string | null;
  config: ReportConfig;
  blocked: boolean;
};

export function GenerateStep({ workspaceId, config, blocked }: Props) {
  const [jobId, setJobId] = useState<string | null>(null);
  const start = useMutation({
    mutationFn: () => createJob(workspaceId ?? "", config),
    onSuccess: (job) => setJobId(job.id),
  });
  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId ?? ""),
    enabled: jobId !== null,
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      return state === "done" || state === "failed" ? false : POLL_MS;
    },
  });
  const data = job.data;
  const running =
    start.isPending || (data !== undefined && !["done", "failed"].includes(data.state));

  return (
    <Stack>
      {blocked && <Alert color="red">{strings.generate.blocked}</Alert>}
      <Button
        onClick={() => {
          setJobId(null);
          start.mutate();
        }}
        loading={running}
        disabled={blocked || workspaceId === null}
      >
        {data ? strings.generate.restart : strings.generate.start}
      </Button>
      <ErrorAlert error={start.error ?? job.error} />
      {data && data.state !== "failed" && (
        <Stack gap="xs">
          <Progress value={Math.round(data.percent * 100)} animated={running} />
          <Text size="sm">
            {data.state === "done" ? strings.generate.done : strings.generate.running}{" "}
            {data.message}
          </Text>
        </Stack>
      )}
      {data?.state === "done" && data.download_url && (
        <Button component="a" href={data.download_url} color="green">
          {strings.generate.download}
        </Button>
      )}
      {data && data.failures.length > 0 && (
        <Alert color="yellow" title={strings.generate.photoFailures(data.failures.length)}>
          <List size="sm">
            {data.failures.map((failure) => (
              <List.Item key={failure}>{failure}</List.Item>
            ))}
          </List>
        </Alert>
      )}
      {data?.state === "failed" && (
        <Alert color="red" title={strings.generate.failed} role="alert">
          <List size="sm" listStyleType="none">
            {data.errors.map((message) => (
              <List.Item key={message}>{message}</List.Item>
            ))}
            {data.issues.map((issue) => (
              <List.Item key={`${issue.code}-${issue.message}`}>{issue.message}</List.Item>
            ))}
          </List>
        </Alert>
      )}
    </Stack>
  );
}
