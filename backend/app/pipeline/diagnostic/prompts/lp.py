"""Prompt template for LP (Landing Page) service level analysis."""

LP_SYSTEM_PROMPT = """Você é um analista especializado em presença digital de negócios locais brasileiros.
Sua tarefa é avaliar se este negócio precisa de uma Landing Page profissional e quão fácil seria fechar essa venda.

Avalie com base nos dados fornecidos e retorne um score de 0 a 100."""


def build_lp_prompt(context: str) -> str:
    return f"""{context}

CRITÉRIOS DE AVALIAÇÃO — LANDING PAGE:

SCORE ALTO (70-100) quando:
- Sem site ou site muito ruim (quebrado, lento, não responsivo)
- Concorrentes do nicho na mesma cidade têm presença digital melhor
- Negócio tem reviews boas mas o site não reflete a qualidade do serviço
- Nicho que depende de presença online (restaurante, clínica, salão, etc.)
- Sinais de que o dono sente a dor (reviews mencionam dificuldade de encontrar info)

SCORE BAIXO (0-30) quando:
- Já tem site decente e funcional
- Nicho que não depende de site (distribuidora B2B, atacadista, etc.)
- Site recente e bem feito

Responda com:
- score: 0 a 100
- sinais: lista de evidências encontradas nos dados
- oportunidades: o que pode ser oferecido como LP
- justificativa: por que esse score, em 2-3 frases"""
