"""
Módulo 3: Gerador de Landing Pages Personalizadas
Gera uma LP completa pro negócio do prospect via Claude API.
Usa system/user/prefill separation, few-shot examples, GSAP motion,
e verificação anti-slop para output de agência real.
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


# ─── Constantes do prompt otimizado ──────────────────────────────────────────

GSAP_CDN = "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5"

DESIGN_EXAMPLES = """
<examples>

<example type="hero_magnetico" descricao="Hero com gradient mesh animado + text reveal staggered + floating elements">
<code_snippet>
/* Gradient mesh vivo — NÃO é um linear-gradient genérico */
.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 20% 80%, rgba(120, 0, 255, 0.15) 0%, transparent 70%),
    radial-gradient(ellipse 60% 40% at 80% 20%, rgba(255, 107, 53, 0.12) 0%, transparent 60%),
    radial-gradient(ellipse 50% 80% at 50% 50%, rgba(0, 200, 150, 0.08) 0%, transparent 50%);
  animation: meshShift 12s ease-in-out infinite alternate;
}
@keyframes meshShift {
  0% { transform: scale(1) rotate(0deg); }
  100% { transform: scale(1.15) rotate(3deg); }
}

/* Text reveal com clip-path — NÃO é um fade-in genérico */
.hero-title span {
  display: inline-block;
  clip-path: inset(100% 0 0 0);
  animation: textReveal 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.hero-title span:nth-child(2) { animation-delay: 0.12s; }
.hero-title span:nth-child(3) { animation-delay: 0.24s; }
@keyframes textReveal {
  to { clip-path: inset(0 0 0 0); }
}

/* Floating decorative element — NÃO é um circle estático */
.hero-orb {
  position: absolute;
  width: clamp(200px, 30vw, 400px);
  height: clamp(200px, 30vw, 400px);
  border-radius: 30% 70% 70% 30% / 30% 30% 70% 70%;
  background: linear-gradient(135deg, var(--accent) 0%, transparent 60%);
  opacity: 0.12;
  filter: blur(60px);
  animation: orbFloat 8s ease-in-out infinite alternate;
}
@keyframes orbFloat {
  0% { transform: translate(0, 0) rotate(0deg); border-radius: 30% 70% 70% 30% / 30% 30% 70% 70%; }
  100% { transform: translate(30px, -40px) rotate(15deg); border-radius: 50% 50% 30% 70% / 60% 40% 60% 40%; }
}
</code_snippet>
</example>

<example type="card_premium" descricao="Card com borda gradient animada + inner glow + tilt 3D no hover">
<code_snippet>
.card {
  position: relative;
  background: var(--surface);
  border-radius: 16px;
  padding: 2rem;
  overflow: hidden;
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.4s ease;
}
/* Borda gradient animada — NÃO é um border: 1px solid genérico */
.card::before {
  content: '';
  position: absolute;
  inset: 0;
  padding: 1px;
  border-radius: inherit;
  background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.03), rgba(255,255,255,0.08));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}
/* Inner spotlight que segue o mouse */
.card::after {
  content: '';
  position: absolute;
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, var(--accent-alpha-10) 0%, transparent 70%);
  border-radius: 50%;
  transform: translate(var(--mouse-x, 50%), var(--mouse-y, 50%)) translate(-50%, -50%);
  opacity: 0;
  transition: opacity 0.4s;
  pointer-events: none;
}
.card:hover { transform: translateY(-6px) scale(1.02); box-shadow: 0 20px 60px rgba(0,0,0,0.25); }
.card:hover::after { opacity: 1; }
</code_snippet>
</example>

