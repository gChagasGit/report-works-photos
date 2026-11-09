import { Alert, Badge, Button, Group, Stack, Table, Text } from "@mantine/core";
import { Dropzone } from "@mantine/dropzone";
import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { uploadPhotosArchive, uploadPhotosFolder } from "../api/endpoints";
import { ErrorAlert } from "../components/ErrorAlert";
import { planUpload } from "../domain/photos";
import { strings } from "../strings/pt-BR";

type Props = {
  workspaceId: string | null;
  counts: Record<string, number>;
  onChanged: () => void;
};

export function PhotosStep({ workspaceId, counts, onChanged }: Props) {
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const folderInput = useRef<HTMLInputElement>(null);

  const upload = useMutation({
    mutationFn: async (files: File[]) => {
      const plan = planUpload(files);
      if (plan.kind === "archive") return uploadPhotosArchive(workspaceId ?? "", plan.file);
      const result = await uploadPhotosFolder(workspaceId ?? "", plan.entries, (done, total) =>
        setProgress({ done, total }),
      );
      return { ...result, skipped: result.skipped + plan.ignored };
    },
    onSuccess: onChanged,
    onSettled: () => setProgress(null),
  });
  const received = upload.data ? Object.values(upload.data.sections).reduce((a, b) => a + b, 0) : 0;
  const folders = Object.entries(counts);
  const send = (files: File[]) => files.length > 0 && upload.mutate(files);

  return (
    <Stack>
      <Dropzone onDrop={send} loading={upload.isPending} disabled={workspaceId === null}>
        <Text ta="center">
          {upload.isPending
            ? progress
              ? strings.photos.uploadingProgress(progress.done, progress.total)
              : strings.photos.uploading
            : strings.photos.drop}
        </Text>
        <Text ta="center" size="sm" c="dimmed">
          {strings.photos.hint}
        </Text>
      </Dropzone>
      <Group justify="center">
        <Button
          variant="light"
          loading={upload.isPending}
          disabled={workspaceId === null}
          onClick={() => folderInput.current?.click()}
        >
          {strings.photos.chooseFolder}
        </Button>
        <input
          ref={(node) => {
            folderInput.current = node;
            node?.setAttribute("webkitdirectory", "");
          }}
          data-testid="folder-input"
          type="file"
          multiple
          hidden
          onChange={(event) => {
            send(Array.from(event.target.files ?? []));
            event.target.value = "";
          }}
        />
      </Group>
      <ErrorAlert error={upload.error} />
      {upload.data && (
        <Alert color="green">
          {strings.photos.received(received)}
          {upload.data.skipped > 0 && ` — ${strings.photos.skipped(upload.data.skipped)}`}
        </Alert>
      )}
      <Text fw={500}>{strings.photos.folders}</Text>
      {folders.length === 0 ? (
        <Text size="sm" c="dimmed">
          {strings.photos.noFolders}
        </Text>
      ) : (
        <Table withTableBorder>
          <Table.Tbody>
            {folders.map(([folder, count]) => (
              <Table.Tr key={folder}>
                <Table.Td>{folder}</Table.Td>
                <Table.Td>
                  <Group justify="flex-end">
                    <Badge variant="light">{strings.photos.photoCount(count)}</Badge>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Stack>
  );
}
