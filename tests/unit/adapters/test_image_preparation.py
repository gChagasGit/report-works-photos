"""Testes do enquadramento de fotos para o modo "Colocar na Célula"."""

from pathlib import Path

import pytest
from PIL import Image

from report_works.adapters.image_preparation import box_pixels, prepare_for_cell


@pytest.mark.parametrize(
    ("block", "max_px", "expected"),
    [
        ((295.5, 233.2), 1600, (1600, 1263)),
        ((100.0, 200.0), 1000, (500, 1000)),
        ((50.0, 50.0), 300, (300, 300)),
        ((1000.0, 1.0), 100, (100, 1)),
    ],
)
def test_box_pixels_keeps_the_block_ratio(
    block: tuple[float, float], max_px: int, expected: tuple[int, int]
) -> None:
    assert box_pixels(block[0], block[1], max_px) == expected


def _px(image: Image.Image, position: tuple[int, int]) -> tuple[int, int, int]:
    value = image.getpixel(position)
    assert isinstance(value, tuple)
    return (int(value[0]), int(value[1]), int(value[2]))


def _save(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> Path:
    Image.new("RGB", size, color).save(path)
    return path


def test_landscape_photo_in_a_taller_box_gets_white_bars_above_and_below(tmp_path: Path) -> None:
    photo = _save(tmp_path / "wide.png", (400, 100), (200, 0, 0))
    out = tmp_path / "out.jpg"

    size = prepare_for_cell(photo, out, block_width=100, block_height=100, max_px=200)

    assert size == (200, 200)
    with Image.open(out) as prepared:
        assert prepared.size == (200, 200)
        assert _px(prepared, (100, 5)) == (255, 255, 255)  # barra superior
        red, green, blue = _px(prepared, (100, 100))
        assert red > 150 and green < 60 and blue < 60  # centro é a foto


def test_portrait_photo_in_a_wide_box_gets_white_bars_on_the_sides(tmp_path: Path) -> None:
    photo = _save(tmp_path / "tall.png", (100, 400), (0, 0, 200))
    out = tmp_path / "out.jpg"

    prepare_for_cell(photo, out, block_width=300, block_height=100, max_px=300)

    with Image.open(out) as prepared:
        assert prepared.size == (300, 100)
        assert _px(prepared, (5, 50)) == (255, 255, 255)
        assert _px(prepared, (150, 50))[2] > 150


def test_small_photo_is_scaled_up_to_fill_the_box_never_distorted(tmp_path: Path) -> None:
    photo = _save(tmp_path / "small.png", (10, 10), (0, 200, 0))
    out = tmp_path / "out.jpg"

    prepare_for_cell(photo, out, block_width=200, block_height=100, max_px=400)

    with Image.open(out) as prepared:
        assert prepared.size == (400, 200)
        assert _px(prepared, (200, 100))[1] > 150
        assert _px(prepared, (20, 100)) == (255, 255, 255)  # quadrada: sobra nas laterais


def test_exif_rotation_is_applied_before_fitting(tmp_path: Path) -> None:
    photo = tmp_path / "rotated.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: girar 90 graus
    Image.new("RGB", (400, 100), (200, 0, 0)).save(photo, exif=exif)
    out = tmp_path / "out.jpg"

    prepare_for_cell(photo, out, block_width=100, block_height=400, max_px=400)

    with Image.open(out) as prepared:
        assert prepared.size == (100, 400)
        # após a rotação a foto fica em pé e ocupa a caixa vertical quase toda
        assert _px(prepared, (50, 200))[0] > 150
        assert _px(prepared, (50, 20))[0] > 150
