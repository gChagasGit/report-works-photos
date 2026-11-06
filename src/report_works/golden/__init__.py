"""Ferramentas para gerar e comparar a referência ("golden") de relatórios."""

from report_works.golden.anchors import (
    AnchoredPicture,
    column_label,
    extract_anchors,
    load_anchors,
    save_anchors,
)

__all__ = [
    "AnchoredPicture",
    "column_label",
    "extract_anchors",
    "load_anchors",
    "save_anchors",
]
