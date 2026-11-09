"""Spike descartável: "Colocar na Célula" via COM (CommandBars.ExecuteMso).

Gera um .xlsx de teste e imprime o que o Excel respondeu. Não toca no repositório.
"""

import sys
import time
import traceback
import zipfile
from pathlib import Path

import xlwings as xw
from PIL import Image

out_dir = Path(sys.argv[1])
out_dir.mkdir(parents=True, exist_ok=True)
png = out_dir / "photo.png"
Image.new("RGB", (800, 600), (30, 120, 200)).save(png)
result = out_dir / "com_result.xlsx"
if result.exists():
    result.unlink()

app = xw.App(visible=True, add_book=False)
try:
    print("Excel", app.api.Version, "build", app.api.Build)
    book = app.books.add()
    sheet = book.sheets[0]

    # Caso 1: célula simples D3
    sheet.range("D3").row_height = 120
    sheet.range("D3").column_width = 30
    # Caso 2: área mesclada F3:F12 (como os blocos do template)
    sheet.range("F3:F12").api.Merge()
    sheet.range("F3").column_width = 30

    cases = {"D3": sheet.range("D3"), "F3(mesclada)": sheet.range("F3")}
    for label, cell in cases.items():
        before = sheet.api.Shapes.Count
        pic = sheet.pictures.add(str(png), left=cell.left + 2, top=cell.top + 2, width=100, height=75)
        print(f"[{label}] shapes antes={before} depois_de_adicionar={sheet.api.Shapes.Count}")
        try:
            pic.api.Select()
            app.api.CommandBars.ExecuteMso("PicturePlaceInCell")
            time.sleep(1.5)
            print(f"[{label}] ExecuteMso OK; shapes agora={sheet.api.Shapes.Count}")
        except Exception:
            print(f"[{label}] ExecuteMso FALHOU:")
            traceback.print_exc(limit=2)

    book.save(str(result))
    book.close()
finally:
    app.quit()

print("--- partes do pacote relacionadas a imagem em célula")
with zipfile.ZipFile(result) as z:
    names = [n for n in z.namelist() if "richData" in n or "metadata" in n or "drawing" in n or "media" in n]
    print(names)
    sheet_xml = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    import re

    print("células com vm=:", re.findall(r'<c r="([A-Z]+\d+)"[^>]*\bvm="(\d+)"', sheet_xml))
