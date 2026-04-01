"""
Módulo 3: Gerador de Landing Pages Personalizadas
Gera uma LP completa pro negócio do prospect via Claude API.
"""

import re

import requests

from app.config import settings


def _get_theme_for_niche(niche: str) -> str:
    """Retorna diretrizes de design específicas por nicho."""
    niche_lower = (niche or "").lower()
    themes = {
        "dentista": "Corporate Premium: navy/slate base (#0f172a, #1e293b) com accent em azul-teal (#0d9488). Fontes: Clash Display (headings) + DM Sans (body). Tom: confiança e modernidade clínica.",
        "clínica": "Corporate Premium: navy profundo (#0c1222) com accent em teal (#14b8a6). Fontes: Satoshi (headings) + Source Sans 3 (body). Tom: autoridade médica e acolhimento.",
        "estética": "Luxury: preto/charcoal (#1a1a2e) com accent em rose-gold (#e8b4b8) ou dourado suave. Fontes: Playfair Display (headings) + DM Sans (body). Tom: exclusividade e sofisticação.",
        "restaurante": "Modern Playful: fundo escuro quente (#1c1917) com accent em laranja/amber (#f59e0b). Fontes: Bricolage Grotesque (headings) + DM Sans (body). Tom: energia, sabor e experiência.",
        "pizzaria": "Modern Playful: fundo dark (#1c1917) com accent em vermelho-tomate (#ef4444) e dourado. Fontes: Cabinet Grotesk (headings) + DM Sans (body). Tom: artesanal e convidativo.",
        "salão": "Luxury: fundo escuro sofisticado (#18181b) com accent em rosa/mauve (#d946ef). Fontes: Fraunces (headings) + DM Sans (body). Tom: glamour e cuidado pessoal.",
        "barbearia": "Industrial: fundo slate escuro (#0f172a) com accent em amber (#d97706). Fontes: Clash Display (headings) + JetBrains Mono (detalhes). Tom: masculino, moderno e premium.",
        "pet": "Solarpunk: fundo quente escuro (#1a1a2e) com accent em green (#22c55e) e earth tones. Fontes: Satoshi (headings) + DM Sans (body). Tom: carinhoso e confiável.",
        "academia": "Dashboard Dense: fundo escuro (#09090b) com accent em lime/green (#84cc16). Fontes: Clash Display (headings) + Source Sans 3 (body). Tom: energia, resultado e performance.",
        "veterinária": "Corporate Premium: fundo slate (#0f172a) com accent em emerald (#10b981). Fontes: Newsreader (headings) + DM Sans (body). Tom: cuidado profissional e empatia.",
        "loja": "Editorial: fundo off-black (#111111) com accent vibrante baseado no produto. Fontes: Bricolage Grotesque (headings) + DM Sans (body). Tom: moderno e curado.",
    }
    for key, theme in themes.items():
        if key in niche_lower:
            return theme
    return "Modern Playful: fundo escuro elegante (#18181b) com accent em emerald (#34d399). Fontes: Satoshi (headings) + DM Sans (body). Tom: profissional e acessível."


