import type { ChatMessage, AgentChatData } from "@/lib/practice-types";

interface NicheTemplate {
  niche: string;
  messages: ChatMessage[];
  quickActions: string[];
  responses: Record<string, ChatMessage[]>;
}

const templates: NicheTemplate[] = [
  {
    niche: "advocacia",
    messages: [
      {
        role: "bot",
        text: "Bem-vindo ao escritorio {businessName}. Como posso ajuda-lo hoje?",
      },
      {
        role: "user",
        text: "Quero entender como funciona o processo de divorcio. Por onde eu começo?",
      },
      {
        role: "bot",
        text: "O processo de divorcio pode ser consensual ou litigioso. No divorcio consensual, ambas as partes concordam com os termos e o procedimento e mais rapido, podendo ser realizado em cartorio quando nao ha filhos menores. Posso agendar uma consulta inicial para avaliarmos o seu caso especifico e indicar o melhor caminho. Quer que eu verifique a disponibilidade da nossa agenda?",
      },
    ],
    quickActions: ["Agendar consulta", "Documentos necessarios", "Honorarios", "Outras areas"],
    responses: {
      "Agendar consulta": [
        {
          role: "bot",
          text: "Para agendar sua consulta com {businessName}, preciso de algumas informacoes. Qual e a sua disponibilidade de horario? Atendemos de segunda a sexta das 9h as 18h e aos sabados pela manha. A consulta inicial tem duracao de aproximadamente 1 hora.",
        },
      ],
      "Documentos necessarios": [
        {
          role: "bot",
          text: "Para um processo de divorcio, os documentos basicos sao: certidao de casamento, RG e CPF de ambos os conjuges, comprovante de residencia, documentos dos filhos (se houver) e documentos dos bens a partilhar (escrituras, documentos de veiculo, extratos bancarios). Posso enviar uma lista completa por e-mail se preferir.",
        },
      ],
      Honorarios: [
        {
          role: "bot",
          text: "Os honorarios do escritorio {businessName} variam conforme a complexidade do caso. O divorcio consensual simples tem valores a partir de um patamar acessivel, enquanto processos litigiosos ou com bens a partilhar requerem uma avaliacao detalhada. Oferecemos consulta inicial para apresentar um orcamento personalizado sem compromisso.",
        },
      ],
      "Outras areas": [
        {
          role: "bot",
          text: "O escritorio {businessName} atua em diversas areas do direito, incluindo Direito de Familia, Direito Civil, Direito Trabalhista, Direito do Consumidor e Direito Empresarial. Para cada area temos advogados especializados. Em qual dessas areas voce precisa de assistencia?",
        },
      ],
    },
  },
  {
    niche: "odonto",
    messages: [
      {
        role: "bot",
        text: "Ola, voce entrou em contato com {businessName}. Estou aqui para ajuda-lo. Como posso ser util?",
      },
      {
        role: "user",
        text: "Estou sentindo uma dor forte em um dente ha dois dias. Voces atendem urgencia?",
      },
      {
        role: "bot",
        text: "Sim, {businessName} oferece atendimento de urgencia odontologica. Dor persistente por mais de dois dias pode indicar uma inflamacao ou infeccao que precisa de avaliacao rapida. Recomendo que voce venha o quanto antes para evitar complicacoes. Temos horarios disponiveis ainda hoje. Posso verificar o primeiro horario livre para voce?",
      },
    ],
    quickActions: ["Agendar consulta", "Tratamentos disponiveis", "Convenios aceitos", "Horario de funcionamento"],
    responses: {
      "Agendar consulta": [
        {
          role: "bot",
          text: "Para agendar seu atendimento em {businessName}, precisamos do seu nome completo, telefone de contato e a principal queixa ou tipo de tratamento desejado. Atendemos de segunda a sabado. Qual o periodo que funciona melhor para voce: manha, tarde ou noite?",
        },
      ],
      "Tratamentos disponiveis": [
        {
          role: "bot",
          text: "{businessName} oferece uma ampla gama de tratamentos: limpeza e profilaxia, restauracoes, extracoess, tratamento de canal, clareamento dental, ortodontia (aparelho fixo e alinhadores transparentes), implantes dentarios e proteses. Ha algum tratamento especifico sobre o qual voce gostaria de mais informacoes?",
        },
      ],
      "Convenios aceitos": [
        {
          role: "bot",
          text: "{businessName} trabalha com os principais convenios odontologicos da regiao. Para confirmar se o seu plano esta na nossa lista, me informe o nome do convenio e vou verificar imediatamente. Tambem atendemos particulares com opcoes de parcelamento.",
        },
      ],
      "Horario de funcionamento": [
        {
          role: "bot",
          text: "{businessName} atende de segunda a sexta das 8h as 19h e aos sabados das 8h as 13h. Para urgencias, entre em contato pelo nosso numero principal e verificamos a disponibilidade de atendimento emergencial fora do horario regular.",
        },
      ],
    },
  },
  {
    niche: "restaurante",
    messages: [
      {
        role: "bot",
        text: "Bem-vindo ao {businessName}. Como posso ajuda-lo hoje?",
      },
      {
        role: "user",
        text: "Voces tem opcoes vegetarianas no cardapio? Somos um grupo de 6 pessoas e algumas nao comem carne.",
      },
      {
        role: "bot",
        text: "Sim, {businessName} tem um cardapio variado com diversas opcoes vegetarianas, incluindo entradas, pratos principais e sobremesas. Nosso chef prepara pratos especiais sem carne com ingredientes frescos e selecionados. Para um grupo de 6 pessoas, recomendo tambem reservar uma mesa com antecedencia para garantir o melhor atendimento. Posso fazer a reserva agora?",
      },
    ],
    quickActions: ["Fazer reserva", "Ver cardapio", "Delivery", "Horario de funcionamento"],
    responses: {
      "Fazer reserva": [
        {
          role: "bot",
          text: "Para reservar sua mesa no {businessName}, preciso de: data e horario pretendido, numero de pessoas e seu nome e telefone para contato. Aceitamos reservas com ate 30 dias de antecedencia. Qual seria a data que voce tem em mente?",
        },
      ],
      "Ver cardapio": [
        {
          role: "bot",
          text: "O cardapio do {businessName} conta com entradas, pratos principais, sobremesas e bebidas cuidadosamente selecionados. Temos opcoes para diferentes restricoes alimentares. Posso enviar o cardapio completo por e-mail ou WhatsApp, ou voce pode consultar diretamente no nosso site. Qual opcao prefere?",
        },
      ],
      Delivery: [
        {
          role: "bot",
          text: "{businessName} realiza entregas em determinadas regioes da cidade. O pedido pode ser feito pelo nosso aplicativo, pelo iFood ou diretamente pelo telefone. O tempo medio de entrega e de 45 minutos. Ha um valor minimo de pedido para delivery. Qual e o seu endereco para verificarmos se esta na area de cobertura?",
        },
      ],
      "Horario de funcionamento": [
        {
          role: "bot",
          text: "{businessName} funciona de terca a domingo. Almoco: das 11h30 as 15h. Jantar: das 18h30 as 23h. As segundas-feiras estamos fechados para descanso da equipe. O delivery segue o mesmo horario de funcionamento.",
        },
      ],
    },
  },
  {
    niche: "academia",
    messages: [
      {
        role: "bot",
        text: "Ola, voce entrou em contato com {businessName}. Pronto para comecar sua transformacao? Como posso ajuda-lo?",
      },
      {
        role: "user",
        text: "Quero saber sobre os planos disponiveis. Voces oferecem alguma aula experimental antes de assinar?",
      },
      {
        role: "bot",
        text: "Sim, {businessName} oferece uma aula experimental gratuita para que voce conheca nossa estrutura e metodologia antes de tomar qualquer decisao. Temos planos mensais, trimestrais e anuais, com valores progressivamente mais vantajosos. Alem das salas de musculacao e cardio, contamos com aulas coletivas incluidas em todos os planos. Quando voce gostaria de agendar sua aula experimental?",
      },
    ],
    quickActions: ["Agendar aula gratis", "Ver planos e precos", "Grade de horarios", "Professores e especialidades"],
    responses: {
      "Agendar aula gratis": [
        {
          role: "bot",
          text: "Otima decisao! Para agendar sua aula experimental gratuita em {businessName}, me informe seu nome, telefone e qual o melhor horario para voce: manha, tarde ou noite. Um de nossos consultores ira confirmar o agendamento e apresentar toda a estrutura disponivel.",
        },
      ],
      "Ver planos e precos": [
        {
          role: "bot",
          text: "{businessName} oferece planos flexiveis: mensal, trimestral e anual. Os planos incluem acesso a musculacao, cardio e aulas coletivas. O plano anual oferece o melhor custo-beneficio com economia significativa em relacao ao mensal. Oferecemos tambem planos corporativos para empresas. Gostaria de receber uma proposta personalizada?",
        },
      ],
      "Grade de horarios": [
        {
          role: "bot",
          text: "{businessName} funciona de segunda a sexta das 6h as 22h, aos sabados das 8h as 18h e aos domingos das 9h as 13h. As aulas coletivas tem horarios distribuidos ao longo do dia. Posso enviar a grade completa de aulas por WhatsApp para voce verificar os horarios que melhor se encaixam na sua rotina.",
        },
      ],
      "Professores e especialidades": [
        {
          role: "bot",
          text: "A equipe de {businessName} e formada por profissionais de Educacao Fisica graduados e especializados. Temos instrutores de musculacao, personal trainers, professores de yoga, pilates, funcional, danca e spinning. Cada aluno recebe acompanhamento individualizado na elaboracao do treino. Voce tem algum objetivo especifico, como emagrecimento, hipertrofia ou condicionamento?",
        },
      ],
    },
  },
  {
    niche: "clinica",
    messages: [
      {
        role: "bot",
        text: "Bem-vindo a {businessName}. Estou aqui para auxiliar no seu agendamento e tirar suas duvidas. Como posso ajuda-lo?",
      },
      {
        role: "user",
        text: "Preciso consultar com um cardiologista. Voces tem essa especialidade? Qual e o prazo para conseguir uma consulta?",
      },
      {
        role: "bot",
        text: "{businessName} conta com cardiologistas experientes em nosso quadro de especialistas. O prazo para consulta de rotina geralmente e de alguns dias, podendo variar conforme a disponibilidade do profissional e a urgencia do caso. Para casos urgentes, priorizamos o atendimento. Voce tem algum convenio ou prefere atendimento particular? Isso ajuda a verificarmos as opcoes disponiveis para voce.",
      },
    ],
    quickActions: ["Agendar consulta", "Exames disponiveis", "Convenios aceitos", "Especialidades"],
    responses: {
      "Agendar consulta": [
        {
          role: "bot",
          text: "Para agendar sua consulta em {businessName}, precisamos: especialidade desejada, nome completo, data de nascimento, convenio (ou informar que e particular) e melhor horario para contato. Atendemos de segunda a sabado. Apos o agendamento, enviaremos uma confirmacao com todas as orientacoes necessarias.",
        },
      ],
      "Exames disponiveis": [
        {
          role: "bot",
          text: "{businessName} realiza uma ampla variedade de exames: laboratoriais, de imagem (ultrassonografia, raio-X, eletrocardiograma), preventivos e especializados. Muitos exames podem ser solicitados na propria consulta e realizados na clinica, sem necessidade de deslocamento adicional. Qual exame voce precisa realizar?",
        },
      ],
      "Convenios aceitos": [
        {
          role: "bot",
          text: "{businessName} trabalha com os principais convenios e planos de saude. Para verificar se o seu plano esta credenciado, me informe o nome do convenio e o numero da carteirinha. Tambem atendemos particulares com valores acessiveis e possibilidade de parcelamento.",
        },
      ],
      Especialidades: [
        {
          role: "bot",
          text: "{businessName} possui especialistas em Clinica Geral, Cardiologia, Dermatologia, Ginecologia, Ortopedia, Neurologia, Endocrinologia, Pediatria e outras especialidades. Nossa equipe e formada por profissionais com solida formacao e experiencia. Ha alguma especialidade especifica que voce precisa?",
        },
      ],
    },
  },
  {
    niche: "contabil",
    messages: [
      {
        role: "bot",
        text: "Bem-vindo a {businessName}. Estou aqui para apoiar voce e sua empresa com as melhores solucoes contabeis. Como posso ajuda-lo?",
      },
      {
        role: "user",
        text: "Estou pensando em abrir uma empresa. Qual e o processo e quanto tempo leva para regularizar tudo?",
      },
      {
        role: "bot",
        text: "A abertura de empresa envolve escolher o tipo societario (MEI, ME, EPP), o regime tributario mais adequado (Simples Nacional, Lucro Presumido ou Lucro Real) e registrar nos orgaos competentes. Com {businessName} cuidando do processo, o prazo medio e de 7 a 15 dias uteis para a empresa estar totalmente regularizada. Podemos analisar o seu segmento e projetar a carga tributaria para recomendar o regime mais vantajoso. Gostaria de agendar uma reuniao de diagnostico sem custos?",
      },
    ],
    quickActions: ["Abrir empresa", "Obrigacoes fiscais", "Simples Nacional", "Falar com contador"],
    responses: {
      "Abrir empresa": [
        {
          role: "bot",
          text: "Para abrir sua empresa com {businessName}, o processo inclui: definicao do tipo de empresa e atividade, elaboracao do contrato social, registro na Junta Comercial, obtencao do CNPJ, inscricoes estadual e municipal e alvara de funcionamento. Nossa equipe cuida de todo o processo. Qual e o ramo de atividade da sua empresa?",
        },
      ],
      "Obrigacoes fiscais": [
        {
          role: "bot",
          text: "As obrigacoes fiscais variam conforme o porte e regime tributario da empresa. De forma geral, incluem apuracao e pagamento de impostos mensais (DAS, DARF), entrega de declaracoes periodicas (DEFIS, ECF, ECD) e cumprimento das obrigacoes trabalhistas e previdenciarias. {businessName} garante que sua empresa esteja sempre em dia e evite multas e penalidades.",
        },
      ],
      "Simples Nacional": [
        {
          role: "bot",
          text: "O Simples Nacional e um regime tributario simplificado para micro e pequenas empresas com faturamento anual de ate R$ 4,8 milhoes. Unifica o pagamento de varios impostos em uma unica guia (DAS) e oferece aliquotas reduzidas em muitos casos. {businessName} pode fazer uma simulacao comparativa entre os regimes para identificar qual gera menor carga tributaria para o seu negocio.",
        },
      ],
      "Falar com contador": [
        {
          role: "bot",
          text: "Nossos contadores em {businessName} estao disponiveis para atendimento presencial, por telefone ou videoconferencia. Para agendar uma conversa, me informe seu nome, o tipo de empresa ou necessidade e o melhor horario para contato. Respondemos todas as mensagens em ate 24 horas uteis.",
        },
      ],
    },
  },
];

