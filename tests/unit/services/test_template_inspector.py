"""Testes da inspeção do template com o `templates/model.xlsx` versionado."""

import unicodedata
from pathlib import Path

import pytest

from report_works.domain.errors import TemplateError
from report_works.services.template_inspector import inspect_template, normalize_label

MODEL = Path(__file__).parents[3] / "templates" / "model.xlsx"
TARGET = "Relatório fotográfico"


def test_inspect_reads_sheets_and_titles() -> None:
    info = inspect_template(MODEL, TARGET)

    assert info.sheets == ("Sheet1", TARGET)
    assert info.sheet_name == TARGET
    assert info.target_found is True
    assert info.rows_for("Entorno da obra") == [11]
    assert info.rows_for("Pavimentos (INTERNAS DA TORRE)") == [104]


def test_duplicated_title_returns_every_row_in_order() -> None:
    info = inspect_template(MODEL, TARGET)

    assert info.rows_for("Geral da obra") == [36, 38, 48]


def test_lookup_ignores_case_spacing_and_unicode_form() -> None:
    info = inspect_template(MODEL, TARGET)
    decomposed = unicodedata.normalize("NFD", "  alvará/licenças ")

    assert info.rows_for("  entorno   DA obra ") == [11]
    assert info.rows_for(decomposed) == [76]


def test_unknown_title_returns_no_rows() -> None:
    assert inspect_template(MODEL, TARGET).rows_for("Não existe") == []


def test_missing_target_sheet_falls_back_to_the_first_sheet() -> None:
    info = inspect_template(MODEL, "Outra aba")

    assert info.target_found is False
    assert info.sheet_name == "Sheet1"


def test_no_target_sheet_uses_the_first_one_without_complaint() -> None:
    info = inspect_template(MODEL, None)

    assert info.target_found is True
    assert info.sheet_name == "Sheet1"


def test_max_rows_limits_the_scan() -> None:
    info = inspect_template(MODEL, TARGET, max_rows=12)

    assert info.rows_for("Entorno da obra") == [11]
    assert info.rows_for("Geral da obra") == []


def test_unreadable_template_raises_domain_error(tmp_path: Path) -> None:
    broken = tmp_path / "broken.xlsx"
    broken.write_text("not a zip")

    with pytest.raises(TemplateError, match="Não foi possível ler"):
        inspect_template(broken, TARGET)


def test_missing_template_raises_domain_error(tmp_path: Path) -> None:
    with pytest.raises(TemplateError):
        inspect_template(tmp_path / "nope.xlsx", TARGET)


def test_normalize_label_is_idempotent() -> None:
    once = normalize_label("  Álvará   X ")

    assert normalize_label(once) == once == "álvará x"