<example type="cta_irresistivel" descricao="CTA com ripple effect + glow pulsante + micro-copy animado">
<code_snippet>
.cta-primary {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 18px 36px;
  font-size: clamp(1rem, 2vw, 1.15rem);
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #fff;
  background: var(--accent);
  border: none;
  border-radius: 14px;
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease;
  /* Glow pulsante — sutil, NÃO neon */
  box-shadow:
    0 0 0 0 var(--accent-alpha-30),
    0 8px 32px rgba(0,0,0,0.2);
  animation: ctaPulse 3s ease-in-out infinite;
}
@keyframes ctaPulse {
  0%, 100% { box-shadow: 0 0 0 0 var(--accent-alpha-30), 0 8px 32px rgba(0,0,0,0.2); }
  50% { box-shadow: 0 0 0 8px var(--accent-alpha-0), 0 12px 40px rgba(0,0,0,0.25); }
}
.cta-primary:hover {
  transform: translateY(-2px) scale(1.04);
  box-shadow: 0 0 0 0 var(--accent-alpha-0), 0 16px 48px rgba(0,0,0,0.3);
}
/* Shimmer sweep no texto */
.cta-primary::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(105deg, transparent 40%, rgba(255,255,255,0.15) 50%, transparent 60%);
  transform: translateX(-100%);
  animation: shimmer 4s ease-in-out infinite;
}
@keyframes shimmer { 0%,100% { transform: translateX(-100%); } 50% { transform: translateX(100%); } }
</code_snippet>
</example>

<example type="scroll_animation_gsap" descricao="Setup GSAP+ScrollTrigger para reveal de seções">
<code_snippet>
/* Inclua no final do body: */
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>
<script>
gsap.registerPlugin(ScrollTrigger);
// Respeita preferência do usuário
if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
  // Reveal de seções com stagger
  gsap.utils.toArray('section').forEach(section => {
    const els = section.querySelectorAll('.reveal');
    gsap.fromTo(els,
      { y: 40, opacity: 0, filter: 'blur(4px)' },
      { y: 0, opacity: 1, filter: 'blur(0px)', duration: 0.8,
        stagger: 0.1, ease: 'power3.out',
        scrollTrigger: { trigger: section, start: 'top 80%', once: true }
      }
    );
  });
  // Parallax sutil em elementos decorativos
  gsap.utils.toArray('.parallax').forEach(el => {
    gsap.to(el, {
      y: -60, ease: 'none',
      scrollTrigger: { trigger: el, start: 'top bottom', end: 'bottom top', scrub: 1.5 }
    });
  });
  // Counter animado nos números de prova social
  gsap.utils.toArray('.stat-number').forEach(el => {
    const target = parseFloat(el.dataset.value);
    gsap.fromTo(el, { textContent: 0 },
      { textContent: target, duration: 1.8, ease: 'power2.out', snap: { textContent: target % 1 === 0 ? 1 : 0.1 },
        scrollTrigger: { trigger: el, start: 'top 85%', once: true }
      }
    );
  });
}
</script>
</code_snippet>
</example>

</examples>
"""

ANTI_PATTERNS = """
<anti_patterns>

