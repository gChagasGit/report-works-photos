import {
  Accordion,
  Autocomplete,
  Badge,
  Button,
  FileButton,
  Group,
  NumberInput,
  Paper,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
} from "@mantine/core";
import { useMutation } from "@tanstack/react-query";
import { uploadSectionPhotos, type TemplateSummary } from "../api/endpoints";
import { ErrorAlert } from "../components/ErrorAlert";
import {
  exampleSections,
  labelStatus,
  newSection,
  sectionErrors,
  type ReportDraft,
  type SectionDraft,
} from "../domain/report";
import { strings } from "../strings/pt-BR";

const ERROR_TEXT = {
  invalid_id: strings.sections.invalidId,
  required: strings.sections.required,
  min: strings.sections.atLeastOne,
  invalid_groups: strings.sections.invalidGroups,
} as const;

type Props = {
  workspaceId: string | null;
  draft: ReportDraft;
  onDraft: (draft: ReportDraft) => void;
  template: TemplateSummary | undefined;
  counts: Record<string, number>;
  onPhotosChanged: () => void;
};

type CardProps = {
  workspaceId: string | null;
  section: SectionDraft;
  template: TemplateSummary | undefined;
  photoCount: number;
  titles: string[];
  onChange: (patch: Partial<SectionDraft>) => void;
  onRemove: () => void;
  onPhotosChanged: () => void;
};

const toNumber = (value: string | number) =>
  typeof value === "number" ? value : Number(value) || 0;

function SectionCard({
  workspaceId,
  section,
  template,
  photoCount,
  titles,
  onChange,
  onRemove,
  onPhotosChanged,
}: CardProps) {
  const upload = useMutation({
    mutationFn: (files: File[]) => uploadSectionPhotos(workspaceId ?? "", section.id, files),
    onSuccess: onPhotosChanged,
  });
  const errors = sectionErrors(section);
  const text = (code: string | undefined) =>
    code ? ERROR_TEXT[code as keyof typeof ERROR_TEXT] : undefined;
  const status = labelStatus(section.label, template);
  const labelError =
    text(errors.label) ?? (status.kind === "missing" ? strings.sections.titleNotFound : undefined);
  const labelHint =
    status.kind === "duplicated" ? strings.sections.titleDuplicated(status.count) : undefined;

  return (
    <Paper withBorder p="md" data-testid={`section-${section.id || section.key}`}>
      <Stack gap="xs">
        <Group align="flex-start" grow>
          <TextInput
            label={strings.sections.folder}
            description={strings.sections.folderHelp}
            value={section.id}
            error={text(errors.id)}
            onChange={(event) => onChange({ id: event.currentTarget.value })}
          />
          <Autocomplete
            label={strings.sections.label}
            data={titles}
            value={section.label}
            error={labelError}
            description={labelHint}
            onChange={(label) => onChange({ label })}
          />
          <NumberInput
            label={strings.sections.maxPhotos}
            min={1}
            value={section.max_photos}
            error={text(errors.max_photos)}
            onChange={(value) => onChange({ max_photos: toNumber(value) })}
          />
        </Group>
        <Group>
          <Switch
            label={strings.sections.fixWidth}
            checked={section.fix_width}
            onChange={(event) => onChange({ fix_width: event.currentTarget.checked })}
          />
          <Switch
            label={strings.sections.grouped}
            checked={section.grouped}
            onChange={(event) => onChange({ grouped: event.currentTarget.checked })}
          />
        </Group>
        {section.grouped && (
          <TextInput
            label={strings.sections.groupSizes}
            description={strings.sections.groupSizesHelp}
            value={section.group_sizes_text}
            error={text(errors.group_sizes_text)}
            onChange={(event) => onChange({ group_sizes_text: event.currentTarget.value })}
          />
        )}
        <Group justify="space-between">
          <Group gap="xs">
            <Badge color={photoCount > 0 ? "green" : "red"} variant="light">
              {strings.photos.photoCount(photoCount)}
            </Badge>
            {photoCount === 0 && section.id !== "" && errors.id === undefined && (
              <Text size="sm" c="red">
                {strings.sections.folderEmpty}
              </Text>
            )}
          </Group>
          <Group gap="xs">
            <FileButton
              multiple
              accept="image/*"
              onChange={(files) => files.length > 0 && upload.mutate(files)}
            >
              {(props) => (
                <Button
                  {...props}
                  size="xs"
                  variant="light"
                  loading={upload.isPending}
                  disabled={workspaceId === null || errors.id !== undefined}
                >
                  {strings.sections.uploadPhotos}
                </Button>
              )}
            </FileButton>
            <Button size="xs" variant="subtle" color="red" onClick={onRemove}>
              {strings.sections.remove}
            </Button>
          </Group>
        </Group>
        <ErrorAlert error={upload.error} />
      </Stack>
    </Paper>
  );
}

export function SectionsStep({
  workspaceId,
  draft,
  onDraft,
  template,
  counts,
  onPhotosChanged,
}: Props) {
  const titles = [...new Set(template?.titles.map((title) => title.text) ?? [])];
  const update = (key: string, patch: Partial<SectionDraft>) =>
    onDraft({
      ...draft,
      sections: draft.sections.map((s) => (s.key === key ? { ...s, ...patch } : s)),
    });

  return (
    <Stack>
      {draft.sections.length === 0 && <Text c="dimmed">{strings.sections.empty}</Text>}
      {draft.sections.map((section) => (
        <SectionCard
          key={section.key}
          workspaceId={workspaceId}
          section={section}
          template={template}
          photoCount={counts[section.id] ?? 0}
          titles={titles}
          onChange={(patch) => update(section.key, patch)}
          onRemove={() =>
            onDraft({ ...draft, sections: draft.sections.filter((s) => s.key !== section.key) })
          }
          onPhotosChanged={onPhotosChanged}
        />
      ))}
      <Group>
        <Button
          variant="light"
          onClick={() => onDraft({ ...draft, sections: [...draft.sections, newSection()] })}
        >
          {strings.sections.add}
        </Button>
        <Button variant="subtle" onClick={() => onDraft({ ...draft, sections: exampleSections() })}>
          {strings.sections.useExample}
        </Button>
        <Button variant="subtle" color="gray" onClick={() => onDraft({ ...draft, sections: [] })}>
          {strings.sections.clear}
        </Button>
      </Group>
      <Accordion variant="contained">
        <Accordion.Item value="advanced">
          <Accordion.Control>{strings.sections.advanced}</Accordion.Control>
          <Accordion.Panel>
            <Stack>
              <div>
                <Text size="sm" fw={500}>
                  {strings.sections.sortMethod}
                </Text>
                <SegmentedControl
                  value={draft.sort_method}
                  data={[
                    { value: "date", label: strings.sections.sortDate },
                    { value: "name", label: strings.sections.sortName },
                  ]}
                  onChange={(value) =>
                    onDraft({ ...draft, sort_method: value === "name" ? "name" : "date" })
                  }
                />
              </div>
              <Select
                label={strings.sections.imageMode}
                allowDeselect={false}
                value={draft.image_mode}
                data={[
                  { value: "in_cell", label: strings.sections.imageInCell },
                  { value: "floating", label: strings.sections.imageFloating },
                ]}
                onChange={(value) =>
                  onDraft({ ...draft, image_mode: value === "floating" ? "floating" : "in_cell" })
                }
              />
              <NumberInput
                label={strings.sections.maxImagePx}
                min={200}
                value={draft.max_image_px}
                onChange={(value) => onDraft({ ...draft, max_image_px: toNumber(value) })}
              />
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>
    </Stack>
  );
}
