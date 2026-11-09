"""Objetos compartilhados pelas rotas (criados uma vez por aplicação)."""

from dataclasses import dataclass

from report_works.adapters.settings import Settings
from report_works.adapters.workspace_store import WorkspaceStore
from report_works.api.jobs import JobRunner


@dataclass(frozen=True)
class Services:
    """Configuração, armazenamento e executor de tarefas da aplicação."""

    settings: Settings
    store: WorkspaceStore
    runner: JobRunner
