"""
Módulo 4: Outreach via WhatsApp
Gera mensagens personalizadas para cada lead.
"""

import urllib.parse

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


def msg_com_site_ruim(lead_data: dict, lp_url: str) -> str:
    """Mensagem pra quem TEM site mas é ruim."""
    nome = lead_data["nome"]
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


def msg_sem_site(lead_data: dict, lp_url: str) -> str:
    """Mensagem pra quem NÃO tem site."""
    nome = lead_data["nome"]

    return f"""Oi! Tudo bem?

Me chamo {settings.your_name}, trabalho com criação de sites pra negócios locais.

Encontrei a {nome} no Google Maps — nota {lead_data.get('rating', '')} estrelas com {lead_data.get('reviews_count', '')} avaliações, vocês mandam muito bem!

Notei que vocês ainda não têm um site. Criei uma versão profissional como demonstração gratuita:

{lp_url}

Ficou com a cara de vocês! Se quiser implementar, me avisa. Sem compromisso nenhum.

Abraço!
{settings.your_name}
{settings.business_name}"""


def msg_followup_48h(lead_data: dict, lp_url: str) -> str:
    """Follow-up 48h depois."""
    nome = lead_data["nome"]

    return f"""Oi! Só passando pra saber se conseguiu ver a prévia que fiz pra {nome}?

{lp_url}

Caso tenha interesse, essa semana ainda consigo implementar com condição especial. Me avisa!

{settings.your_name}"""


def msg_followup_final(lead_data: dict) -> str:
    """Último follow-up (5-7 dias depois)."""
    nome = lead_data["nome"]

    return f"""Oi! Última mensagem sobre aquela prévia do site da {nome}.

Se não for o momento, sem problemas! Mas se quiser conversar sobre presença digital no futuro, é só me chamar.

Bom trabalho pra vocês!
{settings.your_name} | {settings.your_website}"""


def generate_messages(lead_id: int | str, lead_data: dict) -> list[dict]:
    """
    Gera lista de 3 mensagens (initial, followup_48h, followup_final)
    para o lead. Retorna list[dict] com type, message_text, whatsapp_link.
    """
    lp = _lp_url(lead_id)
    phone = _clean_phone(lead_data.get("telefone", ""))

    has_site = lead_data.get("website") and lead_data.get("site_analysis", {}).get("status") == "ok"

    if has_site:
        initial_text = msg_com_site_ruim(lead_data, lp)
    else:
        initial_text = msg_sem_site(lead_data, lp)

    followup_48h_text = msg_followup_48h(lead_data, lp)
    followup_final_text = msg_followup_final(lead_data)

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
