"""Planejador de layout puro: converte seções e contagens de fotos em posições na planilha.

Não faz I/O nem usa Excel; reproduz a grade do fluxo antigo (`ReportEngine`), mas com o número
de colunas e a folga entre blocos vindos da configuração.
"""

from __future__ import annotations

from collections.abc import Mapping
from math import ceil

from report_works.domain import LayoutSettings, ReportConfig, SectionConfig, SectionKind
from report_works.domain.errors import LayoutError
from report_works.domain.issues import IssueSeverity, ValidationIssue
from report_works.domain.layout import LayoutPlan, PhotoSlot
from report_works.i18n import pt_br
from report_works.services.template_inspector import TemplateInfo


def section_anchors(config: ReportConfig, info: TemplateInfo) -> dict[str, int]:
    """Linha do título de cada seção no template (1ª ocorrência, como no fluxo antigo)."""
    anchors: dict[str, int] = {}
    for section in config.sections:
        rows = info.rows_for(section.label)
        if rows:
            anchors[section.id] = rows[0]
    return anchors


def _slot(
    section: SectionConfig,
    layout: LayoutSettings,
    photo_index: int,
    position: int,
    base_row: int,
    group_index: int | None = None,
) -> PhotoSlot:
    columns = layout.photo_columns
    return PhotoSlot(
        section_id=section.id,
        photo_index=photo_index,
        column=columns[position % len(columns)],
        row=base_row + (position // len(columns)) * layout.block_height,
        row_span=layout.image_span,
        fix_width=section.fix_width,
        group_index=group_index,
    )


def _grid_slots(
    section: SectionConfig, layout: LayoutSettings, start_row: int, count: int
) -> list[PhotoSlot]:
    return [_slot(section, layout, index, index, start_row) for index in range(count)]


def _grouped_slots(
    section: SectionConfig, layout: LayoutSettings, start_row: int, count: int
) -> list[PhotoSlot]:
    slots: list[PhotoSlot] = []
    row = start_row
    for group_index, size in enumerate(section.group_sizes):
        for position in range(min(size, count - len(slots))):
            slots.append(_slot(section, layout, len(slots), position, row, group_index))
        if len(slots) >= count:
            break
        row += ceil(size / len(layout.photo_columns)) * layout.block_height
    return slots


def plan_section(
    section: SectionConfig, layout: LayoutSettings, anchor_row: int, photo_count: int
) -> list[PhotoSlot]:
    """Posições das fotos de uma seção (limitadas pela capacidade da própria seção)."""
    count = min(photo_count, section.slot_capacity)
    start_row = anchor_row + layout.row_spacing
    if section.kind is SectionKind.GROUPED:
        return _grouped_slots(section, layout, start_row, count)
    return _grid_slots(section, layout, start_row, count)


def plan_layout(
    config: ReportConfig, anchors: Mapping[str, int], photo_counts: Mapping[str, int]
) -> LayoutPlan:
    """Planeja todas as seções, na ordem da configuração."""
    slots: list[PhotoSlot] = []
    for section in config.sections:
        count = photo_counts.get(section.id, 0)
        if count == 0:
            continue
        if section.id not in anchors:
            raise LayoutError(pt_br.ERR_ANCHOR_MISSING.format(label=section.label))
        slots.extend(plan_section(section, config.layout, anchors[section.id], count))
    return LayoutPlan(slots=tuple(slots))


def _photos_that_fit(
    section: SectionConfig, layout: LayoutSettings, anchor_row: int, next_anchor: int
) -> int:
    """Quantas fotos da seção cabem acima do título seguinte (sem invadi-lo)."""
    slots = plan_section(section, layout, anchor_row, section.slot_capacity)
    return sum(1 for slot in slots if slot.last_row < next_anchor)


def _overflow_message(label: str, last: int, next_row: int, fit: int) -> str:
    if fit == 0:
        return pt_br.ISSUE_SECTION_NO_ROOM.format(label=label, last=last, next=next_row)
    fit_text = pt_br.ISSUE_FIT_ONE if fit == 1 else pt_br.ISSUE_FIT_MANY.format(fit=fit)
    return pt_br.ISSUE_SECTION_OVERFLOW.format(
        label=label, last=last, next=next_row, fit=fit, fit_text=fit_text
    )


def find_overflows(
    config: ReportConfig,
    plan: LayoutPlan,
    anchors: Mapping[str, int],
    template_last_row: int = 0,
) -> list[ValidationIssue]:
    """Detecta seções cujas fotos invadem a seção seguinte (erro) ou passam do fim (aviso)."""
    issues: list[ValidationIssue] = []
    for section in config.sections:
        slots = plan.for_section(section.id)
        if not slots or section.id not in anchors:
            continue
        last = max(slot.last_row for slot in slots)
        later = sorted(row for row in anchors.values() if row > anchors[section.id])
        if later and last >= later[0]:
            fit = _photos_that_fit(section, config.layout, anchors[section.id], later[0])
            message = _overflow_message(section.label, last, later[0], fit)
            issues.append(
                ValidationIssue("section_overflow", IssueSeverity.ERROR, message, section.id)
            )
        elif not later and template_last_row and last > template_last_row:
            message = pt_br.ISSUE_BEYOND_TEMPLATE.format(
                label=section.label, last=last, template_last=template_last_row
            )
            issues.append(
                ValidationIssue("beyond_template", IssueSeverity.WARNING, message, section.id)
            )
    return issues
