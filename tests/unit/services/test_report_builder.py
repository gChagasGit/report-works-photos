"""Testes do ReportBuilder com um escritor falso (sem Excel)."""

from pathlib import Path
from types import TracebackType
from typing import Any, Self

import pytest
from PIL import Image

from report_works.adapters.yaml_config import parse_report_config
from report_works.domain import LayoutSettings, ReportConfig
from report_works.domain.errors import PhotoInsertError
from report_works.domain.layout import PhotoSlot
from report_works.services.report_builder import (
    ProgressEvent,
    ReportBuilder,
    ValidationFailedError,
)

ROOT = Path(__file__).parents[3]
MODEL = ROOT / "templates" / "model.xlsx"
FLOOR_GROUPS = [9, 6, 8, 6, 6, 7, 6, 6, 5, 4, 4, 7, 7, 5, 3, 4, 4, 4, 5, 4, 5, 4]  # soma 119


class FakeWriter:
    def __init__(self, fail_on: set[str] | None = None) -> None:
        self.fail_on = fail_on or set()
        self.opened: tuple[Path, str | None] | None = None
        self.inserted: list[tuple[str, str]] = []
        self.saved: Path | None = None
        self.closed = 0

    def open(self, template: Path, sheet_name: str | None) -> None:
        self.opened = (template, sheet_name)

    def insert(self, photo: Path, slot: PhotoSlot) -> None:
        if photo.name in self.fail_on:
            raise PhotoInsertError(f"falhou {photo.name}")
        self.inserted.append((photo.name, slot.cell))

    def save(self, output: Path) -> None:
        self.saved = output

    def close(self) -> None:
        self.closed += 1

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def _config(**section: Any) -> ReportConfig:
    base = {"id": "entorno", "label": "Entorno da obra", "max_photos": 5}
    base.update(section)
    return parse_report_config(
        {
            "sections": [base],
            "layout_settings": {"sort_method": "name"},
        }
    )


def _photos(root: Path, section_id: str, count: int) -> None:
    folder = root / section_id
    folder.mkdir(parents=True, exist_ok=True)
    for number in range(count):
        Image.new("RGB", (4, 4)).save(folder / f"{number}.png")


def _builder(writer: FakeWriter) -> ReportBuilder:
    return ReportBuilder(lambda _layout: writer)


def test_build_inserts_photos_in_planned_cells_and_saves(tmp_path: Path) -> None:
    _photos(tmp_path, "entorno", 5)
    writer = FakeWriter()
    events: list[ProgressEvent] = []

    result = _builder(writer).build(
        _config(), MODEL, tmp_path, tmp_path / "out.xlsx", on_progress=events.append
    )

    assert writer.opened == (MODEL, "Relatório fotográfico")
    assert writer.inserted == [
        ("0.png", "B13"),
        ("1.png", "D13"),
        ("2.png", "F13"),
        ("3.png", "B25"),
        ("4.png", "D25"),
    ]
    assert writer.saved == tmp_path / "out.xlsx"
    assert writer.closed == 1
    assert (result.inserted, result.failures) == (5, ())
    assert [e.done for e in events] == [1, 2, 3, 4, 5, 5, 5]
    assert events[0].message == "Entorno da obra: foto 1 de 5"
    assert events[-2].message == "Salvando o relatório..."
    assert events[-1].message == "Relatório concluído."
    assert events[-1].percent == 1.0


def test_progress_reaches_exactly_100_percent_for_grouped_sections(tmp_path: Path) -> None:
    """Corrige o 119/120 do fluxo antigo: o total vem do plano, não de max_photos."""
    _photos(tmp_path, "pavimentos", 119)
    config = parse_report_config(
        {
            "sections": [
                {
                    "id": "pavimentos",
                    "label": "Pavimentos (INTERNAS DA TORRE)",
                    "max_photos": 120,
                    "kind": "grouped",
                    "group_sizes": [
                        9,
                        6,
                        8,
                        6,
                        6,
                        7,
                        6,
                        6,
                        5,
                        4,
                        4,
                        7,
                        7,
                        5,
                        3,
                        4,
                        4,
                        4,
                        5,
                        4,
                        5,
                        4,
                    ],
                }
            ]
        }
    )
    events: list[ProgressEvent] = []

    _builder(FakeWriter()).build(config, MODEL, tmp_path, tmp_path / "o.xlsx", events.append)

    assert events[-1].done == events[-1].total == 119
    assert max(e.percent for e in events[:-2]) == 1.0  # a última foto já fecha o plano


def test_photo_failures_are_collected_and_do_not_stop_the_report(tmp_path: Path) -> None:
    _photos(tmp_path, "entorno", 3)
    writer = FakeWriter(fail_on={"1.png"})

    result = _builder(writer).build(_config(), MODEL, tmp_path, tmp_path / "o.xlsx")

    assert result.failures == ("falhou 1.png",)
    assert result.inserted == 2
    assert writer.saved is not None


def test_blocking_problems_stop_before_touching_the_writer(tmp_path: Path) -> None:
    writer = FakeWriter()  # a pasta de fotos não existe

    with pytest.raises(ValidationFailedError) as caught:
        _builder(writer).build(_config(), MODEL, tmp_path, tmp_path / "o.xlsx")

    assert [i.code for i in caught.value.issues] == ["folder_missing"]
    assert writer.opened is None and writer.closed == 0


def test_missing_title_in_the_template_blocks_the_build(tmp_path: Path) -> None:
    _photos(tmp_path, "entorno", 1)

    with pytest.raises(ValidationFailedError) as caught:
        _builder(FakeWriter()).build(
            _config(label="Título inexistente"), MODEL, tmp_path, tmp_path / "o.xlsx"
        )

    assert "label_not_found" in [i.code for i in caught.value.issues]


def test_writer_is_closed_when_saving_fails(tmp_path: Path) -> None:
    _photos(tmp_path, "entorno", 1)

    class BrokenSave(FakeWriter):
        def save(self, output: Path) -> None:
            raise OSError("disco cheio")

    writer = BrokenSave()
    with pytest.raises(OSError, match="disco cheio"):
        _builder(writer).build(_config(), MODEL, tmp_path, tmp_path / "o.xlsx")

    assert writer.closed == 1


def test_layout_settings_reach_the_writer_factory(tmp_path: Path) -> None:
    _photos(tmp_path, "entorno", 1)
    received: list[LayoutSettings] = []
    writer = FakeWriter()

    def factory(layout: LayoutSettings) -> FakeWriter:
        received.append(layout)
        return writer

    ReportBuilder(factory).build(_config(), MODEL, tmp_path, tmp_path / "o.xlsx")

    assert received[0].photo_columns == ["B", "D", "F"]
