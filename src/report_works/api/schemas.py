"""Contratos JSON da API (entrada e saída), com tipos que o frontend gera a partir do OpenAPI."""

from pydantic import BaseModel

from report_works.api.jobs import JobSnapshot
from report_works.domain import ReportConfig
from report_works.domain.issues import ValidationIssue
from report_works.services.template_inspector import TemplateInfo


class WorkspaceOut(BaseModel):
    """Área de trabalho criada."""

    id: str


class TitleOut(BaseModel):
    """Texto encontrado na coluna de títulos do template."""

    row: int
    text: str


class TemplateSummary(BaseModel):
    """O que a interface precisa saber do template enviado."""

    sheets: list[str]
    sheet_name: str
    target_found: bool
    max_row: int
    titles: list[TitleOut]

    @classmethod
    def from_info(cls, info: TemplateInfo) -> "TemplateSummary":
        return cls(
            sheets=list(info.sheets),
            sheet_name=info.sheet_name,
            target_found=info.target_found,
            max_row=info.max_row,
            titles=[TitleOut(row=t.row, text=t.text) for t in info.titles],
        )


class UploadOut(BaseModel):
    """Resultado do envio de fotos soltas."""

    saved: int
    skipped: int


class ZipOut(BaseModel):
    """Resultado do envio de um ZIP: fotos por seção e arquivos ignorados."""

    sections: dict[str, int]
    skipped: int


class PhotoCountsOut(BaseModel):
    """Fotos guardadas por pasta de seção."""

    sections: dict[str, int]


class IssueOut(BaseModel):
    """Um problema de validação."""

    code: str
    severity: str
    message: str
    section_id: str | None = None

    @classmethod
    def from_issue(cls, issue: ValidationIssue) -> "IssueOut":
        return cls(
            code=issue.code,
            severity=str(issue.severity),
            message=issue.message,
            section_id=issue.section_id,
        )


class ValidationOut(BaseModel):
    """Resultado da validação prévia; `blocking` impede a geração."""

    issues: list[IssueOut]
    blocking: bool


class JobRequest(BaseModel):
    """Pedido de geração."""

    workspace_id: str
    config: ReportConfig


class JobOut(BaseModel):
    """Estado de uma tarefa de geração."""

    id: str
    workspace_id: str
    state: str
    done: int
    total: int
    percent: float
    message: str
    failures: list[str]
    issues: list[IssueOut]
    errors: list[str]
    download_url: str | None = None

    @classmethod
    def from_snapshot(cls, snapshot: JobSnapshot) -> "JobOut":
        ready = snapshot.output is not None and snapshot.state == "done"
        return cls(
            id=snapshot.id,
            workspace_id=snapshot.workspace_id,
            state=str(snapshot.state),
            done=snapshot.done,
            total=snapshot.total,
            percent=snapshot.percent,
            message=snapshot.message,
            failures=list(snapshot.failures),
            issues=[IssueOut.from_issue(i) for i in snapshot.issues],
            errors=list(snapshot.errors),
            download_url=f"/api/jobs/{snapshot.id}/download" if ready else None,
        )


class ErrorOut(BaseModel):
    """Corpo de erro: mensagens em português e, se houver, os problemas de validação."""

    detail: list[str]
    issues: list[IssueOut] = []
