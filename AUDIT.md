# AUDIT — report-works-photos

Base auditada: `main` @ `fbdf133` (igual a `origin/main`), mais o trabalho **não rastreado** presente na árvore local (ver §0).
Método: leitura de todos os arquivos + experimentos descartáveis fora do repositório. **Nada foi executado no Excel** (esta máquina não foi usada para rodar o fluxo xlwings); tudo o que não foi comprovado está marcado **[hipótese]**.

## 0. Estado da árvore local

| Item | Situação | Observação |
|---|---|---|
| `app.py`, `scripts/*`, `templates/model.xlsx`, `macro.txt`, `config_exemple.yaml`, `requirements.txt`, `README.md` | rastreado | fluxo Streamlit + xlwings original |
| `INICIAR_APP.bat` | **modificado** | passou a rodar `python main.py` e instala `fastapi uvicorn pydantic` fora do `requirements.txt` |
| `main.py` | não rastreado | FastAPI com `GET/POST /api/config`, `GET /api/select-folder`, `GET /api/select-file` (tkinter). **Não há endpoint para gerar relatório.** |
| `CRIAR_FRONTEND.bat`, `COPIAR_PROJETO.bat`, `package.json`, `package-lock.json`, `node_modules/` | não rastreado | tentativa de Vite/Tailwind; a pasta `frontend/` **não existe** |
| `pytest.ini`, `requirements-dev.txt`, `test_image_handler.py`, `test_report_engine.py`, `__init__.py` (raiz) | não rastreado | ver §3 |

**Consequência:** com o `INICIAR_APP.bat` modificado, hoje **nenhum caminho de UI gera relatório** (Streamlit não é mais chamado; a API não tem rota de geração). O README ainda descreve `http://localhost:8501`.

**Alteração feita nesta etapa (branch `chore/audit-phase-2`):** `.gitignore` reescrito e organizado (venv/caches, node/frontend, config e segredos, relatórios gerados, fotos, logs, SO, IDE). `templates/model.xlsx` continua versionado (`!templates/model.xlsx`). `git ls-files -ci` não encontrou arquivo rastreado que passe a ser ignorado. Foram removidos os padrões amplos `generate*.py` e `setup*.py` (podiam ocultar código real; `test/` já cobre os scripts auxiliares).

---

## 1. Mapa do código

### 1.1 Módulos

| Arquivo | Papel | Linhas |
|---|---|---|
| `app.py` | UI Streamlit **+** estado **+** montagem do YAML **+** orquestração | 131 |
| `scripts/report_engine.py` | `ReportEngine`: abre Excel (xlwings), acha seções, calcula grade, insere imagens, salva | 161 |
| `scripts/image_handler.py` | `ImageHandler.get_sorted_photos`: lista e ordena imagens de uma pasta | 32 |
| `scripts/run_report.py` | CLI duplicada do fluxo de `app.py` (lê `config.yaml`, apaga saída, gera) | 37 |
| `main.py` (WIP) | API FastAPI parcial | 64 |
| `macro.txt` | VBA `ConvertShapesToPlaceInCell` (cópia manual) | 26 |

### 1.2 Classes e funções

- `ReportEngine` (`report_engine.py:6`): `__init__` (7), `_load_config` (24), `load_excel_template` (29), `find_section_row` (47), `_get_target_range` (55), `insert_images_in_report` (61), `_process_single_image` (108), `_insert_fixed_width` (119), `_insert_fit_to_box` (137), `save_and_close` (156).
- `ImageHandler` (`image_handler.py:3`): `get_sorted_photos` (7).
- `app.py`: `select_folder` (18), `select_file` (30), `load_config_to_session` (42), bloco de sidebar (64–71), laço de seções (76–94), botão **GERAR** (100–132).

### 1.3 Fluxo de dados da geração

