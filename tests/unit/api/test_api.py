"""Testes da API HTTP com um escritor falso (sem Excel)."""

import io
import json
import time
import zipfile
from collections.abc import Iterator
from itertools import pairwise
from pathlib import Path
from types import TracebackType
from typing import Any, ClassVar, Self

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from report_works.adapters.settings import Settings
from report_works.api.app import create_app
from report_works.domain import LayoutSettings
from report_works.domain.errors import PhotoInsertError
from report_works.domain.layout import PhotoSlot

ROOT = Path(__file__).parents[3]
MODEL = ROOT / "templates" / "model.xlsx"
SECTION = {"id": "entorno", "label": "Entorno da obra", "max_photos": 5}
CONFIG: dict[str, Any] = {"sections": [SECTION], "layout_settings": {"sort_method": "name"}}


class FakeWriter:
    """Grava um arquivo mínimo e registra as inserções."""

    fail_on: ClassVar[set[str]] = set()
    instances: ClassVar[list["FakeWriter"]] = []

    def __init__(self, _layout: LayoutSettings) -> None:
        self.inserted: list[str] = []
        FakeWriter.instances.append(self)

    def open(self, template: Path, sheet_name: str | None) -> None:
        self.template = template

    def insert(self, photo: Path, slot: PhotoSlot) -> None:
        if photo.name in self.fail_on:
            raise PhotoInsertError(f"falhou {photo.name}")
        self.inserted.append(f"{photo.name}@{slot.cell}")

    def save(self, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake-xlsx")

    def close(self) -> None:
        return None

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    FakeWriter.fail_on = set()
    FakeWriter.instances = []
    settings = Settings(workdir=tmp_path / "work", max_upload_mb=1)
    with TestClient(create_app(settings, FakeWriter)) as test_client:
        yield test_client


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4)).save(buffer, format="PNG")
    return buffer.getvalue()


def _workspace(client: TestClient) -> str:
    return client.post("/api/workspaces").json()["id"]


def _upload_template(client: TestClient, workspace: str) -> Any:
    with MODEL.open("rb") as handle:
        files = {"file": ("model.xlsx", handle, "application/octet-stream")}
        return client.put(f"/api/workspaces/{workspace}/template", files=files)


def _upload_photos(client: TestClient, workspace: str, count: int = 3) -> None:
    files = [("files", (f"{n}.png", _png(), "image/png")) for n in range(count)]
    response = client.post(f"/api/workspaces/{workspace}/photos/entorno", files=files)
    assert response.status_code == 200, response.text


def _wait(client: TestClient, job_id: str) -> dict[str, Any]:
    for _ in range(100):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["state"] in ("done", "failed"):
            return job
        time.sleep(0.05)
    raise AssertionError("a tarefa não terminou")


