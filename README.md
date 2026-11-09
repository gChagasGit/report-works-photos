# Gerador de Relatórios Fotográficos: Engenharia CESIN / Banco do Brasil

Este projeto é uma solução de automação em Python desenvolvida para otimizar a elaboração de **Relatórios de Acompanhamento de Empreendimentos** do Banco do Brasil. A ferramenta automatiza a tarefa repetitiva de preenchimento, identificando seções específicas em templates `.xlsx` e inserindo imagens organizadas de forma inteligente, ajustando automaticamente o layout e as dimensões conforme as exigências técnicas.

### Contexto e Aplicação

No âmbito da engenharia do **CESIN (Central de Serviços Imobiliários)**, o relatório fotográfico é um documento mandatório para o monitoramento de obras e vistorias de ativos vinculados ao Banco do Brasil. Ele serve como lastro para o acompanhamento de medições, custos diretos e a conformidade técnica da construção.

---

## Pré-requisitos

Para que o gerador funcione corretamente, você precisa garantir que possui:

*   **uv**: gerenciador de Python e dependências ([instruções](https://docs.astral.sh/uv/)). Ele instala o Python 3.12 sozinho; não é preciso instalar o Python à parte.
*   **Microsoft Excel** (Microsoft 365), instalado localmente: o relatório é montado pelo Excel (recurso "Colocar na Célula"). Ver `docs/spikes/place-in-cell.md`.
*   **Node.js 20 ou superior**, apenas na primeira execução, para compilar a interface (`frontend/dist`).

---

## Como Instalar e Rodar

1.  **Obtenha o projeto**:
    *   Baixe o [arquivo **.zip**](https://github.com/gChagasGit/report-works-photos/archive/refs/heads/main.zip) do repositório e descompacte-o em uma pasta de sua preferência.
    *   *Ou* clone o repositório via terminal: `git clone https://github.com/gChagasGit/report-works-photos.git`

2.  **Inicie a Aplicação**:
    *   Clique duas vezes em **`INICIAR_APP.bat`** (ou rode `uv run python -m report_works --open`).
    *   **Na primeira execução**: `uv sync` instala as dependências e a interface é compilada (`npm ci` e `npm run build`). Isso pode levar alguns minutos; nas próximas vezes o início é imediato.

3.  **Use a interface**:
    *   O navegador abre em `http://127.0.0.1:8000` (se não abrir, digite o endereço). A interface e a API ficam na mesma URL; a documentação interativa da API fica em `/docs`.
    *   A interface Streamlit antiga (`uv run streamlit run app.py`, `http://localhost:8501`) ainda existe, mas será removida (ver `docs/migration-cleanup.md`).

4.  **Encerrar**:
    *   Para desligar o servidor, volte ao terminal (tela preta) e pressione **CTRL+C**.

### API e configuração

O servidor FastAPI substitui o Streamlit. Para subir: `uv run python -m report_works` (`--open` abre o navegador; a interface compilada em `frontend/dist` é servida em `/` automaticamente). Ele usa o Excel instalado (modo "Colocar na Célula") e gera o relatório em segundo plano.

Configuração por variáveis de ambiente (nada de `.bat` ou edição de arquivos):

| Variável | Padrão | Significado |
|---|---|---|
| `REPORT_WORKDIR` | `./work` | pasta de envios e relatórios (`work/` não é versionada) |
| `REPORT_MAX_UPLOAD_MB` | `2048` | limite de cada envio |
| `CORS_ORIGINS` | vazio | origens permitidas, separadas por vírgula |
| `REPORT_STATIC_DIR` | vazio | frontend compilado, servido em `/` |
| `REPORT_HOST` / `REPORT_PORT` | `127.0.0.1` / `8000` | endereço do servidor |
| `REPORT_RETENTION_HOURS` | `24` | tempo de guarda das áreas de trabalho |

Fluxo da API: `POST /api/workspaces` → `PUT .../template` (envia o `.xlsx` e recebe abas e títulos) → `POST .../photos/zip` (uma pasta por seção; o nome da pasta é o `id`, em minúsculas) ou `POST .../photos/{id}` → `POST .../validate` (títulos, pastas, contagens e espaço no layout, em português) → `POST /api/jobs` → `GET /api/jobs/{id}/events` (andamento em tempo real) → `GET /api/jobs/{id}/download`. A seção em `config_exemple.yaml` pode ser enviada como corpo da validação e da geração (sem `paths`). O modo `image_mode: in_cell` (padrão) coloca cada foto dentro da célula, já enquadrada na proporção do bloco (ver `docs/spikes/place-in-cell.md`).

### Interface web

A interface em `frontend/` (React + TypeScript + Mantine) substitui o Streamlit. Em desenvolvimento, use dois terminais: `mise run dev` (ou `uv run python -m report_works`) para a API e `mise run dev-web` (ou `npm --prefix frontend run dev`) para a interface em `http://localhost:5173`. Sem `mise`: `uv sync` e `npm --prefix frontend ci` preparam as dependências.

O fluxo é guiado em cinco passos, sem diálogos do sistema operacional:

1.  **Template**: envie o `.xlsx`; a interface mostra as abas e os títulos encontrados na coluna B.
2.  **Fotos**: envie um ZIP com uma pasta por seção (o nome da pasta é o `id` da seção); também é possível enviar fotos de uma seção em **Seções**.
3.  **Seções**: defina pasta, título, máximo de fotos e opções. O título é conferido **na hora** contra o template (aceita diferença de maiúsculas e espaços) e o `id` é validado; as contagens de fotos aparecem por pasta.
4.  **Conferência**: o servidor confere títulos, pastas, contagem de fotos e espaço no layout a cada alteração; problemas que impedem a geração bloqueiam o avanço.
5.  **Gerar**: acompanha o andamento e oferece o download do relatório.

Quando o contrato da API muda, regenere os tipos com `mise run api-types` (ou `uv run python -m report_works.export_openapi frontend/openapi.json` e `npm --prefix frontend run api:types`); um teste do backend avisa se o contrato versionado ficou desatualizado.

### Comandos de desenvolvimento

*   Testes: `uv run pytest`
*   Lint, formatação e tipos: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`
*   O arquivo `mise.toml` define as mesmas tarefas (`mise run test`, `mise run lint`, ...) para quem usa o [mise](https://mise.jdx.dev/).

---

## Como Usar a Interface (Streamlit)

A interface foi projetada para ser intuitiva. Siga os passos abaixo:

1.  **Configuração de Caminhos**:
    *   **Template Excel**: Selecione o arquivo `.xlsx` que servirá de modelo (deve conter os títulos das seções previamente escritos).
    *   **Pasta Raiz das Imagens**: Selecione a pasta principal que contém as subpastas das imagens organizadas por seção.

2.  **Definição de Seções**:
    *   Se for sua primeira vez, você pode usar as configurações sugeridas ou adicionar novas clicando em **"Adicionar Nova Seção"**.
    *   **Nome da Pasta**: Deve ser o nome exato da subpasta onde estão as fotos.
    *   **Título no Excel**: Deve ser exatamente igual ao texto escrito na célula do Excel onde a seção começa.
    *   **Máx. de Fotos**: Limite de imagens para aquela seção.
    *   **Fixar Largura?**: Se marcado, a imagem será redimensionada para ocupar toda a largura da célula.
    *   **Pavimentos (Especial)**: Se a seção for de pavimentos, insira a distribuição (ex: `4, 6, 2`) para indicar quantas fotos cada andar possui.

3.  **Gerar Relatório**:
    *   Clique no botão **"GERAR RELATÓRIO"**. 
    *   O sistema salvará suas preferências no arquivo `config.yaml` (sobrescrevendo-o para usos futuros).
    *   O Excel será aberto e você poderá acompanhar a inserção em tempo real através da **barra de progresso** na interface.

---

## Dica Extra: Simular "Place in Cell" (Macro)

Caso o seu Excel não possua a função nativa de "Colocar na Célula" de forma satisfatória, disponibilizamos o arquivo **`macro.txt`**. 

*   Copie o código contido neste arquivo.
*   No Excel, abra o Editor do Visual Basic (ALT + F11).
*   Insira um novo Módulo e cole o código.
*   Isso permitirá replicar a funcionalidade de ajuste fino das imagens dentro das células.

---

## Estrutura de Pastas Sugerida

Para um funcionamento ideal, organize suas fotos assim:
```text
Minha_Obra/
├── Seção_A/
│   ├── foto1.jpg
│   └── foto2.jpg
└── Seção_B/
    ├── foto1.jpg
    └── foto2.jpg
```

---

## Desenvolvimento: memória do projeto com ai-memory

O progresso da refatoração é registrado no [ai-memory](https://github.com/akitaonrails/ai-memory) (instalação local, sem LLM e sem chave de API).

*   **Marcador do projeto**: o arquivo `.ai-memory.toml` (workspace `synderski`, projeto `report-works-photos`) autoriza a captura apenas neste repositório e lista os caminhos que nunca são capturados. Ele não é versionado (está no `.gitignore`).
*   **Captura em modo allowlist**: repositórios sem `.ai-memory.toml` não enviam nenhum evento.
*   **Recomendação**: inicie os agentes pelo comando `ai-memory run <agente>` (por exemplo, `ai-memory run claude-code` ou `ai-memory run antigravity-cli`) para que a sessão fique associada ao projeto e possa ser retomada. Os hooks também funcionam quando o agente é aberto pela extensão ou IDE, mas essa forma não foi validada com o `run`.
*   **Verificação**: `ai-memory status` e `ai-memory doctor`. Após reiniciar o agente, pergunte: "What do you remember about this project?".
