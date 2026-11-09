import type { ReportConfig, TemplateSummary } from "../api/endpoints";

export const SECTION_ID_PATTERN = /^[a-z0-9_]+$/;
export const DEFAULT_SHEET = "Relatório fotográfico";

export type SectionDraft = {
  key: string;
  id: string;
  label: string;
  max_photos: number;
  fix_width: boolean;
  grouped: boolean;
  group_sizes_text: string;
};

export type ReportDraft = {
  target_sheet: string;
  sort_method: "date" | "name";
  image_mode: "in_cell" | "floating";
  max_image_px: number;
  sections: SectionDraft[];
};

let counter = 0;
export const newKey = () => `section-${(counter += 1)}`;

export function newSection(partial: Partial<SectionDraft> = {}): SectionDraft {
  return {
    key: newKey(),
    id: "",
    label: "",
    max_photos: 1,
    fix_width: false,
    grouped: false,
    group_sizes_text: "",
    ...partial,
  };
}

/** Seções do relatório de exemplo (as mesmas do `config_exemple.yaml`). */
export function exampleSections(): SectionDraft[] {
  return [
    newSection({ id: "entorno", label: "Entorno da obra", max_photos: 5 }),
    newSection({ id: "geral_obra", label: "Geral da obra", max_photos: 2, fix_width: true }),
    newSection({ id: "projetos_arts", label: "Projetos/ARTs", max_photos: 4 }),
    newSection({ id: "alvara_licenca", label: "Alvará/Licenças", max_photos: 1 }),
    newSection({
      id: "geral_habitacao",
      label: "Geral da habitação (EXTERNAS DA TORRE)",
      max_photos: 1,
      fix_width: true,
    }),
    newSection({
      id: "pavimentos",
      label: "Pavimentos (INTERNAS DA TORRE)",
      max_photos: 120,
      fix_width: true,
      grouped: true,
      group_sizes_text: "9, 6, 8, 6, 6, 7, 6, 6, 5, 4, 4, 7, 7, 5, 3, 4, 4, 4, 5, 4, 5, 4",
    }),
  ];
}

export function initialDraft(): ReportDraft {
  return {
    target_sheet: DEFAULT_SHEET,
    sort_method: "date",
    image_mode: "in_cell",
    max_image_px: 1600,
    sections: exampleSections(),
  };
}

/** Lê "9, 6, 8"; devolve `null` se algum item não for inteiro maior que zero. */
export function parseGroupSizes(text: string): number[] | null {
  const parts = text
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part !== "");
  if (parts.length === 0) return null;
  const numbers = parts.map((part) => (/^\d+$/.test(part) ? Number(part) : NaN));
  return numbers.every((n) => Number.isInteger(n) && n > 0) ? numbers : null;
}

/** Mesma normalização do backend: Unicode NFC, espaços colapsados e sem diferença de caixa. */
export function normalizeLabel(text: string): string {
  return text.normalize("NFC").split(/\s+/).filter(Boolean).join(" ").toLocaleLowerCase();
}

export type LabelStatus =
  { kind: "ok" } | { kind: "missing" } | { kind: "duplicated"; count: number };

/** Confere o título de uma seção contra os títulos encontrados no template. */
export function labelStatus(label: string, template: TemplateSummary | undefined): LabelStatus {
  if (!template || label.trim() === "") return { kind: "ok" };
  const wanted = normalizeLabel(label);
  const count = template.titles.filter((title) => normalizeLabel(title.text) === wanted).length;
  if (count === 0) return { kind: "missing" };
  return count > 1 ? { kind: "duplicated", count } : { kind: "ok" };
}

/** Monta o corpo enviado à API a partir do rascunho da interface. */
export function toConfig(draft: ReportDraft): ReportConfig {
  return {
    sections: draft.sections.map((section) => {
      const sizes = section.grouped ? (parseGroupSizes(section.group_sizes_text) ?? []) : [];
      return {
        id: section.id.trim(),
        label: section.label.trim(),
        max_photos: section.max_photos,
        fix_width: section.fix_width,
        kind: section.grouped ? "grouped" : "grid",
        group_sizes: sizes,
      };
    }),
    layout_settings: {
      sort_method: draft.sort_method,
      image_mode: draft.image_mode,
      max_image_px: draft.max_image_px,
    } as NonNullable<ReportConfig["layout_settings"]>,
    project_metadata: { target_sheet: draft.target_sheet || null } as NonNullable<
      ReportConfig["project_metadata"]
    >,
  };
}

/** Erros de preenchimento de uma seção, por campo, antes de qualquer chamada à API. */
export function sectionErrors(section: SectionDraft): Partial<Record<keyof SectionDraft, string>> {
  const errors: Partial<Record<keyof SectionDraft, string>> = {};
  if (!SECTION_ID_PATTERN.test(section.id)) errors.id = "invalid_id";
  if (section.label.trim() === "") errors.label = "required";
  if (!Number.isInteger(section.max_photos) || section.max_photos < 1) errors.max_photos = "min";
  if (section.grouped && parseGroupSizes(section.group_sizes_text) === null) {
    errors.group_sizes_text = "invalid_groups";
  }
  return errors;
}

export function draftHasErrors(draft: ReportDraft): boolean {
  return (
    draft.sections.length === 0 ||
    draft.sections.some((section) => Object.keys(sectionErrors(section)).length > 0)
  );
}
