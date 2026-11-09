"""Exporta o contrato OpenAPI para o frontend gerar seus tipos.

Uso: `uv run python -m report_works.export_openapi frontend/openapi.json`
"""

import json
import sys
import tempfile
from pathlib import Path

from report_works.adapters.settings import Settings
from report_works.api.app import create_app

MSG_USAGE = "Uso: python -m report_works.export_openapi <saida.json>"
MSG_WRITTEN = "Contrato OpenAPI gravado em {path}"


def build_openapi() -> dict[str, object]:
    """Gera o esquema OpenAPI da aplicação (sem tocar na pasta de trabalho real)."""
    with tempfile.TemporaryDirectory(prefix="report_works_openapi_") as workdir:
        return create_app(Settings(workdir=Path(workdir))).openapi()


def render_openapi() -> str:
    """Texto JSON estável (chaves em ordem, UTF-8, quebra de linha final)."""
    return json.dumps(build_openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str]) -> int:
    """Grava o contrato no arquivo informado."""
    if len(argv) != 1:
        print(MSG_USAGE, file=sys.stderr)
        return 2
    target = Path(argv[0])
    target.write_text(render_openapi(), encoding="utf-8", newline="\n")
    print(MSG_WRITTEN.format(path=target))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
