"""E2E real pela API: template + ZIP de fotos sintéticas -> geração no Excel -> download."""

import io
import re
import sys
import time
import zipfile
from pathlib import Path

import httpx
import yaml
from PIL import Image, ImageDraw

repo = Path(sys.argv[1])
base = sys.argv[2]
out = Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)

config = yaml.safe_load((repo / "config_exemple.yaml").read_text(encoding="utf-8"))
config.pop("paths", None)  # a API usa a área de trabalho, não caminhos do disco

sizes = [(1600, 1200), (1200, 1600), (2000, 900), (1000, 1000)]
archive = io.BytesIO()
count = 0
with zipfile.ZipFile(archive, "w") as z:
    for section in config["sections"]:
        total = section["max_photos"] if "num_pavimentos" not in section else sum(section["num_pavimentos"])
        for n in range(total):
            w, h = sizes[(count + n) % 4]
            image = Image.new("RGB", (w, h), (40 + (count * 31) % 180, 90, 150))
            draw = ImageDraw.Draw(image)
            draw.rectangle([6, 6, w - 7, h - 7], outline=(255, 255, 255), width=10)
            draw.line([0, 0, w, h], fill=(255, 255, 0), width=10)
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=88)
            z.writestr(f"Minha_Obra/{section['id']}/{n:03d}.jpg", buffer.getvalue())
            count += 1
print("fotos no ZIP:", count, "| tamanho do ZIP:", archive.tell(), "bytes")
archive.seek(0)

with httpx.Client(base_url=base, timeout=600) as client:
    workspace = client.post("/api/workspaces").json()["id"]
    with (repo / "templates" / "model.xlsx").open("rb") as handle:
        template = client.put(f"/api/workspaces/{workspace}/template", files={"file": ("model.xlsx", handle)})
    print("template:", template.status_code, [t["text"] for t in template.json()["titles"][:2]])
    zipped = client.post(f"/api/workspaces/{workspace}/photos/zip", files={"file": ("fotos.zip", archive)})
    print("zip:", zipped.status_code, zipped.json())
    validation = client.post(f"/api/workspaces/{workspace}/validate", json=config).json()
    print("validação: bloqueia =", validation["blocking"], "| problemas =", [(i["code"], i["severity"]) for i in validation["issues"]])
    job = client.post("/api/jobs", json={"workspace_id": workspace, "config": config}).json()
    started = time.perf_counter()
    last = ""
    with client.stream("GET", f"/api/jobs/{job['id']}/events") as events:
        for line in events.iter_lines():
            if line.startswith("data: "):
                import json

                payload = json.loads(line[6:])
                if payload["message"] != last and (payload["done"] % 25 == 0 or payload["state"] != "running"):
                    print(f"  {payload['state']:8} {payload['done']:>3}/{payload['total']:<3} {payload['percent']:.0%} {payload['message']}")
                last = payload["message"]
    final = client.get(f"/api/jobs/{job['id']}").json()
    print(f"estado final: {final['state']} em {time.perf_counter() - started:.1f}s | falhas={final['failures'][:2]} | erros={final['errors']}")
    download = client.get(final["download_url"])
    target = out / "api_report.xlsx"
    target.write_bytes(download.content)
    print("download:", download.status_code, len(download.content), "bytes")

with zipfile.ZipFile(target) as z:
    cells = []
    for part in [n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml", n)]:
        cells += re.findall(r'<c r="([A-Z]+\d+)"[^>]*\bvm="\d+"', z.read(part).decode("utf-8"))
print("imagens em célula no arquivo baixado:", len(cells))
