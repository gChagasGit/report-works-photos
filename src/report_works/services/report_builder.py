"""Caso de uso principal: validar, planejar e gerar o relatório."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from report_works.domain import LayoutSettings, ReportConfig
from report_works.domain.errors import PhotoInsertError, ReportError
from report_works.domain.issues import IssueSeverity, ValidationIssue
from report_works.i18n import pt_br
from report_works.services.layout_planner import plan_layout
from report_works.services.photo_discovery import list_photos, section_folder
from report_works.services.ports import ImageWriter
from report_works.services.preflight import run_preflight
from report_works.services.template_inspector import inspect_template
from report_works.services.validation import has_blocking_issues

WriterFactory = Callable[[LayoutSettings], ImageWriter]


@dataclass(frozen=True)
class ProgressEvent:
    """Andamento da geração; `done`/`total` contam as fotos inseridas."""

    done: int
    total: int
    message: str

    @property
    def percent(self) -> float:
        """Fração concluída entre 0 e 1 (1 só ao salvar e concluir)."""
        return self.done / self.total if self.total else 1.0


ProgressCallback = Callable[[ProgressEvent], None]


def _ignore_progress(_event: ProgressEvent) -> None:
    """Callback padrão quando ninguém acompanha o andamento."""


@dataclass(frozen=True)
class BuildResult:
    """Resultado de uma geração bem-sucedida (pode ter falhas em fotos isoladas)."""

    output: Path
    inserted: int
    failures: tuple[str, ...]
    warnings: tuple[ValidationIssue, ...]


class ValidationFailedError(ReportError):
    """Há problemas que impedem a geração; `issues` traz todos os achados."""

    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        super().__init__(pt_br.ERR_VALIDATION_FAILED)
        self.issues = issues


class ReportBuilder:
    """Orquestra as etapas; não conhece Excel nem HTTP (usa `ImageWriter`)."""

    def __init__(self, writer_factory: WriterFactory) -> None:
        self._writer_factory = writer_factory

    def build(
        self,
        config: ReportConfig,
        template: Path,
        photos_dir: Path,
        output: Path,
        on_progress: ProgressCallback | None = None,
    ) -> BuildResult:
        """Gera o relatório; levanta `ValidationFailedError` se algo impedir a geração."""
        emit = on_progress or _ignore_progress
        info = inspect_template(template, config.metadata.target_sheet)
        report = run_preflight(config, info, photos_dir)
        if has_blocking_issues(list(report.issues)):
            raise ValidationFailedError(report.issues)

        photos = {
            section.id: list_photos(
                section_folder(photos_dir, section.id), config.layout.sort_method
            )
            for section in config.sections
        }
        plan = plan_layout(
            config, report.anchors, {key: len(value) for key, value in photos.items()}
        )
        labels = {section.id: section.label for section in config.sections}

        failures: list[str] = []
        with self._writer_factory(config.layout) as writer:
            writer.open(template, info.sheet_name)
            for done, slot in enumerate(plan.slots, start=1):
                try:
                    writer.insert(photos[slot.section_id][slot.photo_index], slot)
                except PhotoInsertError as error:
                    failures.append(str(error))
                message = pt_br.PROGRESS_INSERTING.format(
                    section=labels[slot.section_id], done=done, total=plan.total
                )
                emit(ProgressEvent(done, plan.total, message))
            emit(ProgressEvent(plan.total, plan.total, pt_br.PROGRESS_SAVING))
            writer.save(output)
        emit(ProgressEvent(plan.total, plan.total, pt_br.PROGRESS_DONE))

        warnings = tuple(i for i in report.issues if i.severity is IssueSeverity.WARNING)
        return BuildResult(
            output=output,
            inserted=plan.total - len(failures),
            failures=tuple(failures),
            warnings=warnings,
        )
