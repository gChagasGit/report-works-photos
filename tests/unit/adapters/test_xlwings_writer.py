"""Testes do XlwingsWriter com um xlwings falso (sem Excel e sem Windows)."""

import importlib
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from PIL import Image

from report_works.adapters.xlwings_writer import XlwingsWriter
from report_works.domain import LayoutSettings
from report_works.domain.errors import (
    ExcelUnavailableError,
    PhotoInsertError,
    ReportError,
    TemplateError,
)
from report_works.domain.layout import PhotoSlot

ROW_HEIGHT = 20.0
CELL_WIDTH = 200.0


class FakeRange:
    def __init__(self, row: int, top: float, left: float, width: float, row_height: float) -> None:
        self.row = row
        self.top = top
        self.left = left
        self.width = width
        self.row_height = row_height


class FakePicture:
    def __init__(self, **kwargs: float | str) -> None:
        self.args = kwargs
        self.api = SimpleNamespace(Placement=None)
        self.top = kwargs["top"]
        self.left = kwargs["left"]


class FakePictures:
    def __init__(self) -> None:
        self.added: list[FakePicture] = []

    def add(self, path: str, **kwargs: float) -> FakePicture:
        picture = FakePicture(path=path, **kwargs)
        self.added.append(picture)
        return picture


class FakeSheet:
    def __init__(self, name: str) -> None:
        self.name = name
        self.pictures = FakePictures()
        self._ranges: dict[str, FakeRange] = {}

    def range(self, address: str) -> FakeRange:
        if address not in self._ranges:
            if ":" in address:
                row = int(address.split(":")[0])
                self._ranges[address] = FakeRange(row, 0, 0, 0, ROW_HEIGHT)
            else:
                row = int(address[1:])
                column = ord(address[0]) - ord("A")
                self._ranges[address] = FakeRange(
                    row, (row - 1) * ROW_HEIGHT, column * 300.0, CELL_WIDTH, ROW_HEIGHT
                )
        return self._ranges[address]


class FakeSheets(list[FakeSheet]):
    def __getitem__(self, key: int | str) -> FakeSheet:  # type: ignore[override]
        if isinstance(key, str):
            return next(sheet for sheet in self if sheet.name == key)
        return super().__getitem__(key)


class FakeBook:
    def __init__(self) -> None:
        self.sheets = FakeSheets([FakeSheet("Sheet1"), FakeSheet("Relatório")])
        self.saved: list[str] = []
        self.closed = 0

    def save(self, path: str) -> None:
        self.saved.append(path)

    def close(self) -> None:
        self.closed += 1


class FakeApp:
    def __init__(self, visible: bool, add_book: bool) -> None:
        self.visible = visible
        self.add_book = add_book
        self.display_alerts = True
        self.quit_calls = 0
        self.book = FakeBook()
        self.books = SimpleNamespace(open=self._open)
        self.api = SimpleNamespace(ActiveWindow=SimpleNamespace(View=None))
        self.opened: list[str] = []

    def _open(self, path: str) -> FakeBook:
        self.opened.append(path)
        return self.book

    def quit(self) -> None:
        self.quit_calls += 1


@pytest.fixture
def excel() -> tuple[ModuleType, list[FakeApp]]:
    apps: list[FakeApp] = []
    module = ModuleType("xlwings")

    def make_app(visible: bool, add_book: bool) -> FakeApp:
        app = FakeApp(visible, add_book)
        apps.append(app)
        return app

    module.App = make_app  # type: ignore[attr-defined]
    return module, apps


def _template(tmp_path: Path) -> Path:
    path = tmp_path / "model.xlsx"
    path.write_bytes(b"x")
    return path


def _photo(tmp_path: Path, width: int, height: int, name: str = "p.png") -> Path:
    path = tmp_path / name
    Image.new("RGB", (width, height)).save(path)
    return path


