"""Escritor de imagens via Excel (xlwings/COM). Funciona só em Windows com Excel instalado.

Porta a lógica do `ReportEngine` antigo (`_insert_fixed_width` e `_insert_fit_to_box`), com três
diferenças: o tamanho das imagens vem do Pillow (sem inserir e apagar uma imagem temporária no
Excel), o Excel fica invisível por padrão e é sempre encerrado, mesmo em caso de erro.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType, TracebackType
from typing import Any, Self

from PIL import Image

from report_works.domain import LayoutSettings
from report_works.domain.errors import (
    ExcelUnavailableError,
    PhotoInsertError,
    ReportError,
    TemplateError,
)
from report_works.domain.layout import PhotoSlot
from report_works.i18n import pt_br

ComObject = Any  # objetos do xlwings/COM não têm tipos estáticos

PX_TO_PT = 0.75
XL_NORMAL_VIEW = 1
XL_MOVE_AND_SIZE = 1
ROW_PADDING_PT = 2  # folga somada à altura da imagem, como no fluxo antigo


def _load_xlwings() -> ModuleType:
    try:
        return importlib.import_module("xlwings")
    except ImportError as error:
        raise ExcelUnavailableError(pt_br.ERR_EXCEL_UNAVAILABLE) from error


def _image_size(photo: Path) -> tuple[int, int]:
    """Largura e altura em pixels, lidas pelo Pillow."""
    with Image.open(photo) as image:
        return image.size


class XlwingsWriter:
    """Implementa `ImageWriter` controlando uma instância do Excel."""

    def __init__(
        self,
        layout: LayoutSettings,
        *,
        visible: bool = False,
        xlwings_module: ModuleType | None = None,
    ) -> None:
        self._layout = layout
        self._visible = visible
        self._xw = xlwings_module
        self._app: Any = None
        self._book: Any = None
        self._sheet: Any = None

    # --- ciclo de vida ----------------------------------------------------------------

    def open(self, template: Path, sheet_name: str | None) -> None:
        """Abre o template e seleciona a aba pedida (ou a primeira, se ela não existir)."""
        xw = self._xw or _load_xlwings()
        path = template.resolve()
        if not path.is_file():
            raise TemplateError(pt_br.ERR_TEMPLATE_UNREADABLE.format(detail=path))
        self._app = xw.App(visible=self._visible, add_book=False)
        try:
            self._app.display_alerts = False  # sobrescrever o arquivo de saída sem perguntar
            self._book = self._app.books.open(str(path))
            if self._visible:
                self._app.api.ActiveWindow.View = XL_NORMAL_VIEW
            names = [sheet.name for sheet in self._book.sheets]
            self._sheet = self._book.sheets[sheet_name if sheet_name in names else 0]
        except Exception:
            self.close()
            raise

    def save(self, output: Path) -> None:
        """Grava o relatório, criando as pastas do caminho de saída."""
        book = self._require_book()
        target = output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        book.save(str(target))

    def close(self) -> None:
        """Fecha a pasta de trabalho e encerra o Excel; pode ser chamado várias vezes."""
        book, app = self._book, self._app
        self._book = self._app = self._sheet = None
        try:
            if book is not None:
                book.close()
        finally:
            if app is not None:
                app.quit()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    # --- inserção -------------------------------------------------------------------------

    def insert(self, photo: Path, slot: PhotoSlot) -> None:
        """Insere uma foto na posição planejada."""
        sheet = self._require_sheet()
        try:
            width_px, height_px = _image_size(photo)
            target = sheet.range(slot.cell)
            if slot.fix_width:
                self._insert_fixed_width(sheet, photo.resolve(), target, slot, width_px, height_px)
            else:
                self._insert_fit_to_box(sheet, photo.resolve(), target, slot, width_px, height_px)
        except ReportError:
            raise
        except Exception as error:  # falhas do COM ou do Pillow viram erro por foto
            message = pt_br.ERR_PHOTO_INSERT.format(name=photo.name, cell=slot.cell, detail=error)
            raise PhotoInsertError(message) from error

    def _insert_fixed_width(
        self,
        sheet: ComObject,
        photo: Path,
        target: ComObject,
        slot: PhotoSlot,
        width_px: int,
        height_px: int,
    ) -> None:
        """Largura fixa: ajusta a altura das linhas do bloco e insere a imagem sem distorcer."""
        width_pt = self._layout.fixed_width_px * PX_TO_PT
        height_pt = width_pt * height_px / width_px
        wanted = max(
            (height_pt + ROW_PADDING_PT) / slot.row_span, self._layout.default_min_row_height
        )
        for row_number in range(slot.row, slot.row + slot.row_span):
            row = sheet.range(f"{row_number}:{row_number}")
            if round(wanted, 2) > round(row.row_height or 0, 2):
                row.row_height = wanted
        picture = sheet.pictures.add(
            str(photo), left=target.left, top=target.top, width=width_pt, height=height_pt
        )
        picture.api.Placement = XL_MOVE_AND_SIZE
        picture.top, picture.left = target.top, target.left

    def _insert_fit_to_box(
        self,
        sheet: ComObject,
        photo: Path,
        target: ComObject,
        slot: PhotoSlot,
        width_px: int,
        height_px: int,
    ) -> None:
        """Enquadra a imagem na caixa (largura da célula x altura das linhas) e a centraliza."""
        default = self._layout.default_min_row_height
        available_height = sum(
            sheet.range(f"{number}:{number}").row_height or default
            for number in range(slot.row, slot.row + slot.row_span)
        )
        ratio = width_px / height_px
        new_width = target.width
        new_height = new_width / ratio
        if new_height > available_height:
            new_height = available_height
            new_width = available_height * ratio
        sheet.pictures.add(
            str(photo),
            left=target.left + (target.width - new_width) / 2,
            top=target.top + (available_height - new_height) / 2,
            width=new_width,
            height=new_height,
        )

    # --- auxiliares -----------------------------------------------------------------------

    def _require_book(self) -> Any:  # noqa: ANN401 - objeto COM sem tipos
        if self._book is None:
            raise ReportError(pt_br.ERR_WRITER_NOT_OPEN)
        return self._book

    def _require_sheet(self) -> Any:  # noqa: ANN401 - objeto COM sem tipos
        if self._sheet is None:
            raise ReportError(pt_br.ERR_WRITER_NOT_OPEN)
        return self._sheet
