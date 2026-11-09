"""Testes dos modelos de domínio e da leitura do YAML."""

from pathlib import Path
from typing import Any

import pytest

from report_works.adapters.yaml_config import load_report_config, parse_report_config
from report_works.domain import ConfigError, SectionKind, SortMethod

EXAMPLE_CONFIG = Path(__file__).parents[3] / "config_exemple.yaml"


def _config(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "sections": [{"id": "entorno", "label": "Entorno da obra", "max_photos": 5}],
    }
    base.update(overrides)
    return base


def test_example_config_is_accepted() -> None:
    config = load_report_config(EXAMPLE_CONFIG)

    assert [s.id for s in config.sections][:2] == ["entorno", "geral_obra"]
    assert config.layout.photo_columns == ["B", "D", "F"]
    assert config.layout.sort_method is SortMethod.DATE
    assert config.metadata.target_sheet == "Relatório fotográfico"


def test_legacy_floor_distribution_becomes_a_grouped_section() -> None:
    config = load_report_config(EXAMPLE_CONFIG)
    floors = next(s for s in config.sections if s.id == "pavimentos")

    assert floors.kind is SectionKind.GROUPED
    assert sum(floors.group_sizes) == 119


def test_grouped_capacity_is_limited_by_the_sum_of_groups() -> None:
    config = load_report_config(EXAMPLE_CONFIG)
    floors = next(s for s in config.sections if s.id == "pavimentos")

    assert floors.max_photos == 120
    assert floors.slot_capacity == 119  # corrige o progresso 119/120 do fluxo antigo


def test_legacy_group_key_works_for_any_section_id() -> None:
    raw = _config(sections=[{"id": "torres", "label": "T", "max_photos": 9, "num_pavimentos": [3]}])

    assert parse_report_config(raw).sections[0].kind is SectionKind.GROUPED


def test_layout_defaults_match_the_legacy_hardcoded_values() -> None:
    layout = parse_report_config(_config()).layout

    assert (layout.image_span, layout.row_spacing, layout.block_gap) == (10, 2, 2)
    assert layout.block_height == 12
    assert layout.fixed_width_px == 390


@pytest.mark.parametrize(
    ("section", "expected"),
    [
        ({"id": "Entorno", "label": "x", "max_photos": 1}, "id: formato inválido"),
        ({"id": "../x", "label": "x", "max_photos": 1}, "id: formato inválido"),
        ({"id": "a", "label": "", "max_photos": 1}, "label: não pode ficar vazio"),
        ({"id": "a", "label": "x", "max_photos": 0}, "max_photos: deve ser maior ou igual a 1"),
        ({"id": "a", "label": "x"}, "max_photos: campo obrigatório"),
        (
            {"id": "a", "label": "x", "max_photos": 1, "kind": "grouped"},
            "Seção agrupada exige a lista de fotos por grupo.",
        ),
        (
            {"id": "a", "label": "x", "max_photos": 1, "group_sizes": [2]},
            "Seção em grade não aceita lista de fotos por grupo.",
        ),
        (
            {"id": "a", "label": "x", "max_photos": 1, "cor": "azul"},
            "campo desconhecido",
        ),
    ],
)
def test_invalid_sections_are_rejected_with_portuguese_messages(
    section: dict[str, Any], expected: str
) -> None:
    with pytest.raises(ConfigError) as caught:
        parse_report_config(_config(sections=[section]))

    assert any(expected in message for message in caught.value.messages)


def test_empty_photo_columns_are_rejected() -> None:
    with pytest.raises(ConfigError) as caught:
        parse_report_config(_config(layout_settings={"photo_columns": []}))

    assert any("não pode ficar vazio" in message for message in caught.value.messages)


def test_invalid_column_letters_and_duplicates_are_rejected() -> None:
    with pytest.raises(ConfigError):
        parse_report_config(_config(layout_settings={"photo_columns": ["b"]}))
    with pytest.raises(ConfigError, match="não podem se repetir"):
        parse_report_config(_config(layout_settings={"photo_columns": ["B", "B"]}))


def test_duplicate_ids_and_labels_are_rejected() -> None:
    sections = [
        {"id": "a", "label": "Um", "max_photos": 1},
        {"id": "a", "label": "Um", "max_photos": 1},
    ]

    with pytest.raises(ConfigError) as caught:
        parse_report_config(_config(sections=sections))

    assert "mesmo identificador: a" in caught.value.messages[0]


def test_config_requires_at_least_one_section() -> None:
    with pytest.raises(ConfigError, match="não pode ficar vazio"):
        parse_report_config({"sections": []})


def test_non_mapping_and_missing_files_raise_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="mapeamento YAML"):
        parse_report_config(["a"])
    with pytest.raises(ConfigError, match="não encontrado"):
        load_report_config(tmp_path / "nao_existe.yaml")


def test_invalid_yaml_raises_config_error(tmp_path: Path) -> None:
    broken = tmp_path / "config.yaml"
    broken.write_text("sections: [unclosed", encoding="utf-8")

    with pytest.raises(ConfigError, match="YAML inválido"):
        load_report_config(broken)
