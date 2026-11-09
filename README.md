# Gerador de Relatórios Fotográficos: Engenharia CESIN / Banco do Brasil

Este projeto é uma solução de automação em Python desenvolvida para otimizar a elaboração de **Relatórios de Acompanhamento de Empreendimentos** do Banco do Brasil. A ferramenta automatiza a tarefa repetitiva de preenchimento, identificando seções específicas em templates `.xlsx` e inserindo imagens organizadas de forma inteligente, ajustando automaticamente o layout e as dimensões conforme as exigências técnicas.

### Contexto e Aplicação

No âmbito da engenharia do **CESIN (Central de Serviços Imobiliários)**, o relatório fotográfico é um documento mandatório para o monitoramento de obras e vistorias de ativos vinculados ao Banco do Brasil. Ele serve como lastro para o acompanhamento de medições, custos diretos e a conformidade técnica da construção.

---

## Pré-requisitos

Para que o gerador funcione corretamente, você precisa garantir que possui:

*   **uv**: gerenciador de Python e dependências ([instruções](https://docs.astral.sh/uv/)). Ele instala o Python 3.12 sozinho; não é preciso instalar o Python à parte.
*   **Microsoft Excel**: Instalado localmente (necessário para a automação via `xlwings`).

---

## Como Instalar e Rodar

1.  **Obtenha o projeto**:
    *   Baixe o [arquivo **.zip**](https://github.com/gChagasGit/report-works-photos/archive/refs/heads/main.zip) do repositório e descompacte-o em uma pasta de sua preferência.
    *   *Ou* clone o repositório via terminal: `git clone https://github.com/gChagasGit/report-works-photos.git`

2.  **Inicie a Aplicação**:
    *   Navegue até a pasta do projeto e localize o arquivo **`INICIAR_APP.bat`**.
    *   Clique duas vezes para executá-lo. 
    *   **Na primeira execução**: O script executa `uv sync`, que cria o ambiente virtual (`.venv`) e instala as dependências do `pyproject.toml`/`uv.lock`. Isso pode levar alguns minutos.

3.  **Acesse a API** (a nova interface web ainda está em construção):
    *   O servidor local inicia em `http://127.0.0.1:8000`; a documentação interativa fica em `http://127.0.0.1:8000/docs`.
    *   A interface Streamlit antiga continua disponível com `uv run streamlit run app.py` (`http://localhost:8501`) até ser substituída.

4.  **Encerrar**:
    *   Para desligar o servidor, volte ao terminal (tela preta) e pressione **CTRL+C**.

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
