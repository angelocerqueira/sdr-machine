"""
Módulo 3 v2: Gerador de Landing Pages Personalizadas
─────────────────────────────────────────────────────
Arquitetura 2-pass:
  Pass 1 → Creative Brief (copy, paleta, layout decisions, ícones)
  Pass 2 → HTML completo a partir do brief

Mudanças vs v1:
  - Cores dinâmicas: Claude escolhe a paleta por negócio (não hardcoded)
  - SVG icons premium: biblioteca inline, zero emojis
  - 2-pass generation: pensar antes de codificar
  - Gold standard snippet: ancora a qualidade visual
  - Token budget adequado: 16k para HTML
  - System prompt enxuto: exemplos no user prompt
"""

import json
import logging
import re

import requests

from app.config import settings

logger = logging.getLogger(__name__)


# Transient errors worth a single retry — provider blip / TCP reset / slow tail.
# 4xx/5xx HTTPError don't retry: not flaky, payload or auth is wrong.
_TRANSIENT_HTTP_ERRORS = (
    requests.exceptions.ReadTimeout,
    requests.exceptions.ConnectTimeout,
    requests.exceptions.ConnectionError,
)


def _llm_post(url: str, headers: dict, body: dict, timeout: int) -> requests.Response:
    """POST to an LLM endpoint with one retry on transient network errors.

    Caller still wraps in try/except for other failures (parsing, 4xx, 5xx).
    """
    for attempt in (0, 1):  # initial attempt + 1 retry
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=timeout)
            resp.raise_for_status()
            return resp
        except _TRANSIENT_HTTP_ERRORS as exc:
            if attempt == 0:
                logger.warning(
                    "LLM call %s — attempt 1 failed (%s); retrying once",
                    url, type(exc).__name__,
                )
                continue
            raise  # 2nd attempt failed — propagate to caller


# ═══════════════════════════════════════════════════════════════════════════════
# SVG ICON LIBRARY — Ícones inline premium, stroke-based, viewBox 0 0 24 24
# O modelo escolhe por nome no Pass 1, e insere o SVG real no Pass 2.
# ═══════════════════════════════════════════════════════════════════════════════

