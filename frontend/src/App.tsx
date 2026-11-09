import { Alert, Button, Container, Group, Stack, Stepper, Text, Title } from "@mantine/core";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { getPhotoCounts, getTemplate, type TemplateSummary } from "./api/endpoints";
import { draftHasErrors, initialDraft, toConfig, type ReportDraft } from "./domain/report";
import { useValidation } from "./hooks/useValidation";
import { useWorkspace } from "./hooks/useWorkspace";
import { GenerateStep } from "./steps/GenerateStep";
import { PhotosStep } from "./steps/PhotosStep";
import { SectionsStep } from "./steps/SectionsStep";
import { TemplateStep } from "./steps/TemplateStep";
import { ValidationStep } from "./steps/ValidationStep";
import { strings } from "./strings/pt-BR";

const LAST_STEP = 4;

export function App() {
  const queryClient = useQueryClient();
  const { workspaceId, error: workspaceError } = useWorkspace();
  const [active, setActive] = useState(0);
  const [draft, setDraft] = useState<ReportDraft>(initialDraft);
  const [template, setTemplate] = useState<TemplateSummary>();
  const [refreshKey, setRefreshKey] = useState(0);

  // Retoma o template enviado em uma sessão anterior (a área de trabalho é reaproveitada).
  useEffect(() => {
    if (!workspaceId) return;
    getTemplate(workspaceId, null)
      .then(setTemplate)
      .catch(() => undefined);
  }, [workspaceId]);

  const photos = useQuery({
    queryKey: ["photos", workspaceId, refreshKey],
    queryFn: () => getPhotoCounts(workspaceId ?? ""),
    enabled: workspaceId !== null,
  });
  const counts = photos.data?.sections ?? {};
  const validation = useValidation(workspaceId, draft, template !== undefined, refreshKey);
  const config = useMemo(() => toConfig(draft), [draft]);

  const onPhotosChanged = () => {
    setRefreshKey((key) => key + 1);
    void queryClient.invalidateQueries({ queryKey: ["photos"] });
  };

  const blocking = validation.data?.blocking ?? true;
  const canAdvance = [
    template !== undefined,
    true,
    !draftHasErrors(draft),
    validation.data !== undefined && !validation.data.blocking && !validation.isFetching,
    false,
  ][active];

  return (
    <Container fluid miw={960} px="lg" py="xl">
      <Stack gap="lg">
        <div>
          <Title order={1}>{strings.app.title}</Title>
          <Text c="dimmed">{strings.app.subtitle}</Text>
        </div>
        {workspaceError && <Alert color="red">{workspaceError}</Alert>}
        <Stepper active={active} onStepClick={setActive} allowNextStepsSelect={false}>
          {(
            [
              ["template", strings.steps.template],
              ["photos", strings.steps.photos],
              ["sections", strings.steps.sections],
              ["validation", strings.steps.validation],
              ["generate", strings.steps.generate],
            ] as const
          ).map(([key, step]) => (
            <Stepper.Step key={key} label={step.label} description={step.description} />
          ))}
        </Stepper>

        {active === 0 && (
          <TemplateStep
            workspaceId={workspaceId}
            draft={draft}
            onDraft={setDraft}
            template={template}
            onTemplate={setTemplate}
          />
        )}
        {active === 1 && (
          <PhotosStep workspaceId={workspaceId} counts={counts} onChanged={onPhotosChanged} />
        )}
        {active === 2 && (
          <SectionsStep
            workspaceId={workspaceId}
            draft={draft}
            onDraft={setDraft}
            template={template}
            counts={counts}
            onPhotosChanged={onPhotosChanged}
          />
        )}
        {active === 3 && <ValidationStep validation={validation} hasTemplate={!!template} />}
        {active === LAST_STEP && (
          <GenerateStep workspaceId={workspaceId} config={config} blocked={blocking} />
        )}

        <Group justify="space-between">
          <Button variant="default" onClick={() => setActive(active - 1)} disabled={active === 0}>
            {strings.nav.back}
          </Button>
          {active < LAST_STEP && (
            <Button onClick={() => setActive(active + 1)} disabled={!canAdvance}>
              {strings.nav.next}
            </Button>
          )}
        </Group>
      </Stack>
    </Container>
  );
}
