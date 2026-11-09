# Limpeza da migraÃ§Ã£o: arquivos legados removidos

**Removidos em 2026-11-09, com a confirmaÃ§Ã£o do dono do projeto:** `app.py`, `scripts/`, `main.py`, `macro.txt`, os testes do motor antigo e o grupo `legacy` (Streamlit). Continuam no histÃ³rico do Git; para recuperar um arquivo: `git checkout <commit-anterior> -- <caminho>`. A tabela abaixo registra o que substituiu cada item.

| Arquivo ou pasta | Papel antigo | SubstituÃ­do por | Como conferir |
|---|---|---|---|
| `app.py` | Interface Streamlit (UI + regra + I/O no mesmo arquivo) | `frontend/` (React) + `src/report_works/api/` | Gerar um relatÃ³rio pela nova interface (`INICIAR_APP.bat`) |
| `scripts/report_engine.py` | Motor xlwings acoplado ao YAML e ao Excel visÃ­vel | `services/layout_planner.py`, `services/report_builder.py` e `adapters/xlwings_writer.py` | Testes do plano contra o relatÃ³rio antigo (`tests/unit/services/test_layout_planner.py`) |
| `scripts/image_handler.py` | Listagem e ordenaÃ§Ã£o de fotos | `services/photo_discovery.py` | Testes de ordenaÃ§Ã£o (EXIF â†’ data de modificaÃ§Ã£o â†’ nome) |
| `scripts/run_report.py` | CLI duplicada que apagava o relatÃ³rio anterior sem perguntar | API (`POST /api/jobs`) | â€” |
| `main.py` (raiz) | API de configuraÃ§Ã£o com diÃ¡logos `tkinter` | `src/report_works/api/` e `python -m report_works` | â€” |
| `macro.txt` | Macro VBA copiada Ã  mÃ£o para "Colocar na CÃ©lula" | Modo `image_mode: in_cell` do `XlwingsWriter` | `docs/spikes/place-in-cell.md` |
| Grupo `legacy` em `pyproject.toml` (`streamlit`) | DependÃªncia do Streamlit | â€” | Remover junto com `app.py` e rodar `uv sync` |
| `test/` (local, ignorado) e `templates/relatorio_final*.xlsx` | SaÃ­das e scripts de teste manuais (~110 MB) | Fixtures geradas por cÃ³digo; `tests/golden/*.json` | JÃ¡ estÃ£o fora do repositÃ³rio |
| `CRIAR_FRONTEND.bat`, `COPIAR_PROJETO.bat`, `package.json`, `package-lock.json` e `__init__.py` da raiz (locais, ignorados) | Restos da tentativa anterior de frontend | `frontend/` | JÃ¡ estÃ£o ignorados pelo Git; pode apagar do disco |

## Resultado jÃ¡ comparado com o fluxo antigo

- Plano de posiÃ§Ãµes do `config_exemple.yaml` x `relatorio_final3.xlsx` (relatÃ³rio gerado pelo fluxo antigo): 132 fotos nos dois; 128 caem exatamente na cÃ©lula planejada (as 119 dos pavimentos inclusive); as 4 de "Projetos/ARTs" (ajuste Ã  caixa, imagem centralizada) variam -1 ou +2 linhas.
- RelatÃ³rio gerado pelo fluxo novo no Excel real, com as mesmas seÃ§Ãµes e 132 fotos sintÃ©ticas: 132 imagens em cÃ©lula, exatamente nas cÃ©lulas planejadas, 468 KB (o antigo tinha ~37 MB).

## Como validar manualmente no Excel

1. Gere um relatÃ³rio com o fluxo **novo** e compare com um relatÃ³rio feito pelo fluxo antigo (por exemplo, `templates/relatorio_final3.xlsx`), usando o mesmo template e as mesmas fotos.
2. Abra os dois no Excel e confira, seÃ§Ã£o por seÃ§Ã£o: tÃ­tulo, quantidade de fotos, ordem, e se cada foto estÃ¡ no bloco certo e sem distorÃ§Ã£o.
3. No relatÃ³rio novo, as fotos ficam dentro das cÃ©lulas (selecione uma cÃ©lula: a imagem Ã© o conteÃºdo dela); no antigo, flutuam sobre a planilha.
4. DiferenÃ§as esperadas: ordenaÃ§Ã£o por data usa a data da foto (EXIF) em vez da data de criaÃ§Ã£o do arquivo; imagens do relatÃ³rio novo sÃ£o reduzidas (maior lado 1600 px) e enquadradas com margem branca.
