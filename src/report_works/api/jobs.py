"""Execução das gerações em segundo plano (uma por vez: o Excel é um recurso único)."""

from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from report_works.adapters.workspace_store import WorkspaceStore
from report_works.domain import ReportConfig
from report_works.domain.errors import (
    JobNotFoundError,
    JobNotReadyError,
    ReportError,
)
from report_works.domain.issues import ValidationIssue
from report_works.i18n import pt_br
from report_works.services.report_builder import (
    ProgressEvent,
    ReportBuilder,
    ValidationFailedError,
)

logger = logging.getLogger(__name__)


class JobState(StrEnum):
    """Ciclo de vida de uma geração."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass(frozen=True)
class JobSnapshot:
    """Cópia imutável do estado de uma tarefa, segura para ler de outra thread."""

    id: str
    workspace_id: str
    state: JobState
    done: int
    total: int
    message: str
    failures: tuple[str, ...]
    issues: tuple[ValidationIssue, ...]
    errors: tuple[str, ...]
    output: Path | None

    @property
    def percent(self) -> float:
        """Fração concluída entre 0 e 1."""
        if self.state is JobState.DONE:
            return 1.0
        return self.done / self.total if self.total else 0.0

    @property
    def finished(self) -> bool:
        """Verdadeiro quando a tarefa terminou (com sucesso ou falha)."""
        return self.state in (JobState.DONE, JobState.FAILED)


@dataclass
class _Job:
    id: str
    workspace_id: str
    state: JobState = JobState.QUEUED
    done: int = 0
    total: int = 0
    message: str = ""
    failures: tuple[str, ...] = ()
    issues: tuple[ValidationIssue, ...] = ()
    errors: tuple[str, ...] = ()
    output: Path | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    def snapshot(self) -> JobSnapshot:
        with self.lock:
            return JobSnapshot(
                id=self.id,
                workspace_id=self.workspace_id,
                state=self.state,
                done=self.done,
                total=self.total,
                message=self.message,
                failures=self.failures,
                issues=self.issues,
                errors=self.errors,
                output=self.output,
            )


class JobRunner:
    """Recebe pedidos de geração e os executa em uma única thread de trabalho."""

    def __init__(self, builder: ReportBuilder, store: WorkspaceStore) -> None:
        self._builder = builder
        self._store = store
        self._jobs: dict[str, _Job] = {}
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="report-job")

    def submit(self, workspace_id: str, config: ReportConfig) -> JobSnapshot:
        """Enfileira uma geração; levanta erro se a área de trabalho não existir."""
        self._store.workspace(workspace_id)
        job = _Job(id=uuid.uuid4().hex, workspace_id=workspace_id)
        self._jobs[job.id] = job
        self._pool.submit(self._run, job, config)
        return job.snapshot()

    def get(self, job_id: str) -> JobSnapshot:
        """Estado atual de uma tarefa."""
        job = self._jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(pt_br.ERR_JOB_NOT_FOUND)
        return job.snapshot()

    def finished_output(self, job_id: str) -> Path:
        """Caminho do relatório pronto; levanta erro se a tarefa não terminou com sucesso."""
        snapshot = self.get(job_id)
        if snapshot.state is not JobState.DONE or snapshot.output is None:
            raise JobNotReadyError(pt_br.ERR_JOB_NOT_READY)
        return snapshot.output

    def shutdown(self) -> None:
        """Aguarda a tarefa em andamento e encerra a thread de trabalho."""
        self._pool.shutdown(wait=True, cancel_futures=True)

    # --- execução (thread de trabalho) ----------------------------------------------------

    def _update(self, job: _Job, **changes: object) -> None:
        with job.lock:
            for name, value in changes.items():
                setattr(job, name, value)

    def _on_progress(self, job: _Job, event: ProgressEvent) -> None:
        self._update(job, done=event.done, total=event.total, message=event.message)

    def _run(self, job: _Job, config: ReportConfig) -> None:
        self._update(job, state=JobState.RUNNING)
        try:
            result = self._builder.build(
                config,
                self._store.template_path(job.workspace_id),
                self._store.photos_dir(job.workspace_id),
                self._store.output_path(job.workspace_id, job.id),
                on_progress=lambda event: self._on_progress(job, event),
            )
            self._update(
                job,
                state=JobState.DONE,
                output=result.output,
                failures=result.failures,
                issues=result.warnings,
            )
        except ValidationFailedError as error:
            self._update(job, state=JobState.FAILED, issues=error.issues, errors=(str(error),))
        except ReportError as error:
            self._update(job, state=JobState.FAILED, errors=(str(error),))
        except Exception:
            logger.exception("Falha inesperada na tarefa %s", job.id)
            self._update(job, state=JobState.FAILED, errors=(pt_br.ERR_UNEXPECTED,))
