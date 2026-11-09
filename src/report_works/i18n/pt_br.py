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
