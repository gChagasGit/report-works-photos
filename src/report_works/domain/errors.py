"""Erros de domínio. As mensagens já estão em português (ver `report_works.i18n`)."""


class ReportError(Exception):
    """Base de todos os erros esperados do gerador de relatórios."""


class ConfigError(ReportError):
    """A configuração do relatório é inválida; `messages` lista cada problema."""

    def __init__(self, messages: list[str]) -> None:
        super().__init__("; ".join(messages))
        self.messages = messages
