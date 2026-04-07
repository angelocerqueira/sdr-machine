"""
Módulo 4: Outreach via WhatsApp
Gera mensagens personalizadas para cada lead usando o diagnóstico de marketing.
"""

import re
import time
import urllib.parse

import requests

from app.config import settings


def _clean_phone(phone: str) -> str:
    """Normaliza número de telefone removendo caracteres especiais."""
    cleaned = (phone or "").replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    if cleaned and not cleaned.startswith("55"):
        cleaned = "55" + cleaned
    return cleaned


def _lp_url(lead_id: int | str) -> str:
    """Constrói a URL da landing page para o lead."""
    return f"{settings.api_url}/api/leads/{lead_id}/lp"


def _get_diagnostic(lead_data: dict) -> dict | None:
    """Extrai diagnóstico de marketing do site_analysis."""
    return lead_data.get("site_analysis", {}).get("diagnostico_marketing")


def _generate_ai_message(lead_data: dict, lp_url: str, msg_type: str) -> str | None:
    """
    Gera mensagem via Claude API baseada no diagnóstico.
    Retorna None se a API falhar (fallback pra template).
    """
    if not settings.llm_api_key:
        return None

    diag = _get_diagnostic(lead_data)
    if not diag:
        return None

    nome = lead_data.get("nome", "")
    rating = lead_data.get("rating", "")
    reviews = lead_data.get("reviews_count", "")
    nicho = lead_data.get("nicho", lead_data.get("categoria", ""))
    momento = diag.get("momento_funil", "")
    resumo = diag.get("resumo_executivo", "")
    prioridades = diag.get("prioridades_top3", [])
    ia_opps = diag.get("potencial_ia_automacao", {}).get("oportunidades", [])

    if msg_type == "initial":
        prompt = f"""Gere uma mensagem de WhatsApp para prospecção de um negócio local brasileiro.

CONTEXTO:
- Você é {settings.your_name}, da {settings.business_name}
- Você trabalha com criação de sites, automações e IA para negócios locais
- Você encontrou o negócio no Google Maps e já criou uma landing page de demonstração

DADOS DO NEGÓCIO:
- Nome: {nome}
- Nicho: {nicho}
- Nota Google: {rating} estrelas ({reviews} avaliações)
- Site atual: {lead_data.get('website', 'NÃO TEM')}

DIAGNÓSTICO DO NEGÓCIO:
- Resumo: {resumo}
- Momento no funil de marketing: {momento}
- Top 3 prioridades: {', '.join(prioridades)}
- Oportunidades de IA/automação: {', '.join(ia_opps) if ia_opps else 'automação geral de processos'}

LINK DA LP DE DEMONSTRAÇÃO: {lp_url}

REGRAS DA MENSAGEM:
1. Tom casual e amigável, como se estivesse mandando um WhatsApp normal
2. Máximo 6-8 linhas (WhatsApp é curto!)
3. Mencione algo ESPECÍFICO do diagnóstico que vai chamar atenção do dono (não genérico)
4. Se identificou oportunidade de IA/automação, mencione de forma natural (ex: "vi que vocês poderiam automatizar o agendamento")
5. Inclua o link da LP como demonstração gratuita
6. Feche com algo leve, sem pressão
7. NÃO use emojis excessivos (máx 2)
8. NÃO use linguagem corporativa ("venho por meio desta", "prezado")
9. Assine com o nome e empresa

Retorne APENAS o texto da mensagem, sem aspas, sem explicação."""

    elif msg_type == "followup_48h":
        prompt = f"""Gere uma mensagem de follow-up de WhatsApp (48h após a primeira mensagem).

CONTEXTO:
- Você é {settings.your_name}, da {settings.business_name}
- Já mandou uma mensagem inicial pra {nome} com uma LP de demonstração
- Quer saber se viram a LP e gerar interesse

DIAGNÓSTICO DO NEGÓCIO:
- Top 3 prioridades: {', '.join(prioridades)}
- Oportunidade de IA mais relevante: {ia_opps[0] if ia_opps else 'automação de processos'}

LINK DA LP: {lp_url}

REGRAS:
1. Máximo 4-5 linhas
2. Casual e leve, sem pressão
3. Mencione UMA coisa específica que poderia melhorar rapidamente pro negócio
4. Inclua o link de novo
5. Sem emojis excessivos
6. Assine com o nome

Retorne APENAS o texto da mensagem."""

    elif msg_type == "followup_final":
        prompt = f"""Gere a última mensagem de follow-up de WhatsApp para {nome}.

CONTEXTO:
- Você é {settings.your_name} | {settings.your_website}
- Já mandou 2 mensagens anteriores sem resposta
- Última chance, quer deixar porta aberta

REGRAS:
1. Máximo 3-4 linhas
2. Respeitoso, sem pressão nenhuma
3. Deixe claro que é a última mensagem
4. Deixe porta aberta pro futuro
5. Assine com nome e site

Retorne APENAS o texto da mensagem."""
    else:
        return None

    model = settings.diagnostic_model or settings.llm_model
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.llm_api_key}",
    }
    payload = {
        "model": model,
        "max_tokens": 500,
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
            return None
        text = (choices[0].get("message", {}).get("content", "") or "").strip()
        # Strip thinking blocks (MiniMax, DeepSeek, etc.)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        if not text:
            return None
        # Remove aspas se a resposta vier envolvida
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        return text
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Fallback templates (usados quando não há diagnóstico ou API falha)
# ---------------------------------------------------------------------------


def _fallback_initial_com_site(lead_data: dict, lp_url: str) -> str:
    """Mensagem fallback pra quem TEM site mas é ruim."""
    nome = lead_data.get("nome", "")
    gaps = lead_data.get("opportunity_reasons", [])[:2]
    gaps_text = ""
    if gaps:
        gaps_text = f" Vi que o site atual tem algumas oportunidades de melhoria ({', '.join(g.lower() for g in gaps)})."

    return f"""Oi! Tudo bem?

Me chamo {settings.your_name}, trabalho com criação de sites e automações pra negócios locais.

Encontrei a {nome} no Google Maps e curti demais a avaliação de vocês ({lead_data.get('rating', '')} estrelas).{gaps_text}

Fiz uma versão moderna do site de vocês como demonstração — totalmente gratuita, sem compromisso:

{lp_url}

Se curtir, a gente conversa sobre implementar. Se não curtir, tá tudo certo também!

Abraço!
{settings.your_name}
{settings.business_name}"""


def _fallback_initial_sem_site(lead_data: dict, lp_url: str) -> str:
    """Mensagem fallback pra quem NÃO tem site."""
    nome = lead_data.get("nome", "")

    return f"""Oi! Tudo bem?

Me chamo {settings.your_name}, trabalho com criação de sites pra negócios locais.

Encontrei a {nome} no Google Maps — nota {lead_data.get('rating', '')} estrelas com {lead_data.get('reviews_count', '')} avaliações, vocês mandam muito bem!

Notei que vocês ainda não têm um site. Criei uma versão profissional como demonstração gratuita:

{lp_url}

Ficou com a cara de vocês! Se quiser implementar, me avisa. Sem compromisso nenhum.

Abraço!
{settings.your_name}
{settings.business_name}"""


def _fallback_followup_48h(lead_data: dict, lp_url: str) -> str:
    nome = lead_data.get("nome", "")
    return f"""Oi! Só passando pra saber se conseguiu ver a prévia que fiz pra {nome}?

{lp_url}

Caso tenha interesse, essa semana ainda consigo implementar com condição especial. Me avisa!

{settings.your_name}"""


def _fallback_followup_final(lead_data: dict) -> str:
    nome = lead_data.get("nome", "")
    return f"""Oi! Última mensagem sobre aquela prévia do site da {nome}.

Se não for o momento, sem problemas! Mas se quiser conversar sobre presença digital no futuro, é só me chamar.

Bom trabalho pra vocês!
{settings.your_name} | {settings.your_website}"""


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------


def generate_messages(lead_id: int | str, lead_data: dict) -> list[dict]:
    """
    Gera lista de 3 mensagens (initial, followup_48h, followup_final).
    Usa IA quando diagnóstico disponível, senão usa templates fallback.
    """
    lp = _lp_url(lead_id)
    phone = _clean_phone(lead_data.get("telefone", ""))
    has_site = lead_data.get("website") and lead_data.get("site_analysis", {}).get("status") == "ok"
    has_diagnostic = _get_diagnostic(lead_data) is not None

    # Tentar IA primeiro, fallback pra template
    if has_diagnostic:
        initial_text = _generate_ai_message(lead_data, lp, "initial")
        time.sleep(1)  # Rate limit between Claude API calls
        followup_48h_text = _generate_ai_message(lead_data, lp, "followup_48h")
        time.sleep(1)
        followup_final_text = _generate_ai_message(lead_data, lp, "followup_final")
    else:
        initial_text = None
        followup_48h_text = None
        followup_final_text = None

    # Fallback pra templates se IA falhou
    if not initial_text:
        initial_text = _fallback_initial_com_site(lead_data, lp) if has_site else _fallback_initial_sem_site(lead_data, lp)
    if not followup_48h_text:
        followup_48h_text = _fallback_followup_48h(lead_data, lp)
    if not followup_final_text:
        followup_final_text = _fallback_followup_final(lead_data)

    def _whatsapp_link(text: str) -> str:
        if not phone:
            return ""
        return f"https://wa.me/{phone}?text={urllib.parse.quote(text)}"

    return [
        {
            "type": "initial",
            "message_text": initial_text,
            "whatsapp_link": _whatsapp_link(initial_text),
        },
        {
            "type": "followup_48h",
            "message_text": followup_48h_text,
            "whatsapp_link": _whatsapp_link(followup_48h_text),
        },
        {
            "type": "followup_final",
            "message_text": followup_final_text,
            "whatsapp_link": _whatsapp_link(followup_final_text),
        },
    ]
