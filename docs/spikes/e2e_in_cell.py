"""E2E real (Excel): plano do exemplo + XlwingsWriter em modo na célula, fotos sintéticas."""

import re
import sys
import time
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

from report_works.adapters.xlwings_writer import XlwingsWriter
from report_works.adapters.yaml_config import load_report_config
from report_works.services.layout_planner import plan_layout, section_anchors
from report_works.services.template_inspector import inspect_template

repo = Path(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
photos_dir = out / "photos"
photos_dir.mkdir(exist_ok=True)

config = load_report_config(repo / "config_exemple.yaml")
model = repo / "templates" / "model.xlsx"
info = inspect_template(model, config.metadata.target_sheet)
anchors = section_anchors(config, info)
plan = plan_layout(config, anchors, {s.id: s.slot_capacity for s in config.sections})
print("slots planejados:", plan.total)

sizes = [(1600, 1200), (1200, 1600), (2000, 900), (1000, 1000)]  # 4:3, 3:4, panorama, 1:1


def make_photo(index: int, label: str) -> Path:
    width, height = sizes[index % len(sizes)]
    image = Image.new("RGB", (width, height), (40 + (index * 37) % 180, 90, 160))
    draw = ImageDraw.Draw(image)
    draw.rectangle([6, 6, width - 7, height - 7], outline=(255, 255, 255), width=10)
    draw.line([0, 0, width, height], fill=(255, 255, 0), width=10)
    draw.text((width // 2 - 60, height // 2), label, fill=(255, 255, 255))
    path = photos_dir / f"p{index:03d}.jpg"
    image.save(path, quality=90)
    return path


report = out / "report_in_cell.xlsx"
if report.exists():
    report.unlink()
errors: list[str] = []
started = time.perf_counter()
with XlwingsWriter(config.layout, visible=False) as writer:
    writer.open(model, config.metadata.target_sheet)
    for index, slot in enumerate(plan.slots):
        try:
            writer.insert(make_photo(index, f"{slot.section_id} {slot.cell}"), slot)
        except Exception as error:
            errors.append(f"{slot.cell}: {error}")
    writer.save(report)
elapsed = time.perf_counter() - started
print(f"inserção + salvar: {elapsed:.1f}s, erros: {len(errors)}", errors[:3])
print("tamanho do arquivo:", report.stat().st_size, "bytes")

with zipfile.ZipFile(report) as z:
    sheet_parts = [n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml", n)]
    cells: list[str] = []
    for part in sheet_parts:
        cells += re.findall(r'<c r="([A-Z]+\d+)"[^>]*\bvm="\d+"', z.read(part).decode("utf-8"))
    drawings = [n for n in z.namelist() if n.startswith("xl/drawings/drawing") and n.endswith(".xml")]
    pics = sum(z.read(d).decode("utf-8").count("<xdr:pic>") for d in drawings)
planned = {slot.cell for slot in plan.slots}
print("células com imagem na célula:", len(cells), "| iguais ao plano:", set(cells) == planned)
print("faltando:", sorted(planned - set(cells))[:5], "| sobrando:", sorted(set(cells) - planned)[:5])
print("imagens flutuantes restantes (logo do template):", pics)
