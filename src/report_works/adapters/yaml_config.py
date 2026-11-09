"""Leitura do `config.yaml` e validação com os modelos de domínio."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from report_works.domain import ConfigError, ReportConfig, describe_validation_errors
from report_works.i18n import pt_br


def parse_report_config(raw: object) -> ReportConfig:
    """Valida um dicionário (por exemplo, vindo do YAML ou do JSON da API)."""
    if not isinstance(raw, dict):
        raise ConfigError([pt_br.ERR_CONFIG_NOT_A_MAPPING])
    try:
        return ReportConfig.model_validate(raw)
    except ValidationError as error:
        raise ConfigError(describe_validation_errors(error)) from error


def load_report_config(path: Path) -> ReportConfig:
    """Lê e valida um arquivo de configuração YAML."""
    if not path.is_file():
        raise ConfigError([pt_br.ERR_CONFIG_FILE_NOT_FOUND.format(path=path)])
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ConfigError([pt_br.ERR_YAML_INVALID.format(detail=error)]) from error
    return parse_report_config(raw)
