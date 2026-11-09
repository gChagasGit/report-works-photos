"""Validação prévia completa: template, pastas de fotos, contagens e espaço no layout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from report_works.domain import ReportConfig
from report_works.domain.errors import ReportError
from report_works.domain.issues import ValidationIssue
from report_works.services.layout_planner import find_overflows, plan_layout, section_anchors
from report_works.services.photo_discovery import count_photos, section_folder
from report_works.services.template_inspector import TemplateInfo
from report_works.services.validation import validate_photos, validate_template


@dataclass(frozen=True)
class PreflightReport:
    """Problemas encontrados e dados reaproveitados pela geração."""

    issues: tuple[ValidationIssue, ...]
    anchors: dict[str, int]


def _photo_counts(config: ReportConfig, photos_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for section in config.sections:
        try:
            counts[section.id] = count_photos(section_folder(photos_dir, section.id))
        except ReportError:
            counts[section.id] = 0  # a validação de fotos já reportou o problema
    return counts


def run_preflight(config: ReportConfig, info: TemplateInfo, photos_dir: Path) -> PreflightReport:
    """Reúne todos os problemas que o usuário precisa ver antes de gerar."""
    issues = validate_template(config, info, config.metadata.target_sheet)
    issues += validate_photos(config, photos_dir)
    anchors = section_anchors(config, info)
    placeable = {
        section_id: count
        for section_id, count in _photo_counts(config, photos_dir).items()
        if count and section_id in anchors
    }
    plan = plan_layout(config, anchors, placeable)
    issues += find_overflows(config, plan, anchors, info.max_row)
    return PreflightReport(issues=tuple(issues), anchors=anchors)
