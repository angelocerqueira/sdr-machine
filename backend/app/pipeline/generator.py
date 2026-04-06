"""
Módulo 3: Gerador de Landing Pages Personalizadas
Gera uma LP completa pro negócio do prospect via Claude API.
"""

import re

import requests

from app.config import settings


def _get_theme_for_niche(niche: str) -> dict:
    """Retorna diretrizes de design específicas por nicho."""
    niche_lower = (niche or "").lower()
    themes = {
        "dentista": {
            "style": "Corporate Premium",
            "bg": "#0f172a", "surface": "#1e293b", "accent": "#0d9488",
            "heading_font": "Clash Display", "body_font": "DM Sans",
            "tone": "confiança e modernidade clínica",
            "copy_framework": "PAS",
            "hero_variant": "split",
        },
        "clínica": {
            "style": "Corporate Premium",
            "bg": "#0c1222", "surface": "#162032", "accent": "#14b8a6",
            "heading_font": "Satoshi", "body_font": "Source Sans 3",
            "tone": "autoridade médica e acolhimento",
            "copy_framework": "PAS",
            "hero_variant": "centered",
        },
        "estética": {
            "style": "Luxury",
            "bg": "#1a1a2e", "surface": "#252540", "accent": "#e8b4b8",
            "heading_font": "Playfair Display", "body_font": "DM Sans",
            "tone": "exclusividade e sofisticação",
            "copy_framework": "AIDA",
            "hero_variant": "gradient",
        },
        "restaurante": {
            "style": "Modern Playful",
            "bg": "#1c1917", "surface": "#292524", "accent": "#f59e0b",
            "heading_font": "Bricolage Grotesque", "body_font": "DM Sans",
            "tone": "energia, sabor e experiência",
            "copy_framework": "BAB",
            "hero_variant": "split",
        },
        "pizzaria": {
            "style": "Modern Playful",
            "bg": "#1c1917", "surface": "#292524", "accent": "#ef4444",
            "heading_font": "Cabinet Grotesk", "body_font": "DM Sans",
            "tone": "artesanal e convidativo",
            "copy_framework": "BAB",
            "hero_variant": "centered",
        },
        "salão": {
            "style": "Luxury",
            "bg": "#18181b", "surface": "#27272a", "accent": "#d946ef",
            "heading_font": "Fraunces", "body_font": "DM Sans",
            "tone": "glamour e cuidado pessoal",
            "copy_framework": "AIDA",
            "hero_variant": "gradient",
        },
        "barbearia": {
            "style": "Industrial",
            "bg": "#0f172a", "surface": "#1e293b", "accent": "#d97706",
            "heading_font": "Clash Display", "body_font": "JetBrains Mono",
            "tone": "masculino, moderno e premium",
            "copy_framework": "BAB",
            "hero_variant": "split",
        },
        "pet": {
            "style": "Solarpunk",
            "bg": "#1a1a2e", "surface": "#252540", "accent": "#22c55e",
            "heading_font": "Satoshi", "body_font": "DM Sans",
            "tone": "carinhoso e confiável",
            "copy_framework": "PAS",
            "hero_variant": "centered",
        },
        "academia": {
            "style": "Dashboard Dense",
            "bg": "#09090b", "surface": "#18181b", "accent": "#84cc16",
            "heading_font": "Clash Display", "body_font": "Source Sans 3",
            "tone": "energia, resultado e performance",
            "copy_framework": "BAB",
            "hero_variant": "split",
        },
        "veterinária": {
            "style": "Corporate Premium",
            "bg": "#0f172a", "surface": "#1e293b", "accent": "#10b981",
            "heading_font": "Newsreader", "body_font": "DM Sans",
            "tone": "cuidado profissional e empatia",
            "copy_framework": "PAS",
            "hero_variant": "centered",
        },
        "loja": {
            "style": "Editorial",
            "bg": "#111111", "surface": "#1a1a1a", "accent": "#f97316",
            "heading_font": "Bricolage Grotesque", "body_font": "DM Sans",
            "tone": "moderno e curado",
            "copy_framework": "AIDA",
            "hero_variant": "split",
        },
    }
    for key, theme in themes.items():
        if key in niche_lower:
            return theme
    return {
        "style": "Modern Playful",
        "bg": "#18181b", "surface": "#27272a", "accent": "#34d399",
        "heading_font": "Satoshi", "body_font": "DM Sans",
        "tone": "profissional e acessível",
        "copy_framework": "PAS",
        "hero_variant": "centered",
    }


