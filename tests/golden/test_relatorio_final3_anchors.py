"""Verifica a referência gerada a partir de templates/relatorio_final3.xlsx.

Para regenerar a referência (exige o arquivo local, que não é versionado):
    uv run python -m report_works.golden templates/relatorio_final3.xlsx \
        tests/golden/relatorio_final3.anchors.json
"""

from pathlib import Path

from report_works.golden import AnchoredPicture, load_anchors

GOLDEN_PATH = Path(__file__).parent / "relatorio_final3.anchors.json"
PHOTO_COLUMNS = {"B", "D", "F"}
EXPECTED_PHOTOS = 132  # 5 + 2 + 4 + 1 + 1 + 119 do config_exemple.yaml


def _grid_photos() -> list[AnchoredPicture]:
    return [p for p in load_anchors(GOLDEN_PATH) if p.from_cell and p.from_cell[0] in PHOTO_COLUMNS]


def test_golden_has_all_pictures_of_the_old_flow() -> None:
    pictures = load_anchors(GOLDEN_PATH)

    assert len(pictures) == EXPECTED_PHOTOS + 1  # + imagem que já existe no template
    assert {p.sheet for p in pictures} == {"Relatório fotográfico"}


def test_golden_photos_sit_on_the_three_column_grid_without_overlap() -> None:
    photos = _grid_photos()
    cells = [p.from_cell for p in photos]

    assert len(photos) == EXPECTED_PHOTOS
    assert len(set(cells)) == len(cells)


def test_golden_first_row_of_photos_starts_at_b13() -> None:
    first_three = [p.from_cell for p in _grid_photos()[:3]]

    assert first_three == ["B13", "D13", "F13"]


def test_golden_second_row_of_photos_is_one_block_below_the_first() -> None:
    """Bloco de 12 linhas (image_span 10 + 2): a 4ª foto da seção "Entorno" fica em B25."""
    fourth_photo = _grid_photos()[3].from_cell

    assert fourth_photo == "B25"


def test_golden_fit_to_box_photos_may_start_off_the_planned_cell() -> None:
    """Fato observado: o canto da imagem centralizada pode cair fora da célula planejada.

    Por isso a comparação do novo fluxo deve ser por região do slot (linhas e colunas do
    bloco), e não por igualdade exata de célula.
    """
    cells = {p.from_cell for p in _grid_photos()}

    assert {"D51", "B54"} <= cells
