export const IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp"];
export const ARCHIVE_EXTENSIONS = [".zip", ".rar"];

export type FolderFile = { file: File; path: string };

export type UploadPlan =
  { kind: "archive"; file: File } | { kind: "folder"; entries: FolderFile[]; ignored: number };

const hasExtension = (name: string, extensions: string[]) =>
  extensions.some((extension) => name.toLowerCase().endsWith(extension));

/** Caminho relativo de um arquivo vindo de uma pasta (seletor de pasta ou arrastar e soltar). */
export function relativePath(file: File): string {
  const source = file as File & { path?: string; webkitRelativePath?: string };
  const raw = source.webkitRelativePath || source.path || file.name;
  return raw.replace(/\\/g, "/").replace(/^(\.?\/)+/, "");
}

/** Decide o que enviar: um único ZIP/RAR, ou as imagens de uma pasta com seus caminhos. */
export function planUpload(files: File[]): UploadPlan {
  const [first] = files;
  if (files.length === 1 && first && hasExtension(first.name, ARCHIVE_EXTENSIONS)) {
    return { kind: "archive", file: first };
  }
  const images = files.filter((file) => hasExtension(file.name, IMAGE_EXTENSIONS));
  return {
    kind: "folder",
    entries: images.map((file) => ({ file, path: relativePath(file) })),
    ignored: files.length - images.length,
  };
}
