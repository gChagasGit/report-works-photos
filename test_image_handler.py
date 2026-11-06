import os
import time
import pytest
from scripts.image_handler import ImageHandler

@pytest.fixture
def default_config():
    """Fixture que provê um dicionário de configuração padrão para os testes."""
    return {
        'layout_settings': {
            'sort_method': 'name'
        }
    }

def test_get_sorted_photos_folder_not_found(default_config, capsys):
    """Testa o comportamento quando a pasta informada não existe."""
    handler = ImageHandler(default_config)
    result = handler.get_sorted_photos("caminho_fake_que_nao_existe")
    
    assert result == []
    captured = capsys.readouterr()
    assert "Pasta não encontrada" in captured.out

def test_get_sorted_photos_by_name(tmp_path, default_config):
    """Testa se as fotos estão sendo filtradas por extensão e ordenadas por nome."""
    # Cria arquivos temporários na pasta tmp_path
    (tmp_path / "b_foto.jpg").touch()
    (tmp_path / "a_foto.png").touch()
    (tmp_path / "documento.txt").touch() # Extensão inválida, deve ser ignorada
    
    handler = ImageHandler(default_config)
    result = handler.get_sorted_photos(str(tmp_path))
    
    assert len(result) == 2
    # A ordenação A-Z deve colocar a_foto.png primeiro
    assert "a_foto.png" in result[0]
    assert "b_foto.jpg" in result[1]

def test_get_sorted_photos_by_date(tmp_path):
    """Testa a ordenação por data de criação das fotos."""
    # Forçamos a configuração para data
    config_date = {'layout_settings': {'sort_method': 'date'}}
    
    # IMPORTANTE: A criação de arquivos é muito rápida. Em alguns sistemas, 
    # a data de criação será idêntica se não houver um pequeno atraso.
    file1 = tmp_path / "foto2.jpg"
    file2 = tmp_path / "foto1.jpg"
    
    file1.touch()
    time.sleep(0.05) # Pausa rápida para garantir datas diferentes
    file2.touch()
    
    handler = ImageHandler(config_date)
    result = handler.get_sorted_photos(str(tmp_path))
    
    assert len(result) == 2
    # A foto2 foi criada primeiro, logo deve aparecer antes
    assert "foto2.jpg" in result[0]
    assert "foto1.jpg" in result[1]