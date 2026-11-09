"""Resultado do planejamento: onde cada foto vai na planilha."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PhotoSlot:
    """Posição de uma foto: célula de ancoragem e quantas linhas o bloco ocupa."""

    section_id: str
    photo_index: int  # posição da foto dentro da seção (0 = primeira)
    column: str
    row: int
    row_span: int
    fix_width: bool
    group_index: int | None = None  # grupo (andar) em seções agrupadas

    @property
    def cell(self) -> str:
        """Endereço A1 da célula de ancoragem, por exemplo `B13`."""
        return f"{self.column}{self.row}"

    @property
    def last_row(self) -> int:
        """Última linha ocupada pelo bloco."""
        return self.row + self.row_span - 1


@dataclass(frozen=True)
class LayoutPlan:
    """Todas as posições do relatório, na ordem de inserção."""

    slots: tuple[PhotoSlot, ...]

    def for_section(self, section_id: str) -> tuple[PhotoSlot, ...]:
        """Posições de uma seção, na ordem das fotos."""
        return tuple(slot for slot in self.slots if slot.section_id == section_id)

    @property
    def total(self) -> int:
        """Quantidade de fotos que serão inseridas (denominador do progresso)."""
        return len(self.slots)