const genericTemplate: NicheTemplate = {
  niche: "",
  messages: [
    {
      role: "bot",
      text: "Bem-vindo a {businessName}. Estou aqui para ajuda-lo. Como posso ser util hoje?",
    },
    {
      role: "user",
      text: "Gostaria de saber mais sobre os servicos oferecidos por voces.",
    },
    {
      role: "bot",
      text: "{businessName} oferece servicos especializados na area de {niche}. Nossa equipe esta pronta para atende-lo com qualidade e agilidade. Posso detalhar algum servico especifico ou prefere agendar uma conversa com um de nossos especialistas?",
    },
  ],
  quickActions: ["Conhecer servicos", "Agendar atendimento", "Valores e orcamento", "Falar com especialista"],
  responses: {
    "Conhecer servicos": [
      {
        role: "bot",
        text: "{businessName} atua no segmento de {niche} oferecendo solucoes completas e personalizadas para cada cliente. Cada projeto recebe atencao individualizada para garantir os melhores resultados. Posso enviar mais detalhes sobre alguma solucao especifica?",
      },
    ],
    "Agendar atendimento": [
      {
        role: "bot",
        text: "Para agendar seu atendimento em {businessName}, me informe seu nome, telefone de contato e o melhor horario para voce. Nossa equipe ira confirmar o agendamento e preparar tudo para oferecer o melhor atendimento possivel.",
      },
    ],
    "Valores e orcamento": [
      {
        role: "bot",
        text: "Os valores dos servicos de {businessName} variam conforme as necessidades e o escopo de cada projeto. Para apresentar um orcamento preciso, precisamos entender melhor a sua situacao. Podemos agendar uma consulta inicial sem compromisso para avaliar o que melhor atende ao seu caso.",
      },
    ],
    "Falar com especialista": [
      {
        role: "bot",
        text: "Nossa equipe de especialistas em {businessName} esta disponivel para atende-lo. Voce pode entrar em contato pelo telefone, e-mail ou agendar uma visita presencial. Qual forma de contato e mais conveniente para voce?",
      },
    ],
  },
};