SVG_ICONS = {
    # ── Geral ──
    "shield": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l7 4v5c0 5.25-3.5 9.74-7 11-3.5-1.26-7-5.75-7-11V6l7-4z"/></svg>',
    "shield-check": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l7 4v5c0 5.25-3.5 9.74-7 11-3.5-1.26-7-5.75-7-11V6l7-4z"/><path d="M9 12l2 2 4-4"/></svg>',
    "scale": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18"/><path d="M4 7l8-4 8 4"/><path d="M4 7v1a4 4 0 004 4h0"/><path d="M20 7v1a4 4 0 01-4 4h0"/><circle cx="8" cy="12" r="1"/><circle cx="16" cy="12" r="1"/></svg>',
    "gavel": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 3.5l6 6-2 2-6-6 2-2z"/><path d="M9 9l-5 5 2 2 5-5"/><path d="M6 19h12"/><path d="M10.5 6.5l-4 4"/></svg>',
    "file-text": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
    "file-search": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><circle cx="11.5" cy="14.5" r="2.5"/><line x1="13.3" y1="16.3" x2="15" y2="18"/></svg>',
    "alert-triangle": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "check-circle": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    "clock": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "map-pin": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "phone": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>',
    "star": '<svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    "star-outline": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    "users": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>',
    "trending-up": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
    "zap": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    "target": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
    "award": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>',
    "eye": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>',
    "lock": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>',
    "refresh-cw": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>',
    "message-circle": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z"/></svg>',
    "calendar": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
    "arrow-right": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>',
    "chevron-down": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>',
    "quote": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M4.583 17.321C3.553 16.227 3 15 3 13.011c0-3.5 2.457-6.637 6.03-8.188l.893 1.378c-3.335 1.804-3.987 4.145-4.247 5.621.537-.278 1.24-.375 1.929-.311C9.591 11.7 11 13.166 11 15c0 1.933-1.567 3.5-3.5 3.5-1.182 0-2.258-.555-2.917-1.179zM14.583 17.321C13.553 16.227 13 15 13 13.011c0-3.5 2.457-6.637 6.03-8.188l.893 1.378c-3.335 1.804-3.987 4.145-4.247 5.621.537-.278 1.24-.375 1.929-.311C19.591 11.7 21 13.166 21 15c0 1.933-1.567 3.5-3.5 3.5-1.182 0-2.258-.555-2.917-1.179z"/></svg>',
    # ── Nicho: Saúde/Dental ──
    "tooth": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2C9.5 2 7 4 7 7c0 2-.5 4-1.5 6S4 17 4 19c0 1.5 1 3 2.5 3s2.5-2 3-4c.3-1.2.8-2 1.5-2h2c.7 0 1.2.8 1.5 2 .5 2 1.5 4 3 4s2.5-1.5 2.5-3c0-2-.5-4-1.5-6S17 9 17 7c0-3-2.5-5-5-5z"/></svg>',
    "heart-pulse": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19.5 12.572l-7.5 7.428-7.5-7.428A5 5 0 0112 5.006a5 5 0 017.5 7.566z"/><path d="M6 12h2l2-3 3 6 2-3h3"/></svg>',
    "stethoscope": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4v6a5 5 0 005 5h2a5 5 0 005-5V4"/><circle cx="19" cy="13" r="2"/><path d="M19 15v3a4 4 0 01-4 4h-2a4 4 0 01-4-4"/><line x1="4" y1="2" x2="4" y2="4"/><line x1="20" y1="2" x2="20" y2="4"/></svg>',
    # ── Nicho: Food ──
    "utensils": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 002-2V2"/><path d="M7 2v20"/><path d="M21 15V2v0a5 5 0 00-5 5v6c0 1.1.9 2 2 2h3zm0 0v7"/></svg>',
    "flame": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 12c2-2.96 0-7-1-8 0 3.038-1.773 4.741-3 6-1.226 1.26-2 3.24-2 5a6 6 0 1012 0c0-1.532-1.056-3.94-2-5-1.786 3-2 2-4 2z"/></svg>',
    # ── Nicho: Beauty ──
    "scissors": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><line x1="20" y1="4" x2="8.12" y2="15.88"/><line x1="14.47" y1="14.48" x2="20" y2="20"/><line x1="8.12" y1="8.12" x2="12" y2="12"/></svg>',
    "sparkles": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z"/><path d="M19 13l.75 2.25L22 16l-2.25.75L19 19l-.75-2.25L16 16l2.25-.75L19 13z"/><path d="M5 17l.5 1.5L7 19l-1.5.5L5 21l-.5-1.5L3 19l1.5-.5L5 17z"/></svg>',
    # ── Nicho: Pet/Vet ──
    "paw": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="8" cy="6" rx="2" ry="2.5"/><ellipse cx="16" cy="6" rx="2" ry="2.5"/><ellipse cx="5" cy="11" rx="2" ry="2.5"/><ellipse cx="19" cy="11" rx="2" ry="2.5"/><path d="M12 18c-2.5 0-5-1.5-5-4s2.5-4 5-4 5 1.5 5 4-2.5 4-5 4z"/></svg>',
    # ── Nicho: Fitness ──
    "dumbbell": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6.5 6.5h11v11h-11z" transform="rotate(45 12 12)"/><line x1="3" y1="21" x2="7" y2="17"/><line x1="17" y1="7" x2="21" y2="3"/></svg>',
    # ── Nicho: Imóveis/Construção ──
    "building": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="9" y1="6" x2="9" y2="6.01"/><line x1="15" y1="6" x2="15" y2="6.01"/><line x1="9" y1="10" x2="9" y2="10.01"/><line x1="15" y1="10" x2="15" y2="10.01"/><line x1="9" y1="14" x2="9" y2="14.01"/><line x1="15" y1="14" x2="15" y2="14.01"/><path d="M9 22v-4h6v4"/></svg>',
    "hard-hat": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M2 18h20"/><path d="M4 18v-3a8 8 0 0116 0v3"/><path d="M12 3v4"/><path d="M8 18v-7"/><path d="M16 18v-7"/></svg>',
    # ── Misc ──
    "dollar-sign": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>',
    "handshake": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 17l-1.5 1.5a2.12 2.12 0 01-3 0L4 16a2.12 2.12 0 010-3L8.5 8.5"/><path d="M13 7l1.5-1.5a2.12 2.12 0 013 0L20 8a2.12 2.12 0 010 3L15.5 15.5"/><path d="M8.5 8.5L13 13"/><path d="M11 13l4 4"/></svg>',
    "leaf": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 8C8 10 5.9 16.17 3.82 21.34L3 21l.34-.82C8.17 18.1 14 15.92 16 7"/><path d="M20.8 3.2S19 8 14 12"/><path d="M3 21l4-4"/></svg>',
    "wrench": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>',
}

# String formatada da biblioteca pra incluir no prompt
def _format_icon_library() -> str:
    """Gera string listando ícones disponíveis com seus nomes."""
    icons_list = ", ".join(sorted(SVG_ICONS.keys()))
    return f"Ícones disponíveis (usar pelo nome entre {{{{icon:nome}}}}): {icons_list}"


# ═══════════════════════════════════════════════════════════════════════════════
# NICHE PERSONALITY — Guias de personalidade, NÃO paletas hardcoded.
# Claude escolhe as cores no Pass 1.
# ═══════════════════════════════════════════════════════════════════════════════

