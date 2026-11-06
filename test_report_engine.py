import pytest
from unittest.mock import patch, MagicMock
from scripts.report_engine import ReportEngine

@pytest.fixture
def mock_config():
    """Configuração falsa para evitar a leitura do arquivo YAML real."""
    return {
        "paths": {"template": "template_fake.xlsx"},
        "layout_settings": {"photo_columns": ["B", "D", "F"], "image_span": 10},
        "project_metadata": {"target_sheet": "Relatório fotográfico"}
    }

@patch("scripts.report_engine.yaml.safe_load")
@patch("scripts.report_engine.xw")
def test_report_engine_initialization(mock_xw, mock_yaml, mock_config):
    """Testa se a engine carrega as configurações corretamente sem abrir o Excel."""
    # Substitui o retorno do yaml.safe_load pelo nosso dicionário falso
    mock_yaml.return_value = mock_config
    
    # Mocka o app do xlwings para não abrir o Excel de verdade e travar o teste
    mock_app = MagicMock()
    mock_xw.App.return_value = mock_app
    
    engine = ReportEngine("config_qualquer.yaml")
    
    assert engine.template_path == "template_fake.xlsx"
    assert engine.photo_columns == ["B", "D", "F"]
    assert engine.target_sheet == "Relatório fotográfico"