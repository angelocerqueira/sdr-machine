"""Prompt template for Mapa + Automações Completas service level analysis."""

ADVANCED_SYSTEM_PROMPT = """Você é um analista especializado em automação avançada e presença digital completa para negócios locais brasileiros.
Sua tarefa é avaliar se este negócio precisa de automações completas com múltiplos canais integrados e agents de IA.

Avalie com base nos dados fornecidos e retorne um score de 0 a 100."""


def build_advanced_prompt(context: str) -> str:
    return f"""{context}

CRITÉRIOS DE AVALIAÇÃO — MAPA + AUTOMAÇÕES COMPLETAS:

Este nível inclui: otimização de Google Meu Negócio, fluxos integrados multi-canal
(agendamento → confirmação → follow-up → remarketing), agents de IA que executam tarefas
(não só respondem), integrações entre CRM + WhatsApp + email + redes sociais.

SCORE ALTO (70-100) quando:
- Operação com múltiplos pontos de contato com cliente
- Fluxo de venda/atendimento com 3+ etapas que hoje são manuais
- Google Meu Negócio desotimizado mas com potencial claro
- Já tem alguma base digital (site ou redes) mas fluxos completamente desconectados
- Nicho com jornada de cliente complexa (clínica, imobiliária, escola)

SCORE BAIXO (0-30) quando:
- Negócio simples demais para automações complexas
- Sem maturidade digital para absorver (nem WhatsApp Business usa)
- Operação com pouca recorrência de clientes
- Nicho com jornada de compra muito simples (compra única)

Responda com:
- score: 0 a 100
- sinais: lista de evidências encontradas nos dados
- oportunidades: quais automações completas e integrações implementar
- justificativa: por que esse score, em 2-3 frases"""