NICHE_GUIDES = {
    "advocacia": {
        "mood": "autoridade, confiança institucional, gravidade profissional",
        "color_direction": "azuis profundos, verdes-escuros ou slate — accent sóbrio mas assertivo (dourado, cobre, teal). NUNCA verde-neon ou cores vibrantes demais.",
        "typography_direction": "Serif para headings (Newsreader, Fraunces, Instrument Serif) ou grotesk pesada (General Sans, Satoshi). Body clean (DM Sans, Manrope).",
        "visual_metaphors": "escudo, coluna, balança, linhas firmes, formas geométricas estáveis",
        "copy_framework": "PAS",
        "icon_suggestions": ["shield-check", "scale", "gavel", "file-text", "file-search", "alert-triangle", "lock", "handshake"],
    },
    "dentista": {
        "mood": "confiança clínica, modernidade, cuidado acessível",
        "color_direction": "dark base com accent em teal, aqua ou mint. Evitar branco hospitalar. Profundidade com tons de slate/zinc.",
        "typography_direction": "Sans-serif moderna para headings (Outfit, Plus Jakarta Sans, Cabinet Grotesk). Body legível (DM Sans, Figtree).",
        "visual_metaphors": "sorriso, precisão, tecnologia, limpeza, transformação",
        "copy_framework": "PAS",
        "icon_suggestions": ["tooth", "sparkles", "check-circle", "clock", "award", "heart-pulse"],
    },
    "clínica": {
        "mood": "autoridade médica, acolhimento, segurança",
        "color_direction": "base escura sofisticada + accent em teal, verde-saúde ou azul-confiança. Temperatura fria mas não gelada.",
        "typography_direction": "Humanista para headings (Satoshi, General Sans). Body com boa legibilidade (Source Sans 3, DM Sans).",
        "visual_metaphors": "cuidado, ciência, resultado, acolhimento, excelência",
        "copy_framework": "PAS",
        "icon_suggestions": ["heart-pulse", "stethoscope", "shield-check", "users", "award", "check-circle"],
    },
    "estética": {
        "mood": "luxo acessível, desejo, transformação pessoal",
        "color_direction": "dark luxuoso (wine, charcoal, onyx) + accent em rose gold, champagne, blush ou lilac. Dourado sutil nos detalhes.",
        "typography_direction": "Serif elegante para headings (Playfair Display, Cormorant, Bodoni Moda). Body delicada (DM Sans, Outfit).",
        "visual_metaphors": "espelho, luz, transformação, curvas suaves, brilho",
        "copy_framework": "AIDA",
        "icon_suggestions": ["sparkles", "eye", "award", "star", "heart-pulse", "calendar"],
    },
    "restaurante": {
        "mood": "experiência sensorial, calor humano, apetite",
        "color_direction": "tons quentes escuros (stone, warm-gray, espresso) + accent em amber, terracotta, warm-orange ou vermelho-queimado.",
        "typography_direction": "Display com personalidade (Bricolage Grotesque, Syne, Fraunces). Body calorosa (DM Sans, Manrope).",
        "visual_metaphors": "fogo, mesa, convívio, artesanal, origem",
        "copy_framework": "BAB",
        "icon_suggestions": ["utensils", "flame", "star", "clock", "map-pin", "users"],
    },
    "pizzaria": {
        "mood": "artesanal, convidativo, tradição com energia",
        "color_direction": "dark quente + accent em vermelho-tomate ou laranja-forno. Detalhes em cream/wheat nos textos.",
        "typography_direction": "Bold e expressiva (Cabinet Grotesk, Clash Display). Body amigável (DM Sans).",
        "visual_metaphors": "forno, massa, calor, comunidade, tradição",
        "copy_framework": "BAB",
        "icon_suggestions": ["flame", "utensils", "star", "clock", "map-pin", "phone"],
    },
    "salão": {
        "mood": "glamour, autocuidado, empoderamento",
        "color_direction": "dark elegante (charcoal, deep-purple) + accent em fuchsia, violet ou rose. Toques metálicos sutis.",
        "typography_direction": "Elegante com atitude (Fraunces, Syne, Clash Display). Body clean (DM Sans, Outfit).",
        "visual_metaphors": "espelho, reflexo, transformação, brilho, estilo",
        "copy_framework": "AIDA",
        "icon_suggestions": ["scissors", "sparkles", "star", "calendar", "award", "eye"],
    },
    "barbearia": {
        "mood": "masculino premium, craft, irmandade",
        "color_direction": "dark industrial (charcoal, gunmetal) + accent em amber, whiskey-gold ou copper. Texturas brutas.",
        "typography_direction": "Industrial/bold (Clash Display, Space Grotesk). Body com peso (JetBrains Mono para detalhes, DM Sans para corpo).",
        "visual_metaphors": "lâmina, precisão, tradição, clube, ofício",
        "copy_framework": "BAB",
        "icon_suggestions": ["scissors", "award", "star", "clock", "users", "target"],
    },
    "pet": {
        "mood": "carinhoso, confiável, alegre",
        "color_direction": "base escura amigável + accent em verde-natureza, coral ou turquesa. Nunca frio demais.",
        "typography_direction": "Friendly e arredondada (Outfit, Plus Jakarta Sans, Nunito Sans). Body suave (DM Sans, Figtree).",
        "visual_metaphors": "pata, coração, natureza, companhia, proteção",
        "copy_framework": "PAS",
        "icon_suggestions": ["paw", "heart-pulse", "shield-check", "star", "clock", "phone"],
    },
    "academia": {
        "mood": "energia, resultado, disciplina premium",
        "color_direction": "dark potente (near-black, graphite) + accent em lime, electric-green, ou orange-energia. Alto contraste.",
        "typography_direction": "Impactante e condensada (Clash Display, Unbounded, Syne). Body atlética (DM Sans, Source Sans 3).",
        "visual_metaphors": "força, progressão, meta, superação, performance",
        "copy_framework": "BAB",
        "icon_suggestions": ["dumbbell", "target", "trending-up", "zap", "award", "clock"],
    },
    "veterinária": {
        "mood": "cuidado profissional, empatia, competência",
        "color_direction": "base escura acolhedora + accent em verde-saúde ou teal-confiança. Calor nos neutros.",
        "typography_direction": "Profissional mas acessível (Satoshi, Outfit). Body clean (DM Sans, Figtree).",
        "visual_metaphors": "pata, estetoscópio, coração, proteção, vida",
        "copy_framework": "PAS",
        "icon_suggestions": ["paw", "heart-pulse", "stethoscope", "shield-check", "clock", "phone"],
    },
    "loja": {
        "mood": "curadoria, descoberta, estilo",
        "color_direction": "dark editorial (ink, charcoal) + accent vibrante que contrasta (coral, amber, electric-blue). Um accent principal + um secundário sutil.",
        "typography_direction": "Editorial com peso (Bricolage Grotesque, General Sans). Body elegante (DM Sans, Manrope).",
        "visual_metaphors": "vitrine, seleção, qualidade, estilo, descoberta",
        "copy_framework": "AIDA",
        "icon_suggestions": ["eye", "sparkles", "star", "trending-up", "award", "arrow-right"],
    },
    "imobiliária": {
        "mood": "aspiracional, confiança, patrimônio",
        "color_direction": "dark sofisticado (navy, charcoal) + accent em dourado, champagne ou teal-premium.",
        "typography_direction": "Elegante e séria (Newsreader, Instrument Serif, General Sans). Body clean (DM Sans, Source Sans 3).",
        "visual_metaphors": "chave, lar, horizonte, investimento, fundação",
        "copy_framework": "AIDA",
        "icon_suggestions": ["building", "lock", "star", "map-pin", "trending-up", "handshake"],
    },
    "construção": {
        "mood": "solidez, competência, resultado tangível",
        "color_direction": "dark industrial (slate, graphite) + accent em amber, safety-orange ou yellow-construção.",
        "typography_direction": "Robusta e direta (Clash Display, Space Grotesk). Body sólida (DM Sans, Source Sans 3).",
        "visual_metaphors": "fundação, estrutura, progresso, ferramenta, planta",
        "copy_framework": "BAB",
        "icon_suggestions": ["hard-hat", "wrench", "building", "check-circle", "shield-check", "trending-up"],
    },
}


