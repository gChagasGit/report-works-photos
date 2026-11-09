"""Testes das configurações por ambiente e do armazenamento de áreas de trabalho."""

import io
import os
import time
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from report_works.adapters.settings import Settings
from report_works.adapters.workspace_store import WorkspaceStore
from report_works.domain.errors import (
    SettingError,
    UnsafePathError,
    UnsupportedFileError,
    UploadTooLargeError,
    WorkspaceNotFoundError,
)


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4)).save(buffer, format="PNG")
    return buffer.getvalue()


def _zip(entries: dict[str, bytes]) -> io.BytesIO:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    buffer.seek(0)
    return buffer


@pytest.fixture
def store(tmp_path: Path) -> WorkspaceStore:
    return WorkspaceStore(tmp_path / "work", max_upload_bytes=1024 * 1024)


# --- Settings -------------------------------------------------------------------------


def test_settings_defaults_when_environment_is_empty() -> None:
    settings = Settings.from_env({})

    assert settings.workdir == Path("work")
    assert settings.max_upload_mb == 2048
    assert settings.max_upload_bytes == 2048 * 1024 * 1024
    assert settings.cors_origins == ()
    assert settings.static_dir is None
    assert (settings.host, settings.port, settings.retention_hours) == ("127.0.0.1", 8000, 24)


def test_settings_read_every_variable() -> None:
    settings = Settings.from_env(
        {
            "REPORT_WORKDIR": "/data",
            "REPORT_MAX_UPLOAD_MB": "10",
            "CORS_ORIGINS": " http://a.test , http://b.test,, ",
            "REPORT_STATIC_DIR": "/app/dist",
            "REPORT_HOST": "0.0.0.0",
            "REPORT_PORT": "9000",
            "REPORT_RETENTION_HOURS": "2",
        }
    )

    assert settings.workdir == Path("/data")
    assert settings.max_upload_mb == 10
    assert settings.cors_origins == ("http://a.test", "http://b.test")
    assert settings.static_dir == Path("/app/dist")
    assert (settings.host, settings.port, settings.retention_hours) == ("0.0.0.0", 9000, 2)


@pytest.mark.parametrize("value", ["abc", "0", "-5", "1.5"])
def test_invalid_numbers_are_reported_in_portuguese(value: str) -> None:
    with pytest.raises(SettingError, match="REPORT_MAX_UPLOAD_MB"):
        Settings.from_env({"REPORT_MAX_UPLOAD_MB": value})


def test_settings_from_the_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPORT_PORT", "1234")

    assert Settings.from_env().port == 1234
    assert os.environ["REPORT_PORT"] == "1234"


# --- WorkspaceStore --------------------------------------------------------------------


def test_workspace_ids_are_validated(store: WorkspaceStore) -> None:
    workspace = store.create()

    assert store.workspace(workspace).is_dir()
    for bad in ["", "../x", "ZZZ", "a" * 31, workspace.upper(), f"{workspace}/.."]:
        with pytest.raises(WorkspaceNotFoundError):
            store.workspace(bad)


def test_template_must_be_xlsx_and_replaces_the_previous(store: WorkspaceStore) -> None:
    workspace = store.create()

    with pytest.raises(UnsupportedFileError, match="não permitido"):
        store.save_template(workspace, io.BytesIO(b"x"), "modelo.xls")
    path = store.save_template(workspace, io.BytesIO(b"one"), "..\\..\\modelo.xlsx")
    store.save_template(workspace, io.BytesIO(b"two"), "modelo.xlsx")

    assert path == store.template_path(workspace)
    assert path.read_bytes() == b"two"


def test_upload_over_the_limit_is_refused_and_leaves_no_partial_file(tmp_path: Path) -> None:
    small = WorkspaceStore(tmp_path / "w", max_upload_bytes=10)
    workspace = small.create()

    with pytest.raises(UploadTooLargeError, match="limite de 0 MB"):
        small.save_template(workspace, io.BytesIO(b"x" * 11), "m.xlsx")

    assert not small.template_path(workspace).exists()


def test_photos_are_saved_by_section_and_other_types_are_skipped(store: WorkspaceStore) -> None:
    workspace = store.create()

    summary = store.save_photos(
        workspace,
        "entorno",
        [
            ("a.JPG", io.BytesIO(_png_bytes())),
            ("../../evil.png", io.BytesIO(_png_bytes())),
            ("notes.txt", io.BytesIO(b"x")),
            ("", io.BytesIO(b"x")),
        ],
    )

    folder = store.photos_dir(workspace) / "entorno"
    assert (summary.saved, summary.skipped) == (2, 2)
    assert sorted(p.name for p in folder.iterdir()) == ["a.JPG", "evil.png"]
    assert store.count_by_section(workspace) == {"entorno": 2}


@pytest.mark.parametrize("section_id", ["../x", "Entorno", "a b", "", "a/b", ".."])
def test_invalid_section_ids_are_refused(store: WorkspaceStore, section_id: str) -> None:
    workspace = store.create()

    with pytest.raises(UnsafePathError, match="Identificador"):
        store.save_photos(workspace, section_id, [("a.png", io.BytesIO(_png_bytes()))])


def test_zip_uses_the_parent_folder_as_the_section_id(store: WorkspaceStore) -> None:
    workspace = store.create()
    png = _png_bytes()
    archive = _zip(
        {
            "Minha_Obra/entorno/1.png": png,
            "Minha_Obra/Geral_Obra/2.jpg": png,
            "solto.png": png,
            "entorno/leia.txt": b"x",
            "Minha Obra/pasta com espaco/3.png": png,
        }
    )

    sections, skipped = store.save_zip(workspace, archive)

    assert sections == {"entorno": 1, "geral_obra": 1}
    assert skipped == 3
    assert (store.photos_dir(workspace) / "geral_obra" / "2.jpg").is_file()


@pytest.mark.parametrize(
    "name",
    [
        "../evil/a.png",
        "/abs/entorno/a.png",
        "C:/x/entorno/a.png",
        "a/../../b.png",
        "entorno/a:b.png",
    ],
)
def test_zip_with_unsafe_paths_is_refused(store: WorkspaceStore, name: str) -> None:
    workspace = store.create()

    with pytest.raises(UnsupportedFileError, match="inseguro"):
        store.save_zip(workspace, _zip({name: _png_bytes()}))

    assert not any(store.photos_dir(workspace).rglob("*.png"))


def test_zip_that_is_not_a_zip_is_refused(store: WorkspaceStore) -> None:
    with pytest.raises(UnsupportedFileError, match="ZIP é inválido"):
        store.save_zip(store.create(), io.BytesIO(b"not a zip"))


def test_zip_total_size_is_limited_while_extracting(tmp_path: Path) -> None:
    small = WorkspaceStore(tmp_path / "w", max_upload_bytes=100)
    workspace = small.create()
    archive = _zip({"entorno/a.png": b"x" * 80, "entorno/b.png": b"x" * 80})

    with pytest.raises(UploadTooLargeError):
        small.save_zip(workspace, archive)


def test_purge_removes_only_old_workspaces(store: WorkspaceStore, tmp_path: Path) -> None:
    old, recent = store.create(), store.create()
    old_path = store.workspace(old)
    past = time.time() - 3 * 3600
    os.utime(old_path, (past, past))

    assert store.purge_older_than(2) == 1
    assert not old_path.exists() and store.workspace(recent).is_dir()
