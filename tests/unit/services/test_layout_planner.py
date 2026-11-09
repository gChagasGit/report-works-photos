"""Testes do planejador de layout (puro) e comparação com a referência golden."""

from pathlib import Path
from typing import Any

import pytest

from report_works.adapters.yaml_config import load_report_config, parse_report_config
from report_works.domain import ReportConfig
from report_works.domain.errors import LayoutError
from report_works.domain.issues import IssueSeverity
from report_works.golden import load_anchors
from report_works.services.layout_planner import (
    find_overflows,
    plan_layout,
    plan_section,
    section_anchors,
)
from report_works.services.template_inspector import inspect_template

ROOT = Path(__file__).parents[3]
EXAMPLE = ROOT / "config_exemple.yaml"
MODEL = ROOT / "templates" / "model.xlsx"
GOLDEN = ROOT / "tests" / "golden" / "relatorio_final3.anchors.json"
TARGET = "Relatório fotográfico"
PHOTO_COLUMNS = {"B", "D", "F"}


def _config(section: dict[str, Any], **layout: Any) -> ReportConfig:
    return parse_report_config({"sections": [section], "layout_settings": layout})


def _cells(config: ReportConfig, anchor: int, count: int) -> list[str]:
    slots = plan_section(config.sections[0], config.layout, anchor, count)
    return [slot.cell for slot in slots]


def test_grid_fills_three_columns_then_jumps_one_block() -> None:
    config = _config({"id": "a", "label": "A", "max_photos": 7})

    assert _cells(config, anchor=11, count=7) == [
        "B13", "D13", "F13", "B25", "D25", "F25", "B37",
    ]  # fmt: skip


def test_grid_is_limited_by_max_photos_and_available_photos() -> None:
    config = _config({"id": "a", "label": "A", "max_photos": 2})

    assert _cells(config, 11, count=9) == ["B13", "D13"]
    assert _cells(config, 11, count=1) == ["B13"]


def test_number_of_columns_follows_the_configuration() -> None:
    config = _config({"id": "a", "label": "A", "max_photos": 5}, photo_columns=["B", "E"])

    assert _cells(config, 10, 5) == ["B12", "E12", "B24", "E24", "B36"]


def test_spacing_and_block_gap_come_from_the_configuration() -> None:
    config = _config(
        {"id": "a", "label": "A", "max_photos": 4},
        row_spacing=1,
        image_span=4,
        block_gap=1,
    )

    assert _cells(config, 10, 4) == ["B11", "D11", "F11", "B16"]


def test_grouped_section_starts_a_new_block_for_each_group() -> None:
    config = _config(
        {"id": "p", "label": "P", "max_photos": 99, "kind": "grouped", "group_sizes": [4, 2, 3]}
    )

    slots = plan_section(config.sections[0], config.layout, 100, 99)

    assert [slot.cell for slot in slots] == [
        "B102", "D102", "F102", "B114",  # grupo 0 (4 fotos = 2 linhas de blocos)
        "B126", "D126",                   # grupo 1
        "B138", "D138", "F138",           # grupo 2
    ]  # fmt: skip
    assert [slot.group_index for slot in slots] == [0, 0, 0, 0, 1, 1, 2, 2, 2]
    assert [slot.photo_index for slot in slots] == list(range(9))


def test_grouped_section_stops_when_photos_run_out() -> None:
    config = _config(
        {"id": "p", "label": "P", "max_photos": 99, "kind": "grouped", "group_sizes": [4, 2]}
    )

    slots = plan_section(config.sections[0], config.layout, 100, 5)

    assert [slot.cell for slot in slots] == ["B102", "D102", "F102", "B114", "B126"]


def test_missing_anchor_raises_layout_error() -> None:
    config = _config({"id": "a", "label": "Seção A", "max_photos": 1})

    with pytest.raises(LayoutError, match="Seção A"):
        plan_layout(config, anchors={}, photo_counts={"a": 1})