_COPY_FRAMEWORKS = {
    "PAS": """Framework PAS (Problem-Agitate-Solution):
- HERO H1: Descreva o PROBLEMA que o cliente enfrenta (não o produto)
- Sub-headline: AGITE — mostre a consequência de não resolver
- CTA: Apresente a SOLUÇÃO — o negócio como resposta
Exemplo: H1="Cansado de esperar semanas por uma consulta?" / Sub="Cada dia sem cuidar do sorriso é um dia a mais de desconforto" / CTA="Agendar minha consulta hoje"
""",
    "AIDA": """Framework AIDA (Attention-Interest-Desire-Action):
- HERO H1: Declaração BOLD que captura ATENÇÃO imediata
- Sub-headline: Fato INTERESSANTE que desperta curiosidade
- Seções: Construa DESEJO com provas e benefícios
- CTA: AÇÃO clara e específica
Exemplo: H1="O sorriso que você sempre quis, em uma única visita" / Sub="Mais de 500 pacientes transformados com tecnologia 3D" / CTA="Quero meu sorriso novo"
""",
    "BAB": """Framework BAB (Before-After-Bridge):
- HERO H1: Descreva o estado ANTES (dor/frustração do cliente)
- Sub-headline: Pinte o DEPOIS (resultado desejado)
- CTA: O negócio é a PONTE entre os dois
Exemplo: H1="De cliente insatisfeito a fã declarado" / Sub="Transforme cada visita em uma experiência que seus clientes vão recomendar" / CTA="Começar minha transformação"
""",
}


