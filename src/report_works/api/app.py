"""Criação da aplicação FastAPI."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from report_works.adapters.settings import Settings
from report_works.adapters.workspace_store import WorkspaceStore
from report_works.adapters.xlwings_writer import XlwingsWriter
from report_works.api.jobs import JobRunner
from report_works.api.routes import router
from report_works.api.schemas import ErrorOut, IssueOut
from report_works.api.services import Services
from report_works.domain import LayoutSettings
from report_works.domain.errors import (
    ConfigError,
    JobNotFoundError,
    JobNotReadyError,
    ReportError,
    TemplateError,
    UnsafePathError,
    UnsupportedFileError,
    UploadTooLargeError,
    WorkspaceNotFoundError,
)
from report_works.domain.validation import describe_error_items
from report_works.services.ports import ImageWriter
from report_works.services.report_builder import ReportBuilder, ValidationFailedError, WriterFactory

logger = logging.getLogger(__name__)

# Primeiro tipo que combinar vale; o restante dos erros de domínio é 400.
STATUS_BY_ERROR: tuple[tuple[type[ReportError], int], ...] = (
    (WorkspaceNotFoundError, 404),
    (JobNotFoundError, 404),
    (JobNotReadyError, 409),
    (UploadTooLargeError, 413),
    (UnsafePathError, 400),
    (UnsupportedFileError, 400),
    (ValidationFailedError, 422),
    (ConfigError, 422),
    (TemplateError, 422),
)


def default_writer_factory(layout: LayoutSettings) -> ImageWriter:
    """Escritor padrão: Excel via xlwings (Windows com Excel instalado)."""
    return XlwingsWriter(layout)


def _error_status(error: ReportError) -> int:
    return next((code for kind, code in STATUS_BY_ERROR if isinstance(error, kind)), 400)


def _error_body(error: ReportError) -> ErrorOut:
    if isinstance(error, ConfigError):
        return ErrorOut(detail=error.messages)
    if isinstance(error, ValidationFailedError):
        return ErrorOut(
            detail=[str(error)], issues=[IssueOut.from_issue(issue) for issue in error.issues]
        )
    return ErrorOut(detail=[str(error)])


def create_app(
    settings: Settings | None = None, writer_factory: WriterFactory | None = None
) -> FastAPI:
    """Monta a aplicação. `writer_factory` permite trocar o Excel por um escritor de teste."""
    settings = settings or Settings.from_env(detect_static=True)
    store = WorkspaceStore(settings.workdir, settings.max_upload_bytes, settings.rar_tool)
    store.purge_older_than(settings.retention_hours)
    runner = JobRunner(ReportBuilder(writer_factory or default_writer_factory), store)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        yield
        runner.shutdown()  # espera a geração em andamento e encerra a thread de trabalho

    app = FastAPI(title="Gerador de Relatórios Fotográficos", lifespan=lifespan)
    app.state.services = Services(settings=settings, store=store, runner=runner)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.exception_handler(ReportError)
    async def report_error_handler(_request: Request, error: ReportError) -> JSONResponse:
        body = _error_body(error)
        return JSONResponse(status_code=_error_status(error), content=body.model_dump())

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        body = ErrorOut(detail=describe_error_items(error.errors()))
        return JSONResponse(status_code=422, content=body.model_dump())

    app.include_router(router)
    if settings.static_dir is not None and settings.static_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="static")
    return app
