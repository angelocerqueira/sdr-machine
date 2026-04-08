"""Shared context formatting used by all analyzer prompts."""


def format_lead_context(
    lead_info: dict,
    site_data: dict,
    html_analysis: dict,
    pagespeed: dict,
    visible_text: str,
    social_profiles: dict,
) -> str:
    """Build the shared context block that all 4 analyzers receive."""
    reviews_text = ""
    if lead_info.get("top_reviews"):
        reviews_text = "\n".join(f'- "{r}"' for r in lead_info["top_reviews"][:3])

    site_status = site_data.get("status", "unknown")
    has_site = site_status == "ok"

    social_lines = []
    ig = social_profiles.get("instagram")
    if ig and isinstance(ig, dict) and ig.get("followers") is not None:
        social_lines.append(
            f"- Instagram: @{ig.get('username', '?')} | {ig.get('followers', 0)} seguidores | "
            f"{ig.get('posts_count', 0)} posts | {'Comercial' if ig.get('is_business') else 'Pessoal'}"
        )
    li = social_profiles.get("linkedin")
    if li and isinstance(li, dict) and li.get("name"):
        social_lines.append(
            f"- LinkedIn: {li.get('name', '?')} | {li.get('followers', 0)} seguidores | "
            f"{li.get('employees_range', '?')} funcionários"
        )
    for platform in ("facebook", "tiktok", "youtube"):
        p = social_profiles.get(platform)
        if p and isinstance(p, dict):
            social_lines.append(f"- {platform.capitalize()}: {p.get('url', 'perfil encontrado')}")
    social_text = "\n".join(social_lines) if social_lines else "Nenhum perfil encontrado."

    return f"""DADOS DO NEGÓCIO:
- Nome: {lead_info.get('nome', 'N/A')}
- Nicho/Categoria: {lead_info.get('nicho', 'N/A')} / {lead_info.get('categoria', 'N/A')}
- Cidade: {lead_info.get('cidade', 'N/A')}
- Nota Google: {lead_info.get('rating', 'N/A')} ({lead_info.get('reviews_count', 0)} avaliações)
- Avaliações destaque:
{reviews_text or 'Sem avaliações disponíveis'}

ANÁLISE TÉCNICA DO SITE:
- Status: {"Site funcional" if has_site else f"Problemas: {site_status}"}
- SSL/HTTPS: {"Sim" if html_analysis.get("has_ssl", site_data.get("has_ssl")) else "Não"}
- Responsivo (mobile): {"Sim" if html_analysis.get("has_responsive_meta") else "Não"}
- Link WhatsApp: {"Sim" if html_analysis.get("has_whatsapp_link") else "Não"}
- Google Analytics: {"Sim" if html_analysis.get("has_analytics") else "Não"}
- Chatbot: {"Sim" if html_analysis.get("has_chatbot") else "Não"}
- CTA: {"Sim" if html_analysis.get("has_cta") else "Não"}
- Redes sociais no site: {"Sim" if html_analysis.get("has_social_links") else "Não"}
- Conteúdo: {html_analysis.get("word_count", 0)} palavras, {html_analysis.get("image_count", 0)} imagens
- Template genérico: {"Sim" if html_analysis.get("is_template") else "Não"}
- PageSpeed mobile: {pagespeed.get("performance_score", "N/A")}/100
- Título: {html_analysis.get("title", "N/A")}

{"CONTEÚDO VISÍVEL (trecho):" + chr(10) + visible_text if visible_text else "SEM WEBSITE."}

REDES SOCIAIS:
{social_text}"""
