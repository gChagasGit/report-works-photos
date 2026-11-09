"""Testes da descoberta e ordenação de fotos."""

import os
from pathlib import Path

import pytest
from PIL import Image

from report_works.domain import SortMethod
from report_works.domain.errors import FolderNotFoundError, UnsafePathError
from report_works.services.photo_discovery import (
    count_photos,
    list_photos,
    read_capture_timestamp,
    section_folder,
)


def _photo(folder: Path, name: str, exif_date: str | None = None) -> Path:
    path = folder / name
    image = Image.new("RGB", (8, 6), (10, 20, 30))
    if exif_date is None:
        image.save(path)
    else:
        exif = Image.Exif()
        exif[0x0132] = exif_date  # DateTime (IFD0)
        image.save(path, exif=exif)
    return path


def _set_mtime(path: Path, seconds: int) -> None:
    os.utime(path, (seconds, seconds))


def test_list_photos_filters_extensions_case_insensitively(tmp_path: Path) -> None:
    _photo(tmp_path, "a.JPG")
    _photo(tmp_path, "b.png")
    (tmp_path / "notes.txt").write_text("x")
    (tmp_path / "folder.jpg").mkdir()

    names = [p.name for p in list_photos(tmp_path, SortMethod.NAME)]

    assert names == ["a.JPG", "b.png"]


def test_list_photos_accepts_custom_extensions(tmp_path: Path) -> None:
    (tmp_path / "a.webp").write_bytes(b"x")
    _photo(tmp_path, "b.png")

    names = [p.name for p in list_photos(tmp_path, SortMethod.NAME, extensions={".webp"})]

    assert names == ["a.webp"]


def test_name_order_ignores_case(tmp_path: Path) -> None:
    for name in ["b.png", "A.png", "c.png"]:
        _photo(tmp_path, name)

    assert [p.name for p in list_photos(tmp_path, SortMethod.NAME)] == ["A.png", "b.png", "c.png"]


def test_date_order_falls_back_to_modification_time(tmp_path: Path) -> None:
    newer = _photo(tmp_path, "a.png")
    older = _photo(tmp_path, "z.png")
    _set_mtime(older, 1_000_000)
    _set_mtime(newer, 2_000_000)

    assert [p.name for p in list_photos(tmp_path, SortMethod.DATE)] == ["z.png", "a.png"]


def test_date_order_prefers_exif_over_modification_time(tmp_path: Path) -> None:
    taken_first = _photo(tmp_path, "a.jpg", exif_date="2020:01:01 10:00:00")
    taken_last = _photo(tmp_path, "b.jpg", exif_date="2021:06:01 10:00:00")
    _set_mtime(taken_first, 3_000_000)  # copiada depois, mas fotografada antes
    _set_mtime(taken_last, 1_000_000)

    assert [p.name for p in list_photos(tmp_path, SortMethod.DATE)] == ["a.jpg", "b.jpg"]


def test_same_date_is_broken_by_name(tmp_path: Path) -> None:
    for name in ["b.png", "a.png"]:
        _set_mtime(_photo(tmp_path, name), 1_000_000)

    assert [p.name for p in list_photos(tmp_path, SortMethod.DATE)] == ["a.png", "b.png"]


def test_capture_timestamp_is_none_for_files_without_exif_or_invalid(tmp_path: Path) -> None:
    plain = _photo(tmp_path, "a.png")
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"not an image")

    assert read_capture_timestamp(plain) is None
    assert read_capture_timestamp(broken) is None


def test_missing_folder_raises_domain_error(tmp_path: Path) -> None:
    with pytest.raises(FolderNotFoundError, match="não encontrada"):
        list_photos(tmp_path / "nope")


def test_count_photos_does_not_open_files(tmp_path: Path) -> None:
    (tmp_path / "a.jpg").write_bytes(b"not an image")
    _photo(tmp_path, "b.png")

    assert count_photos(tmp_path) == 2


def test_section_folder_stays_inside_the_base(tmp_path: Path) -> None:
    assert section_folder(tmp_path, "entorno") == (tmp_path / "entorno").resolve()


@pytest.mark.parametrize("section_id", ["../fora", "..", ".", "a/../.."])
def test_section_folder_rejects_paths_outside_the_base(tmp_path: Path, section_id: str) -> None:
    with pytest.raises(UnsafePathError):
        section_folder(tmp_path, section_id)
