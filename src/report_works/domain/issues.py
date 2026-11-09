"""Problemas encontrados na validação prévia (antes de gerar o relatório)."""

from dataclasses import dataclass
from enum import StrEnum


class IssueSeverity(StrEnum):
    """ERROR impede a geração; WARNING só informa."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ValidationIssue:
    """Um problema legível. `code` é estável para a interface decidir o tratamento."""

    code: str
    severity: IssueSeverity
    message: str
    section_id: str | None = None
