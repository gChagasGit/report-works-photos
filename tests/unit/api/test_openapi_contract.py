"""O contrato OpenAPI versionado precisa refletir a API atual (evita o frontend divergir)."""

from pathlib import Path

from report_works.export_openapi import build_openapi, render_openapi

CONTRACT = Path(__file__).parents[3] / "frontend" / "openapi.json"


def test_committed_contract_is_up_to_date() -> None:
    expected = render_openapi()

    assert CONTRACT.read_text(encoding="utf-8") == expected, (
        "Contrato desatualizado. Rode: uv run python -m report_works.export_openapi "
        "frontend/openapi.json && npm --prefix frontend run api:types"
    )


def test_contract_documents_the_main_routes() -> None:
    paths = set(build_openapi()["paths"])  # type: ignore[call-overload]

    assert {
        "/api/workspaces",
        "/api/workspaces/{workspace_id}/template",
        "/api/workspaces/{workspace_id}/photos/archive",
        "/api/workspaces/{workspace_id}/photos/folder",
        "/api/workspaces/{workspace_id}/validate",
        "/api/jobs",
        "/api/jobs/{job_id}/events",
        "/api/jobs/{job_id}/download",
    } <= paths
