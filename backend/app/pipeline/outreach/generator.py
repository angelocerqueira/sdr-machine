"""
Módulo 4: Outreach via WhatsApp — cadência fria B2B (5 toques).

Persona: SDR sênior B2B. Mensagens que abrem conversa, não fecham venda.
Cadência D+0 (initial) → D+2 (bump) → D+5 (insight) → D+9 (angle) → D+14 (breakup).
"""

import logging
import re
import time
import urllib.parse
from dataclasses import dataclass, field

import requests

from app.config import settings
from app.pipeline.outreach.config import ctas_for, load_angulos
from app.pipeline.outreach.validators import (
    check_compliance,
    check_glossario,
    detect_ai_cliches,
    fix_capitalization,
    fix_punctuation_spacing,
    is_review_negative,
    validate_hard,
    wrap_negative_review,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Generation result (PR2.3 — replaces the old tuple[str | None, list[str]])
# ---------------------------------------------------------------------------


@dataclass
class GenerationResult:
    """Result of a single LLM generation attempt.

    ``text`` is None on any failure (infrastructure or validation). ``errors``
    is empty on infrastructure failures, populated on validation failures.
    ``angulo`` / ``cta`` are set only when generation succeeded (validation
    included). For exhausted-pool scenarios where the LLM returned ``none``,
    they stay None and are recorded as such on the OutreachMessage row.
    """

    text: str | None = None
    errors: list[str] = field(default_factory=list)
    angulo: str | None = None
    cta: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_phone(phone: str) -> str:
    """Normaliza número de telefone removendo caracteres especiais."""
    cleaned = (phone or "").replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    if cleaned and not cleaned.startswith("55"):
        cleaned = "55" + cleaned
    return cleaned


def _lp_url(public_id: str) -> str:
    """Constrói a URL pública da landing page (frontend, public_id)."""
    return f"{settings.frontend_url}/lp/{public_id}"


def _get_diagnostic(lead_data: dict) -> dict | None:
    """Extrai diagnóstico de marketing do site_analysis."""
    return lead_data.get("site_analysis", {}).get("diagnostico_marketing")


def _empresa_idade_anos(data_fundacao) -> int | None:
    """Calcula idade da empresa em anos a partir de data_fundacao (str ISO ou date)."""
    if not data_fundacao:
        return None
    try:
        from datetime import date, datetime as dt
        if isinstance(data_fundacao, str):
            d = dt.strptime(data_fundacao[:10], "%Y-%m-%d").date()
        else:
            d = data_fundacao
        return max(0, date.today().year - d.year)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Context builder — extrai TODOS os sinais ricos do lead pra alimentar prompt
# ---------------------------------------------------------------------------

NIVEL_LABELS = {
    "lp": "landing page",
    "automacao_basica": "automação básica de atendimento",
    "mapa_automacoes": "mapa de automações",
    "vertical_os": "OS vertical",
}

MOMENTO_LABELS = {
    "descoberta": "descoberta — ainda não conhecem o problema",
    "atracao": "atração — sabem do problema mas não te conhecem",
    "consideracao": "consideração — comparando soluções",
    "acao": "ação — prontos pra contratar",
    "apologia": "apologia — clientes que defendem a marca",
}


def _build_context(lead_data: dict, has_lp: bool, lp_url: str | None) -> dict:
    """
    Consolida todos os sinais ricos do lead num único dict pro prompt.
    Tudo opcional — o prompt instrui a usar só o que existe.
    """
    sa = lead_data.get("site_analysis") or {}
    diag = sa.get("diagnostico_marketing") or {}

    nivel_rec = sa.get("nivel_recomendado")
    nivel_block = sa.get(nivel_rec) if nivel_rec else None
    nivel_oportunidades = (nivel_block or {}).get("oportunidades", []) if isinstance(nivel_block, dict) else []
    nivel_sinais = (nivel_block or {}).get("sinais", []) if isinstance(nivel_block, dict) else []

    momento = diag.get("momento_funil") or ""
    funil_atual = (diag.get("funil") or {}).get(momento) or {}
    acoes_top2 = funil_atual.get("acoes_top2") or []

    top_reviews = lead_data.get("top_reviews") or []
    review_destaque = ""
    if top_reviews:
        first = top_reviews[0]
        if isinstance(first, dict):
            review_destaque = (first.get("text") or first.get("comment") or "")[:140]
        elif isinstance(first, str):
            review_destaque = first[:140]

    # PR4.2 salvaguarda: detect negative reviews and swap for a neutral framing
    # BEFORE the text enters the prompt. The LLM never sees the raw negative
    # words, so it can't paraphrase them or quote them back into the message.
    review_negative = is_review_negative(review_destaque)
    review_destaque = wrap_negative_review(review_destaque)

    tech = lead_data.get("tech_stack") or []
    tech_names = []
    for t in tech[:5]:
        if isinstance(t, dict):
            n = t.get("name") or t.get("technology")
            if n:
                tech_names.append(n)
        elif isinstance(t, str):
            tech_names.append(t)

    return {
        "nome": lead_data.get("nome", ""),
        "nicho": lead_data.get("nicho") or lead_data.get("categoria") or "",
        "nicho_canonico": lead_data.get("nicho_canonico"),  # PR4.2 — preferred key for per-nicho config lookups
        "cidade": lead_data.get("cidade", ""),
        "tratamento_formal": lead_data.get("tratamento_formal"),  # populated in PR3
        "rating": lead_data.get("rating", ""),
        "reviews_count": lead_data.get("reviews_count", ""),
        "website": lead_data.get("website") or "",
        "has_site": bool(lead_data.get("website")),
        "has_lp": has_lp,
        "lp_url": lp_url if has_lp else "",
        "razao_social": lead_data.get("razao_social", ""),
        "porte": lead_data.get("porte", ""),
        "idade_anos": _empresa_idade_anos(lead_data.get("data_fundacao")),
        "tech_stack_names": tech_names,
        "review_destaque": review_destaque,        # wrapped if negative (PR4.2)
        "review_negative": review_negative,         # PR4.2 — flag for prompt warning
        "opportunity_reasons": (lead_data.get("opportunity_reasons") or [])[:3],
        # Diagnóstico
        "qualificado": sa.get("qualificado", True),
        "resumo_executivo": diag.get("resumo_executivo") or sa.get("resumo_executivo") or "",
        "momento_funil": momento,
        "momento_label": MOMENTO_LABELS.get(momento, momento),
        "prioridades_top3": diag.get("prioridades_top3") or [],
        "ia_oportunidades": (diag.get("potencial_ia_automacao") or {}).get("oportunidades", []),
        "funil_acoes": [a.get("acao", "") for a in acoes_top2 if isinstance(a, dict)],
        # Estratégia (Service Level Analysis)
        "nivel_recomendado": nivel_rec or "",
        "nivel_label": NIVEL_LABELS.get(nivel_rec or "", ""),
        "nivel_oportunidades": nivel_oportunidades[:3],
        "nivel_sinais": nivel_sinais[:3],
    }


# ---------------------------------------------------------------------------
# Persona + princípios B2B (compartilhados em todos os prompts)
# ---------------------------------------------------------------------------


def _persona_block() -> str:
    return f"""# PERSONA
Você é {settings.your_name}, SDR sênior B2B em outreach FRIO via WhatsApp pela {settings.business_name}.
Cadência total: 5 toques (D+0, D+2, D+5, D+9, D+14). Esta é uma das mensagens dessa cadência.
Seu trabalho é ABRIR conversa, não fechar venda. O sucesso é uma resposta — qualquer resposta.

# REGRAS DURAS — NÃO PODE QUEBRAR (priorizam acima de qualquer outra)
- Use APENAS dados de # DADOS DO LEAD e # DIAGNÓSTICO + ESTRATÉGIA. Nada além.
- NUNCA invente: clima, dia da semana, fim de semana, estatística, percentual, número, nome próprio de pessoa, evento.
- NÃO comente sobre o tempo (gelado, quente, chuva, sol). NÃO diga "tudo bem com você?", "tá frio aí?", "segunda chegou".
- O nome do lead é NOME DA EMPRESA, não pessoa. Não dirija pessoa pelo nome da empresa.
- Se um dado específico não existe acima, ignore — NÃO preencha com palpite.
- Não cite "30-45 dias", "3x mais leads", "aumenta X%" — sem números inventados.

# PRINCÍPIOS DE COLD OUTREACH B2B
1. Especificidade > pitch. Mencione 1 detalhe ÚNICO e VERIFICÁVEL do lead que prove que você leu — sem isso, não escreva.
2. Brevidade brutal. WhatsApp é íntimo, mensagem longa é spam. Conta linhas.
3. Permission-based. Não assume disponibilidade nem urgência.
4. Problem-first. Lidera com observação/diagnóstico, não com produto.
5. CTA mole. Pergunta aberta ou "faz sentido conversar 10 min?" — nunca "agenda agora", "aproveita hoje".
6. Sem corporativês. Nada de "venho por meio desta", "prezado", "espero que esta o encontre bem".
7. Sem emoji-spam. Máximo 1 emoji, e só se servir o tom.
8. Calibração por momento de funil:
   - descoberta → educativa, abre o problema, sem oferta
   - atracao → diferenciação, mostra ângulo único
   - consideracao → comparação, evidência
   - acao → CTA mais direto, mas ainda calibrado
   - apologia → relacionamento, parceria

# TRATAMENTO PESSOAL
- Use "você" (singular) quando o lead tem sócio identificável (campo `tratamento_formal` preenchido) — sinaliza relação pessoal.
- Caso contrário, use "vocês" (plural) — fala com o negócio/time.
- Mantenha consistência: não misture os dois dentro da mesma mensagem.

# TEMPLATES HIPOTÉTICOS (use quando apresentar uma observação)
Linguagem segura — use uma destas estruturas para qualquer observação não verificada:
- "parece que..."
- "pelo que vi do site..."
- "posso estar enganado, mas..."
- "pode ser proposital, mas notei..."

Hipóteses tratadas como fatos = motivo nº 1 de queimar lead. Sempre enquadre como observação.

# QUANTIFICAÇÃO PERMITIDA
Só liberadas observações que usem APENAS dados reais já no contexto:
- ✅ "vi {{reviews_count}} avaliações no Google" — OK (dado real)
- ✅ "rating {{rating}}★" — OK (dado real)
- ❌ "se 10% dos seus leads fechassem..." — PROIBIDO (cálculo hipotético, regex bloqueia)
- ❌ "você poderia faturar X mais" — PROIBIDO (número inventado)"""


def _hook_calibration_block(ctx: dict) -> str:
    """Bloco específico pra mensagem INITIAL — força calibração do hook por nivel_recomendado."""
    return f"""# CALIBRAÇÃO DO HOOK (obrigatória nesta mensagem)
Use o `nivel_recomendado` da ESTRATÉGIA pra escolher o ÂNGULO do hook:
- nivel "lp" → hook sobre site/presença digital (PageSpeed, mobile, CTA, captação online)
- nivel "automacao_basica" → hook sobre operação (atendimento manual, triagem perdida, follow-up de cliente, tempo em tarefa repetitiva)
- nivel "mapa_automacoes" → hook sobre pipeline/ferramentas desconectadas
- nivel "vertical_os" → hook sobre sistema legado do nicho (processo crítico não-digitalizado)

Estratégia recomendada AGORA: {ctx['nivel_label'] or '(não definida — use o sinal mais forte do diagnóstico)'}.
Se o nível não é "lp", NÃO foque em site lento ou PageSpeed — esse não é o vetor.

FONTES DE HOOK (em ordem de preferência, use a 1ª disponível):
1. Ações sugeridas pro momento de funil atual (funil_acoes acima) — convertendo em insight
2. Sinais que justificam a estratégia recomendada (nivel_sinais acima)
3. Tech stack defasada (jQuery, Wix antigo, Flash, etc) — se existir
4. Idade da empresa vs estado digital atual — se idade > 5 anos e site fraco
5. Top 3 prioridades do diagnóstico de marketing — se relevante
6. Reviews recentes mencionarem dor recorrente — se review_destaque indica isso

NÃO invente alavanca. Se nada disso bate, use uma observação mais sóbria (rating + ausência de algo concreto)."""


def _nicho_compliance_block(nicho: str) -> str:
    """Compliance + glossário + cases injection per nicho. Empty string if nicho has no config."""
    from app.pipeline.outreach.config import cases_for, compliance_for, glossario_for
    comp = compliance_for(nicho)
    gloss = glossario_for(nicho)
    cases = cases_for(nicho)
    if not (comp or gloss or cases):
        return ""

    parts = []

    if comp:
        regulacao = comp.get("regulacao", "")
        bloqueantes = comp.get("bloqueantes", [])
        preferir = comp.get("preferir", [])
        parts.append(f"# COMPLIANCE DO NICHO ({regulacao})")
        if bloqueantes:
            parts.append("BLOQUEADOS — NUNCA escreva, mesmo parafraseando:")
            parts.extend(f"- {t}" for t in bloqueantes)
        if preferir:
            parts.append("PREFERIR estes termos institucionais:")
            parts.extend(f"- {t}" for t in preferir)

    if gloss:
        parts.append("\n# GLOSSÁRIO DO NICHO (estilo)")
        parts.append("Substitua estes termos quando aparecerem na escrita:")
        for evitar, substituto in gloss.items():
            parts.append(f"- \"{evitar}\" → \"{substituto}\"")

    if cases:
        parts.append("\n# CASES DISPONÍVEIS (use APENAS se relevante e citável)")
        parts.append("Pode mencionar como 'um caso similar' (anônimo). NÃO invente novos cases.")
        for c in cases[:2]:  # cap at 2 to limit prompt bloat
            parts.append(f"- {c.get('descricao', '')}")

    return "\n".join(parts)


def _initial_structure_block(ctx: dict) -> str:
    """Estrutura mínima obrigatória para a mensagem INITIAL (apresentação + humildade)."""
    tratamento = ctx.get("tratamento_formal")  # may be None for now (PR3 will populate)
    saudacao_hint = f"{tratamento}," if tratamento else "Oi,"
    return f"""# ESTRUTURA MÍNIMA DA INITIAL (obrigatória)
1. Saudação cordial: comece com "{saudacao_hint}".
2. Apresentação em 1 frase: nome do remetente + empresa + o que a empresa faz. Ex: "Aqui é o {settings.your_name}, da {settings.business_name} — ajudo {{nicho_label}} a melhorar presença digital".
3. Razão do contato com humildade (não auditoria do negócio do lead).
4. Observação como hipótese — use SEMPRE templates hipotéticos (ver bloco acima).
5. Pergunta aberta ou CTA mole (use o CTA escolhido da taxonomia).
6. Saída honrosa opcional: "se já estiverem resolvendo, desconsidera" / "espero não estar incomodando".

NUNCA afirme que algo está errado no negócio do lead. Sempre apresente como observação/pergunta."""


# ---------------------------------------------------------------------------
# AI message generation (per type)
# ---------------------------------------------------------------------------


def _format_ctx_facts(ctx: dict) -> str:
    """Bloco de fatos do lead pro prompt — só o que existe, sem placeholders vazios."""
    lines = [f"- Nome: {ctx['nome']}"]
    if ctx['nicho']:
        lines.append(f"- Nicho: {ctx['nicho']}")
    if ctx['cidade']:
        lines.append(f"- Cidade: {ctx['cidade']}")
    if ctx['rating']:
        rev = f" ({ctx['reviews_count']} avaliações)" if ctx['reviews_count'] else ""
        lines.append(f"- Google: {ctx['rating']} estrelas{rev}")
    if ctx['has_site']:
        lines.append(f"- Site: {ctx['website']}")
    else:
        lines.append("- Site: NÃO TEM site próprio")
    if ctx['razao_social']:
        lines.append(f"- Razão social: {ctx['razao_social']}")
    if ctx['idade_anos'] is not None:
        lines.append(f"- Idade da empresa: {ctx['idade_anos']} anos")
    if ctx['porte']:
        lines.append(f"- Porte: {ctx['porte']}")
    if ctx['tech_stack_names']:
        lines.append(f"- Stack detectada: {', '.join(ctx['tech_stack_names'])}")
    if ctx['review_destaque']:
        lines.append(f"- Review em destaque: \"{ctx['review_destaque']}\"")
    return "\n".join(lines)


def _format_diag_block(ctx: dict) -> str:
    parts = []
    if ctx['resumo_executivo']:
        parts.append(f"- Resumo do diagnóstico: {ctx['resumo_executivo']}")
    if ctx['momento_label']:
        parts.append(f"- Momento de funil: {ctx['momento_label']}")
    if ctx['prioridades_top3']:
        parts.append(f"- Top 3 prioridades de marketing: {' / '.join(ctx['prioridades_top3'])}")
    if ctx['ia_oportunidades']:
        parts.append(f"- Oportunidades de IA/automação: {' / '.join(ctx['ia_oportunidades'][:2])}")
    if ctx['funil_acoes']:
        parts.append(f"- Ações sugeridas pra esse momento de funil: {' / '.join(ctx['funil_acoes'])}")
    if ctx['nivel_label']:
        parts.append(f"- Estratégia recomendada: {ctx['nivel_label']}")
        if ctx['nivel_oportunidades']:
            parts.append(f"- O que essa estratégia entrega: {' / '.join(ctx['nivel_oportunidades'])}")
        if ctx['nivel_sinais']:
            parts.append(f"- Sinais que justificam: {' / '.join(ctx['nivel_sinais'])}")
    if ctx['opportunity_reasons']:
        parts.append(f"- Pontos fracos detectados no site: {' / '.join(ctx['opportunity_reasons'])}")
    return "\n".join(parts) if parts else "(diagnóstico ainda não disponível)"


# Specs por tipo de mensagem da cadência
# ---------------------------------------------------------------------------
# A validação pós-LLM agora vive em ``app.pipeline.outreach.validators``
# (PR1.2/PR1.4) — esta camada apenas orquestra ``validate_hard`` + fixers.
# ---------------------------------------------------------------------------


CADENCE_SPECS = {
    "initial": {
        "day": "D+0",
        "max_lines": "6-8",
        "purpose": "abrir conversa com observação específica + soft ask",
        "extra_rules": [
            "Comece com pattern interrupt (NÃO 'Oi tudo bem'). Pode ser uma pergunta, observação, ou referência direta.",
            "OBRIGATÓRIO: calibre o ângulo do hook pelo `nivel_recomendado` da estratégia (ver bloco CALIBRAÇÃO DO HOOK).",
            "Mencione UM detalhe específico do diagnóstico ou dos sinais — não fale em 'oportunidades de marketing' genérico.",
            "Termine com pergunta aberta ou 'faz sentido a gente trocar 10 min?'.",
        ],
    },
    "bump_d2": {
        "day": "D+2",
        "max_lines": "2-3",
        "purpose": "top of mind COM 1 elemento novo (pergunta ou fato), não ping puro",
        "extra_rules": [
            "Adicione UMA pergunta diferente da initial OU UM fato novo do diagnóstico que não foi citado antes.",
            "Ainda assim ultra-curto (2-3 linhas).",
            "PROIBIDO repetir ângulo ou CTA da initial.",
            "PROIBIDO comentar clima, dia da semana, fim de semana, 'tudo bem com você'.",
            "PROIBIDO ser pitch agressivo — é só um nudge com um detalhe novo.",
        ],
    },
    "insight_d5": {
        "day": "D+5",
        "max_lines": "4-6",
        "purpose": "value drop — compartilhar 1 observação fina sobre o lead, sem pedir nada",
        "extra_rules": [
            "Adicione UMA observação fina sobre o lead que não estava na mensagem inicial — usando dados específicos de # DADOS DO LEAD ou # DIAGNÓSTICO + ESTRATÉGIA.",
            "PROIBIDO: estatística inventada, percentual sem fonte, número de dias sem base, 'estudos mostram', 'dados apontam'.",
            "Pode reforçar com 1 dos sinais reais (tech stack, idade, review específica, oportunidade do diagnóstico).",
            "NÃO peça resposta. Termine com algo aberto tipo 'achei que valeria compartilhar'.",
            "Aqui você está construindo crédito, não vendendo.",
        ],
    },
    "angle_d9": {
        "day": "D+9",
        "max_lines": "4-5",
        "purpose": "trocar ângulo — pivot pra outro vetor",
        "extra_rules": [
            "Use ângulo DIFERENTE do das mensagens anteriores. Se até agora foi sobre presença digital, fale de operação. Se foi de operação, fale de receita ou conversão.",
            "PROIBIDO inventar empresas, concorrentes, casos. PROIBIDO 'concorrentes seus já fazem X' a menos que você tenha o dado.",
            "Apoie no `nivel_recomendado` ou nos `nivel_oportunidades` — esses são os vetores válidos pra pivot.",
            "Mensagem inteira tem que ter substância. NÃO termine com só assinatura.",
            "CTA leve.",
            "ESTRUTURA OPCIONAL — frame PSPP (Problema → Solução → Prova → Próximo passo): "
            "Problema = 1 dor concreta do diagnóstico já citado em mensagens anteriores; "
            "Solução = 1 entrega curta (não pitch completo); "
            "Prova = case similar OU métrica REAL do diagnóstico (sem inventar); "
            "Próximo passo = pequeno (diagnóstico ou piloto, não preço).",
            "PSPP é opcional. Se outro ângulo encaixa melhor, vá nele.",
        ],
    },
    "breakup_d14": {
        "day": "D+14",
        "max_lines": "3-4",
        "purpose": "última mensagem — libera o lead, mantém porta aberta",
        "extra_rules": [
            "Deixe explícito que é a última mensagem dessa sequência.",
            "Sem culpa, sem peso. 'Sem problema', 'sem pressão', 'fica em aberto'.",
            "Assine com nome + site/contato.",
        ],
    },
}


def _parse_llm_response(raw: str) -> tuple[str | None, str | None, str, bool, bool]:
    """Parse the structured LLM response with ÂNGULO/CTA/TEXTO headers.

    Returns ``(angulo, cta, text, angulo_header_present, cta_header_present)``.

    - ``angulo`` / ``cta``: chosen key, or None if missing entirely OR explicitly "none".
    - ``text``: message body. Falls back to ``raw`` if no ``TEXTO:`` header was found.
    - ``*_header_present``: True if the header line was found in ``raw`` (used to
      distinguish "missing" from "explicit none" for validation purposes).
    """
    angulo_match = re.search(r"^ÂNGULO:\s*(\S+)\s*$", raw, re.MULTILINE)
    cta_match = re.search(r"^CTA:\s*(\S+)\s*$", raw, re.MULTILINE)
    text_match = re.search(r"^TEXTO:\s*\n(.*)$", raw, re.MULTILINE | re.DOTALL)
    angulo = angulo_match.group(1) if angulo_match else None
    cta = cta_match.group(1) if cta_match else None
    text = text_match.group(1).strip() if text_match else raw
    if angulo == "none":
        angulo = None
    if cta == "none":
        cta = None
    return angulo, cta, text, angulo_match is not None, cta_match is not None


def _generate_ai_message(
    ctx: dict,
    msg_type: str,
    angulos_usados: set[str],
    ctas_usados: set[str],
) -> GenerationResult:
    """
    Gera mensagem via LLM seguindo persona B2B + cadência fria.

    Returns
    -------
    GenerationResult
        - ``text`` populated + ``errors=[]`` + ``angulo``/``cta`` set → success.
        - ``text=None`` + ``errors=[]`` → infrastructure failure (no API key, no
          choices, empty text, transport exception). Caller falls back silently.
        - ``text=None`` + ``errors=[...]`` → LLM call succeeded but the response
          failed taxonomy parsing or ``validate_hard``. Caller falls back AND
          persists the errors with ``status="erro_geracao"``.
    """
    if not settings.llm_api_key:
        return GenerationResult()

    spec = CADENCE_SPECS.get(msg_type)
    if not spec:
        return GenerationResult()

    facts = _format_ctx_facts(ctx)
    diag = _format_diag_block(ctx)

    # ------------------------------------------------------------------
    # Taxonomy pools — what the LLM may choose for THIS toque
    # ------------------------------------------------------------------
    all_angulos = load_angulos()
    available_angulos = {k: v for k, v in all_angulos.items() if k not in angulos_usados}
    available_ctas = [c for c in ctas_for(msg_type) if c not in ctas_usados]

    def _render_dict_lines(d: dict[str, str]) -> str:
        return "\n".join(f"- {k}: {v}" for k, v in d.items()) if d else "(nenhum)"

    def _render_set_lines(items) -> str:
        items = list(items)
        return "\n".join(f"- {k}" for k in items) if items else "(nenhum)"

    def _render_list_lines(items: list[str]) -> str:
        return "\n".join(f"- {k}" for k in items) if items else "(nenhum)"

    taxonomy_block = (
        "# TAXONOMIA (obrigatório retornar nos campos da resposta)\n"
        "Ângulos disponíveis pra esse toque (escolha 1):\n"
        f"{_render_dict_lines(available_angulos)}\n\n"
        "Ângulos JÁ usados nesta cadência (NÃO repita):\n"
        f"{_render_set_lines(angulos_usados)}\n\n"
        "CTAs disponíveis pra esse toque (escolha 1):\n"
        f"{_render_list_lines(available_ctas)}\n\n"
        "CTAs JÁ usados (NÃO repita):\n"
        f"{_render_set_lines(ctas_usados)}"
    )

    if ctx["has_lp"]:
        lp_instruction = f"\n# LANDING PAGE DE DEMONSTRAÇÃO\nVocê pode (não obrigatório) referenciar a LP de demonstração: {ctx['lp_url']}\nUse APENAS se fizer sentido pro tipo de mensagem (initial/insight). Em bump/breakup, não use."
    else:
        lp_instruction = "\n# SEM LANDING PAGE\nVocê NÃO criou nenhum material de demonstração pra esse lead. NÃO mencione, NÃO prometa, NÃO inclua link. Pivot pra observação ou diagnóstico."

    rules_block = "\n".join(f"- {r}" for r in spec["extra_rules"])

    # Blocos específicos da INITIAL: calibração de hook + estrutura mínima
    hook_block = ""
    if msg_type == "initial":
        initial_extras = _hook_calibration_block(ctx) + "\n\n" + _initial_structure_block(ctx)
        hook_block = "\n\n" + initial_extras

    # PR4.3 — Per-nicho compliance + glossário + cases injection.
    # Tries canonical key first, then raw nicho. Empty if neither has config.
    nicho_canonico_key = (ctx.get("nicho_canonico") or "").strip().lower()
    nicho_key = (ctx.get("nicho") or "").strip().lower()
    compliance_block = _nicho_compliance_block(nicho_canonico_key) or _nicho_compliance_block(nicho_key)
    compliance_section = f"\n\n{compliance_block}" if compliance_block else ""

    prompt = f"""{_persona_block()}

# DADOS DO LEAD
{facts}

# DIAGNÓSTICO + ESTRATÉGIA (use o que existir, ignore o resto)
{diag}
{lp_instruction}{hook_block}{compliance_section}

# TIPO DESTA MENSAGEM
- Tipo: {msg_type} ({spec["day"]} da cadência de 5 toques)
- Objetivo: {spec["purpose"]}
- Tamanho máximo: {spec["max_lines"]} linhas
- Regras específicas:
{rules_block}

{taxonomy_block}

# REGRAS GLOBAIS DE FORMATO
- Saída em português do Brasil natural, conversacional.
- NÃO use markdown (sem **, sem #, sem listas com bullet).
- NÃO use aspas ao redor da mensagem.
- Assinatura: nome do remetente em linha separada (sem cargo nem empresa em todas as mensagens — varia conforme momento).
- Se você não tiver UM detalhe específico real do lead pra mencionar, use observação sóbria sobre nicho/cidade/rating em vez de inventar.
- A mensagem precisa ter SUBSTÂNCIA — corpo + assinatura. NÃO entregue só assinatura ou frase truncada.

# FORMATO DE RESPOSTA (obrigatório)
Retorne EXATAMENTE neste formato, sem variações:

ÂNGULO: <chave do ângulo escolhido>
CTA: <chave do CTA escolhido>
TEXTO:
<corpo da mensagem pronto pra copiar e colar>

Nenhuma das chaves pode ser inventada — usar SOMENTE valores listados em "disponíveis". Se o pool estiver vazio (nenhum disponível), retorne a chave especial "none" — o sistema vai tratar."""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.llm_api_key}",
    }
    model = settings.diagnostic_model or settings.llm_model
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        resp = requests.post(
            f"{settings.llm_base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return GenerationResult()
        raw = (choices[0].get("message", {}).get("content", "") or "").strip()
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        if not raw:
            return GenerationResult()
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1].strip()
        if not raw:
            return GenerationResult()

        # ------------------------------------------------------------------
        # Parse structured output (ÂNGULO / CTA / TEXTO)
        # ------------------------------------------------------------------
        angulo, cta, text, angulo_present, cta_present = _parse_llm_response(raw)

        errors: list[str] = []

        # Taxonomy validation — header presence
        if not angulo_present:
            errors.append("taxonomy:angulo_ausente")
        if not cta_present:
            errors.append("taxonomy:cta_ausente")

        # Taxonomy validation — value membership
        # Cap raw LLM values at 64 chars to keep error codes / logs bounded.
        valid_cta_pool = ctas_for(msg_type)
        angulo_safe = (angulo or "")[:64]
        cta_safe = (cta or "")[:64]
        if angulo is not None and angulo not in all_angulos:
            errors.append(f"taxonomy:angulo_invalido:{angulo_safe}")
        if cta is not None and cta not in valid_cta_pool:
            errors.append(f"taxonomy:cta_invalido:{cta_safe}")

        # Taxonomy validation — no repeat within cadence
        if angulo is not None and angulo in angulos_usados:
            errors.append(f"taxonomy:angulo_repetido:{angulo_safe}")
        if cta is not None and cta in ctas_usados:
            errors.append(f"taxonomy:cta_repetido:{cta_safe}")

        # Body validation
        body_result = validate_hard(text, msg_type)
        if not body_result.passed:
            errors.extend(body_result.errors)

        # Soft validation — clichés. 2+ matches → reject; 0-1 → tolerable.
        # Clichés are softer signals than placeholders, so this runs AFTER
        # validate_hard. A single match logs but doesn't block.
        cliche_hits = detect_ai_cliches(text)
        if len(cliche_hits) >= 2:
            errors.extend(cliche_hits)  # already prefixed with "cliche:"
        elif cliche_hits:
            logger.info("Outreach cliché tolerated (single match): %s", cliche_hits[0])

        # ------------------------------------------------------------------
        # PR4.2 — Glossário + Compliance per-nicho soft validation.
        #
        # Lookup key precedence: nicho_canonico (canonical) → nicho (raw).
        # Whichever returns a non-empty result wins; if both miss, no-op.
        #
        # Thresholds:
        #   - compliance: 1+ match blocks immediately (regulatory).
        #   - glossário: 2+ matches block (style); 1 match is tolerated.
        # ------------------------------------------------------------------
        nicho_key = (ctx.get("nicho") or "").strip().lower()
        nicho_canonico_key = (ctx.get("nicho_canonico") or "").strip().lower()

        compliance_hits = (
            check_compliance(text, nicho_canonico_key)
            or check_compliance(text, nicho_key)
        )
        if compliance_hits:
            errors.extend(compliance_hits)

        glossario_hits = (
            check_glossario(text, nicho_canonico_key)
            or check_glossario(text, nicho_key)
        )
        if len(glossario_hits) >= 2:
            errors.extend(glossario_hits)
        elif glossario_hits:
            logger.info("Glossary term tolerated (single match): %s", glossario_hits[0])

        if errors:
            logger.warning(
                "LLM outreach failed validation (type=%s, errors=%s)",
                msg_type,
                errors,
            )
            return GenerationResult(text=None, errors=errors, angulo=None, cta=None)

        # Apply deterministic fixers in order: spacing first, then capitalization.
        text = fix_capitalization(fix_punctuation_spacing(text))
        return GenerationResult(text=text, errors=[], angulo=angulo, cta=cta)
    except Exception as exc:
        logger.warning("LLM outreach failed (type=%s): %s", msg_type, exc)
        return GenerationResult()


