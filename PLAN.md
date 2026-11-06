# PLAN — migração para FastAPI + React + uv + mise

Base: `AUDIT.md` (aprovado). Regras: branch própria por etapa, commits atômicos em inglês **sem co-autoria**, lint + testes ao final de cada etapa, README em português atualizado nas etapas marcadas **[README]**.

## Premissas (suas respostas às decisões do AUDIT §6 não vieram; uso estes padrões, corrija se discordar)

| # | Padrão adotado | Impacto se mudar |
|---|---|---|
| D1 | WIP não rastreado (`main.py`, `.bat` novos, `package.json`, testes soltos) **não é baseline**; fica intocado até a Etapa 12, quando você confirma a remoção | Nenhum até lá |
| D2 | Fidelidade "visualmente equivalente", com tolerância numérica de âncora definida na Etapa 7 (proposta: ±2 px) | Se pixel-exata, E7 passa a exigir validação no Excel por amostra |
| D3 | "Colocar na Célula" **desejável**: experimento isolado na Etapa 13, fora do caminho crítico | Se obrigatório, sobe para antes da E7 e pode mudar o backend |
| D4 | Uso diário em **Linux/Docker ou Windows sem Excel**; xlwings sai do produto | Se precisar de Excel, E7 ganha um segundo backend atrás da mesma interface |
| D5 | Arquivos de ~110 MB e `test/` ficam fora do repo; fixtures pequenas geradas por código | — |
| D6 | `.gitignore` como está | — |

## Decisões técnicas (a justificar/confirmar)

**Motor de planilha:** interface `SheetImageWriter` (Protocol) com implementação `OpenpyxlWriter` (âncora `oneCell`, medidas calculadas). Motivo: único candidato testado que abre o template mantendo mesclagens e área de impressão (AUDIT §4.2). Aceita-se a perda de `customXml`/`printerSettings` até prova de impacto (verificada na E7). A interface permite trocar por OOXML direto (E13) sem mexer no resto.

**Bundler:** **Vite**. É uma SPA sem SSR, o build gera arquivos estáticos que o FastAPI serve (uma única URL, sem Node em produção). Next.js/Remix trariam servidor Node extra; CRA está descontinuado.

**Biblioteca de componentes:** **Mantine** (+ `@mantine/form`, `@mantine/dropzone`, `@mantine/notifications`). O fluxo guiado precisa de Stepper, Dropzone, formulário com validação e notificações; o Mantine entrega isso com tipagem TS e tema, sem montar tudo à mão. Rejeitados: shadcn/ui + Tailwind (mais montagem, e o Tailwind do WIP é a v4, instável com o setup atual) e MUI (mais pesado, API mais verbosa). Complementos: TanStack Query (estado do servidor), Vitest + Testing Library, ESLint + Prettier, tipos gerados do OpenAPI (`openapi-typescript`).

**Execução única:** `mise run start` sobe API + frontend já compilado em `http://localhost:8000`. Sem Docker e sem Python/`mise` instalados **não é possível** cumprir "sem instalar nada"; isso só se fecha com Docker (Etapa 14) ou com um instalador que embuta `uv`. Decisão aberta **D7** abaixo.

## Estrutura alvo

```
pyproject.toml  uv.lock  mise.toml  .python-version  ruff/pyright em pyproject
src/report_works/
  domain/      # models Pydantic (Section, LayoutSettings, ReportConfig), erros
  services/    # photo_discovery, template_inspector, layout_planner, report_builder, jobs
  adapters/    # openpyxl_writer, filesystem (workdir), settings (env)
  api/         # routers FastAPI, schemas, dependências
  i18n/pt_br.py   # todas as strings de usuário
tests/         # unit, integration, golden
frontend/      # Vite + React + TS
docs/docker/   # Dockerfile.sketch e compose.sketch.yaml (inativos)
```
Camadas: `domain` não importa nada; `services` só importa `domain` e interfaces; `adapters`/`api` dependem de `services`. Nenhuma importação de `tkinter`, `xlwings`, `win32`.

## Etapas

Cada etapa = 1 branch (`feat/...`) e 1+ commits atômicos; critério de aceite sempre inclui `ruff check`, `ruff format --check`, `pyright` e `pytest` verdes (e `eslint`/`vitest` a partir da E10).

