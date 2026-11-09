// Todo texto exibido ao usuário fica aqui, para facilitar a internacionalização futura.
const plural = (count: number, one: string, many: string) => (count === 1 ? one : many);

export const strings = {
  app: {
    title: "Gerador de Relatórios Fotográficos",
    subtitle: "Monte o relatório fotográfico da obra a partir de um template Excel.",
  },
  server: {
    checking: "Verificando o servidor...",
    online: "Servidor conectado",
    offline: "Não foi possível falar com o servidor.",
  },
  errors: {
    unexpected: "Ocorreu um erro inesperado.",
  },
  nav: { back: "Voltar", next: "Avançar" },
  steps: {
    template: { label: "Template", description: "Modelo Excel" },
    photos: { label: "Fotos", description: "ZIP, RAR ou pasta" },
    sections: { label: "Seções", description: "Pastas e títulos" },
    validation: { label: "Conferência", description: "Antes de gerar" },
    generate: { label: "Gerar", description: "Relatório final" },
  },
  template: {
    drop: "Arraste o template (.xlsx) aqui ou clique para escolher",
    hint: "O template precisa ter, na coluna B, os títulos das seções do relatório.",
    uploading: "Enviando o template...",
    sheet: "Aba do relatório",
    sheetMissing: (name: string, used: string) =>
      `A aba "${name}" não existe no template; será usada a aba "${used}".`,
    titlesFound: (count: number) =>
      `${count} ${plural(count, "título encontrado", "títulos encontrados")} na coluna B`,
    ready: "Template recebido",
  },
  photos: {
    drop: "Arraste um ZIP, um RAR ou uma pasta de fotos aqui, ou clique para escolher o arquivo",
    hint: "Use uma pasta por seção, com o mesmo nome da pasta definido em Seções (por exemplo, entorno/foto1.jpg).",
    chooseFolder: "Escolher pasta...",
    uploading: "Enviando as fotos...",
    uploadingProgress: (done: number, total: number) => `Enviando as fotos... ${done} de ${total}`,
    received: (count: number) => `${count} ${plural(count, "foto recebida", "fotos recebidas")}`,
    skipped: (count: number) =>
      `${count} ${plural(count, "arquivo ignorado", "arquivos ignorados")} (tipo não aceito ou fora de uma pasta de seção)`,
    folders: "Pastas com fotos",
    noFolders: "Nenhuma foto enviada ainda.",
    photoCount: (count: number) => `${count} ${plural(count, "foto", "fotos")}`,
  },
  sections: {
    folder: "Pasta (id)",
    folderHelp: "Minúsculas, números e _",
    label: "Título no Excel",
    maxPhotos: "Máximo de fotos",
    fixWidth: "Largura fixa",
    grouped: "Agrupada (por andar)",
    groupSizes: "Fotos por grupo",
    groupSizesHelp: "Números separados por vírgula, por exemplo: 9, 6, 8",
    add: "Adicionar seção",
    remove: "Remover",
    useExample: "Usar as seções do exemplo",
    clear: "Limpar seções",
    empty: "Nenhuma seção definida.",
    titleNotFound:
      "Título não encontrado na coluna B do template. Escolha um título da lista ou troque de template.",
    titleDuplicated: (count: number) =>
      `O título aparece ${count} vezes no template; será usada a primeira.`,
    titleOk: "Título encontrado no template",
    folderEmpty: "Nenhuma foto nesta pasta.",
    uploadPhotos: "Enviar fotos desta seção",
    advanced: "Opções avançadas",
    sortMethod: "Ordenar fotos por",
    sortDate: "Data",
    sortName: "Nome",
    imageMode: "Como inserir a foto",
    imageInCell: 'Dentro da célula ("Colocar na Célula")',
    imageFloating: "Imagem flutuante",
    maxImagePx: "Maior lado da foto (px)",
    invalidId: "Use minúsculas, números e _",
    required: "Obrigatório",
    atLeastOne: "Informe ao menos 1",
    invalidGroups: "Informe números inteiros maiores que zero, separados por vírgula",
  },
  validation: {
    checking: "Conferindo o template e as fotos...",
    allGood: "Tudo certo: nada impede a geração do relatório.",
    blocking: "Corrija os problemas abaixo antes de gerar o relatório.",
    errorTitle: "Impede a geração",
    warningTitle: "Aviso",
    failed: "Não foi possível conferir.",
    needTemplate: "Envie o template para conferir.",
  },
  generate: {
    start: "Gerar relatório",
    running: "Gerando o relatório...",
    done: "Relatório pronto",
    download: "Baixar relatório",
    failed: "A geração falhou",
    photoFailures: (count: number) =>
      `${count} ${plural(count, "foto não pôde ser inserida", "fotos não puderam ser inseridas")}`,
    restart: "Gerar novamente",
    blocked: "Há problemas que impedem a geração. Volte e corrija.",
  },
} as const;
