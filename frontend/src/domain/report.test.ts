import { describe, expect, it } from "vitest";
import {
  draftHasErrors,
  exampleSections,
  initialDraft,
  labelStatus,
  newSection,
  normalizeLabel,
  parseGroupSizes,
  sectionErrors,
  toConfig,
} from "./report";
import { TEMPLATE_SUMMARY } from "../test/mockApi";

describe("parseGroupSizes", () => {
  it("lê números separados por vírgula", () => {
    expect(parseGroupSizes("9, 6,8")).toEqual([9, 6, 8]);
  });

  it.each(["", " , ", "a, 2", "0, 3", "-1", "2.5", "3;4"])("recusa %j", (text) => {
    expect(parseGroupSizes(text)).toBeNull();
  });
});

describe("normalizeLabel", () => {
  it("ignora caixa, espaços repetidos e a forma Unicode", () => {
    const decomposed = "ALVARÁ/LICENÇAS".normalize("NFD");

    expect(normalizeLabel(`  ${decomposed}  `)).toBe(normalizeLabel("Alvará/Licenças"));
    expect(normalizeLabel("Geral   da  obra")).toBe("geral da obra");
  });
});

describe("labelStatus", () => {
  it("compara o título com o template", () => {
    expect(labelStatus("  entorno da OBRA", TEMPLATE_SUMMARY)).toEqual({ kind: "ok" });
    expect(labelStatus("Não existe", TEMPLATE_SUMMARY)).toEqual({ kind: "missing" });
    expect(labelStatus("Geral da obra", TEMPLATE_SUMMARY)).toEqual({
      kind: "duplicated",
      count: 2,
    });
  });

  it("não reclama enquanto não há template ou título", () => {
    expect(labelStatus("Qualquer", undefined)).toEqual({ kind: "ok" });
    expect(labelStatus("", TEMPLATE_SUMMARY)).toEqual({ kind: "ok" });
  });
});

describe("toConfig", () => {
  it("monta o corpo da API com seções em grade e agrupadas", () => {
    const draft = initialDraft();

    const config = toConfig(draft);

    expect(config.sections).toHaveLength(6);
    expect(config.sections[0]).toEqual({
      id: "entorno",
      label: "Entorno da obra",
      max_photos: 5,
      fix_width: false,
      kind: "grid",
      group_sizes: [],
    });
    const floors = config.sections[5];
    expect(floors?.kind).toBe("grouped");
    expect(floors?.group_sizes?.reduce((a, b) => a + b, 0)).toBe(119);
    expect(config.layout_settings).toMatchObject({ image_mode: "in_cell", max_image_px: 1600 });
    expect(config.project_metadata?.target_sheet).toBe("Relatório fotográfico");
  });

  it("apara espaços e descarta tamanhos de grupo em seções em grade", () => {
    const section = newSection({ id: " a ", label: " A ", group_sizes_text: "3", grouped: false });

    const [result] = toConfig({ ...initialDraft(), sections: [section] }).sections;

    expect(result).toMatchObject({ id: "a", label: "A", kind: "grid", group_sizes: [] });
  });
});

describe("validação de preenchimento", () => {
  it("aponta cada campo inválido", () => {
    const errors = sectionErrors(
      newSection({
        id: "Entorno",
        label: " ",
        max_photos: 0,
        grouped: true,
        group_sizes_text: "x",
      }),
    );

    expect(errors).toEqual({
      id: "invalid_id",
      label: "required",
      max_photos: "min",
      group_sizes_text: "invalid_groups",
    });
  });

  it("aceita as seções de exemplo e recusa lista vazia", () => {
    expect(exampleSections().map((s) => Object.keys(sectionErrors(s)).length)).toEqual([
      0, 0, 0, 0, 0, 0,
    ]);
    expect(draftHasErrors(initialDraft())).toBe(false);
    expect(draftHasErrors({ ...initialDraft(), sections: [] })).toBe(true);
    expect(draftHasErrors({ ...initialDraft(), sections: [newSection()] })).toBe(true);
  });
});