```
config.yaml ──load_config_to_session──▶ st.session_state.sections
   ▲                                          │ (usuário edita; tkinter escolhe template/pasta)
   │                                          ▼
   └──yaml.dump (SOBRESCREVE) ◀── config_data (layout FIXO em app.py:104-105)
                                              │
                         ReportEngine("config.yaml")  ← relê o arquivo recém-escrito
                                              │
     load_excel_template: xw.App(visible=True) → abre template → aba target_sheet (ou a 1ª)
                                              │
     insert_images_in_report(photos_map = {id: base_images/id})
        1. pré-contagem: Σ min(len(fotos), max_photos)  → denominador do progresso
        2. por seção: find_section_row(label)  [busca igualdade exata em B1:B2000, 1ª ocorrência]
           ├─ id == "pavimentos" e num_pavimentos: blocos por andar
           │     foto i do andar → _get_target_range(i, current_row)
           │     current_row += ceil(n/3) * (image_span + 2)
           └─ demais: fotos[:max_photos] → _get_target_range(i, âncora + row_spacing)
        3. _process_single_image → fix_width ? _insert_fixed_width : _insert_fit_to_box
     save_and_close: book.save(paths.output)   ← NÃO fecha o Excel nem chama app.quit()
```

**Fórmulas de layout** (valores atuais): coluna = `photo_columns[i % 3]`; linha = `base + (i // 3) * (image_span + 2)` (`+2` fixo em `report_engine.py:58`, não vem do YAML); fixed-width: largura `390 px × 0,75 = 292,5 pt`, altura de linha `max((h+2)/10, 23,25)` aplicada às 10 linhas; fit-to-box: escala para caber em `target.width × Σ alturas` e centraliza.

---

## 2. Lacunas de processo manual

Gravidade: **A** = bloqueia ou corrompe resultado; **M** = falha frequente ou silenciosa; **B** = incômodo.

### 2.1 Os 9 pontos pedidos (P1–P9)

| # | Onde | Como falha | Grav. | Correção proposta |
|---|---|---|---|---|
| P1 | `INICIAR_APP.bat:11-24` | Exige Python ≥ 3.12 instalado à mão (Microsoft Store). Sem Python → o usuário trava. O `.bat` ainda instala dependências com `pip` fora do `requirements.txt` (linha 46) | A | `uv` gerencia Python e deps; `mise` fixa versões; distribuição como um comando/URL (Fase 4) |
| P2 | `report_engine.py:3,35` | Depende de **Excel instalado** + `xlwings` + `pywin32` (Windows). Falha em Linux/Docker/macOS sem Excel. Excel abre **visível** (`visible=True`) e fica aberto se ocorrer exceção (sem `try/finally`/`quit`) → processos `EXCEL.EXE` órfãos e arquivo de saída travado | A | Substituir por escrita direta do .xlsx (ver §4); se mantiver Excel em algum modo, usar `with xw.App(visible=False)` e `quit()` em `finally` |
| P3 | `app.py:18-40`, `main.py:39-60` | `tkinter.askdirectory` roda no servidor. Em Docker/servidor remoto não há display; mesmo local, bloqueia a thread HTTP | A | Upload de template e fotos (zip ou multi-arquivo/pasta via `webkitdirectory`) para um diretório de trabalho configurável |
| P4 | `report_engine.py:47-53`; `app.py:82` | O "Título Excel" digitado precisa ser **idêntico** (acento, caixa, espaço) à célula em `B`. Não achou → `continue` **silencioso** (`report_engine.py:76`); a seção some do relatório sem aviso | A | Listar os títulos encontrados no template e deixar o usuário **escolher** (dropdown); validar em tempo real; normalizar (strip/casefold/NFC) e avisar se não achar |
| P4b | `report_engine.py:49-53` | Título repetido: "Geral da obra" aparece nas linhas **36, 38 e 48** do `model.xlsx`; o motor usa a 1ª. Funciona por sorte e muda se alguém inserir linha acima | M | Âncora por célula/intervalo (ex.: `B36`) ou por *named range*, ou exigir título único e acusar duplicata |
| P5 | `app.py:80,126` | Nome da subpasta precisa ser igual ao `id` da seção. Pasta ausente → `print("Pasta não encontrada")` e lista vazia (`image_handler.py:11-13`), sem erro na UI. `id` também é usado em `os.path.join` (aceita `../`) | A | Validar existência e contagem antes de gerar; `id` restrito a `[a-z0-9_]+`; mapear pasta↔seção explicitamente |
| P6 | `app.py:114-115` | `config.yaml` é **sobrescrito a cada clique** em GERAR; também usa o CWD (`"config.yaml"` relativo). Perde comentários do exemplo (`yaml.dump`) e conflita entre execuções simultâneas | M | Config validada por Pydantic, persistida como perfil nomeado (ou por requisição), caminho via variável de ambiente |
| P7 | `app.py:104-105` | `photo_columns`, `image_span`, `row_spacing`, `default_min_row_height`, `fixed_width_px`, aba alvo (`"Relatório fotográfico"`), fonte e tamanho **fixos no código**; os valores de `config_exemple.yaml` são ignorados pela UI. `project_name`, `default_font*` não são usados em lugar nenhum | M | Esquema Pydantic `LayoutSettings` com defaults, exposto na API e editável |
| P8 | `app.py:70` | Saída gravada em `dirname(template)`. Template vazio → `dirname('')` → pasta atual; template em pasta somente leitura ou na rede falha. Gera arquivos de ~37 MB junto ao modelo (`templates/relatorio_final*.xlsx`) | M | Pasta de saída própria e configurável; download pelo navegador |
| P9 | `macro.txt`, README "Dica Extra" | O usuário copia VBA manualmente (ALT+F11) para simular "Colocar na Célula". Depende de `ExecuteMso "PicturePlaceInCell"` com `On Error Resume Next` (erros ignorados), `shp.Select` (lento, depende da UI), arquivo precisa ser `.xlsm` para guardar a macro | M | Tornar "Place in Cell" uma opção do gerador (ver §4.3); remover o passo manual |

