import os
import yaml
from scripts.report_engine import ReportEngine

def remove_report(output_path):
    if os.path.exists(output_path):
        os.remove(output_path)
        print(f"🗑️ Relatório antigo removido: {output_path}")

if __name__ == "__main__":
    # Carrega config para pegar caminhos de saída
    with open("config.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    output_xlsx = config['paths']['output']
    base_images_path = config['paths']['base_images']
    
    # Gera o mapeamento de fotos dinamicamente baseado nos IDs das seções
    photos_data = {}
    for section in config['sections']:
        section_id = section['id']
        photos_data[section_id] = os.path.join(base_images_path, section_id)
    
    # Executa o motor
    try:
        remove_report(output_xlsx)
        
        engine = ReportEngine("config.yaml")
        engine.load_excel_template()
        
        # Insere imagens usando o mapeamento dinâmico
        engine.insert_images_in_report(photos_data)
        
        engine.save_and_close()
        print(" Processo concluído com sucesso!")
        
    except Exception as e:
        print(f" Erro na execução: {e}")