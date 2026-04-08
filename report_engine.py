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
        
        # Parâmetros de Layout centralizados
        layout = self.config.get('layout_settings', {})
        self.FIXED_WIDTH_PX = layout.get('fixed_width_px', 390)
        self.PX_TO_PT = 0.75
        self.DEFAULT_MIN_ROW_HEIGHT = layout.get('default_min_row_height', 23.25)
        self.IMAGE_SPAN = layout.get('image_span', 10)
        self.ROW_SPACING = layout.get('row_spacing', 2)
        self.PHOTO_COLS = layout.get('photo_columns', ["B", "D", "F"])

    def _load_config(self, path):
        """Carrega o arquivo YAML de configuração."""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def load_excel_template(self):
        """Prepara o Excel e seleciona a aba alvo de forma robusta."""
        path = os.path.abspath(self.config['paths']['template'])
        if not os.path.exists(path):
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")

        self.app = xw.App(visible=True, add_book=False)
        self.book = self.app.books.open(path)
        self.app.api.ActiveWindow.View = 1  # Modo Normal (xlNormalView)
        
        meta = self.config.get('project_metadata', {})
        target = meta.get('target_sheet')
        
        # Seleção da aba: pelo nome ou a primeira disponível
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

    def _get_target_range(self, i, base_row):
        """Calcula a célula exata para o grid de colunas."""
        col_letter = self.PHOTO_COLS[i % 3]
        row_offset = (i // 3) * (self.IMAGE_SPAN + 2)
        return self.sheet.range(f"{col_letter}{base_row + row_offset}")

    def insert_images_in_report(self, photos_map, callback=None):
        """Insere imagens com progresso real e suporte a pavimentos."""
        # Passo 1: Pré-contagem para progresso linear preciso
        total_planejado = 0
        for section in self.config['sections']:
            fotos = self.handler.get_sorted_photos(photos_map.get(section['id'], ""))
            total_planejado += min(len(fotos), section.get('max_photos', 999))
        
        if total_planejado == 0:
            print("⚠️ Nenhuma foto encontrada.")
            return

        processadas = 0
        for section in self.config['sections']:
            anchor_row = self.find_section_row(section['label'])
            if not anchor_row: continue

            photos = self.handler.get_sorted_photos(photos_map.get(section['id'], ""))
            fix_width = section.get('fix_width', False)
            current_row = anchor_row + self.ROW_SPACING
            dist = section.get('num_pavimentos')

            # Unificação: pavimentos vs sequencial
            if dist and section['id'] == 'pavimentos':
                photo_idx = 0
                for num_fotos in dist:
                    for i in range(num_fotos):
                        if photo_idx >= len(photos): break
                        
                        target = self._get_target_range(i, current_row)
                        self._process_single_image(photos[photo_idx], target, fix_width)
                        
                        photo_idx += 1
                        processadas += 1
                        if callback:
                            callback(processadas / total_planejado, f"{section['label']} ({processadas}/{total_planejado})")
                    
                    # Salto de linha por pavimento
                    current_row += ((num_fotos - 1) // 3 + 1) * (self.IMAGE_SPAN + 2)
            else:
                for i, photo_path in enumerate(photos[:section.get('max_photos', 999)]):
                    target = self._get_target_range(i, anchor_row + self.ROW_SPACING)
                    self._process_single_image(photo_path, target, fix_width)
                    processadas += 1
                    if callback:
                        callback(processadas / total_planejado, f"{section['label']} ({processadas}/{total_planejado})")

    def _process_single_image(self, path, target, fix_width):
        """Centraliza a lógica de inserção com tratamento de exceção."""
        try:
            abs_path = os.path.abspath(path)
            if fix_width:
                self._insert_fixed_width(abs_path, target)
            else:
                self._insert_fit_to_box(abs_path, target)
        except Exception as e:
            print(f"    Erro em {target.address}: {e}")

    def _insert_fixed_width(self, path, target):
        """Ajusta linhas e insere imagem com largura fixa."""
        # Medição prévia para estabilidade
        temp = self.sheet.pictures.add(path, width=int(self.FIXED_WIDTH_PX * self.PX_TO_PT))
        img_h, img_w = temp.height, temp.width
        temp.delete()

        # Cálculo e aplicação de altura mínima
        target_h = max((img_h + 2) / self.IMAGE_SPAN, self.DEFAULT_MIN_ROW_HEIGHT)
        for r in range(target.row, target.row + self.IMAGE_SPAN):
            row = self.sheet.range(f"{r}:{r}")
            if round(target_h, 2) > round(row.row_height or 0, 2):
                row.row_height = target_h

        pic = self.sheet.pictures.add(path, top=target.top, left=target.left, width=img_w)
        pic.api.Placement = 1 # xlMoveAndSize
        pic.top, pic.left = target.top, target.left

    def _insert_fit_to_box(self, path, target):
        """Enquadra a imagem no container de linhas existente."""
        rows = self.sheet.range(f"{target.row}:{target.row + self.IMAGE_SPAN - 1}")
        
        # Cálculo de altura disponível (suporta linhas mescladas ou individuais)
        h_vals = rows.row_height
        avail_h = sum([h or self.DEFAULT_MIN_ROW_HEIGHT for h in h_vals]) if isinstance(h_vals, list) else (h_vals or self.DEFAULT_MIN_ROW_HEIGHT) * self.IMAGE_SPAN

        pic = self.sheet.pictures.add(path, top=target.top, left=target.left)
        ratio = pic.width / pic.height
        
        new_w, new_h = target.width, target.width / ratio
        if new_h > avail_h:
            new_h, new_w = avail_h, avail_h * ratio

        pic.width, pic.height = new_w, new_h
        pic.left += (target.width - new_w) / 2
        pic.top += (avail_h - new_h) / 2

    def save_and_close(self):
        """Salva o relatório no caminho de saída configurado."""
        path = os.path.abspath(self.config['paths']['output'])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.book.save(path)
        print(f" Relatório salvo com sucesso: {path}")