def test_health(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_template_upload_returns_sheets_and_titles(client: TestClient) -> None:
    workspace = _workspace(client)

    response = _upload_template(client, workspace)

    body = response.json()
    assert response.status_code == 200
    assert body["sheets"] == ["Sheet1", "Relatório fotográfico"]
    assert body["target_found"] is True
    assert {"row": 11, "text": "Entorno da obra"} in body["titles"]
    assert client.get(f"/api/workspaces/{workspace}/template").json() == body


def test_invalid_template_is_rejected_and_not_kept(client: TestClient) -> None:
    workspace = _workspace(client)

    response = client.put(
        f"/api/workspaces/{workspace}/template",
        files={"file": ("m.xlsx", b"nao e um xlsx", "application/octet-stream")},
    )

    assert response.status_code == 422
    assert "Não foi possível ler o template" in response.json()["detail"][0]
    assert client.get(f"/api/workspaces/{workspace}/template").status_code == 422


def test_template_with_wrong_extension_is_rejected(client: TestClient) -> None:
    workspace = _workspace(client)

    response = client.put(
        f"/api/workspaces/{workspace}/template", files={"file": ("m.txt", b"x", "text/plain")}
    )

    assert response.status_code == 400
    assert "não permitido" in response.json()["detail"][0]


def test_unknown_workspace_is_404_in_portuguese(client: TestClient) -> None:
    response = client.get(f"/api/workspaces/{'0' * 32}/photos")

    assert response.status_code == 404
    assert response.json()["detail"] == ["Área de trabalho não encontrada."]


def test_photo_uploads_by_section_and_by_zip(client: TestClient) -> None:
    workspace = _workspace(client)
    _upload_photos(client, workspace, 2)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("obra/geral_obra/a.png", _png())
        z.writestr("leia.txt", "x")
    archive.seek(0)

    zipped = client.post(
        f"/api/workspaces/{workspace}/photos/zip",
        files={"file": ("f.zip", archive, "application/zip")},
    )

    assert zipped.json() == {"sections": {"geral_obra": 1}, "skipped": 1}
    counts = client.get(f"/api/workspaces/{workspace}/photos").json()
    assert counts == {"sections": {"entorno": 2, "geral_obra": 1}}


def test_unsafe_zip_and_section_id_are_rejected(client: TestClient) -> None:
    workspace = _workspace(client)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("../evil/a.png", _png())
    archive.seek(0)

    zipped = client.post(
        f"/api/workspaces/{workspace}/photos/zip",
        files={"file": ("f.zip", archive, "application/zip")},
    )
    bad_section = client.post(
        f"/api/workspaces/{workspace}/photos/..%2Fx",
        files=[("files", ("a.png", _png(), "image/png"))],
    )

    assert zipped.status_code == 400 and "inseguro" in zipped.json()["detail"][0]
    assert bad_section.status_code in (400, 404)
    assert not list(Path(client.app.state.services.settings.workdir).rglob("evil*"))  # type: ignore[attr-defined]


def test_upload_over_the_limit_is_413(client: TestClient) -> None:
    workspace = _workspace(client)
    big = b"x" * (1024 * 1024 + 1)

    response = client.put(
        f"/api/workspaces/{workspace}/template", files={"file": ("m.xlsx", big, "application/zip")}
    )

    assert response.status_code == 413
    assert response.json()["detail"] == ["O envio excede o limite de 1 MB."]


def test_validate_reports_issues_and_blocking(client: TestClient) -> None:
    workspace = _workspace(client)
    _upload_template(client, workspace)

    missing_folder = client.post(f"/api/workspaces/{workspace}/validate", json=CONFIG).json()
    _upload_photos(client, workspace, 3)
    ready = client.post(f"/api/workspaces/{workspace}/validate", json=CONFIG).json()

    assert missing_folder["blocking"] is True
    assert missing_folder["issues"][0]["code"] == "folder_missing"
    assert ready["blocking"] is False
    assert [i["code"] for i in ready["issues"]] == ["fewer_photos"]  # 3 fotos, max 5


def test_validate_without_template_is_422(client: TestClient) -> None:
    response = client.post(f"/api/workspaces/{_workspace(client)}/validate", json=CONFIG)

    assert response.status_code == 422
    assert response.json()["detail"] == ["Envie o template Excel antes de continuar."]


def test_invalid_config_is_422_with_portuguese_messages(client: TestClient) -> None:
    workspace = _workspace(client)
    bad = {"sections": [{"id": "Entorno", "label": "", "max_photos": 0}]}

    response = client.post(f"/api/workspaces/{workspace}/validate", json=bad)

    assert response.status_code == 422
    messages = response.json()["detail"]
    assert "sections.0.id: formato inválido" in messages
    assert "sections.0.label: não pode ficar vazio" in messages
    assert "sections.0.max_photos: deve ser maior ou igual a 1" in messages


def test_full_flow_generates_and_downloads_the_report(client: TestClient) -> None:
    workspace = _workspace(client)
    _upload_template(client, workspace)
    _upload_photos(client, workspace, 5)

    created = client.post("/api/jobs", json={"workspace_id": workspace, "config": CONFIG})
    job = _wait(client, created.json()["id"])
    download = client.get(job["download_url"])

    assert created.status_code == 202
    assert job["state"] == "done" and job["percent"] == 1.0
    assert (job["done"], job["total"]) == (5, 5)
    assert job["failures"] == [] and job["errors"] == []
    assert FakeWriter.instances[0].inserted[0] == "0.png@B13"
    assert download.status_code == 200 and download.content == b"fake-xlsx"
    assert "relatorio.xlsx" in download.headers["content-disposition"]


def test_photo_failures_are_reported_but_the_job_finishes(client: TestClient) -> None:
    workspace = _workspace(client)
    _upload_template(client, workspace)
    _upload_photos(client, workspace, 5)
    FakeWriter.fail_on = {"2.png"}

    job = _wait(
        client,
        client.post("/api/jobs", json={"workspace_id": workspace, "config": CONFIG}).json()["id"],
    )

    assert job["state"] == "done"
    assert job["failures"] == ["falhou 2.png"]


def test_job_with_blocking_problems_fails_with_issues(client: TestClient) -> None:
    workspace = _workspace(client)
    _upload_template(client, workspace)  # sem fotos

    job = _wait(
        client,
        client.post("/api/jobs", json={"workspace_id": workspace, "config": CONFIG}).json()["id"],
    )

    assert job["state"] == "failed"
    assert job["errors"] == ["Há problemas que impedem a geração do relatório."]
    assert job["issues"][0]["code"] == "folder_missing"
    assert job["download_url"] is None
    assert client.get(f"/api/jobs/{job['id']}/download").status_code == 409


def test_job_without_template_is_refused_up_front(client: TestClient) -> None:
    response = client.post("/api/jobs", json={"workspace_id": _workspace(client), "config": CONFIG})

    assert response.status_code == 422


def test_unknown_job_is_404(client: TestClient) -> None:
    assert client.get("/api/jobs/naoexiste").status_code == 404
    assert client.get("/api/jobs/naoexiste/events").status_code == 404
    assert client.get("/api/jobs/naoexiste/download").status_code == 404


def test_progress_is_streamed_as_server_sent_events(client: TestClient) -> None:
    workspace = _workspace(client)
    _upload_template(client, workspace)
    _upload_photos(client, workspace, 5)
    job_id = client.post("/api/jobs", json={"workspace_id": workspace, "config": CONFIG}).json()[
        "id"
    ]

    with client.stream("GET", f"/api/jobs/{job_id}/events") as response:
        payloads = [
            json.loads(line.removeprefix("data: "))
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]

    assert response.headers["content-type"].startswith("text/event-stream")
    assert payloads[-1]["state"] == "done" and payloads[-1]["percent"] == 1.0
    assert all(a["done"] <= b["done"] for a, b in pairwise(payloads))


def test_cors_is_only_enabled_for_configured_origins(tmp_path: Path) -> None:
    settings = Settings(workdir=tmp_path / "w", cors_origins=("http://localhost:5173",))
    with TestClient(create_app(settings, FakeWriter)) as cors_client:
        allowed = cors_client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        denied = cors_client.get("/api/health", headers={"Origin": "http://evil.test"})

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers


def test_static_frontend_is_served_when_configured(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>ok</h1>", encoding="utf-8")
    settings = Settings(workdir=tmp_path / "w", static_dir=dist)

    with TestClient(create_app(settings, FakeWriter)) as static_client:
        assert static_client.get("/").text == "<h1>ok</h1>"
        assert static_client.get("/api/health").json() == {"status": "ok"}
