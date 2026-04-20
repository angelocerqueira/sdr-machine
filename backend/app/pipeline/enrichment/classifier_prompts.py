"""Prompt and tool-use schema for nicho inference via LLM."""
from __future__ import annotations

from app.pipeline.enrichment.classifier_enums import NichoCanonico


NICHO_TOOL_SCHEMA = {
    "name": "classify_nicho",
    "description": (
        "Classifica o negócio em um dos 15 buckets canônicos de nicho. "
        "Use 'outros' apenas se nenhum bucket se encaixar minimamente."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "nicho_canonico": {
                "type": "string",
                "enum": [n.value for n in NichoCanonico],
                "description": "Bucket canônico do nicho",
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Confiança da classificação (0-1)",
            },
            "reasoning": {
                "type": "string",
                "description": "Justificativa curta (1 frase)",
            },
        },
        "required": ["nicho_canonico", "confidence", "reasoning"],
    },
}


_FEW_SHOT = """Exemplos:

Entrada: Nome="Clinica Sorriso", nicho_raw="Dentist", descricao="Odontologia geral"
Saída: dentista | 0.98 | Clínica odontológica explícita

Entrada: Nome="Bella Estética", nicho_raw="Beauty Salon", descricao="Harmonização facial"
Saída: estetica | 0.90 | Harmonização facial é estética, não salão

Entrada: Nome="Consultoria ACME", nicho_raw="", descricao="Consultoria empresarial B2B"
Saída: outros | 0.95 | Consultoria não tem bucket específico
"""


def build_nicho_prompt(
    *,
    nome: str,
    nicho_raw: str | None,
    descricao: str | None,
    reviews: list[str] | None,
) -> str:
    """Build the user-turn prompt for the nicho classifier."""
    sample_reviews = (reviews or [])[:3]
    reviews_block = "\n".join(f"- {r}" for r in sample_reviews) if sample_reviews else "(nenhuma)"

    return (
        "Você é um classificador de nichos de negócios brasileiros.\n"
        "Buckets permitidos: "
        + ", ".join(n.value for n in NichoCanonico)
        + "\n\n"
        + _FEW_SHOT
        + "\n"
        + "Classifique o seguinte negócio. Use 'outros' apenas se nenhum bucket se encaixar.\n\n"
        + f"Nome: {nome or '(vazio)'}\n"
        + f"Nicho bruto: {nicho_raw or '(vazio)'}\n"
        + f"Descrição: {descricao or '(vazia)'}\n"
        + f"Amostra de reviews:\n{reviews_block}\n"
    )
