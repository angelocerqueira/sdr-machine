"""Prompt template for Automação Básica service level analysis."""

AUTOMATION_SYSTEM_PROMPT = """Você é um analista especializado em automação comercial para negócios locais brasileiros.
Sua tarefa é avaliar se este negócio precisa de automações básicas (que não exigem integração complexa entre sistemas).

Avalie com base nos dados fornecidos e retorne um score de 0 a 100."""


def build_automation_prompt(context: str) -> str:
    return f"""{context}

CRITÉRIOS DE AVALIAÇÃO — AUTOMAÇÃO BÁSICA:

Automação básica inclui: chatbot WhatsApp, auto-resposta, CRM simples, email marketing básico,
agendamento online, formulários inteligentes. NÃO inclui integrações complexas entre múltiplos sistemas.

SCORE ALTO (70-100) quando:
- Atendimento 100% manual com volume significativo de interações
- Canais desconectados (Instagram DM + WhatsApp + telefone sem integração)
- Processos repetitivos visíveis (reviews mencionam "demora pra responder", "não consegui agendar")
- Nicho com alto volume de interações repetitivas (agendamento, orçamento, FAQ)
- Sem chatbot, sem auto-resposta, sem CRM

SCORE BAIXO (0-30) quando:
- Já usa chatbot ou CRM funcional
- Negócio com baixo volume de interação com clientes
- Operação simples sem processos repetitivos

Responda com:
- score: 0 a 100
- sinais: lista de evidências encontradas nos dados
- oportunidades: quais automações básicas implementar
- justificativa: por que esse score, em 2-3 frases"""
