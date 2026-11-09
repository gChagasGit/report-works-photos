import { Alert, Badge, Group, Select, Stack, Text } from "@mantine/core";
import { Dropzone } from "@mantine/dropzone";
import { useMutation } from "@tanstack/react-query";
import { getTemplate, uploadTemplate, type TemplateSummary } from "../api/endpoints";
import { ErrorAlert } from "../components/ErrorAlert";
import type { ReportDraft } from "../domain/report";
import { strings } from "../strings/pt-BR";

const XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
const PREVIEW_TITLES = 12;

type Props = {
  workspaceId: string | null;
  draft: ReportDraft;
  onDraft: (draft: ReportDraft) => void;
  template: TemplateSummary | undefined;
  onTemplate: (template: TemplateSummary) => void;
};

export function TemplateStep({ workspaceId, draft, onDraft, template, onTemplate }: Props) {
  const upload = useMutation({
    mutationFn: (file: File) => uploadTemplate(workspaceId ?? "", file, draft.target_sheet),
    onSuccess: onTemplate,
  });
  const resummarize = useMutation({
    mutationFn: (sheet: string) => getTemplate(workspaceId ?? "", sheet),
    onSuccess: onTemplate,
  });

  return (
    <Stack>
      <Dropzone
        onDrop={(files) => files[0] && upload.mutate(files[0])}
        accept={{ [XLSX_MIME]: [".xlsx"] }}
        multiple={false}
        loading={upload.isPending}
        disabled={workspaceId === null}
      >
        <Text ta="center">
          {upload.isPending ? strings.template.uploading : strings.template.drop}
        </Text>
        <Text ta="center" size="sm" c="dimmed">
          {strings.template.hint}
        </Text>
      </Dropzone>
      <ErrorAlert error={upload.error ?? resummarize.error} />
      {template && (
        <Stack gap="xs">
          <Text fw={500}>{strings.template.ready}</Text>
          <Select
            label={strings.template.sheet}
            data={template.sheets}
            value={template.sheet_name}
            allowDeselect={false}
            onChange={(sheet) => {
              if (!sheet) return;
              onDraft({ ...draft, target_sheet: sheet });
              resummarize.mutate(sheet);
            }}
          />
          {!template.target_found && (
            <Alert color="yellow">
              {strings.template.sheetMissing(draft.target_sheet, template.sheet_name)}
            </Alert>
          )}
          <Text size="sm" c="dimmed">
            {strings.template.titlesFound(template.titles.length)}
          </Text>
          <Group gap="xs">
            {template.titles.slice(0, PREVIEW_TITLES).map((title) => (
              <Badge key={title.row} variant="light" color="gray" maw={260}>
                {title.text}
              </Badge>
            ))}
          </Group>
        </Stack>
      )}
    </Stack>
  );
}
