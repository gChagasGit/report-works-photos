import { Alert, Badge, Group, Stack, Table, Text } from "@mantine/core";
import { Dropzone } from "@mantine/dropzone";
import { useMutation } from "@tanstack/react-query";
import { uploadPhotosZip } from "../api/endpoints";
import { ErrorAlert } from "../components/ErrorAlert";
import { strings } from "../strings/pt-BR";

const ZIP_MIMES = ["application/zip", "application/x-zip-compressed"];

type Props = {
  workspaceId: string | null;
  counts: Record<string, number>;
  onChanged: () => void;
};

export function PhotosStep({ workspaceId, counts, onChanged }: Props) {
  const upload = useMutation({
    mutationFn: (file: File) => uploadPhotosZip(workspaceId ?? "", file),
    onSuccess: onChanged,
  });
  const received = upload.data ? Object.values(upload.data.sections).reduce((a, b) => a + b, 0) : 0;
  const folders = Object.entries(counts);

  return (
    <Stack>
      <Dropzone
        onDrop={(files) => files[0] && upload.mutate(files[0])}
        accept={{ ...Object.fromEntries(ZIP_MIMES.map((mime) => [mime, [".zip"]])) }}
        multiple={false}
        loading={upload.isPending}
        disabled={workspaceId === null}
      >
        <Text ta="center">{upload.isPending ? strings.photos.uploading : strings.photos.drop}</Text>
        <Text ta="center" size="sm" c="dimmed">
          {strings.photos.hint}
        </Text>
      </Dropzone>
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