| # | Etapa | Entrega | Critério de aceite |
|---|---|---|---|
| 1 | **Golden de referência** | Script que extrai de um `.xlsx` as âncoras (`from/to/ext`, aba, altura de linhas) para JSON. Referência = `templates/relatorio_final3.xlsx` (saída antiga) + `config.yaml` + `C:/dev/Synderski/images_organized`. Descreve como gerar nova referência com o fluxo antigo | JSON golden versionado (pequeno); 132 fotos + 1 logo reconhecidos; script com teste |
| 2 | **Esqueleto de tooling** [README] | `pyproject.toml`, `uv.lock`, `.python-version`, `mise.toml` (`dev`, `test`, `lint`, `build`), ruff, pyright, pytest; remover `requirements.txt` e `requirements-dev.txt`; mover os 2 testes válidos para `tests/` | `uv sync` limpo; `mise run lint` e `mise run test` verdes (ou equivalentes `uv run` se `mise` não estiver instalado — registro no relatório) |
| 3 | **Domínio + strings** | Modelos Pydantic (`ReportConfig`, `LayoutSettings`, `SectionConfig` com `kind: grid \| grouped`, `floors`), erros de domínio, `i18n/pt_br.py` | Carrega `config_exemple.yaml` e rejeita: `id` inválido, `max_photos<1`, colunas vazias; testes cobrindo cada rejeição; nenhum parâmetro de layout fixo fora do modelo |
| 4 | **Descoberta de fotos** | `photo_discovery`: extensões configuráveis, ordenação `name`/`exif`/`mtime`, sem `print` | Testes sem `sleep` (usa `os.utime`); pasta ausente → erro de domínio |
| 5 | **Inspeção e validação do template** | `template_inspector` (openpyxl somente leitura): lista abas, candidatos de título em B, duplicatas, capacidade de cada seção | Sobre `model.xlsx`: encontra os 6 títulos, acusa "Geral da obra" duplicado, calcula capacidade; testes |
| 6 | **Planejador de layout (puro)** | `layout_planner`: transforma seções+fotos em lista de `Slot(cell, largura, altura)`; sem I/O | Reproduz as posições (célula âncora) do golden para as 6 seções; função ≤ 30 linhas cada; testes de grade e pavimentos |
| 7 | **Escrita com openpyxl** | `OpenpyxlWriter`: medidas pt/px/EMU, fit-to-box e largura fixa, âncora `oneCell`, reamostragem Pillow (lado maior configurável) | Saída vs golden dentro da tolerância (D2); arquivo bem menor que 37 MB; abre no openpyxl; **checagem manual no Excel** por você (procedimento no README); lista do que se perdeu (`customXml`, impressora) |
| 8 | **Serviço de relatório + progresso** | `report_builder` orquestra E4–E7; eventos de progresso; erros por foto coletados; falha se 0 fotos | Progresso chega a 100% no cenário do exemplo (119/120 resolvido); teste de 0 fotos falha como esperado |
| 9 | **API FastAPI** [README] | Rotas: upload de template, upload de fotos (zip), `POST /validate`, `POST /jobs`, SSE de progresso, download; configuração por variáveis de ambiente (`REPORT_WORKDIR`, `REPORT_MAX_UPLOAD_MB`, `CORS_ORIGINS`); limpeza do workdir | Testes com `TestClient`; path traversal bloqueado em teste; OpenAPI exportado; sem tkinter |
| 10 | **Esqueleto do frontend** | `frontend/` Vite+React+TS+Mantine, tipos gerados do OpenAPI, ESLint/Prettier, Vitest; tarefas `mise` | `mise run build` gera `frontend/dist`; um teste Vitest verde |
| 11 | **Fluxo guiado** [README] | Passos: Template → Fotos → Seções → Validação → Gerar/Baixar. Validação em tempo real: títulos existem, pastas existem, contagem × capacidade, duplicatas. Textos só via arquivo de strings | Teste de componente por passo; cenário "título inexistente" bloqueia o botão e aponta o erro |
| 12 | **Integração e limpeza** [README] | FastAPI serve `frontend/dist`; `mise run start`; remover Streamlit, `app.py`, `scripts/`, `main.py` do WIP, `.bat`, `macro.txt` (**com sua confirmação do que apagar**) | Comparação final: mesmas entradas do E1 → relatório novo vs golden (relatório de diferenças); validação manual no Excel |
| 13 | **Experimento "Place in Cell"** (opcional) | Prova mínima com `richData` em 1 imagem, aberta no Excel; só então decide se vira opção | Relatório com resultado; **nada** vai ao produto sem sua aprovação |
| 14 | **Docker (esboço inativo)** [README] | `docs/docker/Dockerfile.sketch` e `compose.sketch.yaml` (abaixo), sem ativar | Revisão sua; `docker build` fica fora do escopo por não haver Docker nesta máquina |

Dependências: 1→(2..)→3→4,5→6→7→8→9→10→11→12→14; 13 depende de 7.

## Esboço futuro (não ativado)

```dockerfile
# docs/docker/Dockerfile.sketch
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
ENV REPORT_WORKDIR=/data REPORT_STATIC_DIR=/app/frontend/dist HOST=0.0.0.0 PORT=8000
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
      CORS_ORIGINS: ""
    volumes:
      - report_data:/data
volumes:
  report_data:
```

## Riscos e pontos em aberto

- **D7:** "um comando sem instalar Python" só se cumpre com Docker (E14) ou instalador que embuta `uv`. Até lá, o requisito mínimo é `mise` (ou `uv`) instalado. Qual caminho prefere para Windows sem Docker?
- **`mise` e `docker` não estão instalados** nesta máquina; instalar `mise` é pré-requisito para validar `mise run ...` (senão uso `uv run` equivalente e aviso).
- **Tolerância e paridade (E7)** dependem do seu aceite visual no Excel.
- **ai-memory:** não encontrei ferramenta com esse nome; uso a memória de arquivos do Claude Code até você indicar o que é (CLI/MCP/caminho).
- Não verificado: `pytest`/`ruff`/`pyright` ainda não rodaram (nada instalado no `.venv`).