### 2.2 Lacunas adicionais encontradas

| # | Onde | Como falha | Grav. | Correção |
|---|---|---|---|---|
| X1 | `report_engine.py:69-71` + `app.py:128-130` | Sem fotos (`total == 0`) o motor só faz `print` e retorna; `app.py` segue, chama `save_and_close` e exibe **"Arquivo salvo"** com o template intacto | A | Levantar erro de domínio e bloquear o botão |
| X2 | `report_engine.py:84` vs `65-67` | Seção "pavimentos": o código testa `id == 'pavimentos'` (literal) e ignora `max_photos`; o denominador do progresso usa `max_photos`. No `config_exemple.yaml`, `Σ num_pavimentos = 119` e `max_photos = 120` → o progresso termina em **119/120 (99,2%)**. Seção com outro `id` e `num_pavimentos` é ignorada em silêncio (`app.py:93` mostra o campo por `or 'num_pavimentos' in section`, inconsistente) | M | Tipo de seção explícito (`kind: grid \| grouped`); contar a partir do plano de inserção |
| X3 | `report_engine.py:116-117` | Falha em uma imagem vira `print` e segue; o relatório sai incompleto com "Concluído" | M | Coletar erros por foto e devolvê-los no resultado |
| X4 | `report_engine.py:57` | `% 3` fixo, enquanto `photo_columns` é configurável: com 2 ou 4 colunas quebra ou ignora | M | Usar `len(photo_columns)` |
| X5 | `image_handler.py:16` | Só `.jpg/.jpeg/.png/.bmp`; `.webp`, `.tif`, `.heic` (comum em celular) são ignorados em silêncio. Sem tratar rotação EXIF **[hipótese: o Excel exibe a imagem sem aplicar EXIF; testar com foto de celular]** | M | Lista configurável + conversão/normalização (Pillow) |
| X6 | `image_handler.py:31` | `os.path.getctime` = data de criação no Windows, mas "mudança de metadados" no Linux; ordem muda em Docker. Cópia de arquivos redefine a data | M | Ordenar por EXIF `DateTimeOriginal`, com *fallback* para nome; parâmetro explícito |
| X7 | `report_engine.py:101` | Não há checagem de **capacidade do template**: nada compara `max_photos` com os blocos reservados na planilha; fotos a mais invadem a seção seguinte **[hipótese: confirmar contando blocos entre âncoras em `model.xlsx`]** | A | Validar capacidade (nº de blocos × colunas) antes de gerar |
| X8 | `report_engine.py:119-135` | Largura fixa de 390 px vs. coluna B/D/F de 43,8 caracteres (~311 px com fonte padrão de 7 px/caractere) **[hipótese: a imagem excede a coluna e sobrepõe a vizinha; medir no Excel]**. Altura de linha é global à linha: aumentar para a coluna B também altera D e F | M | Calcular largura a partir da coluna real; documentar |
| X9 | `report_engine.py:122-124,133` | Cada imagem é inserida **duas vezes** (medição + definitiva) → 2× I/O e COM (lento com ~130 fotos) | B | Medir via Pillow (sem Excel) |
| X10 | `report_engine.py:134` | `Placement = 1` (mover e dimensionar) só no ramo fixo; o ramo "fit" usa o padrão. Comportamento ao redimensionar linhas difere por seção | B | Política única de âncora |
| X11 | Saídas de ~37 MB (`templates/relatorio_final3.xlsx`: 133 imagens, ~37,7 MB) | Fotos originais são embutidas sem redução | M | Reamostrar (ex.: lado maior ≤ 1600 px, JPEG q85) conforme parâmetro |
| X12 | `run_report.py:26` | `remove_report` apaga o relatório anterior sem confirmar; lógica duplicada de `app.py` | M | Uma única camada de serviço |
| X13 | `app.py:131-132` | `except Exception` exibe `str(e)` cru ao usuário (ex.: erro COM) | M | Exceções de domínio com mensagem em português; log técnico separado |
| X14 | `main.py:12-18` | `allow_origins=["*"]` com `allow_credentials=True`; `POST /api/config` grava YAML arbitrário em disco | M | Origens por variável de ambiente; validar corpo com Pydantic |
| X15 | README | Documenta porta 8501/Streamlit; WIP usa 8000. Raiz tem `__init__.py` e `package.json` soltos | B | Atualizar README em cada etapa |
| X16 | `requirements.txt` | 40 pacotes congelados (streamlit, pandas, pyarrow, altair, pydeck, GitPython...), só ~5 diretos (xlwings, pywin32, PyYAML, openpyxl, Pillow). `pywin32` quebra instalação em Linux | M | `pyproject.toml` com dependências diretas; `uv.lock` |
| X17 | `.gitignore` original | Ignorava `test/` (que guarda `generate_test_images.py`, `setup_photos.py`) — scripts úteis nunca versionados; `config.yaml` ignorado sem aviso na UI | B | Mover geradores para `tests/fixtures` versionados |

