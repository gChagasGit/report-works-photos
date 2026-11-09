"""Inspeção do template Excel: abas e títulos de seção na coluna indicada."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string
from openpyxl.utils.exceptions import InvalidFileException

from report_works.domain.errors import TemplateError
from report_works.i18n import pt_br

DEFAULT_TITLE_COLUMN = "B"
DEFAULT_MAX_ROWS = 2000  # mesmo limite do fluxo antigo (B1:B2000)


def normalize_label(text: str) -> str:
    """Forma comparável de um título: Unicode NFC, espaços colapsados e sem diferença de caixa."""
    return " ".join(unicodedata.normalize("NFC", text).split()).casefold()


@dataclass(frozen=True)
class TitleCell:
    """Uma célula de texto da coluna de títulos."""

    row: int
    text: str


@dataclass(frozen=True)
class TemplateInfo:
    """Resumo do template necessário para validar e posicionar as seções."""

    sheets: tuple[str, ...]
    sheet_name: str
    target_found: bool
    titles: tuple[TitleCell, ...]

    def rows_for(self, label: str) -> list[int]:
        """Linhas (em ordem) cujo texto equivale a `label`."""
        wanted = normalize_label(label)
        return [cell.row for cell in self.titles if normalize_label(cell.text) == wanted]


def inspect_template(
    path: Path,
    target_sheet: str | None,
    title_column: str = DEFAULT_TITLE_COLUMN,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> TemplateInfo:
    """Lê as abas e os textos da coluna de títulos (somente leitura, sem abrir o Excel)."""
    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
    except (OSError, BadZipFile, InvalidFileException, KeyError, ValueError) as error:
        raise TemplateError(pt_br.ERR_TEMPLATE_UNREADABLE.format(detail=error)) from error
    try:
        sheets = tuple(workbook.sheetnames)
        target_found = target_sheet in sheets
        sheet_name = target_sheet if target_sheet and target_found else sheets[0]
        column = column_index_from_string(title_column)
        titles: list[TitleCell] = []
        for row in workbook[sheet_name].iter_rows(min_col=column, max_col=column, max_row=max_rows):
            cell = row[0]
            value = cell.value
            if isinstance(value, str) and value.strip():
                titles.append(TitleCell(row=cell.row or 0, text=value))
    finally:
        workbook.close()
    return TemplateInfo(
        sheets=sheets,
        sheet_name=sheet_name,
        target_found=target_found or target_sheet is None,
        titles=tuple(titles),
    )
