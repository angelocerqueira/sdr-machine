"""Prompt pro node de diagnóstico de marketing (funil completo)."""

MARKETING_SYSTEM_PROMPT = """Você é um estrategista de marketing sênior para negócios locais brasileiros.
Analisa o contexto fornecido e produz um diagnóstico de marketing completo, acionável e específico ao negócio.
Evite genérico; use dados concretos da análise. Português do Brasil."""


MARKETING_JSON_INSTRUCTION = """

IMPORTANTE: Responda APENAS com JSON válido no formato exato abaixo, sem texto adicional, sem markdown fences.
{
  "resumo_executivo": "<2-3 frases sobre o estado geral do negócio>",
  "momento_funil": "<descoberta|atracao|consideracao|acao|apologia>",
  "potencial_ia_automacao": {
    "score": <0-100>,
    "oportunidades": ["<oportunidade curta>", ...],
    "justificativa": "<por que esse score>"
  },
  "prioridades_top3": ["<prioridade 1>", "<prioridade 2>", "<prioridade 3>"],
  "funil": {
    "descoberta":   {"diagnostico": "<...>", "acoes_top2": [{"acao":"<...>","resultado_esperado":"<...>","kpi":"<...>"}, {"acao":"<...>","resultado_esperado":"<...>","kpi":"<...>"}]},
    "atracao":      {"diagnostico": "<...>", "acoes_top2": [{"acao":"<...>","resultado_esperado":"<...>","kpi":"<...>"}, {"acao":"<...>","resultado_esperado":"<...>","kpi":"<...>"}]},
    "consideracao": {"diagnostico": "<...>", "acoes_top2": [{"acao":"<...>","resultado_esperado":"<...>","kpi":"<...>"}, {"acao":"<...>","resultado_esperado":"<...>","kpi":"<...>"}]},
    "acao":         {"diagnostico": "<...>", "acoes_top2": [{"acao":"<...>","resultado_esperado":"<...>","kpi":"<...>"}, {"acao":"<...>","resultado_esperado":"<...>","kpi":"<...>"}]},
    "apologia":     {"diagnostico": "<...>", "acoes_top2": [{"acao":"<...>","resultado_esperado":"<...>","kpi":"<...>"}, {"acao":"<...>","resultado_esperado":"<...>","kpi":"<...>"}]}
  }
}"""


def build_marketing_prompt(context: str) -> str:
    """Monta o user prompt com o contexto compartilhado."""
    return f"""{context}

TAREFA:
1. Identifique o momento atual do negócio no funil de marketing (descoberta, atracao, consideracao, acao, apologia). Escolha UMA etapa — a que melhor descreve o estado atual.
2. Avalie o potencial de IA e automação (score 0-100, oportunidades específicas, justificativa).
3. Liste as 3 prioridades de curto prazo (acionáveis, específicas).
4. Para cada uma das 5 etapas do funil, produza:
   - diagnóstico curto da situação atual
   - 2 ações top (com resultado esperado e KPI)
5. Escreva um resumo executivo em 2-3 frases.

Seja específico ao negócio — use o nome, nicho, cidade, dados do site, redes sociais. NÃO seja genérico.{MARKETING_JSON_INSTRUCTION}"""