---

## 3. Violações de convenção

| Categoria | Evidência |
|---|---|
| Nomes em português / sem padrão | `total_planejado`, `processadas`, `photos_map`/`photos` misturados, `num_pavimentos`, `select_folder(label, key_suffix, default_path)`; constantes como atributos de instância em CAIXA ALTA (`self.FIXED_WIDTH_PX`, `report_engine.py:17-22`); arquivos `config_exemple.yaml` (grafia), `INICIAR_APP.bat`; `ImageHandler` guarda o `config` inteiro (dict cru) só para ler `sort_method` |
| Funções longas / multi-responsabilidade | `insert_images_in_report` (46 linhas, 2 ramos, contagem + progresso + I/O); `app.py` inteiro: UI, estado, YAML, execução e erros no mesmo módulo; bloco do botão GERAR (33 linhas) |
| Acoplamento UI ↔ regra | Layout, aba e fonte definidos em `app.py:104-105`; `ReportEngine` recebe **caminho de YAML** e lê do disco; `callback(percent, msg)` com texto de UI (PT) dentro do motor; `print` como log; tkinter dentro de handler HTTP (`main.py`) |
| Acoplamento com infraestrutura | `xlwings`/COM importado no topo (`report_engine.py:3`) impede testar sem Excel; `os.getcwd()` e `"config.yaml"` relativos |
| Tipagem | Zero anotações; configs como `dict` sem esquema; sem `py.typed`, mypy/pyright não configurados |
| Testes | `pytest.ini` aponta `testpaths = tests` (pasta inexistente; os arquivos estão na raiz). `test_report_engine.py` afirma `engine.template_path`, `engine.photo_columns`, `engine.target_sheet`, que **não existem** em `ReportEngine` e a classe abre o YAML real em `__init__` → falha prevista **[por leitura; `pytest` não está instalado no `.venv`, não executei]**. `test_image_handler.py` é válido, mas usa `time.sleep` e `capsys` (acoplado ao `print`). Nenhum teste de `find_section_row`, `_get_target_range`, pavimentos ou progresso. `requirements-dev.txt` herda `pywin32` |
| Tooling | Sem ruff/linters, sem `pyproject.toml`, sem CI |

