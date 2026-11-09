"""Confere que o esboço de Docker só usa o que o código realmente lê e expõe."""

import inspect
import re
from pathlib import Path

import yaml

from report_works.adapters.settings import ENV_VARIABLES, Settings

DOCKER_DIR = Path(__file__).parents[2] / "docs" / "docker"
ENV_NAME = re.compile(r"\b(REPORT_[A-Z_]+|CORS_ORIGINS)\b")


def test_every_declared_variable_is_read_by_settings() -> None:
    body = inspect.getsource(Settings.from_env)

    assert all(f'"{name}"' in body for name in ENV_VARIABLES)


def test_dockerfile_only_sets_variables_the_code_reads() -> None:
    dockerfile = (DOCKER_DIR / "Dockerfile.sketch").read_text(encoding="utf-8")
    code_lines = [ln for ln in dockerfile.splitlines() if not ln.lstrip().startswith("#")]

    used = set(ENV_NAME.findall("\n".join(code_lines)))

    assert used  # o Dockerfile configura o servidor por variáveis
    assert used <= set(ENV_VARIABLES)


def test_compose_only_sets_variables_the_code_reads_and_publishes_the_api_port() -> None:
    compose = yaml.safe_load((DOCKER_DIR / "compose.sketch.yaml").read_text(encoding="utf-8"))
    service = compose["services"]["app"]

    assert set(service["environment"]) <= set(ENV_VARIABLES)
    assert service["environment"]["REPORT_WORKDIR"] == "/data"
    assert "127.0.0.1:8000:8000" in service["ports"]
    assert "report_data:/data" in service["volumes"]
    assert "report_data" in compose["volumes"]


def test_dockerfile_matches_the_app_contract() -> None:
    dockerfile = (DOCKER_DIR / "Dockerfile.sketch").read_text(encoding="utf-8")

    assert "REPORT_PORT=8000" in dockerfile and "EXPOSE 8000" in dockerfile
    assert "/api/health" in dockerfile  # rota que o HEALTHCHECK consulta existe na API
    assert 'CMD ["python", "-m", "report_works"]' in dockerfile
    assert "--no-default-groups" in dockerfile  # sem pytest/ruff/streamlit na imagem


def test_dockerignore_sketch_keeps_private_and_heavy_files_out_of_the_image() -> None:
    lines = (DOCKER_DIR / "dockerignore.sketch").read_text(encoding="utf-8").splitlines()

    for pattern in ("node_modules", ".venv", "work", "config.yaml", "images", ".git"):
        assert pattern in lines
