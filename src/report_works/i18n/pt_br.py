"""Mensagens em português do Brasil.

Todo texto mostrado ao usuário final (interface e erros) deve vir deste módulo.
"""

# --- Arquivo de configuração -------------------------------------------------
ERR_CONFIG_FILE_NOT_FOUND = "Arquivo de configuração não encontrado: {path}"
ERR_CONFIG_NOT_A_MAPPING = "O arquivo de configuração deve conter um mapeamento YAML."
ERR_YAML_INVALID = "YAML inválido: {detail}"

# --- Seções ------------------------------------------------------------------
ERR_GROUPED_NEEDS_SIZES = "Seção agrupada exige a lista de fotos por grupo."
ERR_GRID_FORBIDS_SIZES = "Seção em grade não aceita lista de fotos por grupo."
ERR_DUPLICATE_SECTION_ID = "Há seções com o mesmo identificador: {values}."
ERR_DUPLICATE_SECTION_LABEL = "Há seções com o mesmo título no Excel: {values}."

# --- Layout ------------------------------------------------------------------
ERR_COLUMNS_DUPLICATED = "As colunas de fotos não podem se repetir."

# --- Fotos e template --------------------------------------------------------
ERR_FOLDER_NOT_FOUND = "Pasta de fotos não encontrada: {path}"
ERR_UNSAFE_PATH = "O identificador da seção aponta para fora da pasta de fotos: {section_id}"
ERR_TEMPLATE_UNREADABLE = "Não foi possível ler o template Excel: {detail}"

# --- Problemas encontrados na validação prévia -------------------------------
ISSUE_SHEET_NOT_FOUND = 'A aba "{sheet}" não existe no template; será usada a aba "{used}".'
ISSUE_LABEL_NOT_FOUND = 'O título "{label}" não foi encontrado na coluna B da aba "{sheet}".'
ISSUE_LABEL_DUPLICATED = (
    'O título "{label}" aparece {count} vezes (linhas {rows}); será usada a linha {first}.'
)
ISSUE_FOLDER_MISSING = 'A pasta de fotos da seção "{label}" não existe: {path}'
ISSUE_UNSAFE_FOLDER = 'O identificador da seção "{label}" aponta para fora da pasta de fotos.'
ISSUE_NO_PHOTOS = 'Nenhuma foto encontrada na pasta da seção "{label}".'
ISSUE_FEWER_PHOTOS = 'A seção "{label}" prevê {expected} fotos, mas a pasta tem {found}.'
ISSUE_MORE_PHOTOS = (
    'A pasta da seção "{label}" tem {found} fotos; serão usadas as primeiras {used}.'
)

# --- Layout e inserção no Excel ----------------------------------------------
ERR_ANCHOR_MISSING = 'A seção "{label}" não tem título no template.'
ERR_PHOTO_INSERT = "Não foi possível inserir a foto {name} em {cell}: {detail}"
ERR_EXCEL_UNAVAILABLE = (
    "A automação do Excel não está disponível. É necessário Windows com Microsoft Excel instalado."
)
ERR_WRITER_NOT_OPEN = "O template não foi aberto."
ISSUE_SECTION_OVERFLOW = (
    'A seção "{label}" ocupa até a linha {last}, mas a seção seguinte começa na linha {next}.'
)
ISSUE_BEYOND_TEMPLATE = (
    'A seção "{label}" ocupa até a linha {last}, além do fim do template (linha {template_last}).'
)

# --- Descrição de erros de validação (campo: motivo) -------------------------
FIELD_ERROR = "{field}: {reason}"
REASON_MISSING = "campo obrigatório"
REASON_PATTERN = "formato inválido"
REASON_TOO_SHORT = "não pode ficar vazio"
REASON_GREATER_OR_EQUAL = "deve ser maior ou igual a {limit}"
REASON_GREATER_THAN = "deve ser maior que {limit}"
REASON_TYPE = "tipo de valor inválido"
REASON_UNKNOWN_FIELD = "campo desconhecido"
REASON_INVALID = "valor inválido"
