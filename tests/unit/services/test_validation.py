"""Testes da validação prévia de template e fotos."""

from pathlib import Path
from typing import Any

from PIL import Image

from report_works.adapters.yaml_config import load_report_config, parse_report_config
from report_works.domain import ReportConfig, SectionConfig
from report_works.domain.issues import IssueSeverity
from report_works.services.template_inspector import inspect_template
from report_works.services.validation import (
    has_blocking_issues,
    validate_photos,
    validate_template,
)

ROOT = Path(__file__).parents[3]
MODEL = ROOT / "templates" / "model.xlsx"
TARGET = "Relatório fotográfico"


def _config(*sections: dict[str, Any]) -> ReportConfig:
    return parse_report_config({"sections": list(sections)})


def _section(section_id: str, label: str, max_photos: int = 2) -> dict[str, Any]:
    return {"id": section_id, "label": label, "max_photos": max_photos}


def _photos(folder: Path, count: int) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for number in range(count):
        Image.new("RGB", (4, 4)).save(folder / f"{number}.png")


def test_example_config_matches_the_real_template_with_one_duplicate_warning() -> None:
    config = load_report_config(ROOT / "config_exemple.yaml")
    info = inspect_template(MODEL, TARGET)

    issues = validate_template(config, info, TARGET)

    assert [(i.code, i.severity, i.section_id) for i in issues] == [
        ("label_duplicated", IssueSeverity.WARNING, "geral_obra")
    ]
    assert "36, 38, 48" in issues[0].message
    assert not has_blocking_issues(issues)


def test_missing_title_blocks_generation_with_a_portuguese_message() -> None:
    info = inspect_template(MODEL, TARGET)

    issues = validate_template(_config(_section("x", "Título que não existe")), info, TARGET)

    assert has_blocking_issues(issues)
    assert issues[0].code == "label_not_found"
    assert 'O título "Título que não existe" não foi encontrado' in issues[0].message


def test_missing_target_sheet_warns_and_titles_are_searched_in_the_fallback_sheet() -> None:
    info = inspect_template(MODEL, "Aba inexistente")

    issues = validate_template(_config(_section("x", "Entorno da obra")), info, "Aba inexistente")

    # A aba "Sheet1" (a primeira) não tem os títulos: o aviso vem acompanhado do erro do título.
    assert [(i.code, i.severity) for i in issues] == [
        ("sheet_not_found", IssueSeverity.WARNING),
        ("label_not_found", IssueSeverity.ERROR),
    ]


def test_photo_folder_checks(tmp_path: Path) -> None:
    _photos(tmp_path / "ok", 2)
    _photos(tmp_path / "few", 1)
    _photos(tmp_path / "many", 5)
    (tmp_path / "empty").mkdir()
    config = _config(
        _section("ok", "A"),
        _section("few", "B"),
        _section("many", "C"),
        _section("empty", "D"),
        _section("missing", "E"),
    )

    issues = validate_photos(config, tmp_path)

    assert [(i.section_id, i.code, i.severity) for i in issues] == [
        ("few", "fewer_photos", IssueSeverity.WARNING),
        ("many", "more_photos", IssueSeverity.WARNING),
        ("empty", "no_photos", IssueSeverity.ERROR),
        ("missing", "folder_missing", IssueSeverity.ERROR),
    ]
    assert has_blocking_issues(issues)


def test_grouped_section_expects_the_sum_of_its_groups(tmp_path: Path) -> None:
    _photos(tmp_path / "floors", 3)
    section = {
        "id": "floors",
        "label": "P",
        "max_photos": 99,
        "kind": "grouped",
        "group_sizes": [2, 2],
    }

    issues = validate_photos(_config(section), tmp_path)

    assert [i.code for i in issues] == ["fewer_photos"]
    assert "prevê 4 fotos, mas a pasta tem 3" in issues[0].message


def test_id_pointing_outside_the_base_is_blocked(tmp_path: Path) -> None:
    unsafe = SectionConfig.model_construct(id="../fora", label="X", max_photos=1, group_sizes=[])
    config = ReportConfig.model_construct(sections=[unsafe])

    issues = validate_photos(config, tmp_path)

    assert [i.code for i in issues] == ["unsafe_folder"]


def test_no_issues_means_nothing_blocks() -> None:
    assert has_blocking_issues([]) is False
