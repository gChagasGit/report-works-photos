"""Preparação de fotos para o modo "Colocar na Célula".

O Excel estica a imagem em célula até preencher o bloco (comprovado no spike, ver
`docs/spikes/place-in-cell.md`). Por isso a foto é enquadrada aqui, na proporção exata do bloco,
com margens brancas (equivale ao "ajustar à caixa" do fluxo antigo), e reduzida ao tamanho útil.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

BACKGROUND = (255, 255, 255)
JPEG_QUALITY = 85


def box_pixels(block_width: float, block_height: float, max_px: int) -> tuple[int, int]:
    """Tamanho em pixels da caixa com a proporção do bloco e o maior lado igual a `max_px`."""
    if block_width >= block_height:
        return max_px, max(1, round(max_px * block_height / block_width))
    return max(1, round(max_px * block_width / block_height)), max_px


def prepare_for_cell(
    photo: Path, output: Path, block_width: float, block_height: float, max_px: int
) -> tuple[int, int]:
    """Grava em `output` (JPEG) a foto centralizada numa caixa da proporção do bloco.

    Aplica a rotação EXIF antes de medir, o que também corrige fotos de celular de lado.
    Retorna o tamanho final (largura, altura) em pixels.
    """
    width, height = box_pixels(block_width, block_height, max_px)
    with Image.open(photo) as source:
        upright = ImageOps.exif_transpose(source)
        fitted = ImageOps.contain(upright.convert("RGB"), (width, height))
    canvas = Image.new("RGB", (width, height), BACKGROUND)
    canvas.paste(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))
    canvas.save(output, format="JPEG", quality=JPEG_QUALITY)
    return width, height