---

## 4. Riscos para a migração

### 4.1 Risco central
O motor é inteiramente **xlwings/COM**: usa `Application`, `ActiveWindow`, `Pictures.add`, `Shape.Placement`, alturas de linha do Excel. Em Linux/Docker **não existe Excel**; é preciso reimplementar posicionamento e medição fora do Excel, e as medidas (pontos/pixels/EMU, largura de coluna em "caracteres") deixam de vir prontas.

### 4.2 Experimentos já feitos (descartáveis, fora do repo)

1. **openpyxl 3.1.5, `load_workbook(model.xlsx)` → adicionar 1 imagem com `OneCellAnchor` → `save`**:
   - preservou: 179 células mescladas, área de impressão (`$B$2:$F$681`), as duas abas, a imagem existente (agora 2 imagens), `TwoCellAnchor editAs="oneCell"` da imagem original;
   - **perdeu**: `customXml/*` (9 partes), `xl/printerSettings/printerSettings1.bin`; aparentemente também não gravou `xl/sharedStrings.xml` com esse nome (o arquivo recarrega bem; causa não investigada);
   - gerou `oneCellAnchor` e manteve `twoCellAnchor` conforme esperado; o arquivo reabre no openpyxl. **Não abri no Excel** → fidelidade visual **[não verificada]**.
2. **XlsxWriter 3.3.1**: `Worksheet.embed_image` **existe** (insere imagem "dentro da célula"); a classe `Workbook` **não** tem API para abrir arquivo existente (confirmado por introspecção).

### 4.3 Comparação de alternativas

| Critério | xlwings (hoje) | openpyxl | XlsxWriter | OOXML direto (zip+XML) | LibreOffice headless |
|---|---|---|---|---|---|
| Roda sem Excel / em Docker | ✗ | ✓ | ✓ | ✓ | ✓ (imagem maior) |
| Abre o template existente | ✓ | ✓ | **✗ (só cria arquivo novo)** | ✓ | ✓ |
| Preserva mesclagens e área de impressão | ✓ | ✓ (testado, carga) | — (recriar o template inteiro em código) | ✓ (intocado) | **[hipótese]** pode alterar estilos |
| Preserva `customXml`, impressora, extensões | ✓ | ✗ (testado) | — | ✓ | **[hipótese]** |
| Âncora de imagem | Excel decide (`Placement`) | `OneCellAnchor`/`TwoCellAnchor`/`AbsoluteAnchor`, offsets em EMU (testado `OneCell`) | `object_position` 1/2/3, `x_offset` | Total (XML) | via UNO **[hipótese]** |
| Medir linha/coluna | Nativo | Calcular: alturas em pt; larguras em caracteres → px depende da fonte padrão | idem | idem | Nativo |
| "Place in Cell" | Só via macro/`ExecuteMso` | **Não suportado** **[hipótese: confirmar na documentação/código da 3.1.5]** | `embed_image()` ✓, mas só no arquivo novo | Possível via `xl/richData/*` + `xl/metadata.xml` + `vm=` na célula **[hipótese de viabilidade; exige teste no Excel]** | **[hipótese]** não confirmado |
| Esforço | — | Baixo | Alto (recriar 179 mesclagens, estilos, logo, 680 linhas) | Médio-alto | Médio; dependência pesada |

**Leitura (não decisão):** o par mais promissor é **openpyxl para o fluxo "imagem flutuante ancorada"** (já testado: abre o template, mantém layout, ancora). "Place in Cell" real exige **OOXML direto** (pós-processamento do .xlsx) ou recriação com XlsxWriter; ambos precisam de teste no Excel antes de prometer. Alternativa de baixo risco: manter **âncora `oneCell`** (a saída atual já usa `twoCellAnchor editAs="oneCell"`, que "move com a célula, não dimensiona") e tratar "Place in Cell" como recurso opcional.

