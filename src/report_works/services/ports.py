"""Interfaces (portas) que os serviços usam para falar com o mundo externo."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Protocol, Self

from report_works.domain.layout import PhotoSlot


class ImageWriter(Protocol):
    """Insere fotos em uma cópia do template e grava o relatório.

    A implementação atual usa o Excel (xlwings); outras podem escrever o arquivo diretamente.
    """

    def open(self, template: Path, sheet_name: str | None) -> None:
        """Abre o template e seleciona a aba (a primeira, se `sheet_name` não existir)."""
        ...

    def insert(self, photo: Path, slot: PhotoSlot) -> None:
        """Insere uma foto na posição indicada; levanta `PhotoInsertError` em caso de falha."""
        ...

    def save(self, output: Path) -> None:
        """Grava o relatório no caminho indicado, criando as pastas necessárias."""
        ...

    def close(self) -> None:
        """Libera os recursos (fecha o Excel). Deve ser seguro chamar mais de uma vez."""
        ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
