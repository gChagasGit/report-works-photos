import os

class ImageHandler:
    def __init__(self, config):
        self.config = config

    def get_sorted_photos(self, folder_path):
        """Lista fotos e aplica a ordenação baseada na flag do YAML."""
        abs_folder = os.path.abspath(folder_path)
        
        if not os.path.exists(abs_folder):
            print(f" Pasta não encontrada: {abs_folder}")
            return []

        # Filtra apenas extensões de imagem comuns
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
        files = [
            os.path.join(abs_folder, f) 
            for f in os.listdir(abs_folder) 
            if f.lower().endswith(valid_extensions)
        ]
        
        # Recupera o método de ordenação do YAML (padrão é 'date')
        sort_method = self.config.get('layout_settings', {}).get('sort_method', 'date').lower()
        print(f"Ordenando fotos por {sort_method.upper()}.")

        if sort_method == 'name':
            # Ordenação por nome de arquivo (A-Z)
            files.sort()
        else:
            # Ordenação por data de modificação (Crescente)
            files.sort(key=os.path.getmtime)

        return files