def _slot(*, fix_width: bool, cell: str = "B13", span: int = 10) -> PhotoSlot:
    return PhotoSlot("s", 0, cell[0], int(cell[1:]), span, fix_width)


def _open_writer(
    tmp_path: Path, excel: tuple[ModuleType, list[FakeApp]], **kwargs: Any
) -> tuple[XlwingsWriter, FakeApp]:
    module, apps = excel
    writer = XlwingsWriter(LayoutSettings(), xlwings_module=module, **kwargs)
    writer.open(_template(tmp_path), "Relatório")
    return writer, apps[0]


def test_open_selects_the_target_sheet_and_hides_excel(
    tmp_path: Path, excel: tuple[ModuleType, list[FakeApp]]
) -> None:
    writer, app = _open_writer(tmp_path, excel)

    assert app.visible is False and app.add_book is False
    assert app.display_alerts is False
    assert app.api.ActiveWindow.View is None  # janela inexistente com o Excel invisível
    assert app.opened == [str((tmp_path / "model.xlsx").resolve())]
    writer.insert(_photo(tmp_path, 10, 10), _slot(fix_width=False))
    assert len(app.book.sheets["Relatório"].pictures.added) == 1


def test_missing_sheet_falls_back_to_the_first_one(
    tmp_path: Path, excel: tuple[ModuleType, list[FakeApp]]
) -> None:
    module, apps = excel
    writer = XlwingsWriter(LayoutSettings(), xlwings_module=module, visible=True)

    writer.open(_template(tmp_path), "Outra")
    writer.insert(_photo(tmp_path, 10, 10), _slot(fix_width=False))

    assert apps[0].api.ActiveWindow.View == 1  # modo Normal, só quando visível
    assert len(apps[0].book.sheets["Sheet1"].pictures.added) == 1


def test_fit_to_box_landscape_uses_the_cell_width_and_centers_vertically(
    tmp_path: Path, excel: tuple[ModuleType, list[FakeApp]]
) -> None:
    writer, app = _open_writer(tmp_path, excel)

    writer.insert(_photo(tmp_path, 800, 400), _slot(fix_width=False, cell="B13"))

    picture = app.book.sheets["Relatório"].pictures.added[0]
    assert (picture.args["width"], picture.args["height"]) == (200.0, 100.0)
    assert picture.args["left"] == 300.0  # coluna B; ocupa a largura toda, sem folga lateral
    # altura disponível = 10 linhas x 20 pt = 200; sobra 100, metade acima
    assert picture.args["top"] == 12 * ROW_HEIGHT + 50.0
    assert picture.api.Placement is None


def test_fit_to_box_portrait_is_limited_by_height_and_centered_horizontally(
    tmp_path: Path, excel: tuple[ModuleType, list[FakeApp]]
) -> None:
    writer, app = _open_writer(tmp_path, excel)

    writer.insert(_photo(tmp_path, 400, 800), _slot(fix_width=False, cell="D13"))

    picture = app.book.sheets["Relatório"].pictures.added[0]
    assert (picture.args["width"], picture.args["height"]) == (100.0, 200.0)
    assert picture.args["left"] == 3 * 300.0 + 50.0  # coluna D (left 900) + metade da folga
    assert picture.args["top"] == 12 * ROW_HEIGHT


def test_fixed_width_sets_picture_size_row_heights_and_placement(
    tmp_path: Path, excel: tuple[ModuleType, list[FakeApp]]
) -> None:
    writer, app = _open_writer(tmp_path, excel)
    sheet = app.book.sheets["Relatório"]

    writer.insert(_photo(tmp_path, 800, 600), _slot(fix_width=True))

    picture = sheet.pictures.added[0]
    assert picture.args["width"] == 292.5  # 390 px x 0,75
    assert picture.args["height"] == 292.5 * 600 / 800
    assert picture.api.Placement == 1
    wanted = max((picture.args["height"] + 2) / 10, 23.25)  # type: ignore[operator]
    assert [sheet.range(f"{r}:{r}").row_height for r in range(13, 23)] == [wanted] * 10


