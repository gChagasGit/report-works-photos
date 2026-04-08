import yaml
import os
import xlwings as xw
from image_handler import ImageHandler

class ReportEngine:
    def __init__(self, config_path):
        """Inicializa o motor com configurações de layout e constantes de conversão."""
        self.config = self._load_config(config_path)
        self.app = None
        self.book = None
        self.sheet = None
        self.handler = ImageHandler(self.config)
        
        # Parâmetros de Layout
        layout = self.config.get('layout_settings', {})
        self.FIXED_WIDTH_PX = layout.get('fixed_width_px', 390)
        self.PX_TO_PT = 0.75
        self.DEFAULT_MIN_ROW_HEIGHT = layout.get('default_min_row_height', 23.25)
        self.IMAGE_SPAN = layout.get('image_span', 10)
        self.ROW_SPACING = layout.get('row_spacing', 2)

    def _load_config(self, path):
        """Carrega o arquivo YAML de configuração."""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def load_excel_template(self):
        """Prepara o Excel e seleciona a aba alvo."""
        path = os.path.abspath(self.config['paths']['template'])
        if not os.path.exists(path):
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")

        self.app = xw.App(visible=True, add_book=False)
        self.book = self.app.books.open(path)
        self.app.api.ActiveWindow.View = 1  # Modo Normal
        
        meta = self.config['project_metadata']
        target = meta.get('target_sheet')
        all_names = [s.name for s in self.book.sheets]
        self.sheet = self.book.sheets[target] if target in all_names else self.book.sheets[0]
        print(f" Aba '{self.sheet.name}' carregada.")

    def find_section_row(self, label_text):
        """Localiza a linha da âncora de texto na coluna B."""
        search_range = self.sheet.range("B1:B2000").value
        for i, value in enumerate(search_range):
            if value == label_text:
                return i + 1
        return None

    def _get_target_geometry(self, i, start_row):
        """Calcula coordenadas para o grid de 3 colunas."""
        cols = self.config['layout_settings']['photo_columns']
        col_letter = cols[i % 3]
        row_offset = (i // 3) * (self.IMAGE_SPAN + 2)
        target_address = f"{col_letter}{start_row + self.ROW_SPACING + row_offset}"
        return self.sheet.range(target_address)

    def insert_images_in_report(self, photos_map):
        """Distribui imagens por seções ou pavimentos estruturados."""
        for section in self.config['sections']:
            print(f"📸 Processando: {section['label']}...")
            anchor_row = self.find_section_row(section['label'])
            if not anchor_row: continue

            photos = self.handler.get_sorted_photos(photos_map.get(section['id'], ""))
            fix_width = section.get('fix_width', False)
            distribuicao = section.get('num_pavimentos')

            if distribuicao and section['id'] == 'pavimentos':
                self._insert_by_pavimento(photos, distribuicao, anchor_row, fix_width)
            else:
                self._insert_sequentially(photos, anchor_row, section.get('max_photos', 999), fix_width)

    def _insert_by_pavimento(self, photos, distribuicao, anchor_row, fix_width):
        """Lógica para agrupamento por pavimentos com quebra de linha."""
        photo_idx = 0
        current_base_row = anchor_row + self.ROW_SPACING
        photo_cols = self.config['layout_settings']['photo_columns']

        for num_fotos in distribuicao:
            for i in range(num_fotos):
                if photo_idx >= len(photos): break
                
                row_offset = (i // 3) * (self.IMAGE_SPAN + 2)
                target_cell = self.sheet.range(f"{photo_cols[i % 3]}{current_base_row + row_offset}")
                
                self._process_single_image(photos[photo_idx], target_cell, fix_width)
                photo_idx += 1
            
            # Pula para a próxima linha livre após o pavimento
            linhas_gastas = ((num_fotos - 1) // 3 + 1)
            current_base_row += linhas_gastas * (self.IMAGE_SPAN + 2)

    def _insert_sequentially(self, photos, anchor_row, max_photos, fix_width):
        """Preenchimento padrão sequencial."""
        for i, photo_path in enumerate(photos):
            if i >= max_photos: break
            target_range = self._get_target_geometry(i, anchor_row)
            self._process_single_image(photo_path, target_range, fix_width)

    def _process_single_image(self, path, target, fix_width):
        """Encapsula a inserção com tratamento de erro."""
        abs_path = os.path.abspath(path)
        try:
            if fix_width:
                self._insert_fixed_width(abs_path, target)
            else:
                self._insert_fit_to_box(abs_path, target)
        except Exception as e:
            print(f"    Erro em {target.address}: {e}")

    def _insert_fixed_width(self, path, target):
        """Insere com largura fixa e ajuste de altura estabilizado."""
        # Medição temporária
        temp_pic = self.sheet.pictures.add(path, width=int(self.FIXED_WIDTH_PX * self.PX_TO_PT))
        img_h, img_w = temp_pic.height, temp_pic.width
        temp_pic.delete()

        # Cálculo de altura
        target_h = max((img_h + 2) / self.IMAGE_SPAN, self.DEFAULT_MIN_ROW_HEIGHT)

        # Estabilização das linhas antes da inserção
        for row_idx in range(target.row, target.row + self.IMAGE_SPAN):
            row_range = self.sheet.range(f"{row_idx}:{row_idx}")
            if round(target_h, 2) > round(row_range.row_height or 0, 2):
                row_range.row_height = target_h

        # Inserção definitiva
        pic = self.sheet.pictures.add(path, top=target.top, left=target.left, width=img_w)
        pic.api.Placement = 1 
        pic.top, pic.left = target.top, target.left

        print(f"    [Fixed] {target.address} | H: {target_h:.2f}")

    def _insert_fit_to_box(self, path, target):
        """Ajusta a imagem ao espaço existente."""
        avail_w = target.width
        rows = self.sheet.range(f"{target.row}:{target.row + self.IMAGE_SPAN - 1}")
        
        h_data = rows.row_height
        avail_h = sum([h or self.DEFAULT_MIN_ROW_HEIGHT for h in h_data]) if isinstance(h_data, list) else (h_data or self.DEFAULT_MIN_ROW_HEIGHT) * self.IMAGE_SPAN

        pic = self.sheet.pictures.add(path, top=target.top, left=target.left)
        pic.api.Placement = 1 
        
        ratio = pic.width / pic.height
        new_w, new_h = avail_w, avail_w / ratio

        if new_h > avail_h:
            new_h, new_w = avail_h, avail_h * ratio

        pic.width, pic.height = new_w, new_h
        pic.left += (avail_w - new_w) / 2
        pic.top += (avail_h - new_h) / 2
        print(f"    [Fit] {target.address}")

    def save_and_close(self):
        """Salva o arquivo final."""
        path = os.path.abspath(self.config['paths']['output'])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.book.save(path)
        print(f" Relatório salvo: {path}")