### 4.4 Outros riscos

| Risco | Detalhe |
|---|---|
| **Paridade visual** | Hoje a escala é feita com medidas reais do Excel. Em outra lib há erro de arredondamento pt↔px↔EMU e dependência da fonte padrão do workbook. Mitigação: teste de "imagem dourada" (comparar âncoras `from/to` e `ext` com a saída xlwings de `relatorio_final3.xlsx`, tolerância definida por você) e conferência manual no Excel |
| **Perda de partes do pacote** | `customXml`/`printerSettings` se perdem no openpyxl (testado). Impacto prático **[hipótese: baixo]**; impressão deve ser conferida |
| **Memória / tamanho** | 133 imagens → saída ~37 MB; openpyxl carrega imagens em memória. Reamostrar com Pillow antes de inserir |
| **Ordenação de fotos** | `getctime` não portátil (X6) |
| **Upload web** | Pastas grandes (centenas de MB) via navegador; precisa limite, streaming, limpeza de diretórios temporários e nomes seguros (path traversal) |
| **Concorrência** | Hoje 1 usuário/1 Excel. Em servidor: diretório de trabalho por job, fila ou geração em *thread*/processo, progresso por SSE/WebSocket |
| **Ferramentas nesta máquina** | `uv` e `node` presentes; **`mise` e `docker` ausentes** → `mise run ...` e testes de container não podem ser validados aqui sem instalar |
| **Windows + Excel** | Se o uso diário continuar Windows com Excel, manter xlwings como *backend opcional* tem custo; decisão sua (D2/D4) |
| **WIP conflitante** | `main.py`, `package.json` (Tailwind), `CRIAR_FRONTEND.bat` seguem direção própria; Fase 4 pede avaliar bundler/biblioteca |

### 4.5 Experimentos propostos para a Fase 5 (antes de escolher o backend)

1. Reproduzir uma seção (ex.: Entorno, fit-to-box) e uma fixa (Geral da obra) com openpyxl e comparar `from/to/ext` com `relatorio_final3.xlsx`.
2. Abrir o resultado no Excel e checar: sobreposição de colunas (X8), impressão (área, margens), tamanho do arquivo.
3. Prova mínima de `richData` (Place in Cell) em um .xlsx de 1 imagem, aberto no Excel.
4. Foto de celular com EXIF de rotação (X5).

---

## 5. O que não foi verificado

- Nenhuma execução do fluxo real (Excel/xlwings/Streamlit) e nenhuma abertura de arquivo no Excel.
- `pytest` não foi executado (não instalado no `.venv`); falhas de teste citadas vêm de leitura.
- Todas as marcas **[hipótese]** acima.
- Comportamento de `xlwings.pictures.add` quando só `width` é passado (proporção da altura) — inferido, não testado.
- Capacidade real de cada seção do `model.xlsx` (X7).

## 6. Decisões que dependem de você

1. **Baseline:** o WIP não rastreado (`main.py`, `.bat` novos, `package.json`, testes) é ponto de partida ou descartável? Sugestão: descartar o que não for reaproveitado e comitar só o necessário.
2. **Fidelidade visual:** pixel-exata em relação ao xlwings ou "visualmente equivalente"? Define openpyxl vs OOXML direto vs LibreOffice.
3. **"Colocar na Célula":** requisito obrigatório ou desejável?
4. **Plataforma de uso diário:** continua Windows com Excel (xlwings como backend opcional) ou passa a ser Linux/Docker sem Excel?
5. **Dados de exemplo:** `test/` (ignorado) e `templates/relatorio_final*.xlsx` (~110 MB locais) — manter fora do repo e usar geradores de imagem em `tests/fixtures`?
6. **Limpeza do `.gitignore`:** confirmar remoção dos padrões amplos `generate*.py`/`setup*.py`.
7. **Branch:** edições seguem em branch própria (`chore/audit-phase-2` neste momento). Nada foi commitado.

*Parado aqui, aguardando sua aprovação para a Fase 5 (plano em etapas).*