def generate_landing_page(lead_data: dict) -> str:
    """
    Gera HTML completo de uma landing page personalizada pro negócio do lead.
    Usa Claude API pra criar design + copy sob medida.
    Retorna o HTML completo ou string vazia em caso de falha.
    """
    reviews_text = ""
    if lead_data.get("top_reviews"):
        reviews_text = "\n".join(f'- "{r}"' for r in lead_data["top_reviews"][:3])

    gaps_text = ""
    if lead_data.get("opportunity_reasons"):
        gaps_text = "\n".join(f"- {r}" for r in lead_data["opportunity_reasons"])

    phone_clean = (lead_data.get("telefone") or "").replace("+", "").replace("-", "").replace(" ", "")
    niche = lead_data.get('categoria', lead_data.get('nicho', ''))
    theme = _get_theme_for_niche(niche)

    # Contexto do diagnóstico de marketing (se disponível)
    diagnostic_context = ""
    diag = lead_data.get("site_analysis", {}).get("diagnostico_marketing")
    if diag:
        diagnostic_context = f"""
DIAGNÓSTICO DE MARKETING:
- Resumo: {diag.get('resumo_executivo', '')}
- Momento no funil: {diag.get('momento_funil', '')}
- Prioridades: {', '.join(diag.get('prioridades_top3', []))}
- Potencial IA: {diag.get('potencial_ia_automacao', {}).get('justificativa', '')}

Use estas informações pra ajustar o tom e foco da LP:
- Se momento_funil=descoberta → LP mais educativa, explique quem é o negócio e por que confiar
- Se momento_funil=atracao/consideracao → LP focada em diferenciação e prova social
- Se momento_funil=acao → LP direta, CTA forte e urgência"""

    prompt = f"""Gere o HTML COMPLETO de uma landing page que seja MEMORÁVEL e visualmente impressionante para o seguinte negócio local brasileiro.
O objetivo é fazer o dono do negócio pensar "caramba, eu PRECISO desse site" ao abrir o link.

DADOS DO NEGÓCIO:
- Nome: {lead_data['nome']}
- Categoria: {niche}
- Endereço: {lead_data.get('endereco', '')}
- Telefone: {lead_data.get('telefone', '')}
- Nota Google: {lead_data.get('rating', '')} estrelas ({lead_data.get('reviews_count', '')} avaliações)
- Website atual: {lead_data.get('website', 'NÃO TEM')}

AVALIAÇÕES REAIS DO GOOGLE (use como depoimentos):
{reviews_text or 'Sem avaliações disponíveis'}

PROBLEMAS DO SITE ATUAL:
{gaps_text or 'Sem análise disponível'}
{diagnostic_context}

TEMA DE DESIGN (OBRIGATÓRIO — siga estas diretrizes):
{theme}

REQUISITOS DE DESIGN:
1. HTML COMPLETO com <!DOCTYPE html>, <head>, <body> — arquivo standalone
2. TIPOGRAFIA DISTINTA: use Google Fonts conforme o tema. NUNCA use Inter, Roboto, Arial ou system fonts. Use pesos extremos (300 vs 800). Tamanhos com clamp() pra fluid type (ex: clamp(2.5rem, 5vw, 4.5rem) pra headlines).
3. 100% RESPONSIVO (mobile-first): hero stack vertical no mobile, lado a lado no desktop. Grid de features: 1col → 2col → 3col. CTAs full-width no mobile.
4. CORES E ATMOSFERA: siga o tema acima. NUNCA fundo branco puro (#fff). Use off-blacks, gradientes sutis, noise textures via CSS. Cor dominante com accent forte.
5. MOTION E ANIMAÇÃO:
   - Staggered reveal: elementos aparecem com animation-delay (50-100ms entre eles), fade-up de 20px, opacity 0→1, duration 500ms, easing cubic-bezier(0.16, 1, 0.3, 1)
   - Hover em cards: scale 1.02-1.05, transição de sombra 150ms
   - CTA principal: pulso sutil ou glow animado
   - Respeitar prefers-reduced-motion
6. LAYOUT ESPACIAL: negative space generoso (120-200px padding entre seções). Hero ocupa ~100vh. Seções alternando tons de fundo pra criar ritmo visual. Layouts ASSIMÉTRICOS — evite simetria previsível.
7. BACKGROUNDS: gradient meshes, formas CSS abstratas, grain overlay sutil. Nunca fundos flat sem textura.

SEÇÕES OBRIGATÓRIAS (nesta ordem):
1. HERO: headline com benefício em <10 palavras (descreva a TRANSFORMAÇÃO, não o produto) + sub-headline 1 frase + CTA "Agendar pelo WhatsApp" (link: https://wa.me/{phone_clean}). Visual com gradientes ou formas CSS.
2. SOCIAL PROOF: barra com nota Google ({lead_data.get('rating', '')} estrelas), número de avaliações, badges de confiança. Números grandes e destacados.
3. SERVIÇOS: 4-6 cards com emoji/SVG + título + descrição curta. Grid responsivo.
4. COMO FUNCIONA: 3 passos visuais em timeline ou numbered cards.
5. DEPOIMENTOS: use reviews reais se disponíveis. Cards com aspas, nome. Se não tiver reviews, crie 2 depoimentos realistas pro nicho.
6. FAQ: 3-4 perguntas com accordion CSS (details/summary). Perguntas comuns pro nicho.
7. CTA FINAL: repetir CTA principal com urgência ("Vagas limitadas", "Agende esta semana"). WhatsApp link.
8. FOOTER: simples, com endereço + telefone + redes.
9. BANNER SUTIL no topo: "Preview criada por {settings.business_name} — {settings.your_website}" com link pro portfólio.

COPYWRITING:
- Headlines com benefício/transformação, NUNCA genéricas como "Bem-vindo ao [nome]"
- CTAs com verbo de ação + resultado: "Agendar minha consulta", "Garantir minha vaga", "Pedir meu orçamento". NUNCA "Saiba mais" ou "Clique aqui".
- Parágrafos curtos (2-3 linhas max). Bullet points > blocos de texto.
- Todo texto em português brasileiro natural.

RESTRIÇÕES TÉCNICAS:
- Ícones: emojis ou SVG inline (NÃO FontAwesome CDN)
- NÃO inclua imagens externas — use gradientes, formas CSS, emojis e SVG
- Todo CSS inline no <style> — ZERO dependências exceto Google Fonts
- Semantic HTML: <header>, <main>, <section>, <footer>
- Contrast ratio WCAG AA mínimo. Focus states visíveis.

ANTI-PATTERNS (NUNCA FAÇA ISSO):
- Inter, Roboto, Arial ou system fonts
- Gradientes roxos genéricos em fundo branco
- Layouts previsíveis e 100% simétricos
- Hero genérico com "Bem-vindo ao [Nome]"
- CTAs fracos ("Saiba mais", "Clique aqui")
- Seções sem espaçamento adequado (< 80px padding)
- Fundos brancos puros sem atmosfera

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
