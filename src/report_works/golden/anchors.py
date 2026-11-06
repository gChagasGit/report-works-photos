"""Extração das âncoras de imagens de um arquivo .xlsx.

Lê o pacote OOXML diretamente (sem Excel e sem openpyxl), para gerar a referência
("golden") usada na comparação entre o fluxo antigo e o novo.
"""

from __future__ import annotations

import json
import posixpath
from dataclasses import asdict, dataclass
from pathlib import Path
from xml.etree.ElementTree import Element
from zipfile import ZipFile

from defusedxml.ElementTree import fromstring

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_XDR = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"

_ANCHOR_TAGS = ("twoCellAnchor", "oneCellAnchor", "absoluteAnchor")
_ALPHABET_SIZE = 26


@dataclass(frozen=True)
class AnchoredPicture:
    """Uma imagem ancorada em uma aba, na ordem em que aparece no desenho."""

    sheet: str
    from_cell: str | None
    to_cell: str | None
    name: str
    media: str
    media_size: int


def column_label(column_index: int) -> str:
    """Converte um índice de coluna base 0 em letras (0 -> A, 27 -> AB)."""
    if column_index < 0:
        raise ValueError(f"Índice de coluna inválido: {column_index}")
    label = ""
    number = column_index + 1
    while number:
        number, remainder = divmod(number - 1, _ALPHABET_SIZE)
        label = chr(ord("A") + remainder) + label
    return label


def _read_xml(archive: ZipFile, part: str) -> Element:
    return fromstring(archive.read(part))


def _relationships(archive: ZipFile, part: str) -> dict[str, tuple[str, str]]:
    """Mapeia o id de cada relacionamento de `part` para (tipo, parte de destino)."""
    directory, filename = posixpath.split(part)
    rels_part = posixpath.join(directory, "_rels", f"{filename}.rels")
    if rels_part not in archive.namelist():
        return {}
    result: dict[str, tuple[str, str]] = {}
    for rel in _read_xml(archive, rels_part):
        rel_id = rel.get("Id")
        target = rel.get("Target")
        if rel_id is None or target is None:
            continue
        resolved = (
            target.lstrip("/")
            if target.startswith("/")
            else posixpath.normpath(posixpath.join(directory, target))
        )
        result[rel_id] = (rel.get("Type", ""), resolved)
    return result


def _sheet_parts(archive: ZipFile) -> list[tuple[str, str]]:
    """Retorna (nome da aba, parte XML da aba) na ordem do workbook."""
    workbook = _read_xml(archive, "xl/workbook.xml")
    rels = _relationships(archive, "xl/workbook.xml")
    sheets: list[tuple[str, str]] = []
    for sheet in workbook.iter(f"{{{NS_MAIN}}}sheet"):
        name = sheet.get("name")
        rel_id = sheet.get(f"{{{NS_REL}}}id")
        if name is not None and rel_id in rels:
            sheets.append((name, rels[rel_id][1]))
    return sheets


def _cell_from_marker(anchor: Element, marker_tag: str) -> str | None:
    marker = anchor.find(f"{{{NS_XDR}}}{marker_tag}")
    if marker is None:
        return None
    col = marker.findtext(f"{{{NS_XDR}}}col")
    row = marker.findtext(f"{{{NS_XDR}}}row")
    if col is None or row is None:
        return None
    return f"{column_label(int(col))}{int(row) + 1}"


def _picture_from_anchor(
    archive: ZipFile,
    sheet: str,
    anchor: Element,
    drawing_rels: dict[str, tuple[str, str]],
) -> AnchoredPicture | None:
    pic = anchor.find(f"{{{NS_XDR}}}pic")
    if pic is None:
        return None
    properties = pic.find(f"{{{NS_XDR}}}nvPicPr/{{{NS_XDR}}}cNvPr")
    blip = pic.find(f"{{{NS_XDR}}}blipFill/{{{NS_A}}}blip")
    embed = blip.get(f"{{{NS_REL}}}embed") if blip is not None else None
    media = drawing_rels[embed][1] if embed in drawing_rels else ""
    return AnchoredPicture(
        sheet=sheet,
        from_cell=_cell_from_marker(anchor, "from"),
        to_cell=_cell_from_marker(anchor, "to"),
        name=properties.get("name", "") if properties is not None else "",
        media=posixpath.basename(media),
        media_size=archive.getinfo(media).file_size if media else 0,
    )


def extract_anchors(xlsx_path: Path) -> list[AnchoredPicture]:
    """Lista as imagens ancoradas de todas as abas, na ordem do desenho."""
    pictures: list[AnchoredPicture] = []
    with ZipFile(xlsx_path) as archive:
        for sheet_name, sheet_part in _sheet_parts(archive):
            for rel_type, target in _relationships(archive, sheet_part).values():
                if not rel_type.endswith("/drawing"):
                    continue
                drawing_rels = _relationships(archive, target)
                for anchor in _read_xml(archive, target):
                    if anchor.tag.removeprefix(f"{{{NS_XDR}}}") not in _ANCHOR_TAGS:
                        continue
                    picture = _picture_from_anchor(archive, sheet_name, anchor, drawing_rels)
                    if picture is not None:
                        pictures.append(picture)
    return pictures


def save_anchors(pictures: list[AnchoredPicture], output_path: Path) -> None:
    """Grava as âncoras em JSON (UTF-8, indentado, com quebra de linha final)."""
    payload = [asdict(picture) for picture in pictures]
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def load_anchors(input_path: Path) -> list[AnchoredPicture]:
    """Lê as âncoras gravadas por `save_anchors`."""
    raw: list[dict[str, object]] = json.loads(input_path.read_text(encoding="utf-8"))
    return [
        AnchoredPicture(
            sheet=str(item["sheet"]),
            from_cell=None if item["from_cell"] is None else str(item["from_cell"]),
            to_cell=None if item["to_cell"] is None else str(item["to_cell"]),
            name=str(item["name"]),
            media=str(item["media"]),
            media_size=int(str(item["media_size"])),
        )
        for item in raw
    ]
