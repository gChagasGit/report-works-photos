"""Validação prévia: o que o usuário precisa corrigir antes de gerar o relatório."""

from __future__ import annotations

from pathlib import Path

from report_works.domain import ReportConfig, SectionConfig
from report_works.domain.errors import FolderNotFoundError, UnsafePathError
from report_works.domain.issues import IssueSeverity, ValidationIssue
from report_works.i18n import pt_br
from report_works.services.photo_discovery import count_photos, section_folder
from report_works.services.template_inspector import TemplateInfo


def _issue(
    code: str, severity: IssueSeverity, message: str, section: SectionConfig | None = None
) -> ValidationIssue:
    return ValidationIssue(
        code=code, severity=severity, message=message, section_id=section.id if section else None
    )


def _check_section_title(section: SectionConfig, info: TemplateInfo) -> list[ValidationIssue]:
    rows = info.rows_for(section.label)
    if not rows:
        message = pt_br.ISSUE_LABEL_NOT_FOUND.format(label=section.label, sheet=info.sheet_name)
        return [_issue("label_not_found", IssueSeverity.ERROR, message, section)]
    if len(rows) > 1:
        message = pt_br.ISSUE_LABEL_DUPLICATED.format(
            label=section.label,
            count=len(rows),
            rows=", ".join(str(row) for row in rows),
            first=rows[0],
        )
        return [_issue("label_duplicated", IssueSeverity.WARNING, message, section)]
    return []


def validate_template(
    config: ReportConfig, info: TemplateInfo, target_sheet: str | None
) -> list[ValidationIssue]:
    """Confere se a aba alvo e o título de cada seção existem no template."""
    issues: list[ValidationIssue] = []
    if target_sheet and not info.target_found:
        message = pt_br.ISSUE_SHEET_NOT_FOUND.format(sheet=target_sheet, used=info.sheet_name)
        issues.append(_issue("sheet_not_found", IssueSeverity.WARNING, message))
    for section in config.sections:
        issues.extend(_check_section_title(section, info))
    return issues


def _check_section_photos(section: SectionConfig, base_dir: Path) -> list[ValidationIssue]:
    try:
        folder = section_folder(base_dir, section.id)
        found = count_photos(folder)
    except UnsafePathError:
        message = pt_br.ISSUE_UNSAFE_FOLDER.format(label=section.label)
        return [_issue("unsafe_folder", IssueSeverity.ERROR, message, section)]
    except FolderNotFoundError:
        message = pt_br.ISSUE_FOLDER_MISSING.format(label=section.label, path=base_dir / section.id)
        return [_issue("folder_missing", IssueSeverity.ERROR, message, section)]
    if found == 0:
        message = pt_br.ISSUE_NO_PHOTOS.format(label=section.label)
        return [_issue("no_photos", IssueSeverity.ERROR, message, section)]
    capacity = section.slot_capacity
    if found < capacity:
        message = pt_br.ISSUE_FEWER_PHOTOS.format(
            label=section.label, expected=capacity, found=found
        )
        return [_issue("fewer_photos", IssueSeverity.WARNING, message, section)]
    if found > capacity:
        message = pt_br.ISSUE_MORE_PHOTOS.format(label=section.label, found=found, used=capacity)
        return [_issue("more_photos", IssueSeverity.WARNING, message, section)]
    return []


def validate_photos(config: ReportConfig, base_dir: Path) -> list[ValidationIssue]:
    """Confere pastas e contagem de fotos de cada seção."""
    issues: list[ValidationIssue] = []
    for section in config.sections:
        issues.extend(_check_section_photos(section, base_dir))
    return issues


def has_blocking_issues(issues: list[ValidationIssue]) -> bool:
    """Verdadeiro se algum problema impede a geração."""
    return any(issue.severity is IssueSeverity.ERROR for issue in issues)