# ---------------------------------------------------------------------------
# Fallback templates (sem LLM ou diagnóstico — mais sóbrios, sem pitch)
# ---------------------------------------------------------------------------


def _fallback(ctx: dict, msg_type: str) -> str:
    """
    Fallback determinístico sem LLM. Sóbrio, sem pitch agressivo.
    Adapta a presença/ausência de LP automaticamente.
    """
    nome = ctx["nome"]
    rating = ctx["rating"]
    reviews = ctx["reviews_count"]
    has_lp = ctx["has_lp"]
    lp_url = ctx["lp_url"]
    has_site = ctx["has_site"]

    sender = settings.your_name
    site = settings.your_website

    if msg_type == "initial":
        if has_site and has_lp:
            return f"""Oi! Tudo certo?
Aqui é o {sender}. Vi a {nome} no Google ({rating}★, {reviews} avaliações) — deu pra perceber que vocês têm tração no offline, mas o site atual deixa um gap claro.
Montei uma versão alternativa só pra você visualizar a ideia (sem compromisso): {lp_url}
Faz sentido a gente trocar 10 min essa semana pra eu te mostrar o que tem por trás?
{sender}"""
        if not has_site and has_lp:
            return f"""Oi! Aqui é o {sender}.
Vi a {nome} no Google ({rating}★, {reviews} avaliações) e notei que vocês não têm site — isso tá custando lead pra concorrente.
Criei uma demo rápida pra mostrar como ficaria: {lp_url}
Faz sentido a gente trocar 10 min sobre isso?
{sender}"""
        # sem LP
        if has_site:
            return f"""Oi! Aqui é o {sender}.
Olhei o site da {nome} e vi alguns ajustes específicos que valeriam testar (especialmente em mobile e captação de lead).
Não tô vendendo nada agora — quero saber se vocês estão olhando esse vetor de marketing digital. Faz sentido trocarmos 10 min?
{sender}"""
        return f"""Oi! Aqui é o {sender}.
Vi a {nome} no Google ({rating}★, {reviews} avaliações) — vocês mandam bem no atendimento, mas sem site próprio o lead novo bate em concorrente.
Tô falando com alguns negócios do nicho de {ctx['nicho']} pra entender se site + automação simples faz sentido pra vocês.
Topa 10 min pra eu te mostrar como funciona?
{sender}"""

    if msg_type == "bump_d2":
        return f"""Oi {nome.split()[0] if nome else ''} — só dando ping aqui pra não perder o tópico.
Chegou a olhar?
{sender}"""

    if msg_type == "insight_d5":
        if has_lp:
            return f"""Oi! Sem pressa em responder — só queria deixar uma observação.
A demo que montei pra {nome} segue no ar caso queira mostrar pra alguém da equipe ou comparar com o site atual: {lp_url}
Achei que valeria deixar à mão.
{sender}"""
        return f"""Oi! Sem pressa em responder — só queria deixar uma observação.
A maior alavanca digital pro seu nicho costuma ser a primeira impressão que o lead tem antes de qualquer contato — site, LP ou perfil bem feito. Pelo que olhei, tem espaço pra fechar isso melhor.
Tô por aqui se quiser conversar.
{sender}"""

    if msg_type == "angle_d9":
        return f"""Oi! Última tentativa de pegar você nesse vetor — depois sumo.
Se faz mais sentido conversar sobre operação (atendimento, agendamento, automação) em vez de presença digital, também rola. Esse é meu outro vetor.
Me dá um sinal e eu mudo o ângulo.
{sender}"""

    # breakup_d14
    return f"""Oi! Última mensagem dessa sequência.
Sem problema se não for o momento. Fica em aberto — qualquer coisa, é só me chamar.
Bom trabalho pra {nome}!
{sender} | {site}"""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