NÃO FAÇA — "AI SLOP" (design genérico de IA):
╔═══════════════════════════════════════════════════════════════╗
║  ❌ linear-gradient(135deg, #667eea, #764ba2)               ║
║  ❌ background: #f5f5f5 (cinza genérico)                    ║
║  ❌ font-family: Inter, Roboto, Arial, system-ui            ║
║  ❌ border-radius: 8px em TUDO (monotonia)                  ║
║  ❌ box-shadow: 0 2px 8px rgba(0,0,0,0.1) (sombra morta)   ║
║  ❌ opacity: 0 → 1 como ÚNICA animação                     ║
║  ❌ Cards todos iguais, simétricos, grid perfeito           ║
║  ❌ Cores pastel sem personalidade (#e0e7ff, #f0fdf4)       ║
║  ❌ "Welcome to X" / "About Us" / "Our Services"           ║
║  ❌ Hero com imagem stock + overlay gradient                 ║
║  ❌ Espaçamento uniforme entre TODAS as seções              ║
║  ❌ @keyframes fadeIn { to { opacity: 1 } } como animação   ║
╚═══════════════════════════════════════════════════════════════╝

FAÇA ISTO — DESIGN REAL DE AGÊNCIA:
╔═══════════════════════════════════════════════════════════════╗
║  ✅ Gradient meshes com 3+ radial-gradients sobrepostos     ║
║  ✅ Dark themes com profundidade (3+ tons de dark)          ║
║  ✅ Google Fonts expressivas: Satoshi, Cabinet Grotesk,     ║
║     Space Grotesk, Outfit, Syne, Unbounded, Plus Jakarta    ║
║  ✅ border-radius VARIADO: 4px, 16px, 24px, 50% (proposit.)║
║  ✅ Sombras em camadas: 2-3 box-shadows sobrepostas        ║
║  ✅ clip-path reveals, translateY+blur combo, text split    ║
║  ✅ Cards com tamanhos DIFERENTES, grid irregular           ║
║  ✅ Cores com PERSONALIDADE: accent forte + neutrals deep   ║
║  ✅ Headlines = benefício transformador, nunca descritivo   ║
║  ✅ Hero com gradient mesh vivo OU tipografia oversized     ║
║  ✅ Ritmo visual: seções densas alternando com respiros     ║
║  ✅ GSAP ScrollTrigger: blur+y+opacity combo, parallax     ║
║  ✅ Micro-interações: card spotlight, button ripple, glow   ║
╚═══════════════════════════════════════════════════════════════╝

</anti_patterns>
"""

MOTION_SPECS = """
<motion_system>

BIBLIOTECA: GSAP 3.12 + ScrollTrigger (CDN cloudflare)
Scripts no final do <body>, APÓS todo o HTML.

EASING CURVES (usar em TUDO):
  - Entradas: cubic-bezier(0.16, 1, 0.3, 1) — "power3.out" no GSAP
  - Saídas: cubic-bezier(0.7, 0, 0.84, 0) — "power3.in" no GSAP
  - Hover: cubic-bezier(0.34, 1.56, 0.64, 1) — overshoot bounce
  - NUNCA use "ease", "ease-in-out", ou "linear" sozinhos

SCROLL ANIMATIONS (via GSAP ScrollTrigger):
  1. Section reveal: y:40 + opacity:0 + filter:blur(4px) → y:0 + opacity:1 + blur:0
     - stagger: 0.1s entre elementos filhos com classe .reveal
     - trigger: 'top 80%', once: true
  2. Parallax decorativo: elementos .parallax movem y:-60 com scrub:1.5
  3. Counter animado: .stat-number com data-value="4.8" anima de 0 ao valor
  4. Text split: headlines de seção com chars animados individualmente (opcional, alto impacto)

CSS ANIMATIONS (carregam sem JS):
  1. Hero text reveal: clip-path: inset(100% 0 0 0) → inset(0) com stagger via animation-delay
  2. CTA glow: box-shadow pulsante 3s infinite com var(--accent) alpha
  3. CTA shimmer: sweep de luz diagonal 4s infinite
  4. Gradient mesh: transform scale + rotate suave 12s alternate
  5. Floating orbs: translateY + border-radius morph 8s alternate
  6. Navbar shadow: transição de box-shadow via classe .scrolled (IntersectionObserver mínimo)

REGRA DE OURO: @media (prefers-reduced-motion: reduce) desliga TODAS as animações.

IMPORTANTE — ORDEM NO HTML:
  1. Todo o HTML semântico
  2. <script src="gsap.min.js"> (CDN cloudflare)
  3. <script src="ScrollTrigger.min.js"> (CDN cloudflare)
  4. <script> inline com setup (max 40 linhas)

</motion_system>
"""


def _build_prompt_messages(
    lead_data: dict,
    niche: str,
    theme: dict,
    reviews_text: str,
    gaps_text: str,
    diagnostic_context: str,
    phone_clean: str,
    copy_fw: str,
) -> tuple[str, list[dict]]:
    """
    Constrói system prompt e lista de mensagens (user + assistant prefill)
    para gerar uma landing page de alta conversão.

    Retorna (system_prompt, messages) onde messages inclui o prefill
    "<!DOCTYPE html>" para forçar output direto em HTML.
    """

    system_prompt = f"""<role>
Você é o VITOR — um design engineer de elite que trabalha na interseção de
brand design, motion design e engenharia frontend. Você tem 12 anos de experiência
criando landing pages que convertem para negócios locais brasileiros.

Seu trabalho é reconhecido por:
- NUNCA parecer "feito por IA" — cada LP tem personalidade única e memorável
- Motion design cinematográfico com GSAP ScrollTrigger (scroll reveals, parallax, counters animados)
- Tipografia expressiva com Google Fonts que ninguém mais usa
- Dark themes com profundidade real (3-4 tons, não flat)
- Layouts que quebram a previsibilidade (assimetria intencional, grid breaking, overlaps)
- Micro-interações que encantam (card spotlight, button shimmer, gradient morphing)
- Código production-ready: semântico, acessível, performático

Suas ferramentas:
- HTML5 semântico + CSS moderno (container queries, has(), nesting)
- GSAP 3.12 + ScrollTrigger para scroll animations
- Google Fonts (NUNCA Inter, Roboto, Arial)
- SVG inline para ícones e formas
- CSS Houdini-inspired techniques (gradient meshes, morphing shapes)
</role>

<filosofia_design>
PRINCÍPIO #1 — ANTI-SLOP:
Todo elemento deve justificar sua existência. Se parece genérico, reescreva.
Se outra IA geraria igual, mude. O teste: um designer humano olharia e diria "isso é bom".

PRINCÍPIO #2 — MOTION COM PROPÓSITO:
Animação não é decoração, é storytelling. Cada animação guia o olho,
revela informação progressivamente, ou cria sensação de premium.

PRINCÍPIO #3 — DARK ≠ ESCURO:
Dark themes têm PROFUNDIDADE. Mínimo 4 tons de escuro no background system.
Surface cards flutuam SOBRE o background, não se fundem nele.

PRINCÍPIO #4 — OBJETIVO ÚNICO:
A LP tem UM destino: WhatsApp. Sem escape routes. Sem links externos.
Sem distrações. Cada pixel empurra para o CTA.
</filosofia_design>

<regras_absolutas>
1. JAMAIS gere texto antes do HTML. Continue DIRETO do DOCTYPE fornecido.
2. NUNCA invente depoimentos. Use APENAS reviews reais fornecidos ou omita.
3. NUNCA use Inter, Roboto, Arial, system-ui, sans-serif genérico como fonte.
4. NUNCA use gradientes roxo-azul genéricos (#667eea → #764ba2).
5. TODA animação respeita prefers-reduced-motion.
6. O hero DEVE ter CTA visível above the fold com WhatsApp link.
7. Cada <section> TEM id para navegação por âncoras.
8. Links: APENAS wa.me, âncoras internas (#xxx), tel:, Google Fonts. NADA MAIS.
9. GSAP carrega via CDN cloudflare no final do body. Max 40 linhas de JS.
10. Código LIMPO: sem comentários óbvios, sem CSS redundante, sem divs wrapper desnecessários.
</regras_absolutas>

{DESIGN_EXAMPLES}

{ANTI_PATTERNS}

{MOTION_SPECS}"""

    user_prompt = f"""Crie a landing page completa para o negócio abaixo.

<dados_negocio>
  <nome>{lead_data.get('nome', 'N/A')}</nome>
  <categoria>{niche}</categoria>
  <endereco>{lead_data.get('endereco', '')}</endereco>
  <telefone>{lead_data.get('telefone', '')}</telefone>
  <whatsapp_link>https://wa.me/{phone_clean}</whatsapp_link>
  <nota_google>{lead_data.get('rating', '')}</nota_google>
  <total_avaliacoes>{lead_data.get('reviews_count', '')}</total_avaliacoes>
  <website_atual>{lead_data.get('website', 'NÃO TEM')}</website_atual>
</dados_negocio>

<avaliacoes_reais>
{reviews_text or 'Nenhuma disponível — use APENAS nota e número como proof. NÃO invente depoimentos.'}
</avaliacoes_reais>

<problemas_site_atual>
{gaps_text or 'Sem análise disponível'}
</problemas_site_atual>

<contexto_diagnostico>
{diagnostic_context}
</contexto_diagnostico>

<design_tokens>
  <estilo>{theme["style"]}</estilo>
  <bg>{theme["bg"]}</bg>
  <surface>{theme["surface"]}</surface>
  <accent>{theme["accent"]}</accent>
  <tom>{theme["tone"]}</tom>
  <heading_font>{theme["heading_font"]}</heading_font>
  <body_font>{theme["body_font"]}</body_font>
  <hero_variant>{theme["hero_variant"]}</hero_variant>
  <copy_framework>{theme["copy_framework"]}</copy_framework>
</design_tokens>

<copy_framework_detalhado>
{copy_fw}
Aplique este framework em TODA a LP, não apenas no hero.
</copy_framework_detalhado>

<banner_info>
  <business_name>{settings.business_name}</business_name>
  <website>{settings.your_website}</website>
  <cidade>{lead_data.get('cidade', 'sua cidade')}</cidade>
</banner_info>

<processo_criativo>
Antes de escrever código, tome estas decisões mentalmente (NÃO inclua no output):

PASSO 1 — IDENTIDADE: Qual a personalidade visual deste negócio?
  - Um restaurante sofisticado ≠ uma clínica odontológica ≠ uma academia
  - Que EMOÇÃO o visitante deve sentir? Confiança? Desejo? Urgência? Acolhimento?

PASSO 2 — TIPOGRAFIA: Escolha 2 fontes do Google Fonts que NÃO sejam Inter/Roboto/Arial.
  - Heading: expressiva, com personalidade (Satoshi, Cabinet Grotesk, Syne, Outfit, Space Grotesk, Unbounded, Plus Jakarta Sans, Clash Display, General Sans)
  - Body: legível, complementar (DM Sans, Manrope, Figtree, Geist, Onest)
  - O PAR deve criar tensão harmoniosa — não duas fontes iguais

PASSO 3 — PALETA: Monte o color system completo:
  - --bg: tom mais escuro (background principal)
  - --bg-deep: 1 tom mais escuro que bg (footer, seções alternadas)
  - --bg-soft: 1 tom mais claro que bg (variação de seções)
  - --surface: card/modal background (claramente diferente de bg)
  - --accent: cor de ação (CTAs, destaques, links)
  - --accent-soft: accent com 10-15% opacity (hover states, glows)
  - --text: rgba(255,255,255,0.92)
  - --text-muted: rgba(255,255,255,0.55)
  - --border: rgba(255,255,255,0.06)

PASSO 4 — HERO IMPACT: O hero é a primeira impressão.
  - Qual headline comunica a TRANSFORMAÇÃO em ≤10 palavras?
  - Que elemento visual diferencia: gradient mesh? tipografia oversized? forma orgânica?
  - O CTA está GRANDE e IMPOSSÍVEL de ignorar?

PASSO 5 — MOTION PLAN: Quais animações vão guiar o storytelling?
  - Hero: text reveal com clip-path + orb flutuante + gradient shift
  - Scroll: GSAP reveals com blur+y combo, parallax em elementos decorativos
  - Interação: card spotlight (mouse follow), CTA shimmer, hover lifts
  - Counters: números de prova social animados quando entram na viewport

PASSO 6 — LAYOUT BREAKING: Onde vou quebrar a previsibilidade?
  - Pelo menos 1 seção com layout assimétrico (grid irregular ou offset)
  - Cards com tamanhos diferentes (1 featured + 2 menores)
  - Overlap intencional de pelo menos 1 elemento entre seções
  - Espaçamento RITMADO: seções densas → respiro → densa → respiro

PASSO 7 — VERIFICAÇÃO ANTI-SLOP:
  - Remova QUALQUER coisa que outra IA geraria igual
  - As fontes são expressivas? (não Inter/Roboto)
  - As cores têm personalidade? (não pastel genérico)
  - As animações são cinematográficas? (não fade-in básico)
  - Os cards têm micro-interação? (não hover:scale(1.05) morto)
  - A LP parece feita por uma AGÊNCIA, não por um template?
</processo_criativo>

<secoes_obrigatorias>

Cada seção DEVE ter id para funcionar com a navbar de âncoras.
Adicione classe "reveal" nos elementos que devem animar com GSAP.

1. BANNER TOPO (não é seção):
   - Fino (28-32px), background accent, z-index acima da navbar
   - "Preview criada por {settings.business_name} — {settings.your_website}"
   - font-size: 11-12px, centralizado

2. NAVBAR (sticky, backdrop-filter: blur(16px)):
   - Desktop: logo/nome esquerda → links âncora centro → CTA WhatsApp direita
   - Mobile: nome + CTA compacto. SEM hamburger.
   - Shadow on scroll via IntersectionObserver mínimo
   - Links: "Serviços", "Como Funciona", "Depoimentos", "FAQ"

3. HERO (id="inicio", min-height: 100svh):
   - H1: benefício/transformação ≤10 palavras. Framework: {theme["copy_framework"]}
   - Sub-headline: 1 frase complementar (max 20 palavras)
   - CTA primário: "Agendar pelo WhatsApp" → wa.me/{phone_clean}
     - Ícone WhatsApp SVG inline, glow pulsante, shimmer sweep
   - Micro-copy: "Sem compromisso · Resposta imediata"
   - CTA secundário sutil: "Conheça nossos serviços ↓" → #servicos
   - Proof: "{lead_data.get('rating', '')}★ · {lead_data.get('reviews_count', '')} avaliações"
   - Visual: gradient mesh animado + orb flutuante + formas decorativas
   - ANIMAÇÃO: text reveal clip-path staggered, orb float, gradient shift

4. BARRA DE CONFIANÇA:
   - 3-4 stats em row (nota Google, anos, clientes atendidos, etc.)
   - Números com classe .stat-number + data-value para counter animado GSAP
   - Scroll horizontal suave no mobile

5. PROBLEMA (id="problema"):
   - "Você já passou por isso?" — headline empática
   - 3-4 dores ESPECÍFICAS do nicho em cards ou lista com ícones
   - Linguagem emocional, identificável. Tom: "isso sou eu"
   - NUNCA mencione o negócio nesta seção

6. SOLUÇÃO (id="solucao"):
   - Transição: "E se existisse um lugar onde..."
   - {lead_data.get('nome', '')} como resposta para cada dor
   - 2-3 bullets com bold + descrição
   - Mini CTA: "Conheça nossos serviços ↓"

7. SERVIÇOS (id="servicos"):
   - Headline = benefício, NÃO "Nossos Serviços"
   - 4-6 cards em grid responsivo (layout IRREGULAR: 1 featured grande + menores)
   - Cada card: ícone SVG/emoji + título bold + 1-2 linhas benefício
   - Cards com: borda gradient, inner spotlight (mouse follow via CSS var), hover lift

8. COMO FUNCIONA (id="como-funciona"):
   - 3 steps em timeline visual
   - Número grande (accent, 48-64px) + título + 1 frase
   - Linha ou path SVG conectando steps
   - Desktop: horizontal. Mobile: vertical

   CTA MID-PAGE (após "Como Funciona"):
   - "Pronto para começar?" + botão WhatsApp + micro-copy com cidade

9. DEPOIMENTOS (id="depoimentos"):
   - COM reviews reais: cards com aspas decorativas (accent), texto, nome/iniciais
   - SEM reviews: "Reconhecido no Google" com nota 72-96px + estrelas + total avaliações
   - NUNCA invente depoimentos fictícios
   - Layout: carousel overflow-x no mobile, grid no desktop

10. FAQ (id="faq"):
    - 5-6 perguntas via <details>/<summary>
    - Summary estilizado: cursor pointer, padding, seta que rotaciona via CSS
    - Respostas ≤50 palavras
    - Perguntas REAIS do nicho

11. CTA FINAL (id="contato"):
    - Background accent/gradient
    - Headline com urgência contextual (NÃO falsa escassez)
    - Botão WhatsApp GRANDE invertido
    - Proof: cidade + "Resposta em minutos" + "Sem compromisso"

12. FOOTER:
    - Background --bg-deep (mais escuro que bg principal)
    - Endereço, tel: link, horários estimados
    - Copyright: "© 2025 {lead_data.get('nome', '')} · Site por {settings.business_name}"
    - ZERO links externos

CTA FLUTUANTE MOBILE (fora das seções):
  - position: fixed, bottom: 0, width: 100%, z-index: 99
  - "Agendar pelo WhatsApp" + ícone WhatsApp SVG
  - Background accent, padding 16px, safe-area-inset-bottom
  - box-shadow: 0 -4px 20px rgba(0,0,0,0.3)
  - VISÍVEL apenas em max-width: 768px

</secoes_obrigatorias>

<copywriting_rules>
- Headlines = BENEFÍCIO/TRANSFORMAÇÃO, nunca descritivas
- PROIBIDO: "Bem-vindo", "Conheça", "Sobre nós", "Nossos serviços" como headlines
- CTAs em primeira pessoa: "Agendar MINHA consulta", "Garantir MINHA vaga"
- NUNCA: "Saiba mais", "Clique aqui", "Entre em contato", "Submit"
- Micro-copy ABAIXO de cada CTA sem exceção
- Parágrafos: máximo 3 linhas. Prefira bullets a blocos.
- Bold nos termos-chave para scannability
- PROIBIDO superlativos vazios: "revolucionário", "o melhor", "líder de mercado"
- Português brasileiro natural — coloquial mas profissional
- Cada H2 comunica benefício, não nomeia seção
</copywriting_rules>

<requisitos_tecnicos>
- <!DOCTYPE html>, <html lang="pt-BR">, meta viewport + charset + title
- Semantic HTML: header, nav, main, section[id], footer
- CSS em <style> no <head>. ZERO CSS externo (exceto Google Fonts)
- Google Fonts via <link> no <head> com display=swap
- html {{ scroll-behavior: smooth }}
- Ícones: emojis ou SVG inline. PROIBIDO FontAwesome ou CDN de ícones
- PROIBIDO imagens externas — use gradientes, SVG, formas CSS, emojis
- GSAP + ScrollTrigger via CDN cloudflare no FINAL do body
- JS inline max 40 linhas (GSAP setup + navbar scroll)
- Accessibility: contrast WCAG AA, focus-visible, aria-hidden em SVGs decorativos
- Meta title (50-60 chars): nome + cidade + nicho
- Meta description (150-160 chars): benefício + CTA
- padding-bottom no body: 80px no mobile para CTA flutuante
- PROIBIDO: animações com mais de 4 properties simultâneas (performance)
- PROIBIDO: filter: blur() em elementos visíveis durante scroll (jank)
</requisitos_tecnicos>

Gere o HTML completo agora. Continue DIRETO do DOCTYPE já fornecido, sem texto antes ou depois."""

    messages = [
        {"role": "user", "content": user_prompt},
        {"role": "assistant", "content": "<!DOCTYPE html>"},
    ]

    return system_prompt, messages


def generate_landing_page(lead_data: dict) -> str:
    """
    Gera HTML completo de uma landing page personalizada pro negócio do lead.
    Usa Claude API com system/user/prefill separation para output de alta qualidade.
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

    system_prompt, messages = _build_prompt_messages(
        lead_data=lead_data,
        niche=niche,
        theme=theme,
        reviews_text=reviews_text,
        gaps_text=gaps_text,
        diagnostic_context=diagnostic_context,
        phone_clean=phone_clean,
        copy_fw=copy_fw,
    )

    headers = {
        "Content-Type": "application/json",
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": settings.claude_model,
        "max_tokens": 12000,
        "system": system_prompt,
        "messages": messages,
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

        if html.startswith("```"):
            html = re.sub(r"^```\w*\n?", "", html)
            html = re.sub(r"\n?```$", "", html)

        # Prepend o prefill que o modelo continuou
        html = "<!DOCTYPE html>" + html

        return html

    except Exception:
        return ""
