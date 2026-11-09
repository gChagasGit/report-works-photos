"""Regras e modelos do domínio; não importa I/O, HTTP nem Excel."""

from report_works.domain.errors import ConfigError, ReportError
from report_works.domain.models import (
    LayoutSettings,
    PathsConfig,
    ProjectMetadata,
    ReportConfig,
    SectionConfig,
    SectionKind,
    SortMethod,
)
from report_works.domain.validation import describe_validation_errors

__all__ = [
    "ConfigError",
    "LayoutSettings",
    "PathsConfig",
    "ProjectMetadata",
    "ReportConfig",
    "ReportError",
    "SectionConfig",
    "SectionKind",
    "SortMethod",
    "describe_validation_errors",
]
