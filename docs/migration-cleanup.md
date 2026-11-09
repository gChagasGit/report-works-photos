# Limpeza da migração: arquivos candidatos à remoção

**Nada disto foi apagado.** A remoção depende da sua confirmação (decisão do plano, Etapa 10). Cada item diz o que o substitui e como conferir antes de apagar.

| Arquivo ou pasta | Papel antigo | Substituído por | Conferir antes de apagar |
|---|---|---|---|
| `app.py` | Interface Streamlit (UI + regra + I/O no mesmo arquivo) | `frontend/` (React) + `src/report_works/api/` | Gerar um relatório pela nova interface (`INICIAR_APP.bat`) |
| `scripts/report_engine.py` | Motor xlwings acoplado ao YAML e ao Excel visível | `services/layout_planner.py`, `services/report_builder.py` e `adapters/xlwings_writer.py` | Testes do plano contra o relatório antigo (`tests/unit/services/test_layout_planner.py`) |
| `scripts/image_handler.py` | Listagem e ordenação de fotos | `services/photo_discovery.py` | Testes de ordenação (EXIF → data de modificação → nome) |
| `scripts/run_report.py` | CLI duplicada que apagava o relatório anterior sem perguntar | API (`POST /api/jobs`) | — |
| `main.py` (raiz) | API de configuração com diálogos `tkinter` | `src/report_works/api/` e `python -m report_works` | — |
| `macro.txt` | Macro VBA copiada à mão para "Colocar na Célula" | Modo `image_mode: in_cell` do `XlwingsWriter` | `docs/spikes/place-in-cell.md` |
| Grupo `legacy` em `pyproject.toml` (`streamlit`) | Dependência do Streamlit | — | Remover junto com `app.py` e rodar `uv sync` |
| `test/` (local, ignorado) e `templates/relatorio_final*.xlsx` | Saídas e scripts de teste manuais (~110 MB) | Fixtures geradas por código; `tests/golden/*.json` | Já estão fora do repositório |
| `CRIAR_FRONTEND.bat`, `COPIAR_PROJETO.bat`, `package.json`, `package-lock.json` e `__init__.py` da raiz (locais, ignorados) | Restos da tentativa anterior de frontend | `frontend/` | Já estão ignorados pelo Git; pode apagar do disco |

## Resultado já comparado com o fluxo antigo

- Plano de posições do `config_exemple.yaml` x `relatorio_final3.xlsx` (relatório gerado pelo fluxo antigo): 132 fotos nos dois; 128 caem exatamente na célula planejada (as 119 dos pavimentos inclusive); as 4 de "Projetos/ARTs" (ajuste à caixa, imagem centralizada) variam -1 ou +2 linhas.
- Relatório gerado pelo fluxo novo no Excel real, com as mesmas seções e 132 fotos sintéticas: 132 imagens em célula, exatamente nas células planejadas, 468 KB (o antigo tinha ~37 MB).

## Como validar manualmente no Excel (recomendado antes de apagar)

1. Gere um relatório com o fluxo **antigo** (Streamlit) e outro com o **novo**, usando o mesmo template e as mesmas fotos.
2. Abra os dois no Excel e confira, seção por seção: título, quantidade de fotos, ordem, e se cada foto está no bloco certo e sem distorção.
3. No relatório novo, as fotos ficam dentro das células (selecione uma célula: a imagem é o conteúdo dela); no antigo, flutuam sobre a planilha.
4. Diferenças esperadas: ordenação por data usa a data da foto (EXIF) em vez da data de criação do arquivo; imagens do relatório novo são reduzidas (maior lado 1600 px) e enquadradas com margem branca.