def test_fixed_width_never_shrinks_taller_rows(
    tmp_path: Path, excel: tuple[ModuleType, list[FakeApp]]
) -> None:
    writer, app = _open_writer(tmp_path, excel)
    sheet = app.book.sheets["Relatório"]
    sheet.range("15:15").row_height = 99.0

    writer.insert(_photo(tmp_path, 800, 600), _slot(fix_width=True))

    assert sheet.range("15:15").row_height == 99.0
    assert sheet.range("13:13").row_height == 23.25


def test_unreadable_photo_becomes_a_photo_insert_error(
    tmp_path: Path, excel: tuple[ModuleType, list[FakeApp]]
) -> None:
    writer, _ = _open_writer(tmp_path, excel)
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"not an image")

    with pytest.raises(PhotoInsertError, match=r"broken\.jpg em B13"):
        writer.insert(broken, _slot(fix_width=False))


def test_save_creates_missing_folders(
    tmp_path: Path, excel: tuple[ModuleType, list[FakeApp]]
) -> None:
    writer, app = _open_writer(tmp_path, excel)
    output = tmp_path / "saida" / "relatorio.xlsx"

    writer.save(output)

    assert output.parent.is_dir()
    assert app.book.saved == [str(output.resolve())]


def test_close_quits_excel_once_and_is_idempotent(
    tmp_path: Path, excel: tuple[ModuleType, list[FakeApp]]
) -> None:
    writer, app = _open_writer(tmp_path, excel)

    writer.close()
    writer.close()

    assert (app.book.closed, app.quit_calls) == (1, 1)


def test_context_manager_quits_excel_even_when_the_body_fails(
    tmp_path: Path, excel: tuple[ModuleType, list[FakeApp]]
) -> None:
    module, apps = excel
    with pytest.raises(RuntimeError), XlwingsWriter(LayoutSettings(), xlwings_module=module) as w:
        w.open(_template(tmp_path), None)
        raise RuntimeError("boom")

    assert apps[0].quit_calls == 1


def test_failure_while_opening_still_quits_excel(
    tmp_path: Path, excel: tuple[ModuleType, list[FakeApp]]
) -> None:
    module, apps = excel
    writer = XlwingsWriter(LayoutSettings(), xlwings_module=module)
    original = FakeApp._open

    def failing_open(self: FakeApp, path: str) -> FakeBook:
        raise OSError("arquivo travado")

    FakeApp._open = failing_open  # type: ignore[method-assign]
    try:
        with pytest.raises(OSError, match="travado"):
            writer.open(_template(tmp_path), None)
    finally:
        FakeApp._open = original  # type: ignore[method-assign]

    assert apps[0].quit_calls == 1


def test_using_the_writer_before_open_is_an_error(tmp_path: Path) -> None:
    writer = XlwingsWriter(LayoutSettings())

    with pytest.raises(ReportError, match="não foi aberto"):
        writer.insert(_photo(tmp_path, 4, 4), _slot(fix_width=False))
    with pytest.raises(ReportError, match="não foi aberto"):
        writer.save(tmp_path / "x.xlsx")


def test_missing_template_is_a_template_error(
    tmp_path: Path, excel: tuple[ModuleType, list[FakeApp]]
) -> None:
    module, apps = excel
    writer = XlwingsWriter(LayoutSettings(), xlwings_module=module)

    with pytest.raises(TemplateError):
        writer.open(tmp_path / "nao_existe.xlsx", None)

    assert apps == []  # o Excel nem chegou a ser iniciado


def test_missing_xlwings_is_reported_in_portuguese(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_module(name: str) -> ModuleType:
        raise ImportError(name)

    monkeypatch.setattr(importlib, "import_module", no_module)
    writer = XlwingsWriter(LayoutSettings())

    with pytest.raises(ExcelUnavailableError, match="Microsoft Excel"):
        writer.open(_template(tmp_path), None)
