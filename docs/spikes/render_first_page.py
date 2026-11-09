"""Exporta a primeira página do arquivo para PDF (para inspeção visual do spike)."""
import sys
import xlwings as xw

source, target = sys.argv[1], sys.argv[2]
app = xw.App(visible=False, add_book=False)
try:
    book = app.books.open(source)
    sheet = book.sheets["Relatório fotográfico"]
    sheet.api.ExportAsFixedFormat(0, target, 0, True, False, 1, 1)
    book.close()
finally:
    app.quit()
print("ok", target)
