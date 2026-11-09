"""Testes da configuração do frontend servido e da linha de comando."""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from report_works import __main__ as entrypoint
from report_works.adapters.settings import Settings
from report_works.api.app import create_app


def _build_dist(root: Path) -> Path:
    dist = root / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<h1>interface</h1>", encoding="utf-8")
    (dist / "app.js").write_text("console.log(1)", encoding="utf-8")
    return dist


def test_frontend_dist_is_detected_only_when_asked_and_compiled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert Settings.from_env({}, detect_static=True).static_dir is None  # ainda não compilada

    _build_dist(tmp_path)

    assert Settings.from_env({}).static_dir is None  # sem pedir, nada muda
    assert Settings.from_env({}, detect_static=True).static_dir == Path("frontend") / "dist"


def test_explicit_static_dir_wins_over_detection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _build_dist(tmp_path)

    settings = Settings.from_env({"REPORT_STATIC_DIR": "/app/dist"}, detect_static=True)

    assert settings.static_dir == Path("/app/dist")


def test_default_app_serves_the_compiled_frontend_and_the_api_on_one_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("REPORT_WORKDIR", str(tmp_path / "work"))
    _build_dist(tmp_path)

    with TestClient(create_app()) as client:
        assert client.get("/").text == "<h1>interface</h1>"
        assert client.get("/app.js").status_code == 200
        assert client.get("/api/health").json() == {"status": "ok"}


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    calls: dict[str, Any] = {"opened": [], "run": None}

    class FakeTimer:
        def __init__(self, delay: float, function: Any, args: list[str]) -> None:
            calls["opened"].append((delay, args))

        def start(self) -> None:
            return None

    monkeypatch.setattr(entrypoint.threading, "Timer", FakeTimer)
    monkeypatch.setattr(
        entrypoint.uvicorn, "run", lambda *a, **kw: calls.__setitem__("run", (a, kw))
    )
    return calls


def test_main_prints_the_url_and_starts_uvicorn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recorded: dict[str, Any],
) -> None:
    monkeypatch.chdir(tmp_path)
    _build_dist(tmp_path)
    monkeypatch.setenv("REPORT_PORT", "9001")

    entrypoint.main([])

    assert "Abra http://127.0.0.1:9001 no navegador" in capsys.readouterr().out
    args, kwargs = recorded["run"]
    assert args == ("report_works.api.app:create_app",)
    assert kwargs == {"factory": True, "host": "127.0.0.1", "port": 9001}
    assert recorded["opened"] == []


def test_open_flag_schedules_the_browser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, recorded: dict[str, Any]
) -> None:
    monkeypatch.chdir(tmp_path)
    _build_dist(tmp_path)

    entrypoint.main(["--open"])

    assert recorded["opened"] == [(1.5, ["http://127.0.0.1:8000"])]


def test_without_a_compiled_frontend_it_says_only_the_api_is_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recorded: dict[str, Any],
) -> None:
    monkeypatch.chdir(tmp_path)

    entrypoint.main(["--open"])

    assert "Só a API está disponível, em http://127.0.0.1:8000/docs" in capsys.readouterr().out
    assert recorded["opened"] == []  # não abre o navegador se não há interface


def test_wildcard_host_is_shown_as_localhost() -> None:
    assert entrypoint.display_host("0.0.0.0") == "127.0.0.1"
    assert entrypoint.display_host("192.168.0.5") == "192.168.0.5"
