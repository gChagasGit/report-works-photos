"""Configuração do servidor por variáveis de ambiente (pronta para Docker).

| Variável                | Padrão          | Significado                                        |
|-------------------------|-----------------|----------------------------------------------------|
| REPORT_WORKDIR          | ./work          | pasta onde ficam envios e relatórios               |
| REPORT_MAX_UPLOAD_MB    | 2048            | limite de cada envio (arquivo, lote de fotos ou ZIP)|
| CORS_ORIGINS            | (vazio)         | origens permitidas, separadas por vírgula           |
| REPORT_STATIC_DIR       | (vazio)         | pasta do frontend compilado, servida em `/`        |
| REPORT_HOST / REPORT_PORT | 127.0.0.1 / 8000 | endereço do servidor                             |
| REPORT_RETENTION_HOURS  | 24              | tempo de guarda das áreas de trabalho              |
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from report_works.domain.errors import SettingError
from report_works.i18n import pt_br

BYTES_PER_MB = 1024 * 1024
DEFAULT_STATIC_DIR = Path("frontend") / "dist"

# Variáveis lidas por `Settings.from_env` (um teste confere Docker e compose contra esta lista).
ENV_VARIABLES = (
    "REPORT_WORKDIR",
    "REPORT_MAX_UPLOAD_MB",
    "CORS_ORIGINS",
    "REPORT_STATIC_DIR",
    "REPORT_HOST",
    "REPORT_PORT",
    "REPORT_RETENTION_HOURS",
)


def _positive_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value < 1:
        raise SettingError(pt_br.ERR_SETTING_INVALID.format(name=name, value=raw))
    return value


@dataclass(frozen=True)
class Settings:
    """Parâmetros de execução do servidor."""

    workdir: Path = Path("work")
    max_upload_mb: int = 2048
    cors_origins: tuple[str, ...] = ()
    static_dir: Path | None = None
    host: str = "127.0.0.1"
    port: int = 8000
    retention_hours: int = 24

    @property
    def max_upload_bytes(self) -> int:
        """Limite de cada envio, em bytes."""
        return self.max_upload_mb * BYTES_PER_MB

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None, *, detect_static: bool = False) -> Self:
        """Lê as variáveis de ambiente (ou do mapeamento informado, útil em testes).

        Com `detect_static`, usa `frontend/dist` (relativo à pasta atual) quando
        `REPORT_STATIC_DIR` não foi informado e a interface já foi compilada.
        """
        source = os.environ if env is None else env
        origins = tuple(o.strip() for o in source.get("CORS_ORIGINS", "").split(",") if o.strip())
        static = source.get("REPORT_STATIC_DIR", "").strip()
        if not static and detect_static and (DEFAULT_STATIC_DIR / "index.html").is_file():
            static = str(DEFAULT_STATIC_DIR)
        return cls(
            workdir=Path(source.get("REPORT_WORKDIR", "").strip() or "work"),
            max_upload_mb=_positive_int(source, "REPORT_MAX_UPLOAD_MB", 2048),
            cors_origins=origins,
            static_dir=Path(static) if static else None,
            host=source.get("REPORT_HOST", "").strip() or "127.0.0.1",
            port=_positive_int(source, "REPORT_PORT", 8000),
            retention_hours=_positive_int(source, "REPORT_RETENTION_HOURS", 24),
        )
