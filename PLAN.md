# PLAN — migração para FastAPI + React + uv (revisão 2, decisões D1–D5)

Base: `AUDIT.md` (aprovado). Regras: branch própria por etapa, commits atômicos em inglês **sem co-autoria**, lint + testes ao final de cada etapa, README em português atualizado nas etapas marcadas **[README]**, página de progresso gravada no ai-memory ao fim de cada etapa.

## Decisões do usuário (2026-11-05)

| # | Decisão | Consequência no plano |
|---|---|---|
| D1 | O trabalho novo não rastreado é o ponto de partida | Etapa 0 versiona `main.py`, testes e `.bat` como baseline. `package.json`/Tailwind e `__init__.py` da raiz ficam de fora (o frontend é recriado na E8) |
| D2 | Sem exigência de fidelidade visual, só o mesmo resultado | Comparação com o golden por **posição de célula, ordem e quantidade de fotos**, não por pixel |
| D3 | "Colocar na Célula" obrigatório (copiar e colar a imagem dentro da célula) | Spike dedicado na E6, antes da API. O resultado decide o motor |
| D4 | Foco inicial: Excel do Windows | **xlwings continua como motor inicial**, atrás de uma interface (`SheetImageWriter`); Docker/Linux fica para depois |
| D5 | Arquivos pesados e `test/` fora do repo | Fixtures pequenas geradas por código |

## Decisões técnicas

- **Motor:** interface `SheetImageWriter` (Protocol). Implementação inicial `XlwingsWriter` (porta a lógica atual, só Windows+Excel). Um segundo backend (openpyxl/OOXML, sem Excel) só entra se o spike de "Colocar na Célula" ou o Docker exigirem.
- **Bundler:** Vite (SPA; o FastAPI serve o build estático em uma única URL). **Componentes:** Mantine (+ `@mantine/form`, `dropzone`, `notifications`), TanStack Query, Vitest + Testing Library, ESLint + Prettier, tipos gerados do OpenAPI.
- **Arquivos locais no Windows:** como o servidor roda na mesma máquina, a API aceita **upload** (compatível com Docker) e a interface oferece escolher arquivo/pasta pelo navegador. Nada de tkinter.
- **Execução:** `uv run` / tarefas `mise` (o `mise` não está instalado; uso `uv run` e documento o equivalente até você instalar).

## Estrutura alvo

```
pyproject.toml  uv.lock  mise.toml  .python-version
src/report_works/{domain,services,adapters,api,i18n}/
tests/{unit,integration,golden}/
frontend/        # Vite + React + TS
docs/docker/     # Dockerfile.sketch e compose.sketch.yaml (inativos)
```
`domain` não importa nada; `services` só importa `domain` e interfaces; `adapters`/`api` dependem de `services`. Importação de `tkinter` proibida; `xlwings`/`win32` só em `adapters`.

## Etapas

| # | Etapa | Entrega | Critério de aceite |
|---|---|---|---|
| 0 | **Baseline** | Commit do WIP aprovado (D1) numa branch `chore/baseline`; descarte (sem apagar do disco) de `package.json`, `package-lock.json`, `node_modules/`, `__init__.py` raiz, `CRIAR_FRONTEND.bat` e `COPIAR_PROJETO.bat` do versionamento | `git status` limpo; nada de segredo/foto versionado |
| 1 | **Tooling** [README] | `pyproject.toml`, `uv.lock`, `.python-version`, `mise.toml`, ruff, pyright, pytest; remover `requirements*.txt`; mover testes para `tests/`; corrigir `pytest.ini` | `uv sync` limpo; `ruff check`, `ruff format --check`, `pyright`, `pytest` verdes |
| 2 | **Golden** | Script que extrai de um `.xlsx` a lista de (aba, célula âncora, ordem, nome da imagem) e gera JSON; golden a partir de `templates/relatorio_final3.xlsx` | 132 fotos + logo reconhecidos; teste do extrator com xlsx sintético |
| 3 | **Domínio + strings** | Modelos Pydantic (`ReportConfig`, `LayoutSettings`, `SectionConfig` com `kind: grid \| grouped`), erros de domínio, `i18n/pt_br.py` | Carrega `config_exemple.yaml`; rejeita `id` inválido, `max_photos<1`; sem layout fixo fora do modelo |
| 4 | **Fotos + inspeção do template** | `photo_discovery` (extensões, ordem `name`/`exif`/`mtime`) e `template_inspector` (abas, títulos em B, duplicatas, capacidade) | Testes sem `sleep`; `model.xlsx`: acha os 6 títulos e acusa "Geral da obra" duplicado |
| 5 | **Planejador + XlwingsWriter** | `layout_planner` puro (seção+fotos → slots) e `XlwingsWriter` com `try/finally` e `quit()` | Planejador reproduz as células do golden; teste do writer com xlwings mockado; execução real no Excel fica marcada como verificação manual |
| 6 | **Spike "Colocar na Célula"** | Experimento isolado (COM `ExecuteMso PicturePlaceInCell`, alternativa OOXML `richData`) em arquivo descartável | Relatório curto: o que funciona/não, em qual versão do Excel; decisão sua antes de seguir |
| 7 | **Serviço + API FastAPI** [README] | `report_builder` com progresso; rotas: upload, `POST /validate`, `POST /jobs`, SSE de progresso, download; configuração por variáveis de ambiente | `TestClient` verde; path traversal bloqueado; 0 fotos falha; progresso chega a 100% |
| 8 | **Frontend: esqueleto** | `frontend/` Vite+React+TS+Mantine, tipos do OpenAPI, ESLint/Prettier, Vitest | `npm run build` gera `dist`; 1 teste Vitest verde |
| 9 | **Frontend: fluxo guiado** [README] | Template → Fotos → Seções → Validação → Gerar/Baixar, validação em tempo real, textos só em arquivo de strings | Teste por passo; título inexistente bloqueia o botão |
| 10 | **Integração e limpeza** [README] | FastAPI serve `frontend/dist`; um comando para subir tudo; remover Streamlit, `app.py`, `scripts/`, `.bat` antigos e `macro.txt` (**com sua confirmação**) | Mesmas entradas do golden → resultado equivalente; validação manual no Excel |
| 11 | **Docker (esboço inativo)** [README] | `docs/docker/*.sketch` | Revisão sua |

## Esboço futuro (não ativado)

```dockerfile
# docs/docker/Dockerfile.sketch (exige backend sem Excel, ver E6)
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY src ./src
COPY --from=web /web/dist ./frontend/dist
ENV REPORT_WORKDIR=/data REPORT_STATIC_DIR=/app/frontend/dist
EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "report_works.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```
```yaml
# docs/docker/compose.sketch.yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    environment:
      REPORT_WORKDIR: /data
      REPORT_MAX_UPLOAD_MB: "2048"
    volumes: [report_data:/data]
volumes:
  report_data:
```

## Riscos e pontos em aberto

- "Um comando sem instalar Python" só se cumpre com Docker (E11) ou um instalador que embuta `uv`.
- `mise` e `docker` não estão instalados; execução real no Excel não pode ser automatizada aqui.
- O `config.yaml` local aponta para `C:/dev/...` (inexistente); caminhos reais estão em `D:/dev/...`.
- Antigravity ainda não validou o ai-memory; embeddings aguardam reinício do servidor.
