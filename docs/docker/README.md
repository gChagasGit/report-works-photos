# Docker (esboço inativo)

Estes arquivos preparam o projeto para rodar em container **sem retrabalho**, mas **não estão ativos**: nenhum foi construído ou executado (não há Docker na máquina de desenvolvimento).

| Arquivo | O que é |
|---|---|
| `Dockerfile.sketch` | Imagem em dois estágios: compila a interface (Node 22) e monta o ambiente Python com `uv` (sem Excel e sem dependências de desenvolvimento), usuário sem privilégios, `HEALTHCHECK` em `/api/health` |
| `compose.sketch.yaml` | Um serviço, porta só em `127.0.0.1`, volume `report_data` em `/data`, sistema de arquivos somente leitura |
| `dockerignore.sketch` | Conteúdo para o `.dockerignore` (fora da imagem: fotos, relatórios, `node_modules`, `.git`...) |

## O que já está pronto para o container

- Configuração **só por variáveis de ambiente** (`REPORT_WORKDIR`, `REPORT_MAX_UPLOAD_MB`, `CORS_ORIGINS`, `REPORT_STATIC_DIR`, `REPORT_HOST`, `REPORT_PORT`, `REPORT_RETENTION_HOURS`); um teste confere que o Dockerfile e o compose só usam variáveis que o código lê.
- Caminhos configuráveis e nenhuma dependência de interface gráfica do sistema operacional (sem `tkinter`); envio de template e fotos pelo navegador.
- A interface compilada é servida pela própria API (uma única URL).
- `xlwings` só é instalado em Windows (marcador no `pyproject.toml`), então a imagem Linux instala sem ele.

## O que impede de ativar hoje (decisão sua)

**O modo "Colocar na Célula" depende do Microsoft Excel** (COM, via `xlwings`), que não roda em container Linux. Hoje o `XlwingsWriter` é o único escritor de imagens; num container ele falharia com a mensagem "A automação do Excel não está disponível".

Para ativar o Docker é preciso um segundo escritor de imagens que **não use o Excel**, atrás da mesma interface `ImageWriter` (`src/report_works/services/ports.py`), e a API escolher o escritor por configuração. O spike `docs/spikes/place-in-cell.md` lista os candidatos, **todos hipóteses ainda não testadas**:

- Escrever as partes `xl/richData/*` e `xl/metadata.xml` direto no `.xlsx` (OOXML), que é o formato que o Excel gerou nos testes. Exige provar a viabilidade abrindo o resultado no Excel.
- `XlsxWriter.embed_image()`: cria "imagem em célula", mas só em arquivo novo (não abre o template).
- `openpyxl`: abre o template, mas insere imagens flutuantes; hipótese de que descarta `richData`.

Enquanto isso, o modo `image_mode: floating` pode ser a base de um escritor sem Excel (imagem ancorada, sem "Colocar na Célula"), o que **não atende** ao requisito de colocar na célula.

## Como ativar quando houver escritor sem Excel

1. `cp docs/docker/Dockerfile.sketch Dockerfile` e `cp docs/docker/dockerignore.sketch .dockerignore`.
2. Ligar o novo escritor em `create_app` (por exemplo, `REPORT_WRITER=ooxml`).
3. `docker compose -f docs/docker/compose.sketch.yaml up --build` e abrir `http://127.0.0.1:8000`.
4. Validar no Excel o relatório baixado (roteiro em `docs/migration-cleanup.md`).
