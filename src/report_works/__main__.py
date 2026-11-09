"""Sobe o servidor: `uv run python -m report_works` (configuração por variáveis de ambiente)."""

import uvicorn

from report_works.adapters.settings import Settings


def main() -> None:
    """Inicia o uvicorn com o host e a porta das configurações."""
    settings = Settings.from_env()
    uvicorn.run(
        "report_works.api.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )


if __name__ == "__main__":
    main()
