"""Spike 2: tempo, Excel invisível, célula de destino e template real (cópia descartável)."""

import re
import shutil
import sys
import time
import traceback
import zipfile
from pathlib import Path

import xlwings as xw
from PIL import Image

out = Path(sys.argv[1])
template_src = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
png = out / "photo.png"
Image.new("RGB", (800, 600), (200, 60, 60)).save(png)


def vm_cells(xlsx: Path, sheet_part: str) -> list[str]:
    with zipfile.ZipFile(xlsx) as z:
        xml = z.read(sheet_part).decode("utf-8")
    return re.findall(r'<c r="([A-Z]+\d+)"[^>]*\bvm="\d+"', xml)


def place(app, sheet, cell) -> None:
    pic = sheet.pictures.add(str(png), left=cell.left + 1, top=cell.top + 1, width=60, height=45)
    pic.api.Select()
    app.api.CommandBars.ExecuteMso("PicturePlaceInCell")


# --- A) Excel INVISÍVEL ---------------------------------------------------------------
app = xw.App(visible=False, add_book=False)
try:
    book = app.books.add()
    sheet = book.sheets[0]
    try:
        place(app, sheet, sheet.range("B3"))
        print("A) invisível: shapes depois =", sheet.api.Shapes.Count)
    except Exception as error:
        print("A) invisível: FALHOU ->", type(error).__name__, str(error)[:120])
    book.close()
finally:
    app.quit()
time.sleep(3)

# --- B) visível: tempo para 20 fotos + célula de destino ------------------------------
app = xw.App(visible=True, add_book=False)
try:
    book = app.books.add()
    sheet = book.sheets[0]
    sheet.range("A1:A40").row_height = 60
    start = time.perf_counter()
    for row in range(1, 21):
        place(app, sheet, sheet.range(f"A{row}"))
    elapsed = time.perf_counter() - start
    print(f"B) 20 fotos em {elapsed:.2f}s ({elapsed / 20:.3f}s por foto); shapes restantes =", sheet.api.Shapes.Count)
    # imagem grande cujo canto superior esquerdo está em C5 mas que cobre C5:E8
    sheet.range("C5:E8").row_height = 40
    big = sheet.pictures.add(str(png), left=sheet.range("C5").left + 1, top=sheet.range("C5").top + 1, width=300, height=200)
    big.api.Select()
    app.api.CommandBars.ExecuteMso("PicturePlaceInCell")
    path_b = out / "b.xlsx"
    if path_b.exists():
        path_b.unlink()
    book.save(str(path_b))
    book.close()
finally:
    app.quit()
cells = vm_cells(path_b, "xl/worksheets/sheet1.xml")
print("B) células com imagem:", len(cells), "| inclui C5:", "C5" in cells, "| outras na área C5:E8:", [c for c in cells if c[0] in "CDE"])
time.sleep(3)

# --- C) template real (cópia): bloco mesclado B13:B22 -----------------------------------
copy = out / "model_copy.xlsx"
shutil.copy(template_src, copy)
app = xw.App(visible=True, add_book=False)
try:
    book = app.books.open(str(copy))
    sheet = book.sheets["Relatório fotográfico"]
    print("C) B13 mesclada:", sheet.range("B13").api.MergeCells, "área:", sheet.range("B13").api.MergeArea.Address)
    for address in ("B13", "D13", "F13"):
        place(app, sheet, sheet.range(address))
    print("C) shapes restantes na aba (inclui a imagem do template):", sheet.api.Shapes.Count)
    path_c = out / "c.xlsx"
    if path_c.exists():
        path_c.unlink()
    book.save(str(path_c))
    book.close()
finally:
    app.quit()
with zipfile.ZipFile(path_c) as z:
    sheets = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet")]
    print("C) partes richData:", sorted(n for n in z.namelist() if "richData" in n)[:3], "...")
    for part in sheets:
        found = re.findall(r'<c r="([A-Z]+\d+)"[^>]*\bvm="\d+"', z.read(part).decode("utf-8"))
        if found:
            print("C) células com imagem em", part, "->", found)
print("C) tamanho do arquivo:", path_c.stat().st_size, "bytes (modelo original:", template_src.stat().st_size, ")")
