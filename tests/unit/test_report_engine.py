"""Testes do ReportEngine legado (sem abrir o Excel)."""

from pathlib import Path

import yaml
from scripts.report_engine import ReportEngine


def test_engine_reads_layout_settings(tmp_path: Path) -> None:
    config = {
        "paths": {"template": "template_fake.xlsx"},
        "layout_settings": {"photo_columns": ["B", "D"], "image_span": 8, "row_spacing": 3},
        "project_metadata": {"target_sheet": "Relatório fotográfico"},
        "sections": [],
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")

    engine = ReportEngine(str(config_path))

    assert engine.PHOTO_COLS == ["B", "D"]
    assert engine.IMAGE_SPAN == 8
    assert engine.ROW_SPACING == 3


def test_engine_uses_defaults_when_layout_is_missing(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump({"paths": {}, "sections": []}), encoding="utf-8")

    engine = ReportEngine(str(config_path))

    assert engine.PHOTO_COLS == ["B", "D", "F"]
    assert engine.IMAGE_SPAN == 10
    assert engine.FIXED_WIDTH_PX == 390
