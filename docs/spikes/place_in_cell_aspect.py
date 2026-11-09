"""Spike 3: proporção da imagem em célula (retrato e panorama) no template real (cópia)."""
import shutil
import sys
from pathlib import Path

import xlwings as xw
from PIL import Image, ImageDraw

out = Path(sys.argv[1]); template = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)


def make(name, size, color):
    image = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(image)
    draw.rectangle([4, 4, size[0] - 5, size[1] - 5], outline=(255, 255, 255), width=6)
    draw.line([0, 0, size[0], size[1]], fill=(255, 255, 0), width=8)  # diagonal revela distorção
    path = out / name
    image.save(path)
    return path


photos = {
    "B13": make("portrait.png", (600, 900), (40, 90, 200)),   # 2:3 retrato
    "D13": make("wide.png", (1600, 500), (30, 150, 70)),      # panorama 3.2:1
    "F13": make("square.png", (700, 700), (170, 60, 150)),    # 1:1
}
copy = out / "aspect.xlsx"
shutil.copy(template, copy)
app = xw.App(visible=False, add_book=False)
try:
    book = app.books.open(str(copy))
    sheet = book.sheets["Relatório fotográfico"]
    for address, photo in photos.items():
        cell = sheet.range(address)
        print(address, "área:", cell.api.MergeArea.Address, "largura pt:", round(cell.api.MergeArea.Width, 1), "altura pt:", round(cell.api.MergeArea.Height, 1))
        pic = sheet.pictures.add(str(photo), left=cell.left + 1, top=cell.top + 1, width=40, height=30)
        pic.api.Select()
        app.api.CommandBars.ExecuteMso("PicturePlaceInCell")
    sheet.api.ExportAsFixedFormat(0, str(out / "aspect.pdf"), 0, True, False, 1, 1)
    book.close(); 
finally:
    app.quit()
print("ok")
