"""Shared HTML utility functions used across the pipeline."""

from bs4 import BeautifulSoup


def _extract_visible_text(html: str) -> str:
    """Extrai texto visível do HTML, limitado a 2000 chars pra economizar tokens."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return text[:2000]
