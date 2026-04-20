"""Qualifier node — consolidates 4 analyzer results into final recommendation."""

from app.config import settings
from app.pipeline.diagnostic.state import (
    GraphState,
    NivelScore,
    ServiceLevelAnalysis,
    NivelKey,
    NIVEL_KEYS,
    FALLBACK_NIVEL,
)

_RESULT_MAP: list[tuple[str, NivelKey]] = [
    ("lp_result", "lp"),
    ("automacao_result", "automacao_basica"),
    ("advanced_result", "mapa_automacoes"),
    ("os_result", "vertical_os"),
]

VIABLE_THRESHOLD = 40


def qualify(state: GraphState, disqualify_threshold: int | None = None) -> dict:
    """Consolidate 4 analyzer results into a ServiceLevelAnalysis."""
    threshold = disqualify_threshold if disqualify_threshold is not None else settings.disqualify_threshold

    results: dict[NivelKey, NivelScore] = {}
    for state_key, nivel_key in _RESULT_MAP:
        result = getattr(state, state_key)
        results[nivel_key] = result if result is not None else FALLBACK_NIVEL

    scores = {k: v.score for k, v in results.items()}

    all_below = all(s < threshold for s in scores.values())
    if all_below:
        qualificado = False
        motivo = f"Todos os scores abaixo de {threshold}: " + ", ".join(
            f"{k}={s}" for k, s in scores.items()
        )
        nivel_recomendado = max(scores, key=scores.get)
    else:
        qualificado = True
        motivo = None
        nivel_recomendado = None
        for nivel_key in reversed(NIVEL_KEYS):
            if scores[nivel_key] >= VIABLE_THRESHOLD:
                nivel_recomendado = nivel_key
                break
        if nivel_recomendado is None:
            nivel_recomendado = max(scores, key=scores.get)

    nome = state.lead_info.get("nome", "Lead")
    top_nivel_label = {
        "lp": "Landing Page",
        "automacao_basica": "Automação Básica",
        "mapa_automacoes": "Mapa + Automações",
        "vertical_os": "Vertical OS",
    }
    best = results[nivel_recomendado]
    resumo_parts = [
        f"{nome}: nível recomendado é {top_nivel_label[nivel_recomendado]} (score {scores[nivel_recomendado]}/100).",
    ]
    if best.oportunidades:
        resumo_parts.append(f"Oportunidades: {', '.join(best.oportunidades[:3])}.")
    resumo = " ".join(resumo_parts)

    final = ServiceLevelAnalysis(
        lp=results["lp"],
        automacao_basica=results["automacao_basica"],
        mapa_automacoes=results["mapa_automacoes"],
        vertical_os=results["vertical_os"],
        nivel_recomendado=nivel_recomendado,
        qualificado=qualificado,
        motivo_desqualificacao=motivo,
        resumo_executivo=resumo,
        diagnostico_marketing=state.marketing_result,
    )

    return {"final_result": final}