def _get_niche_guide(niche: str) -> dict:
    """Retorna guia de personalidade para o nicho. Fallback genérico."""
    niche_lower = (niche or "").lower()
    for key, guide in NICHE_GUIDES.items():
        if key in niche_lower:
            return guide
    return {
        "mood": "profissional, confiável, moderno",
        "color_direction": "dark base sofisticada + accent com personalidade. Escolha cores que reflitam a identidade do negócio, NUNCA verde-menta genérico.",
        "typography_direction": "Heading expressiva (Satoshi, Outfit, Cabinet Grotesk, General Sans). Body legível (DM Sans, Manrope, Figtree).",
        "visual_metaphors": "confiança, resultado, qualidade, proximidade",
        "copy_framework": "PAS",
        "icon_suggestions": ["check-circle", "star", "shield-check", "zap", "users", "clock"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COPY FRAMEWORKS
# ═══════════════════════════════════════════════════════════════════════════════

_COPY_FRAMEWORKS = {
    "PAS": "PAS (Problema→Agitação→Solução): H1 descreve o PROBLEMA, sub agita a consequência, CTA apresenta a solução.",
    "AIDA": "AIDA (Atenção→Interesse→Desejo→Ação): H1 bold captura atenção, sub desperta curiosidade, seções constroem desejo, CTA é ação clara.",
    "BAB": "BAB (Antes→Depois→Ponte): H1 descreve o estado antes, sub pinta o depois, negócio é a ponte.",
}


# ═══════════════════════════════════════════════════════════════════════════════
# GOLD STANDARD — Snippet HTML que demonstra o nível de qualidade esperado.
# NÃO é template — é referência de craft.
# ═══════════════════════════════════════════════════════════════════════════════

GOLD_STANDARD = """
<gold_standard_reference>
Este snippet demonstra o NÍVEL de qualidade visual esperado. NÃO copie — use como referência de craft.

<!-- Hero com gradient mesh real + text reveal + floating orb -->
<section id="inicio" class="hero" style="min-height:100svh;position:relative;display:flex;align-items:center;overflow:hidden;">
  <!-- Gradient mesh: 3 radial-gradients sobrepostos, animados -->
  <div class="hero-mesh" style="position:absolute;inset:0;background:
    radial-gradient(ellipse 70% 50% at 25% 75%, rgba(var(--accent-rgb),0.12) 0%, transparent 65%),
    radial-gradient(ellipse 55% 45% at 80% 25%, rgba(var(--accent-rgb),0.08) 0%, transparent 55%),
    radial-gradient(ellipse 40% 70% at 50% 50%, rgba(var(--accent-rgb),0.05) 0%, transparent 50%);
    animation: meshShift 14s ease-in-out infinite alternate;"></div>

  <!-- Orb flutuante: border-radius morph + blur -->
  <div class="hero-orb" style="position:absolute;right:10%;top:20%;width:clamp(180px,28vw,360px);aspect-ratio:1;
    border-radius:30% 70% 70% 30%/30% 30% 70% 70%;
    background:linear-gradient(135deg,var(--accent) 0%,transparent 60%);
    opacity:0.1;filter:blur(50px);animation:orbFloat 9s ease-in-out infinite alternate;"></div>

  <div style="position:relative;z-index:2;max-width:720px;margin:0 auto;padding:0 24px;text-align:center;">
    <!-- Text reveal com clip-path staggered -->
    <h1 class="hero-title" style="font-family:var(--font-heading);font-size:clamp(2.4rem,5.5vw,4rem);
      font-weight:800;line-height:1.08;letter-spacing:-0.03em;color:var(--text);">
      <span style="display:inline-block;clip-path:inset(100% 0 0 0);animation:textReveal .8s cubic-bezier(.16,1,.3,1) .2s forwards;">
        Proteja o futuro
      </span><br>
      <span style="display:inline-block;clip-path:inset(100% 0 0 0);animation:textReveal .8s cubic-bezier(.16,1,.3,1) .35s forwards;">
        do <em style="color:var(--accent);font-style:normal;">seu patrimônio</em>
      </span>
    </h1>

    <!-- CTA com shimmer + glow pulsante -->
    <a href="#" class="cta-primary" style="display:inline-flex;align-items:center;gap:10px;margin-top:2rem;
      padding:18px 36px;font-size:clamp(1rem,2vw,1.15rem);font-weight:700;color:#fff;
      background:var(--accent);border:none;border-radius:14px;text-decoration:none;position:relative;overflow:hidden;
      box-shadow:0 0 0 0 rgba(var(--accent-rgb),0.3),0 8px 32px rgba(0,0,0,0.2);
      animation:ctaPulse 3s ease-in-out infinite;">
      <!-- WhatsApp SVG inline, NÃO emoji -->
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.625.846 5.059 2.284 7.034L.789 23.492a.5.5 0 00.611.611l4.458-1.495A11.96 11.96 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22a9.94 9.94 0 01-5.39-1.582l-.386-.238-3.205 1.074 1.074-3.205-.238-.386A9.94 9.94 0 012 12C2 6.477 6.477 2 12 2s10 4.477 10 10-4.477 10-10 10z"/></svg>
      Falar com especialista agora
    </a>
    <p style="margin-top:12px;font-size:13px;color:var(--text-muted);">Sem compromisso · Resposta em minutos</p>
  </div>
</section>

<!-- Card com borda gradient animada + inner spotlight -->
<div class="card" style="position:relative;background:var(--surface);border-radius:16px;padding:2rem;overflow:hidden;
  transition:transform .4s cubic-bezier(.16,1,.3,1),box-shadow .4s ease;">
  <!-- Borda gradient via mask composite -->
  <div style="position:absolute;inset:0;padding:1px;border-radius:inherit;
    background:linear-gradient(135deg,rgba(255,255,255,0.1),rgba(255,255,255,0.03),rgba(255,255,255,0.08));
    -webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);
    -webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none;"></div>
  <!-- Ícone SVG inline, NÃO emoji -->
  <div style="width:48px;height:48px;display:flex;align-items:center;justify-content:center;
    border-radius:12px;background:rgba(var(--accent-rgb),0.1);color:var(--accent);margin-bottom:1rem;">
    {{icon:shield-check}}
  </div>
  <h3 style="font-family:var(--font-heading);font-size:1.15rem;font-weight:700;color:var(--text);margin-bottom:8px;">
    Defesa preventiva completa
  </h3>
  <p style="font-size:0.9rem;color:var(--text-muted);line-height:1.6;">
    Identificamos riscos antes que se tornem multas, protegendo suas operações com monitoramento contínuo.
  </p>
</div>
</gold_standard_reference>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PASS 1 — Creative Brief
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_creative_brief(lead_data: dict, niche: str, guide: dict, reviews_text: str, gaps_text: str, diagnostic_context: str) -> dict | None:
    """
    Pass 1: Gera um creative brief estruturado em JSON.
    Claude decide paleta, tipografia, copy e ícones.
    """
    copy_fw = _COPY_FRAMEWORKS.get(guide["copy_framework"], _COPY_FRAMEWORKS["PAS"])

    system = f"""Você é um diretor criativo de agência digital brasileira com 15 anos de experiência.
Sua tarefa: criar um BRIEF CRIATIVO completo para uma landing page de um negócio local.

Retorne APENAS JSON válido. Nenhum texto antes ou depois. Sem markdown backticks.

O JSON deve seguir EXATAMENTE esta estrutura:
{{
  "palette": {{
    "bg": "#hex (tom mais escuro, background principal)",
    "bg_deep": "#hex (ainda mais escuro que bg, para footer)",
    "bg_soft": "#hex (levemente mais claro que bg, para seções alternadas)",
    "surface": "#hex (cards, claramente diferente de bg)",
    "accent": "#hex (cor de ação, CTAs, destaques)",
    "accent_rgb": "r,g,b (mesma cor accent em RGB para alphas)"
  }},
  "typography": {{
    "heading": "Nome da Google Font (NUNCA Inter, Roboto, Arial)",
    "body": "Nome da Google Font complementar"
  }},
  "hero": {{
    "headline": "≤10 palavras, benefício/transformação",
    "subheadline": "1 frase complementar, max 20 palavras",
    "cta_text": "CTA em 1ª pessoa, ex: Agendar minha consulta",
    "micro_copy": "Sem compromisso · Resposta imediata",
    "cta_secondary": "Texto do CTA secundário, ex: Conheça nossos serviços ↓"
  }},
  "sections": {{
    "problems": [
      {{"title": "...", "description": "1 frase", "icon": "nome-do-icone"}},
      {{"title": "...", "description": "1 frase", "icon": "nome-do-icone"}},
      {{"title": "...", "description": "1 frase", "icon": "nome-do-icone"}},
      {{"title": "...", "description": "1 frase", "icon": "nome-do-icone"}}
    ],
    "solution_headline": "headline de benefício",
    "solution_bullets": ["bullet 1 com bold", "bullet 2", "bullet 3"],
    "services": [
      {{"title": "...", "description": "1-2 frases de benefício", "icon": "nome-do-icone", "featured": true}},
      {{"title": "...", "description": "...", "icon": "...", "featured": false}},
      {{"title": "...", "description": "...", "icon": "...", "featured": false}},
      {{"title": "...", "description": "...", "icon": "...", "featured": false}},
      {{"title": "...", "description": "...", "icon": "...", "featured": false}}
    ],
    "steps": [
      {{"title": "...", "description": "1 frase"}},
      {{"title": "...", "description": "1 frase"}},
      {{"title": "...", "description": "1 frase"}}
    ],
    "faq": [
      {{"question": "pergunta real do nicho?", "answer": "resposta ≤50 palavras"}},
      {{"question": "...", "answer": "..."}},
      {{"question": "...", "answer": "..."}},
      {{"question": "...", "answer": "..."}},
      {{"question": "...", "answer": "..."}}
    ],
    "cta_final_headline": "headline com urgência contextual (NÃO falsa escassez)"
  }},
  "design_decisions": {{
    "hero_variant": "split|centered|gradient (qual layout de hero)",
    "grid_break": "descrição de onde quebrar simetria (ex: 1 card featured grande + 4 menores)",
    "accent_usage": "como usar accent: só CTAs e destaques, ou também backgrounds?"
  }}
}}"""

    user = f"""Negócio: {lead_data.get('nome', 'N/A')}
Categoria: {niche}
Cidade: {lead_data.get('cidade', '')}
Nota Google: {lead_data.get('rating', '')} ({lead_data.get('reviews_count', '')} avaliações)
Website atual: {lead_data.get('website', 'NÃO TEM')}

Avaliações reais:
{reviews_text or 'Nenhuma disponível — NÃO invente depoimentos.'}

Problemas do site atual:
{gaps_text or 'Sem análise'}

{diagnostic_context}

Direção do nicho:
- Mood: {guide['mood']}
- Cores: {guide['color_direction']}
- Tipografia: {guide['typography_direction']}
- Metáforas visuais: {guide['visual_metaphors']}
- Framework de copy: {copy_fw}

Ícones SVG disponíveis (usar APENAS estes nomes):
{', '.join(sorted(SVG_ICONS.keys()))}

Ícones sugeridos para este nicho: {', '.join(guide['icon_suggestions'])}

REGRAS CRÍTICAS:
- Headlines = BENEFÍCIO/TRANSFORMAÇÃO, nunca descritivas ("Nossos Serviços" é PROIBIDO)
- CTAs em 1ª pessoa: "Agendar MINHA consulta", nunca "Saiba mais"
- Cores com PERSONALIDADE: não use verde-menta #34d399 genérico
- A paleta deve ter pelo menos 4 tons de dark para profundidade
- As fontes devem ter PERSONALIDADE e ser específicas para este negócio"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.llm_api_key}",
    }

    try:
        resp = _llm_post(
            f"{settings.llm_base_url}/chat/completions",
            headers=headers,
            body={
                "model": settings.llm_model,
                "temperature": 0.85,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=60,
        )
        data = resp.json()
        logger.debug("Pass 1 raw response keys: %s", list(data.keys()))

        # Extrair conteúdo — suporta formato OpenAI e Anthropic
        raw = ""
        choices = data.get("choices") or []
        content = data.get("content") or []
        if choices:
            raw = (choices[0].get("message", {}).get("content", "") or "").strip()
        elif content:
            raw = (content[0].get("text", "") or "").strip()

        if not raw:
            base_resp = data.get("base_resp", {})
            sensitive = data.get("output_sensitive_type")
            finish = (data.get("choices") or [{}])[0].get("finish_reason") if data.get("choices") else None
            logger.error("Pass 1: resposta vazia da API para %s. finish_reason=%s, "
                         "output_sensitive_type=%s, base_resp=%s",
                         lead_data.get("nome", "?"), finish, sensitive,
                         json.dumps(base_resp, ensure_ascii=False)[:300] if base_resp else "N/A")
            return None

        # Strip thinking blocks (MiniMax, DeepSeek, etc.)
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

        # Limpar possíveis backticks
        raw = re.sub(r"^```\w*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

        return json.loads(raw)

    except json.JSONDecodeError:
        logger.error("Pass 1: JSON inválido para %s. Raw (500 chars): %s",
                     lead_data.get("nome", "?"), raw[:500] if raw else "(vazio)")
        return None
    except Exception:
        logger.exception("Pass 1 falhou para %s", lead_data.get("nome", "?"))
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# PASS 2 — HTML Generation
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_html(lead_data: dict, niche: str, brief: dict, phone_clean: str, reviews_text: str) -> str:
    """
    Pass 2: Gera HTML completo usando o creative brief como fundação.
    System prompt enxuto. Brief como contexto estruturado.
    """

    # Serializar ícones disponíveis pro modelo usar
    icons_block = "\n".join(
        f'  "{name}": \'{svg}\'' for name, svg in SVG_ICONS.items()
    )

    system = f"""<role>
Você é VITOR — design engineer de elite, 12 anos criando LPs premium para negócios brasileiros.
Seu código é reconhecido por nunca parecer "feito por IA".
</role>

<regras>
1. Continue DIRETO do DOCTYPE fornecido. ZERO texto antes ou depois do HTML.
2. Use APENAS os SVG icons fornecidos na biblioteca — ZERO emojis como ícones.
3. Cada ícone deve estar dentro de um container estilizado (background accent alpha, border-radius, padding).
4. NUNCA invente depoimentos. Use APENAS reviews reais ou omita a seção.
5. NUNCA use Inter, Roboto, Arial, system-ui como fonte.
6. TODA animação respeita prefers-reduced-motion.
7. GSAP + ScrollTrigger via CDN cloudflare no final do body. Max 40 linhas JS.
8. Links: APENAS wa.me, âncoras internas, tel:, Google Fonts.
9. Ícones: SVG inline da biblioteca. PROIBIDO emojis, FontAwesome, CDN de ícones.
10. PROIBIDO imagens externas — gradientes, SVG, formas CSS apenas.
11. Cards devem ter borda gradient via mask-composite + inner spotlight hover.
12. Grid de serviços: 1 card featured (span 2 cols ou maior) + cards menores = ASSIMETRIA.
13. Pelo menos 1 seção com layout assimétrico ou grid irregular.
14. 4+ tons de escuro no background system (--bg, --bg-deep, --bg-soft, --surface).
15. CTA com shimmer sweep + glow pulsante (não estático).
16. CSS MOBILE-FIRST: escreva estilos base para mobile (320-480px), depois @media (min-width: 768px) para tablet e (min-width: 1024px) para desktop. NUNCA max-width. Touch targets ≥48px. Font-size base 16px mobile, clamp() para headings.
17. RESPIRO VERTICAL: sections com padding: clamp(4rem, 10vw, 7rem) 0. Gap entre cards ≥1.5rem. Headings com margin-bottom ≥1rem. Parágrafos com line-height ≥1.7. Nunca mais que 3 elementos sem whitespace visual separando-os.
18. GRID MOBILE: grids colapsam para 1 coluna em mobile. Card featured ocupa 100% width. Stats em 2x2 grid no mobile, não 4 colunas. FAQ full-width sempre.
</regras>

<icon_library>
Copie EXATAMENTE o SVG correspondente ao nome. Disponíveis:
{icons_block}
</icon_library>

{GOLD_STANDARD}"""

    # Formatar brief como contexto estruturado
    brief_json = json.dumps(brief, ensure_ascii=False, indent=2)

    user = f"""Gere a LP completa para:

<negocio>
  Nome: {lead_data.get('nome', 'N/A')}
  Categoria: {niche}
  Endereço: {lead_data.get('endereco', '')}
  Telefone: {lead_data.get('telefone', '')}
  WhatsApp: https://wa.me/{phone_clean}
  Nota: {lead_data.get('rating', '')} ({lead_data.get('reviews_count', '')} avaliações)
</negocio>

<creative_brief>
{brief_json}
</creative_brief>

<avaliacoes_reais>
{reviews_text or 'Nenhuma — NÃO invente. Use nota/número como social proof.'}
</avaliacoes_reais>

<banner>
  Texto: "Preview criada por {settings.business_name} — {settings.your_website}"
  Fino (28-32px), background accent, z-index acima da navbar.
</banner>

<footer_credito>
  "© 2025 {lead_data.get('nome', '')} · Site por {settings.business_name}"
</footer_credito>

<estrutura_obrigatoria>
1. BANNER TOPO (preview {settings.business_name})
2. NAVBAR (sticky, blur, links âncora: Serviços, Como Funciona, Avaliações, FAQ + CTA WhatsApp)
3. HERO (id="inicio", 100svh, gradient mesh, text reveal clip-path, CTA com shimmer+glow, orb flutuante)
4. BARRA DE CONFIANÇA (stats com .stat-number + data-value para counter GSAP)
5. PROBLEMA (id="problema", dores do cliente, cards com ícones SVG)
6. SOLUÇÃO (id="solucao", negócio como resposta)
7. SERVIÇOS (id="servicos", grid IRREGULAR: 1 featured + menores, ícones SVG, borda gradient, spotlight hover)
8. COMO FUNCIONA (id="como-funciona", 3 steps timeline, números grandes accent)
9. CTA MID-PAGE (WhatsApp + micro-copy)
10. DEPOIMENTOS (id="depoimentos", reviews reais OU nota grande + estrelas)
11. FAQ (id="faq", <details>/<summary>, 5 perguntas, seta CSS animada)
12. CTA FINAL (id="contato", background accent/gradient, botão grande invertido)
13. FOOTER (--bg-deep, endereço, tel, copyright)
14. CTA FLUTUANTE MOBILE (fixed bottom, só max-width:768px)
</estrutura_obrigatoria>

<requisitos_tecnicos>
- DOCTYPE, lang="pt-BR", meta viewport/charset/title
- Google Fonts via <link> display=swap — USAR as fontes do brief
- CSS em <style> no head. CSS Variables: --bg, --bg-deep, --bg-soft, --surface, --accent, --accent-rgb, --text, --text-muted, --border, --font-heading, --font-body
- html {{ scroll-behavior: smooth }}
- GSAP 3.12 + ScrollTrigger CDN cloudflare no final do body
- Section reveals: y:40 + opacity:0 + blur:4px → limpo, stagger .1s, once:true
- Parallax em elementos decorativos: y:-60, scrub:1.5
- Counter animado: .stat-number[data-value] anima de 0 ao valor
- Navbar scroll shadow via classe .scrolled
- @media (prefers-reduced-motion: reduce) desliga tudo
- padding-bottom body 80px mobile para CTA flutuante
- Meta title ≤60 chars, meta description ≤160 chars
</requisitos_tecnicos>

<mobile_first>
- Thumb zone: CTAs e nav items com min-height 48px e padding generoso
- Hero: h1 clamp(1.8rem, 6vw, 4rem), sub clamp(1rem, 2.5vw, 1.25rem)
- Containers: max-width 1200px desktop, padding 20px mobile / 40px tablet / 0 desktop
- Seções: padding-block clamp(4rem, 10vw, 7rem) — GENEROSO, nunca menos que 4rem
- Cards: padding clamp(1.5rem, 4vw, 2.5rem), gap entre cards clamp(1rem, 3vw, 1.5rem)
- Stack vertical em mobile: tudo 1 coluna abaixo de 768px
- Testar mentalmente: o conteúdo respira no iPhone SE (375px)?
</mobile_first>

IMPORTANTE: Comece DIRETAMENTE com <!DOCTYPE html>. Nenhum texto, explicação ou markdown antes do DOCTYPE.

Gere o HTML completo agora."""

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    try:
        resp = _llm_post(
            f"{settings.llm_base_url}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.llm_api_key}",
            },
            body={
                "model": settings.llm_model,
                "temperature": 0.7,
                "messages": messages,
            },
            timeout=240,
        )
        data = resp.json()

        # Extrair conteúdo — suporta formato OpenAI e Anthropic
        html = ""
        choices = data.get("choices") or []
        content = data.get("content") or []
        if choices:
            html = (choices[0].get("message", {}).get("content", "") or "").strip()
        elif content:
            html = (content[0].get("text", "") or "").strip()

        if not html:
            base_resp = data.get("base_resp", {})
            sensitive = data.get("output_sensitive_type")
            finish = (data.get("choices") or [{}])[0].get("finish_reason") if data.get("choices") else None
            logger.error("Pass 2: resposta vazia da API para %s. finish_reason=%s, "
                         "output_sensitive_type=%s, base_resp=%s",
                         lead_data.get("nome", "?"), finish, sensitive,
                         json.dumps(base_resp, ensure_ascii=False)[:300] if base_resp else "N/A")
            return ""

        # Strip thinking blocks (MiniMax, DeepSeek, etc.)
        html = re.sub(r"<think>.*?</think>", "", html, flags=re.DOTALL).strip()

        if html.startswith("```"):
            html = re.sub(r"^```\w*\n?", "", html)
            html = re.sub(r"\n?```$", "", html)

        # Garantir DOCTYPE mesmo se o modelo não incluiu
        if not html.lstrip().lower().startswith("<!doctype"):
            html = "<!DOCTYPE html>\n" + html

        return html

    except Exception:
        logger.exception("Pass 2 falhou para %s", lead_data.get("nome", "?"))
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — Orquestra os 2 passes
# ═══════════════════════════════════════════════════════════════════════════════

def generate_landing_page(lead_data: dict) -> str:
    """
    Gera HTML completo de uma landing page personalizada em 2 passes:
    1. Creative Brief (copy, cores, ícones, layout)
    2. HTML completo a partir do brief

    Retorna HTML ou string vazia em caso de falha.
    """
    # ── Preparar dados ──
    reviews_text = ""
    if lead_data.get("top_reviews"):
        reviews_text = "\n".join(f'- "{r}"' for r in lead_data["top_reviews"][:5])

    gaps_text = ""
    if lead_data.get("opportunity_reasons"):
        gaps_text = "\n".join(f"- {r}" for r in lead_data["opportunity_reasons"])

    phone_clean = (lead_data.get("telefone") or "").replace("+", "").replace("-", "").replace(" ", "")
    niche = lead_data.get("categoria", lead_data.get("nicho", ""))
    guide = _get_niche_guide(niche)

    # Contexto de diagnóstico
    diagnostic_context = ""
    diag = lead_data.get("site_analysis", {}).get("diagnostico_marketing")
    if diag:
        resumo = diag.get("resumo_executivo") or diag.get("diagnostico_resumo", "")
        momento = diag.get("momento_funil") or diag.get("funil_predominante", "")
        prioridades = diag.get("prioridades_top3") or diag.get("proximos_passos", [])
        pot = diag.get("potencial_ia_automacao", {})
        justificativa = pot.get("justificativa", "") if isinstance(pot, dict) else ""
        justificativa = justificativa or diag.get("justificativa_qualificacao", "")

        diagnostic_context = f"""Diagnóstico de marketing:
- Resumo: {resumo}
- Momento funil: {momento}
- Prioridades: {', '.join(prioridades) if prioridades else 'N/A'}
- Potencial IA: {justificativa}
Ajuste tom conforme momento: descoberta→educativa, atração→diferenciação, ação→CTA direto."""

    # ── Pass 1: Creative Brief ──
    logger.info("Pass 1: Gerando creative brief para %s", lead_data.get("nome", "?"))
    brief = _generate_creative_brief(
        lead_data=lead_data,
        niche=niche,
        guide=guide,
        reviews_text=reviews_text,
        gaps_text=gaps_text,
        diagnostic_context=diagnostic_context,
    )

    if not brief:
        logger.error("Creative brief falhou — abortando geração")
        return ""

    logger.info("Pass 1 OK. Paleta: %s | Fonts: %s + %s",
                brief.get("palette", {}).get("accent", "?"),
                brief.get("typography", {}).get("heading", "?"),
                brief.get("typography", {}).get("body", "?"))

    # ── Pass 2: HTML ──
    logger.info("Pass 2: Gerando HTML para %s", lead_data.get("nome", "?"))
    html = _generate_html(
        lead_data=lead_data,
        niche=niche,
        brief=brief,
        phone_clean=phone_clean,
        reviews_text=reviews_text,
    )

    if not html:
        logger.error("HTML generation falhou para %s", lead_data.get("nome", "?"))
        return ""

    # ── Post-processing: substituir placeholders de ícone por SVG real ──
    def _replace_icon(match):
        name = match.group(1).strip()
        return SVG_ICONS.get(name, f'<!-- icon "{name}" not found -->')

    html = re.sub(r'\{\{icon:([^}]+)\}\}', _replace_icon, html)

    logger.info("LP gerada com sucesso para %s (%d chars)", lead_data.get("nome", "?"), len(html))
    return html
