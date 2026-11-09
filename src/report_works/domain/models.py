"""Modelos validados da configuração do relatório (substituem o YAML sem esquema)."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Self, cast

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator

from report_works.i18n import pt_br

SECTION_ID_PATTERN = r"^[a-z0-9_]+$"
COLUMN_PATTERN = r"^[A-Z]{1,3}$"
LEGACY_GROUP_KEY = "num_pavimentos"

ColumnLetter = Annotated[str, Field(pattern=COLUMN_PATTERN)]


class SectionKind(StrEnum):
    """Como as fotos de uma seção são distribuídas na planilha."""

    GRID = "grid"  # sequência simples na grade de colunas
    GROUPED = "grouped"  # grupos (por exemplo, andares), cada um iniciando um novo bloco


class SortMethod(StrEnum):
    """Critério de ordenação das fotos de uma pasta."""

    DATE = "date"
    NAME = "name"


class SectionConfig(BaseModel):
    """Uma seção do relatório: pasta de fotos + título no Excel."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=SECTION_ID_PATTERN)
    label: str = Field(min_length=1)
    max_photos: int = Field(ge=1)
    fix_width: bool = False
    kind: SectionKind = SectionKind.GRID
    group_sizes: list[PositiveInt] = Field(default_factory=list[int])

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_group_key(cls, data: object) -> object:
        """Aceita o campo antigo `num_pavimentos` (qualquer `id`) como seção agrupada."""
        if not isinstance(data, dict):
            return data
        raw = cast(dict[str, Any], data)
        if LEGACY_GROUP_KEY not in raw:
            return raw
        migrated = {key: value for key, value in raw.items() if key != LEGACY_GROUP_KEY}
        migrated.setdefault("group_sizes", raw[LEGACY_GROUP_KEY])
        migrated.setdefault("kind", SectionKind.GROUPED)
        return migrated

    @model_validator(mode="after")
    def _check_kind_matches_sizes(self) -> Self:
        if self.kind is SectionKind.GROUPED and not self.group_sizes:
            raise ValueError(pt_br.ERR_GROUPED_NEEDS_SIZES)
        if self.kind is SectionKind.GRID and self.group_sizes:
            raise ValueError(pt_br.ERR_GRID_FORBIDS_SIZES)
        return self

    @property
    def slot_capacity(self) -> int:
        """Quantas fotos a seção insere no máximo (corrige o progresso 119/120 do legado)."""
        if self.kind is SectionKind.GROUPED:
            return min(sum(self.group_sizes), self.max_photos)
        return self.max_photos


class LayoutSettings(BaseModel):
    """Parâmetros de posicionamento das imagens (antes fixos em `app.py`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    photo_columns: list[ColumnLetter] = Field(default_factory=lambda: ["B", "D", "F"], min_length=1)
    image_span: PositiveInt = 10
    row_spacing: int = Field(default=2, ge=0)
    block_gap: int = Field(default=2, ge=0)
    default_min_row_height: float = Field(default=23.25, gt=0)
    fixed_width_px: PositiveInt = 390
    sort_method: SortMethod = SortMethod.DATE

    @model_validator(mode="after")
    def _check_unique_columns(self) -> Self:
        if len(set(self.photo_columns)) != len(self.photo_columns):
            raise ValueError(pt_br.ERR_COLUMNS_DUPLICATED)
        return self

    @property
    def block_height(self) -> int:
        """Linhas ocupadas por um bloco de fotos (imagem + folga entre blocos)."""
        return self.image_span + self.block_gap


class ProjectMetadata(BaseModel):
    """Metadados do projeto e aba alvo da planilha."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_name: str = "Relatório"
    target_sheet: str | None = "Relatório fotográfico"
    default_font: str = "Arial"
    default_font_size: PositiveInt = 18


class PathsConfig(BaseModel):
    """Caminhos de trabalho; todos opcionais porque a API usa um diretório de trabalho."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    template: Path | None = None
    output: Path | None = None
    base_images: Path | None = None


class ReportConfig(BaseModel):
    """Configuração completa de um relatório."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    paths: PathsConfig = Field(default_factory=PathsConfig)
    layout: LayoutSettings = Field(default_factory=LayoutSettings, alias="layout_settings")
    metadata: ProjectMetadata = Field(default_factory=ProjectMetadata, alias="project_metadata")
    sections: list[SectionConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_unique_sections(self) -> Self:
        ids = [section.id for section in self.sections]
        labels = [section.label for section in self.sections]
        if len(set(ids)) != len(ids):
            raise ValueError(pt_br.ERR_DUPLICATE_SECTION_ID.format(values=_duplicates(ids)))
        if len(set(labels)) != len(labels):
            raise ValueError(pt_br.ERR_DUPLICATE_SECTION_LABEL.format(values=_duplicates(labels)))
        return self


def _duplicates(values: list[str]) -> str:
    repeated = sorted({value for value in values if values.count(value) > 1})
    return ", ".join(repeated)
