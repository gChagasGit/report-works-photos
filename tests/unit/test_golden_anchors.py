"""Testes do extrator de âncoras com planilhas sintéticas (sem Excel)."""

from pathlib import Path

import pytest
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XlImage
from PIL import Image

from report_works.golden import (
    column_label,
    extract_anchors,
    load_anchors,
    save_anchors,
)


@pytest.mark.parametrize(
    ("index", "label"),
    [(0, "A"), (1, "B"), (25, "Z"), (26, "AA"), (27, "AB"), (701, "ZZ"), (702, "AAA")],
)
def test_column_label(index: int, label: str) -> None:
    assert column_label(index) == label


def test_column_label_rejects_negative_index() -> None:
    with pytest.raises(ValueError, match="inválido"):
        column_label(-1)


def _make_workbook(tmp_path: Path) -> Path:
    workbook = Workbook()
    first = workbook.active
    assert first is not None
    first.title = "Capa"
    second = workbook.create_sheet("Relatório fotográfico")
    for number, cell in enumerate(["B13", "D13", "F13"]):
        image_path = tmp_path / f"photo{number}.png"
        Image.new("RGB", (40 + number, 30), (200, 10, 10)).save(image_path)
        second.add_image(XlImage(str(image_path)), cell)
    path = tmp_path / "report.xlsx"
    workbook.save(path)
    return path


def test_extract_anchors_returns_cells_in_drawing_order(tmp_path: Path) -> None:
    pictures = extract_anchors(_make_workbook(tmp_path))

    assert [p.from_cell for p in pictures] == ["B13", "D13", "F13"]
    assert {p.sheet for p in pictures} == {"Relatório fotográfico"}
    assert all(p.media.endswith(".png") and p.media_size > 0 for p in pictures)


def test_extract_anchors_without_drawings_is_empty(tmp_path: Path) -> None:
    path = tmp_path / "empty.xlsx"
    Workbook().save(path)

    assert extract_anchors(path) == []


def test_anchors_survive_a_json_round_trip(tmp_path: Path) -> None:
    pictures = extract_anchors(_make_workbook(tmp_path))
    json_path = tmp_path / "anchors.json"

    save_anchors(pictures, json_path)

    assert load_anchors(json_path) == pictures
