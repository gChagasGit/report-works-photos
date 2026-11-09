"""Rotas HTTP. Só traduzem requisições; a regra de negócio fica em `services`."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated, cast

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from report_works.api.schemas import (
    ArchiveOut,
    ErrorOut,
    IssueOut,
    JobOut,
    JobRequest,
    PhotoCountsOut,
    TemplateSummary,
    UploadOut,
    ValidationOut,
    WorkspaceOut,
)
from report_works.api.services import Services
from report_works.domain import ReportConfig
from report_works.domain.errors import ReportError, TemplateError, UnsupportedFileError
from report_works.i18n import pt_br
from report_works.services.preflight import run_preflight
from report_works.services.template_inspector import inspect_template
from report_works.services.validation import has_blocking_issues

DEFAULT_SHEET = "Relatório fotográfico"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
POLL_SECONDS = 0.25

router = APIRouter(
    prefix="/api",
    responses={
        400: {"model": ErrorOut},
        404: {"model": ErrorOut},
        409: {"model": ErrorOut},
        413: {"model": ErrorOut},
        422: {"model": ErrorOut},
    },
)


def _services(request: Request) -> Services:
    return cast(Services, request.app.state.services)


def _existing_template(services: Services, workspace_id: str) -> Path:
    path = services.store.template_path(workspace_id)
    if not path.is_file():
        raise TemplateError(pt_br.ERR_TEMPLATE_NOT_UPLOADED)
    return path


@router.get("/health")
def health() -> dict[str, str]:
    """Verifica se o servidor responde."""
    return {"status": "ok"}


@router.post("/workspaces", status_code=201)
def create_workspace(request: Request) -> WorkspaceOut:
    """Cria uma área de trabalho para um relatório."""
    return WorkspaceOut(id=_services(request).store.create())


@router.put("/workspaces/{workspace_id}/template")
def upload_template(
    request: Request,
    workspace_id: str,
    file: Annotated[UploadFile, File()],
    target_sheet: Annotated[str | None, Query()] = DEFAULT_SHEET,
) -> TemplateSummary:
    """Envia o template Excel e devolve abas e títulos encontrados."""
    services = _services(request)
    path = services.store.save_template(workspace_id, file.file, file.filename or "")
    try:
        return TemplateSummary.from_info(inspect_template(path, target_sheet))
    except ReportError:
        path.unlink(missing_ok=True)
        raise


@router.get("/workspaces/{workspace_id}/template")
def get_template(
    request: Request,
    workspace_id: str,
    target_sheet: Annotated[str | None, Query()] = DEFAULT_SHEET,
) -> TemplateSummary:
    """Resume o template já enviado."""
    services = _services(request)
    path = _existing_template(services, workspace_id)
    return TemplateSummary.from_info(inspect_template(path, target_sheet))


@router.post("/workspaces/{workspace_id}/photos/archive")
def upload_photos_archive(
    request: Request, workspace_id: str, file: Annotated[UploadFile, File()]
) -> ArchiveOut:
    """Envia um ZIP ou RAR com uma pasta por seção (nome da pasta = identificador da seção)."""
    sections, skipped = _services(request).store.save_archive(workspace_id, file.file)
    return ArchiveOut(sections=sections, skipped=skipped)


@router.post("/workspaces/{workspace_id}/photos/folder")
def upload_photos_folder(
    request: Request,
    workspace_id: str,
    files: Annotated[list[UploadFile], File()],
    paths: Annotated[list[str], Form()],
) -> ArchiveOut:
    """Envia (um lote de) arquivos de uma pasta; `paths[i]` é o caminho relativo de `files[i]`."""
    if len(files) != len(paths):
        raise UnsupportedFileError(pt_br.ERR_FOLDER_PATHS_MISMATCH)
    sections, skipped = _services(request).store.save_folder(
        workspace_id, [(path, file.file) for path, file in zip(paths, files, strict=True)]
    )
    return ArchiveOut(sections=sections, skipped=skipped)


@router.post("/workspaces/{workspace_id}/photos/{section_id}")
def upload_section_photos(
    request: Request,
    workspace_id: str,
    section_id: str,
    files: Annotated[list[UploadFile], File()],
) -> UploadOut:
    """Envia fotos soltas para a pasta de uma seção."""
    summary = _services(request).store.save_photos(
        workspace_id, section_id, [(f.filename or "", f.file) for f in files]
    )
    return UploadOut(saved=summary.saved, skipped=summary.skipped)


@router.get("/workspaces/{workspace_id}/photos")
def photo_counts(request: Request, workspace_id: str) -> PhotoCountsOut:
    """Quantidade de fotos guardadas por pasta de seção."""
    return PhotoCountsOut(sections=_services(request).store.count_by_section(workspace_id))


@router.post("/workspaces/{workspace_id}/validate")
def validate(request: Request, workspace_id: str, config: ReportConfig) -> ValidationOut:
    """Validação prévia: títulos no template, pastas, contagem de fotos e espaço no layout."""
    services = _services(request)
    template = _existing_template(services, workspace_id)
    info = inspect_template(template, config.metadata.target_sheet)
    report = run_preflight(config, info, services.store.photos_dir(workspace_id))
    return ValidationOut(
        issues=[IssueOut.from_issue(issue) for issue in report.issues],
        blocking=has_blocking_issues(list(report.issues)),
    )


@router.post("/jobs", status_code=202)
def create_job(request: Request, body: JobRequest) -> JobOut:
    """Inicia a geração do relatório em segundo plano."""
    services = _services(request)
    _existing_template(services, body.workspace_id)
    return JobOut.from_snapshot(services.runner.submit(body.workspace_id, body.config))


@router.get("/jobs/{job_id}")
def get_job(request: Request, job_id: str) -> JobOut:
    """Estado atual de uma geração."""
    return JobOut.from_snapshot(_services(request).runner.get(job_id))


@router.get("/jobs/{job_id}/events")
async def job_events(request: Request, job_id: str) -> StreamingResponse:
    """Andamento da geração como Server-Sent Events, até o fim da tarefa."""
    runner = _services(request).runner
    runner.get(job_id)  # falha logo (404) se a tarefa não existir

    async def stream() -> AsyncIterator[str]:
        last: tuple[object, ...] = ()
        while True:
            snapshot = runner.get(job_id)
            current = (snapshot.state, snapshot.done, snapshot.message)
            if current != last:
                last = current
                yield f"data: {JobOut.from_snapshot(snapshot).model_dump_json()}\n\n"
            if snapshot.finished:
                return
            await asyncio.sleep(POLL_SECONDS)

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/jobs/{job_id}/download")
def download(request: Request, job_id: str) -> FileResponse:
    """Baixa o relatório pronto."""
    path = _services(request).runner.finished_output(job_id)
    return FileResponse(path, media_type=XLSX_MEDIA_TYPE, filename="relatorio.xlsx")
