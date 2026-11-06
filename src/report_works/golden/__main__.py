"""Uso: python -m report_works.golden <relatorio.xlsx> <saida.json>."""

import sys
from pathlib import Path

from report_works.golden.anchors import extract_anchors, save_anchors

MSG_USAGE = "Uso: python -m report_works.golden <relatorio.xlsx> <saida.json>"
MSG_WRITTEN = "{count} imagens gravadas em {path}"


def main(argv: list[str]) -> int:
    """Extrai as âncoras de um .xlsx e grava o JSON de referência."""
    if len(argv) != 2:
        print(MSG_USAGE, file=sys.stderr)
        return 2
    source, target = Path(argv[0]), Path(argv[1])
    pictures = extract_anchors(source)
    save_anchors(pictures, target)
    print(MSG_WRITTEN.format(count=len(pictures), path=target))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
