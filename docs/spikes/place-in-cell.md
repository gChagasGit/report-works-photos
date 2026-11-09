# Spike: "Colocar na Célula" (Etapa 6)

Requisito do dono do projeto: a foto deve entrar **dentro da célula** (como o recurso "Colocar na Célula" do Excel), sem a macro copiada à mão do `macro.txt`.

**Ambiente do teste (2026-11-09):** Windows 10, Microsoft 365 Excel 16.0 (build 20326, x64), Python 3.12, xlwings 0.37.8. Tudo rodou no Excel real, com arquivos temporários fora do repositório.

## Fatos comprovados

| # | Teste | Resultado |
|---|---|---|
| 1 | Imagem flutuante, `Select()` e `CommandBars.ExecuteMso("PicturePlaceInCell")` via COM | Funciona. O número de `Shapes` da aba vai de 1 para 0 e o pacote passa a ter `xl/richData/*` e `xl/metadata.xml`, com `vm="1"` na célula |
| 2 | Mesmo comando com `xw.App(visible=False)` | Funciona com o Excel invisível |
| 3 | Tempo | 20 fotos em 4,1 s (≈ 0,2 s por foto) |
| 4 | Célula de destino | A célula sob o **canto superior esquerdo** da imagem provisória (imagem grande cobrindo C5:E8 resultou só em C5) |
| 5 | Células mescladas | Funciona (F3:F12 e os blocos B13:B22, D13:D22, F13:F22 do `templates/model.xlsx`). O logo flutuante do template continua flutuante |
| 6 | Proporção | O Excel **estica** a imagem até preencher o bloco: foto vertical 2:3, panorâmica 3,2:1 e quadrada ficaram com a diagonal de canto a canto (distorcidas), bloco de 295,5 x 233,2 pt |
| 7 | Relatório completo do `config_exemple.yaml` (132 fotos sintéticas: 4:3, 3:4, panorama, 1:1) com o `XlwingsWriter` | 132 imagens em célula, **exatamente nas células planejadas**, 0 erros, 42,9 s (inclui gerar as fotos), arquivo de 465 KB (o relatório antigo tinha ~37 MB), só o logo do template flutuante |
| 8 | Conferência visual (primeira página exportada para PDF pelo próprio Excel) | Fotos centralizadas no bloco, sem distorção, com margens brancas; em largura fixa as linhas crescem como no fluxo antigo; o texto marcador do bloco (por exemplo "Placa de Obra do BB") é substituído pela imagem |

## O que foi implementado por causa do spike

- `LayoutSettings.image_mode` (`in_cell` é o padrão; `floating` mantém o comportamento antigo) e `max_image_px` (maior lado da foto preparada, 1600).
- `adapters/image_preparation.py`: enquadra a foto na **proporção do bloco** com margens brancas (equivale ao "ajustar à caixa") e reduz o tamanho. Aplica a rotação EXIF (corrige fotos de celular de lado).
- `XlwingsWriter._insert_in_cell`: ajusta as linhas (largura fixa), mede a área mesclada do slot (mescla o bloco se o template ainda não o fizer), prepara a foto, insere uma imagem provisória no canto da célula e executa o comando.

## Limites e hipóteses (não verificados)

- Testado só no Microsoft 365 build 16.0.20326. **Hipótese:** Excel 2016/2019 não têm imagens em célula e o `ExecuteMso("PicturePlaceInCell")` falha; o erro vira `PhotoInsertError` com mensagem em português.
- A conferência visual foi no PDF exportado, não na janela do Excel.
- **Hipótese:** o `openpyxl` descarta as partes `richData` ao salvar. Não abra e salve o relatório gerado com ele; o fluxo deve terminar no Excel.
- **Linux/Docker:** não há equivalente testado. Candidatos, todos hipóteses: `XlsxWriter.embed_image()` (só em arquivo novo, não abre o template) e escrita direta das partes `richData` no OOXML (viabilidade a provar com testes no Excel).
- Não testado: redimensionar linhas/colunas depois de gerar (hipótese: a imagem acompanha o bloco, por ser conteúdo da célula) e abrir o relatório em versões antigas.
- O Excel visível ou invisível não alterou o resultado; o ribbon não é necessário para o comando.

## Como reproduzir (Windows com Excel)

Scripts em `docs/spikes/` (rodar com `uv run python <script> <pasta-de-saida> ...`):

- `place_in_cell_com.py <saida>`: viabilidade do comando em célula simples e mesclada.
- `place_in_cell_probe.py <saida> <templates/model.xlsx>`: Excel invisível, tempo e template real.
- `place_in_cell_aspect.py <saida> <templates/model.xlsx>`: distorção com fotos vertical, panorâmica e quadrada.
- `e2e_in_cell.py <raiz-do-repo> <saida>`: relatório completo com fotos sintéticas e comparação com o plano.
- `render_first_page.py <xlsx> <pdf>`: exporta a primeira página para PDF.

Os scripts abrem o Excel; feche seus arquivos antes de rodar.
