"""Descoberta e ordenação das fotos de uma pasta."""

from __future__ import annotations

from collections.abc import Collection
from datetime import datetime
from pathlib import Path

from PIL import Image

from report_works.domain import SortMethod
from report_works.domain.errors import FolderNotFoundError, UnsafePathError
from report_works.i18n import pt_br

DEFAULT_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".bmp"})

_EXIF_SUB_IFD = 0x8769
_TAG_DATETIME_ORIGINAL = 0x9003
_TAG_DATETIME = 0x0132
_EXIF_DATE_FORMAT = "%Y:%m:%d %H:%M:%S"


def section_folder(base_dir: Path, section_id: str) -> Path:
    """Pasta de fotos de uma seção, garantindo que fique dentro de `base_dir`."""
    base = base_dir.resolve()
    folder = (base / section_id).resolve()
    if folder == base or not folder.is_relative_to(base):
        raise UnsafePathError(pt_br.ERR_UNSAFE_PATH.format(section_id=section_id))
    return folder


def _photo_files(folder: Path, extensions: Collection[str]) -> list[Path]:
    if not folder.is_dir():
        raise FolderNotFoundError(pt_br.ERR_FOLDER_NOT_FOUND.format(path=folder))
    allowed = {extension.lower() for extension in extensions}
    return [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in allowed]


def count_photos(folder: Path, extensions: Collection[str] = DEFAULT_EXTENSIONS) -> int:
    """Conta as fotos sem abri-las (barato, usado na validação em tempo real)."""
    return len(_photo_files(folder, extensions))


def read_capture_timestamp(path: Path) -> float | None:
    """Data de captura (EXIF) como timestamp; `None` se a foto não tiver ou não abrir."""
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            raw: object = exif.get_ifd(_EXIF_SUB_IFD).get(_TAG_DATETIME_ORIGINAL) or exif.get(
                _TAG_DATETIME
            )
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        return None
    if not isinstance(raw, str):
        return None
    try:
        return datetime.strptime(raw.strip(), _EXIF_DATE_FORMAT).timestamp()
    except ValueError:
        return None


def _date_key(path: Path) -> tuple[float, str]:
    """Data de captura (EXIF) ou, na falta dela, data de modificação; desempate pelo nome."""
    timestamp = read_capture_timestamp(path)
    if timestamp is None:
        timestamp = path.stat().st_mtime
    return (timestamp, path.name.casefold())


def _name_key(path: Path) -> tuple[str, str]:
    return (path.name.casefold(), path.name)


def list_photos(
    folder: Path,
    sort: SortMethod = SortMethod.DATE,
    extensions: Collection[str] = DEFAULT_EXTENSIONS,
) -> list[Path]:
    """Fotos da pasta ordenadas de forma portátil (a mesma em Windows, Linux e Docker).

    `DATE` usa a data EXIF e cai para a data de modificação; o fluxo antigo usava a data de
    criação do arquivo, que muda de significado entre sistemas operacionais.
    """
    files = _photo_files(folder, extensions)
    if sort is SortMethod.NAME:
        return sorted(files, key=_name_key)
    return sorted(files, key=_date_key)