def generate_landing_page(lead_data: dict) -> str:
    """
    Gera HTML completo de uma landing page personalizada pro negócio do lead.
    Usa Claude API pra criar design + copy sob medida.
    Retorna o HTML completo ou string vazia em caso de falha.
    """
    reviews_text = ""
    if lead_data.get("top_reviews"):
        reviews_text = "\n".join(f'- "{r}"' for r in lead_data["top_reviews"][:5])

    gaps_text = ""
    if lead_data.get("opportunity_reasons"):
        gaps_text = "\n".join(f"- {r}" for r in lead_data["opportunity_reasons"])

    phone_clean = (lead_data.get("telefone") or "").replace("+", "").replace("-", "").replace(" ", "")
    niche = lead_data.get('categoria', lead_data.get('nicho', ''))
    theme = _get_theme_for_niche(niche)
    copy_fw = _COPY_FRAMEWORKS[theme["copy_framework"]]

    # Contexto do diagnóstico de marketing (se disponível)
    diagnostic_context = ""
    diag = lead_data.get("site_analysis", {}).get("diagnostico_marketing")
    if diag:
        diagnostic_context = f"""
DIAGNÓSTICO DE MARKETING DO NEGÓCIO:
- Resumo: {diag.get('resumo_executivo', '')}
- Momento no funil: {diag.get('momento_funil', '')}
- Prioridades: {', '.join(diag.get('prioridades_top3', []))}
- Potencial IA: {diag.get('potencial_ia_automacao', {}).get('justificativa', '')}

Ajuste o tom e foco da LP conforme o momento:
- descoberta → LP mais educativa, explique quem é o negócio e por que confiar
- atracao/consideracao → LP focada em diferenciação e prova social
- acao → LP direta, CTA forte e urgência"""

    prompt = f"""Você é um designer/copywriter de elite especializado em landing pages de alta conversão para negócios locais brasileiros.
Sua missão: criar uma LP que faça o dono do negócio pensar "eu PRECISO desse site" ao abrir o link.

═══════════════════════════════════════
DADOS DO NEGÓCIO
═══════════════════════════════════════
- Nome: {lead_data.get('nome', 'N/A')}
- Categoria: {niche}
- Endereço: {lead_data.get('endereco', '')}
- Telefone: {lead_data.get('telefone', '')}
- Nota Google: {lead_data.get('rating', '')} estrelas ({lead_data.get('reviews_count', '')} avaliações)
- Website atual: {lead_data.get('website', 'NÃO TEM')}

Avaliações reais do Google (use como depoimentos REAIS — não invente):
{reviews_text or 'Nenhuma disponível — use apenas a nota e número de avaliações como proof. NÃO invente depoimentos.'}

Problemas detectados no site atual:
{gaps_text or 'Sem análise disponível'}
{diagnostic_context}

═══════════════════════════════════════
FRAMEWORK DE COPY: {theme["copy_framework"]}
═══════════════════════════════════════
{copy_fw}
Aplique este framework em TODA a LP, não apenas no hero.

═══════════════════════════════════════
DIRETRIZES DE DESIGN
═══════════════════════════════════════
ESTILO: {theme["style"]}
PALETA:
  - Background principal: {theme["bg"]}
  - Surface (cards, seções alternadas): {theme["surface"]}
  - Accent (CTAs, destaques): {theme["accent"]}
  - Text: rgba(255,255,255,0.92) para principal, rgba(255,255,255,0.6) para secundário
TOM: {theme["tone"]}

TIPOGRAFIA (Google Fonts OBRIGATÓRIO):
  - Headings: "{theme["heading_font"]}" — pesos 700-900, letter-spacing: -0.02em
  - Body: "{theme["body_font"]}" — peso 400-500
  - Fluid type: clamp(2.5rem, 5vw, 4.5rem) para H1, clamp(1.1rem, 2vw, 1.25rem) para body
  - PROIBIDO: Inter, Roboto, Arial, system-ui, sans-serif genérico

HERO VARIANT: {theme["hero_variant"]}
  - centered: headline + sub + CTA centralizados, background com gradient mesh
  - split: texto à esquerda, forma visual/gradiente à direita, layout assimétrico
  - gradient: hero full-screen com gradient animado como protagonista

MOTION E ANIMAÇÃO (CSS only):
  - Staggered reveal: @keyframes fade-up (translateY(30px) → 0, opacity 0 → 1)
    animation-delay: 0ms, 80ms, 160ms, 240ms entre elementos
    duration: 600ms, easing: cubic-bezier(0.16, 1, 0.3, 1)
  - Cards hover: transform scale(1.03), box-shadow expansion, transition 200ms
  - CTA principal: glow animado com box-shadow pulsante
  - @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; transition: none !important; }} }}

LAYOUT E ESPAÇAMENTO:
  - Padding entre seções: clamp(80px, 12vw, 160px)
  - Max-width do conteúdo: 1200px, centrado
  - Hero: min-height 100vh (ou 100svh)
  - Layouts ASSIMÉTRICOS — quebre a previsibilidade com grids irregulares, overlaps, posicionamento offset
  - Mobile-first: stack vertical no mobile, expand no desktop via @media (min-width: 768px)

BACKGROUNDS E TEXTURA:
  - Nunca fundo flat — use gradient meshes, radial-gradient layers, noise overlay via CSS
  - Grain overlay: background-image com SVG noise, opacity 0.03-0.06
  - Seções alternando entre bg e surface para ritmo visual
  - Formas decorativas: pseudo-elements com blur, gradientes posicionados absolute

═══════════════════════════════════════
NAVEGAÇÃO E CTA STICKY
═══════════════════════════════════════
NAVBAR DE ANCORAGEM (OBRIGATÓRIO):
- <nav> fixo no topo (position: sticky, top: 0, z-index: 100)
- Fundo com backdrop-filter: blur(12px) e background semi-transparente (bg com 80% opacity)
- Logo/nome do negócio à esquerda (texto, não imagem)
- Links de âncora ao centro: "Serviços", "Como Funciona", "Depoimentos", "FAQ" — href="#servicos", href="#como-funciona", etc.
- Botão CTA à direita: "Agendar agora" → WhatsApp link, estilo accent, menor que o CTA do hero
- No MOBILE: navbar compacta com apenas o nome + botão CTA. Links ficam ocultos (sem hamburger — LP não precisa de menu mobile, o scroll natural basta)
- Transição suave: a navbar ganha box-shadow ao scrollar (use CSS :has() ou IntersectionObserver mínimo)
- NUNCA inclua links externos na navbar — apenas âncoras internas e o CTA WhatsApp

CTA FLUTUANTE MOBILE (OBRIGATÓRIO):
- No mobile (max-width: 768px), adicionar um botão CTA fixo na parte inferior da tela
- Position: fixed, bottom: 0, width: 100%, z-index: 99
- Texto: "Agendar pelo WhatsApp" com ícone de WhatsApp SVG
- Background accent, padding generoso (16px), safe-area-inset-bottom para iPhones
- Sombra para cima (box-shadow: 0 -4px 20px rgba(0,0,0,0.3))
- Este botão garante que o CTA está SEMPRE visível, a qualquer scroll position

PRINCÍPIO DE OBJETIVO ÚNICO:
- A LP tem UM objetivo: fazer o visitante clicar no WhatsApp
- Todo link da página deve apontar para o WhatsApp ou para uma âncora interna
- ZERO links externos (exceto o wa.me e Google Fonts)
- Sem "escape routes" — sem menu de navegação do site, sem links para redes sociais, sem "saiba mais" para outra página

═══════════════════════════════════════
SEÇÕES OBRIGATÓRIAS (nesta ordem)
═══════════════════════════════════════
Cada <section> DEVE ter um id para funcionar com os links da navbar.

1. BANNER TOPO: "Preview criada por {settings.business_name} — {settings.your_website}"
   - Fino (28-32px height), acima da navbar, background accent, z-index acima da navbar
   - Texto pequeno (11-12px), centralizado

2. NAVBAR (sticky, como descrito acima)

3. HERO (id="inicio", min-height: 100vh):
   - H1: benefício/transformação em ≤10 palavras. Siga o framework {theme["copy_framework"]}
   - Sub-headline: 1 frase complementar (max 20 palavras)
   - CTA primário: botão GRANDE e proeminente "Agendar pelo WhatsApp" → https://wa.me/{phone_clean}
     - Ícone WhatsApp SVG inline dentro do botão
     - Glow animado (box-shadow pulsante com accent color)
   - Micro-copy abaixo do CTA: "Sem compromisso · Resposta imediata"
   - CTA secundário: link sutil "Conheça nossos serviços ↓" → href="#servicos"
   - Proof rápido: "{lead_data.get('rating', '')}★ · {lead_data.get('reviews_count', '')} avaliações no Google" com estrelas visuais
   - Elementos visuais: gradient mesh, formas CSS decorativas, ou padrão geométrico

4. BARRA DE CONFIANÇA:
   - Números grandes e destacados em row horizontal (ex: "4.8★ Google", "150+ clientes", "5 anos de experiência")
   - Cada número em um card compacto com ícone
   - Scroll horizontal suave no mobile (overflow-x: auto, sem scrollbar visível)
   - Background surface para separar visualmente do hero

5. PROBLEMA (id="problema", seção empática — NÃO mencione o negócio):
   - Headline tipo "Você já passou por isso?"
   - 3-4 dores/frustrações ESPECÍFICAS do público do nicho, em cards ou lista visual
   - Linguagem emocional e identificável. O visitante deve pensar "isso sou eu"
   - Fundo bg para contraste com a seção anterior

6. SOLUÇÃO (id="solucao"):
   - Transição natural: "E se existisse um lugar onde..."
   - Apresente o {lead_data.get('nome', '')} como a resposta para cada dor da seção anterior
   - 2-3 bullets com bold nos termos-chave + breve descrição
   - Pequeno CTA: "Conheça nossos serviços ↓"

7. SERVIÇOS/DIFERENCIAIS (id="servicos"):
   - Headline: algo como "O que fazemos por você" (benefício, não feature)
   - 4-6 cards em grid responsivo (1col → 2col → 3col)
   - Cada card: ícone SVG ou emoji grande (32-40px) + título bold + 1-2 linhas de benefício (não feature)
   - Cards com hover: scale(1.03) + box-shadow expansion + borda accent sutil
   - Background surface para ritmo visual

8. COMO FUNCIONA (id="como-funciona"):
   - 3 passos em timeline visual ou numbered step cards
   - Número grande (48-64px, cor accent) + título + 1 frase de descrição
   - Layout: horizontal no desktop, vertical no mobile
   - Linha ou barra conectando os steps visualmente

   CTA MID-PAGE (após "Como Funciona"):
   - Seção curta com headline "Pronto para começar?" ou "Que tal dar o primeiro passo?"
   - Botão WhatsApp igual ao do hero (mesmo estilo, mesmo link)
   - Micro-copy: "Atendemos em {lead_data.get('cidade', 'sua cidade')}"

9. DEPOIMENTOS (id="depoimentos"):
   - Se tiver reviews reais: cards com aspas grandes decorativas (accent color), texto da review, nome/iniciais
   - Se NÃO tiver reviews: seção "Reconhecido no Google" com nota grande (72-96px), estrelas visuais, número de avaliações. NÃO invente depoimentos fictícios.
   - Layout: carousel horizontal no mobile (overflow-x), grid 2-3 cols no desktop
   - Cards com fundo surface, borda sutil, cantos arredondados

10. FAQ (id="faq"):
    - Headline: "Perguntas Frequentes" ou "Tire suas dúvidas"
    - 5-6 perguntas usando <details>/<summary> (accordion CSS nativo)
    - Estilize o <summary>: cursor pointer, padding, font-weight bold, ícone de seta que rotaciona
    - Respostas curtas (max 50 palavras cada), fazem sentido sozinhas
    - Perguntas devem ser dúvidas REAIS que clientes do nicho teriam
    - Sem fundo extra — mantenha clean

11. CTA FINAL (id="contato"):
    - Background accent ou gradient accent com texto escuro
    - Headline com urgência CONTEXTUAL (não falsa escassez): "Seu [resultado desejado] começa com uma mensagem"
    - Botão WhatsApp GRANDE, estilo invertido (bg escuro, texto accent ou branco)
    - Proof: "Atendemos em {lead_data.get('cidade', '')}", "Resposta em minutos"
    - Micro-copy: "Sem compromisso · Cancelamento a qualquer momento"

12. FOOTER:
    - Background mais escuro que o bg principal
    - Info: endereço, telefone (link tel:), horários estimados do nicho
    - Copyright: "© 2024 {lead_data.get('nome', '')} · Site por {settings.business_name}"
    - ZERO links para redes sociais ou páginas externas

═══════════════════════════════════════
COPYWRITING — REGRAS INVIOLÁVEIS
═══════════════════════════════════════
- Headlines = BENEFÍCIO/TRANSFORMAÇÃO para o CLIENTE, nunca descritivas
- "Bem-vindo ao X", "Conheça o X", "Sobre nós" são PROIBIDOS como headlines
- CTAs em primeira pessoa: "Agendar MINHA consulta", "Garantir MINHA vaga", "Pedir MEU orçamento"
- CTAs específicos: NUNCA "Saiba mais", "Clique aqui", "Entre em contato", "Submit"
- Micro-copy abaixo de CADA botão CTA: "Sem compromisso", "Resposta imediata", "Atendimento humanizado"
- Parágrafos: máximo 3 linhas. Prefira bullets a blocos de texto.
- Bold nos termos-chave dentro de cada frase para scannability
- PROIBIDO superlatives vazios: "revolucionário", "o melhor", "incrível", "líder de mercado", "game-changing"
- Todo texto em português brasileiro natural — coloquial mas profissional
- Cada seção deve ter um heading (H2) que comunica benefício, não apenas nomeia a seção

═══════════════════════════════════════
REQUISITOS TÉCNICOS
═══════════════════════════════════════
- HTML completo: <!DOCTYPE html>, <html lang="pt-BR">, <head> com meta viewport + charset + title, <body>
- Semantic HTML: <header>, <nav>, <main>, <section id="xxx">, <footer>
- CSS no <style> dentro do <head> — ZERO arquivos externos exceto Google Fonts
- Google Fonts via <link> no <head> com display=swap
- html {{ scroll-behavior: smooth }} para navegação suave entre âncoras
- Ícones: emojis ou SVG inline. PROIBIDO FontAwesome ou qualquer icon CDN
- PROIBIDO imagens externas — use gradientes, SVG, formas CSS, emojis
- JS mínimo permitido: APENAS para efeitos de scroll da navbar (shadow on scroll). Máximo 15 linhas de JS.
- Performance: CSS inline, fonts com display=swap, sem bibliotecas externas
- Accessibility: contrast ratio WCAG AA, focus-visible states, aria-hidden em SVGs decorativos
- Meta tags: <title> com nome + cidade + nicho (50-60 chars), meta description com benefício + CTA (150-160 chars)
- padding-bottom no body: 80px no mobile para não ficar atrás do CTA flutuante

═══════════════════════════════════════
ANTI-PATTERNS — NUNCA FAÇA
═══════════════════════════════════════
- Inter, Roboto, Arial, system-ui como fonte
- Fundo branco puro (#fff) ou cinza claro genérico (#f5f5f5)
- Gradientes roxos genéricos
- Layouts 100% simétricos e previsíveis — quebre com assimetria
- "Bem-vindo ao [Nome]" ou "Conheça o [Nome]" como headline
- CTAs vagos ("Saiba mais", "Clique aqui", "Submit", "Enviar")
- Inventar depoimentos/reviews que não existem nos dados
- Seções sem padding adequado (< 80px)
- Texto genérico que serviria para qualquer negócio do planeta
- Cards sem hover effect
- Hero sem CTA visível above the fold
- FAQ com respostas longas (> 50 palavras)
- Links para páginas externas (exceto wa.me) — a LP é um funil fechado
- Navbar com menu hambúrguer complexo — no mobile só nome + CTA
- Sem navbar — a navegação entre seções é OBRIGATÓRIA

Retorne APENAS o HTML completo. Sem markdown, sem explicação, sem ```html```. Comece direto com <!DOCTYPE html>."""

    headers = {
        "Content-Type": "application/json",
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": settings.claude_model,
        "max_tokens": 12000,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=180,
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
