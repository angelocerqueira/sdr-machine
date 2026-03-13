"""
Módulo 3: Gerador de Landing Pages Personalizadas
Gera uma LP completa pro negócio do prospect via Claude API.
"""

import re

import requests

from app.config import settings


def generate_landing_page(lead_data: dict) -> str:
    """
    Gera HTML completo de uma landing page personalizada pro negócio do lead.
    Usa Claude API pra criar design + copy sob medida.
    Retorna o HTML completo ou string vazia em caso de falha.
    """
    reviews_text = ""
    if lead_data.get("top_reviews"):
        reviews_text = "\n".join(f'- "{r}"' for r in lead_data["top_reviews"][:2])

    gaps_text = ""
    if lead_data.get("opportunity_reasons"):
        gaps_text = "\n".join(f"- {r}" for r in lead_data["opportunity_reasons"])

    phone_clean = (lead_data.get("telefone") or "").replace("+", "").replace("-", "").replace(" ", "")

    prompt = f"""Gere o HTML COMPLETO de uma landing page moderna e profissional para o seguinte negócio local brasileiro.
O objetivo é impressionar o dono do negócio quando ele abrir o link — ele precisa pensar "caramba, ficou muito melhor que o meu site atual".

DADOS DO NEGÓCIO:
- Nome: {lead_data['nome']}
- Categoria: {lead_data.get('categoria', lead_data.get('nicho', ''))}
- Endereço: {lead_data.get('endereco', '')}
- Telefone: {lead_data.get('telefone', '')}
- Nota Google: {lead_data.get('rating', '')} estrelas ({lead_data.get('reviews_count', '')} avaliações)
- Website atual: {lead_data.get('website', 'NÃO TEM')}

AVALIAÇÕES REAIS DO GOOGLE (use como depoimentos):
{reviews_text or 'Sem avaliações disponíveis'}

PROBLEMAS DO SITE ATUAL:
{gaps_text or 'Sem análise disponível'}

REQUISITOS DO HTML:
1. HTML COMPLETO com <!DOCTYPE html>, <head>, <body> — arquivo standalone
2. Design MODERNO: cores profissionais que combinem com o nicho, tipografia via Google Fonts
3. 100% RESPONSIVO (mobile-first)
4. Seções obrigatórias:
   - Hero com headline forte + CTA "Agendar pelo WhatsApp" (link: https://wa.me/{phone_clean})
   - Barra de stats (rating, anos, etc — pode inventar dados razoáveis)
   - Serviços/especialidades (baseado no nicho, 4-6 itens)
   - Depoimento (use as reviews reais se tiver)
   - CTA final com WhatsApp
   - Footer simples
5. BANNER SUTIL no topo: "Preview criada por {settings.business_name} — {settings.your_website}" com link pro seu portfólio
6. Animações CSS suaves (fadeIn no scroll)
7. Ícones: use emojis ou SVG inline (NÃO use FontAwesome CDN)
8. NÃO inclua imagens externas — use gradientes, formas CSS e emojis
9. Paleta de cores que faça sentido pro nicho (ex: verde/azul pra saúde, quente pra restaurante)
10. Todo CSS inline no <style> — ZERO dependências externas exceto Google Fonts

Retorne APENAS o HTML completo, sem markdown, sem explicação, sem ```html```. Comece direto com <!DOCTYPE html>."""

    headers = {
        "Content-Type": "application/json",
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": settings.claude_model,
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        html = data["content"][0]["text"].strip()

        # Limpa caso venha com markdown wrapper
        if html.startswith("```"):
            html = re.sub(r"^```\w*\n?", "", html)
            html = re.sub(r"\n?```$", "", html)

        return html

    except Exception:
        return ""