CADENCE_ORDER = ["initial", "bump_d2", "insight_d5", "angle_d9", "breakup_d14"]


def generate_messages(public_id: str, lead_data: dict, has_lp: bool = False) -> list[dict]:
    """
    Gera lista de 5 mensagens da cadência fria B2B.
    Usa LLM quando há diagnóstico + chave configurada; fallback determinístico caso contrário.
    has_lp: se True, mensagens podem referenciar a LP de demonstração.
    """
    from app.pipeline.outreach.config import compliance_for

    lp = _lp_url(public_id) if has_lp else None
    ctx = _build_context(lead_data, has_lp=has_lp, lp_url=lp)

    # Lead desqualificado → não gera cadência (volta lista vazia, caller decide o que fazer)
    if ctx["qualificado"] is False:
        return []

    phone = _clean_phone(lead_data.get("telefone", ""))
    has_diag = bool(ctx["resumo_executivo"] or ctx["prioridades_top3"] or ctx["nivel_recomendado"])

    # PR4.3 — needs_review notification flag. Computed once per cadence (nicho
    # doesn't change between toques). All 5 messages inherit the same value:
    # True if the lead's nicho has a compliance config (regulated nichos:
    # advocacia, medicina, odontologia, contabilidade, arquitetura, engenharia).
    # Tries canonical key first, then raw nicho. Frontend renders a badge.
    nicho_canonico_key = (lead_data.get("nicho_canonico") or "").strip().lower()
    nicho_key = (lead_data.get("nicho") or "").strip().lower()
    needs_review = bool(compliance_for(nicho_canonico_key) or compliance_for(nicho_key))

    messages: list[dict] = []
    last_idx = len(CADENCE_ORDER) - 1
    # Per-cadence taxonomy bookkeeping (isolated to this call — never leaks).
    angulos_usados: set[str] = set()
    ctas_usados: set[str] = set()

    for i, msg_type in enumerate(CADENCE_ORDER):
        result = GenerationResult()
        if has_diag:
            result = _generate_ai_message(ctx, msg_type, angulos_usados, ctas_usados)
            # Rate limit só ENTRE chamadas LLM, não na última.
            if i < last_idx:
                time.sleep(1)

        if result.text:
            text = result.text
            status = "pronta"
            if result.angulo:
                angulos_usados.add(result.angulo)
            if result.cta:
                ctas_usados.add(result.cta)
        else:
            text = _fallback(ctx, msg_type)
            # Erro só quando o LLM rodou e a validação reprovou; falhas de
            # infraestrutura (sem chave, sem diag, sem choices) caem em
            # fallback silencioso com status="pronta".
            status = "erro_geracao" if result.errors else "pronta"

        whatsapp_link = ""
        if phone and text:
            whatsapp_link = f"https://wa.me/{phone}?text={urllib.parse.quote(text)}"

        messages.append({
            "type": msg_type,
            "message_text": text,
            "whatsapp_link": whatsapp_link,
            "status": status,
            "validation_errors": result.errors or None,
            "angulo_usado": result.angulo,
            "cta_usado": result.cta,
            "needs_review": needs_review,
        })

    return messages
