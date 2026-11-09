"""Erros de domínio. As mensagens já estão em português (ver `report_works.i18n`)."""


class ReportError(Exception):
    """Base de todos os erros esperados do gerador de relatórios."""


class FolderNotFoundError(ReportError):
    """A pasta de fotos de uma seção não existe."""


class UnsafePathError(ReportError):
    """Um identificador tentou sair da pasta raiz de fotos (por exemplo, `../`)."""


class TemplateError(ReportError):
    """O template Excel não pôde ser lido."""


class ConfigError(ReportError):
    """A configuração do relatório é inválida; `messages` lista cada problema."""

    def __init__(self, messages: list[str]) -> None:
        super().__init__("; ".join(messages))
        self.messages = messages
