"""Sobe o servidor: `uv run python -m report_works [--open]`.

A configuração vem de variáveis de ambiente (ver `report_works.adapters.settings`). Se a
interface estiver compilada em `frontend/dist`, ela é servida na mesma URL da API.
"""

import argparse
import threading
import webbrowser
from collections.abc import Sequence

import uvicorn

from report_works.adapters.settings import Settings
from report_works.i18n import pt_br

OPEN_DELAY_SECONDS = 1.5  # tempo para o servidor começar a responder antes de abrir o navegador


def build_parser() -> argparse.ArgumentParser:
    """Argumentos aceitos na linha de comando."""
    parser = argparse.ArgumentParser(prog="report_works", description=__doc__)
    parser.add_argument(
        "--open", action="store_true", dest="open_browser", help="abre o navegador ao iniciar"
    )
    return parser


def display_host(host: str) -> str:
    """Endereço que o usuário digita no navegador (0.0.0.0 não é um destino válido)."""
    return "127.0.0.1" if host in ("0.0.0.0", "::") else host


def main(argv: Sequence[str] | None = None) -> None:
    """Inicia o uvicorn com o host e a porta das configurações."""
    args = build_parser().parse_args(argv)
    settings = Settings.from_env(detect_static=True)
    url = f"http://{display_host(settings.host)}:{settings.port}"
    message = pt_br.MSG_SERVER_URL if settings.static_dir else pt_br.MSG_NO_FRONTEND
    print(message.format(url=url), flush=True)
    if args.open_browser and settings.static_dir:
        threading.Timer(OPEN_DELAY_SECONDS, webbrowser.open, args=[url]).start()
    uvicorn.run(
        "report_works.api.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )


if __name__ == "__main__":
    main()