function replacePlaceholders(
  text: string,
  businessName: string,
  niche: string
): string {
  return text
    .replace(/\{businessName\}/g, businessName)
    .replace(/\{niche\}/g, niche);
}

function applyPlaceholders(
  template: NicheTemplate,
  businessName: string,
  niche: string
): { messages: ChatMessage[]; quickActions: string[]; responses: Record<string, ChatMessage[]> } {
  const messages: ChatMessage[] = template.messages.map((msg) => ({
    role: msg.role,
    text: replacePlaceholders(msg.text, businessName, niche),
  }));

  const responses: Record<string, ChatMessage[]> = {};
  for (const [action, msgs] of Object.entries(template.responses)) {
    responses[action] = msgs.map((msg) => ({
      role: msg.role,
      text: replacePlaceholders(msg.text, businessName, niche),
    }));
  }

  return { messages, quickActions: template.quickActions, responses };
}

export function buildChatDataForLead(lead: {
  nome: string;
  nicho: string | null;
}): AgentChatData {
  const businessName = lead.nome;
  const niche = lead.nicho || "empresa";

  const matchedTemplate =
    templates.find((t) =>
      lead.nicho?.toLowerCase().includes(t.niche)
    ) ?? genericTemplate;

  const { messages, quickActions, responses } = applyPlaceholders(
    matchedTemplate,
    businessName,
    niche
  );

  return {
    businessName,
    niche,
    messages,
    quickActions,
    responses,
  };
}