def test_sections_without_photos_are_skipped() -> None:
    config = _config({"id": "a", "label": "A", "max_photos": 1})

    assert plan_layout(config, anchors={}, photo_counts={"a": 0}).total == 0


def test_overflow_into_the_next_section_is_an_error() -> None:
    config = parse_report_config(
        {
            "sections": [
                {"id": "a", "label": "A", "max_photos": 9},
                {"id": "b", "label": "B", "max_photos": 1},
            ]
        }
    )
    anchors = {"a": 10, "b": 30}
    plan = plan_layout(config, anchors, {"a": 9, "b": 1})

    issues = find_overflows(config, plan, anchors)

    assert [(i.code, i.severity, i.section_id) for i in issues] == [
        ("section_overflow", IssueSeverity.ERROR, "a")
    ]
    assert "começa na linha 30" in issues[0].message
    assert "cabem 3 fotos" in issues[0].message
    assert 'reduza o "Máximo de fotos" para 3' in issues[0].message


def test_overflow_message_says_when_not_even_one_photo_fits() -> None:
    config = parse_report_config(
        {
            "sections": [
                {"id": "a", "label": "A", "max_photos": 3},
                {"id": "b", "label": "B", "max_photos": 1},
            ]
        }
    )
    anchors = {"a": 10, "b": 14}
    plan = plan_layout(config, anchors, {"a": 3, "b": 1})

    issues = find_overflows(config, plan, anchors)

    assert "não cabe nenhuma foto" in issues[0].message


def test_going_past_the_end_of_the_template_is_only_a_warning() -> None:
    config = _config({"id": "a", "label": "A", "max_photos": 9})
    plan = plan_layout(config, {"a": 10}, {"a": 9})

    issues = find_overflows(config, plan, {"a": 10}, template_last_row=40)

    assert [(i.code, i.severity) for i in issues] == [("beyond_template", IssueSeverity.WARNING)]


# --- comparação com o fluxo antigo (golden) --------------------------------------------


def _example_plan() -> tuple[ReportConfig, Any]:
    config = load_report_config(EXAMPLE)
    info = inspect_template(MODEL, TARGET)
    anchors = section_anchors(config, info)
    counts = {section.id: section.slot_capacity for section in config.sections}
    return config, (plan_layout(config, anchors, counts), anchors, info)


def test_plan_has_the_same_number_of_photos_as_the_old_report() -> None:
    _, (plan, _, _) = _example_plan()
    golden_photos = [
        p for p in load_anchors(GOLDEN) if p.from_cell and p.from_cell[0] in PHOTO_COLUMNS
    ]

    assert plan.total == len(golden_photos) == 132


def test_plan_matches_the_old_report_by_slot_region() -> None:
    """Cada foto fica na mesma coluna e a no máximo 1 linha acima ou 2 abaixo do slot.

    Medido no exemplo: 128 das 132 fotos caem exatamente na célula planejada (inclusive as 119
    dos pavimentos). As 4 de "Projetos/ARTs" (ajuste à caixa, imagem centralizada) desviam
    -1 ou +2 linhas, por isso a tolerância é [-1, +2].
    """
    _, (plan, _, _) = _example_plan()
    golden_photos = [
        p for p in load_anchors(GOLDEN) if p.from_cell and p.from_cell[0] in PHOTO_COLUMNS
    ]

    mismatches: list[str] = []
    exact = 0
    for slot, photo in zip(plan.slots, golden_photos, strict=True):
        assert photo.from_cell is not None
        column, row = photo.from_cell[0], int(photo.from_cell[1:])
        exact += int(photo.from_cell == slot.cell)
        if column != slot.column or not (-1 <= row - slot.row <= 2):
            mismatches.append(
                f"{slot.section_id}#{slot.photo_index}: {slot.cell} x {photo.from_cell}"
            )

    assert mismatches == []
    assert exact == 128


def test_example_report_fits_in_the_template_without_overflow() -> None:
    config, (plan, anchors, info) = _example_plan()

    assert find_overflows(config, plan, anchors, info.max_row) == []
