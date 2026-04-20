"""Tests para o módulo de enriquecimento (enricher.py)."""

from unittest.mock import patch, MagicMock

from app.pipeline.enricher import (
    analyze_html,
    calculate_score,
    _extract_visible_text,
    _extract_social_urls,
    _is_profile_url,
    _scrape_instagram_profile,
    scrape_social_profiles,
    enrich_lead_data,
)
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="Clínica odontológica">
    <title>Odonto Sorriso</title>
    <script>window.dataLayer=[];</script>
</head>
<body>
    <a href="https://wa.me/5549999887766">WhatsApp</a>
    <a href="https://instagram.com/odontosorriso">Instagram</a>
    <button>Agende sua consulta</button>
    <img src="logo.png"><img src="foto.png"><img src="equipe.png">
    <p>Somos uma clínica odontológica com mais de 10 anos de experiência em Chapecó.</p>
</body>
</html>
"""

SAMPLE_LEAD_INFO = {
    "nome": "Odonto Sorriso",
    "nicho": "dentista",
    "categoria": "Dentista",
    "cidade": "Chapecó SC",
    "rating": 4.7,
    "reviews_count": 123,
    "top_reviews": ["Excelente atendimento!", "Muito profissional"],
}


# ---------------------------------------------------------------------------
# Tests: analyze_html
# ---------------------------------------------------------------------------

class TestAnalyzeHtml:
    def test_full_html(self):
        result = analyze_html(SAMPLE_HTML)
        assert result["has_responsive_meta"] is True
        assert result["has_whatsapp_link"] is True
        assert result["has_social_links"] is True
        assert result["has_cta"] is True
        assert result["title"] == "Odonto Sorriso"
        assert result["description"] == "Clínica odontológica"
        assert result["image_count"] == 3
        assert result["word_count"] > 0

    def test_empty_html(self):
        result = analyze_html("")
        assert result["has_responsive_meta"] is False
        assert result["has_whatsapp_link"] is False
        assert result["has_cta"] is False
        assert result["title"] == ""
        assert result["word_count"] == 0


# ---------------------------------------------------------------------------
# Tests: calculate_score
# ---------------------------------------------------------------------------

class TestCalculateScore:
    def test_no_website(self):
        score, reasons = calculate_score(
            {"status": "no_website"}, {}, {}
        )
        assert score == 95
        assert "Sem website" in reasons[0]

    def test_connection_error(self):
        score, reasons = calculate_score(
            {"status": "connection_error"}, {}, {}
        )
        assert score == 85

    def test_good_site(self):
        score, _ = calculate_score(
            {"status": "ok", "has_ssl": True},
            {
                "has_responsive_meta": True,
                "has_whatsapp_link": True,
                "has_analytics": True,
                "has_chatbot": True,
                "has_cta": True,
                "word_count": 500,
                "is_template": False,
                "image_count": 10,
            },
            {"performance_score": 80},
        )
        assert score == 0

    def test_bad_site(self):
        score, reasons = calculate_score(
            {"status": "ok", "has_ssl": False},
            {
                "has_responsive_meta": False,
                "has_whatsapp_link": False,
                "has_analytics": False,
                "has_chatbot": False,
                "has_cta": False,
                "word_count": 50,
                "is_template": True,
                "image_count": 0,
            },
            {"performance_score": 30},
        )
        assert score >= 80
        assert len(reasons) >= 5


# ---------------------------------------------------------------------------
# Tests: _extract_visible_text
# ---------------------------------------------------------------------------

class TestExtractVisibleText:
    def test_extracts_text(self):
        text = _extract_visible_text(SAMPLE_HTML)
        assert "Odonto Sorriso" in text
        assert "clínica odontológica" in text
        assert "<script>" not in text

    def test_empty_html(self):
        assert _extract_visible_text("") == ""

    def test_truncates(self):
        big_html = "<p>" + "x" * 5000 + "</p>"
        assert len(_extract_visible_text(big_html)) <= 2000


# ---------------------------------------------------------------------------
# Tests: enrich_lead_data
# ---------------------------------------------------------------------------

class TestEnrichLeadData:
    @patch("app.pipeline.enricher.run_diagnostic")
    @patch("app.pipeline.enricher.check_pagespeed")
    @patch("app.pipeline.enricher.fetch_website")
    def test_with_diagnostic_qualified(self, mock_fetch, mock_pagespeed, mock_diag):
        from app.pipeline.diagnostic.state import NivelScore, ServiceLevelAnalysis

        mock_fetch.return_value = {"status": "ok", "html": SAMPLE_HTML, "has_ssl": True}
        mock_pagespeed.return_value = {"performance_score": 70}
        sla = ServiceLevelAnalysis(
            lp=NivelScore(score=80, sinais=["s"], oportunidades=["o"], justificativa="j"),
            automacao_basica=NivelScore(score=60, sinais=["s"], oportunidades=["o"], justificativa="j"),
            mapa_automacoes=NivelScore(score=40, sinais=["s"], oportunidades=["o"], justificativa="j"),
            vertical_os=NivelScore(score=15, sinais=["s"], oportunidades=["o"], justificativa="j"),
            nivel_recomendado="lp",
            qualificado=True,
            motivo_desqualificacao=None,
            resumo_executivo="Resumo.",
        )
        mock_diag.return_value = sla

        result = enrich_lead_data("http://example.com", lead_info=SAMPLE_LEAD_INFO)

        assert result["qualified"] is True
        assert "service_levels" in result["site_analysis"]

    @patch("app.pipeline.enricher.settings")
    @patch("app.pipeline.enricher.run_diagnostic")
    @patch("app.pipeline.enricher.check_pagespeed")
    @patch("app.pipeline.enricher.fetch_website")
    def test_with_diagnostic_disqualified(self, mock_fetch, mock_pagespeed, mock_diag, mock_settings):
        from app.pipeline.diagnostic.state import NivelScore, ServiceLevelAnalysis

        mock_settings.ai_potential_threshold = 25
        mock_settings.skip_social_scraping = True
        mock_settings.apify_token = ""
        mock_fetch.return_value = {"status": "ok", "html": SAMPLE_HTML, "has_ssl": True}
        mock_pagespeed.return_value = {"performance_score": 70}
        sla = ServiceLevelAnalysis(
            lp=NivelScore(score=10, sinais=["s"], oportunidades=[], justificativa="j"),
            automacao_basica=NivelScore(score=5, sinais=["s"], oportunidades=[], justificativa="j"),
            mapa_automacoes=NivelScore(score=8, sinais=["s"], oportunidades=[], justificativa="j"),
            vertical_os=NivelScore(score=3, sinais=["s"], oportunidades=[], justificativa="j"),
            nivel_recomendado="lp",
            qualificado=False,
            motivo_desqualificacao="Sem potencial",
            resumo_executivo="Desqualificado.",
        )
        mock_diag.return_value = sla

        result = enrich_lead_data("http://example.com", lead_info=SAMPLE_LEAD_INFO)

        assert result["qualified"] is False
        assert "service_levels" in result["site_analysis"]

    @patch("app.pipeline.enricher.run_diagnostic")
    @patch("app.pipeline.enricher.check_pagespeed")
    @patch("app.pipeline.enricher.fetch_website")
    def test_diagnostic_failure_still_enriches(self, mock_fetch, mock_pagespeed, mock_diag):
        mock_fetch.return_value = {"status": "ok", "html": SAMPLE_HTML, "has_ssl": True}
        mock_pagespeed.return_value = {"performance_score": 70}
        mock_diag.return_value = None  # Graph failure

        result = enrich_lead_data("http://example.com", lead_info=SAMPLE_LEAD_INFO)

        assert result["qualified"] is True
        assert "service_levels" not in result["site_analysis"]
        assert result["opportunity_score"] is not None

    @patch("app.pipeline.enricher.run_diagnostic")
    @patch("app.pipeline.enricher.check_pagespeed")
    @patch("app.pipeline.enricher.fetch_website")
    def test_with_service_levels(self, mock_fetch, mock_pagespeed, mock_run_diag):
        from app.pipeline.diagnostic.state import NivelScore, ServiceLevelAnalysis

        mock_fetch.return_value = {"status": "ok", "html": SAMPLE_HTML, "has_ssl": True}
        mock_pagespeed.return_value = {"performance_score": 70}

        sla = ServiceLevelAnalysis(
            lp=NivelScore(score=80, sinais=["Sem site"], oportunidades=["LP"], justificativa="j"),
            automacao_basica=NivelScore(score=60, sinais=["s"], oportunidades=["o"], justificativa="j"),
            mapa_automacoes=NivelScore(score=40, sinais=["s"], oportunidades=["o"], justificativa="j"),
            vertical_os=NivelScore(score=15, sinais=["s"], oportunidades=["o"], justificativa="j"),
            nivel_recomendado="lp",
            qualificado=True,
            motivo_desqualificacao=None,
            resumo_executivo="Resumo.",
        )
        mock_run_diag.return_value = sla

        result = enrich_lead_data("http://example.com", lead_info=SAMPLE_LEAD_INFO)

        assert result["qualified"] is True
        assert "service_levels" in result["site_analysis"]
        assert result["site_analysis"]["service_levels"]["lp"]["score"] == 80
        assert result["site_analysis"]["service_levels"]["nivel_recomendado"] == "lp"

    @patch("app.pipeline.enricher.run_diagnostic")
    @patch("app.pipeline.enricher.check_pagespeed")
    @patch("app.pipeline.enricher.fetch_website")
    def test_with_service_levels_disqualified(self, mock_fetch, mock_pagespeed, mock_run_diag):
        from app.pipeline.diagnostic.state import NivelScore, ServiceLevelAnalysis

        mock_fetch.return_value = {"status": "ok", "html": SAMPLE_HTML, "has_ssl": True}
        mock_pagespeed.return_value = {"performance_score": 70}

        sla = ServiceLevelAnalysis(
            lp=NivelScore(score=10, sinais=["s"], oportunidades=[], justificativa="j"),
            automacao_basica=NivelScore(score=5, sinais=["s"], oportunidades=[], justificativa="j"),
            mapa_automacoes=NivelScore(score=8, sinais=["s"], oportunidades=[], justificativa="j"),
            vertical_os=NivelScore(score=3, sinais=["s"], oportunidades=[], justificativa="j"),
            nivel_recomendado="lp",
            qualificado=False,
            motivo_desqualificacao="Sem potencial",
            resumo_executivo="Desqualificado.",
        )
        mock_run_diag.return_value = sla

        result = enrich_lead_data("http://example.com", lead_info=SAMPLE_LEAD_INFO)

        assert result["qualified"] is False

    @patch("app.pipeline.enricher.fetch_website")
    def test_without_lead_info(self, mock_fetch):
        mock_fetch.return_value = {"status": "no_website", "html": ""}

        result = enrich_lead_data("", lead_info=None, skip_pagespeed=True)

        assert result["qualified"] is True
        assert result["opportunity_score"] == 95
        assert "diagnostico_marketing" not in result["site_analysis"]

    @patch("app.pipeline.enricher.settings")
    @patch("app.pipeline.enricher.run_diagnostic")
    @patch("app.pipeline.enricher.fetch_website")
    def test_skip_social_scraping(self, mock_fetch, mock_diag, mock_settings):
        """Social scraping should be skipped when skip_social_scraping=True."""
        mock_settings.skip_social_scraping = True
        mock_settings.apify_token = "test-token"
        mock_settings.skip_ai_diagnostic = True
        mock_settings.ai_potential_threshold = 25
        mock_fetch.return_value = {"status": "ok", "html": SAMPLE_HTML, "has_ssl": True}
        mock_diag.return_value = None

        result = enrich_lead_data("http://example.com", lead_info=SAMPLE_LEAD_INFO, skip_pagespeed=True)

        assert result["social_profiles"] == {}


# ---------------------------------------------------------------------------
# Tests: _extract_social_urls (profile URL filtering)
# ---------------------------------------------------------------------------

class TestExtractSocialUrls:
    def test_extracts_profile_urls(self):
        html = '<a href="https://instagram.com/dentista123">IG</a><a href="https://facebook.com/minhaclinica">FB</a>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_social_urls(soup)
        assert "instagram" in result
        assert "facebook" in result

    def test_filters_share_links(self):
        html = '<a href="https://facebook.com/sharer/sharer.php?u=test">Compartilhar</a>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_social_urls(soup)
        assert "facebook" not in result

    def test_filters_instagram_post_links(self):
        html = '<a href="https://instagram.com/p/ABC123">Ver post</a>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_social_urls(soup)
        assert "instagram" not in result

    def test_filters_instagram_reel_links(self):
        html = '<a href="https://instagram.com/reel/XYZ789">Ver reel</a>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_social_urls(soup)
        assert "instagram" not in result

    def test_filters_linkedin_share_links(self):
        html = '<a href="https://linkedin.com/shareArticle?url=test">Share</a>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_social_urls(soup)
        assert "linkedin" not in result

    def test_preserves_original_case(self):
        html = '<a href="https://Instagram.com/MyClinic">IG</a>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_social_urls(soup)
        assert result.get("instagram") == "https://Instagram.com/MyClinic"

    def test_takes_first_profile_only(self):
        html = '<a href="https://instagram.com/first">1</a><a href="https://instagram.com/second">2</a>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_social_urls(soup)
        assert "first" in result["instagram"]


class TestIsProfileUrl:
    def test_valid_profile(self):
        assert _is_profile_url("instagram", "https://instagram.com/dentista123") is True

    def test_post_url(self):
        assert _is_profile_url("instagram", "https://instagram.com/p/abc123") is False

    def test_share_url(self):
        assert _is_profile_url("facebook", "https://facebook.com/sharer/test") is False

    def test_no_path(self):
        assert _is_profile_url("instagram", "https://instagram.com/") is False

    def test_youtube_watch(self):
        assert _is_profile_url("youtube", "https://youtube.com/watch?v=abc") is False

    def test_youtube_channel(self):
        assert _is_profile_url("youtube", "https://youtube.com/mychannel") is True


# ---------------------------------------------------------------------------
# Tests: scrape_social_profiles
# ---------------------------------------------------------------------------

class TestScrapeProfiles:
    @patch("app.pipeline.enricher._search_linkedin_company")
    @patch("app.pipeline.enricher._scrape_instagram_profile")
    def test_only_scrapes_instagram_when_url_found(self, mock_ig, mock_li):
        mock_ig.return_value = {"platform": "instagram", "username": "test", "followers": 100}
        mock_li.return_value = None

        social_urls = {"instagram": "https://instagram.com/test"}
        result = scrape_social_profiles({"nome": "Test", "cidade": "SP"}, social_urls)

        assert "instagram" in result
        mock_ig.assert_called_once()
        mock_li.assert_not_called()  # No linkedin URL → no LinkedIn scrape

    @patch("app.pipeline.enricher._search_linkedin_company")
    @patch("app.pipeline.enricher._scrape_instagram_profile")
    def test_scrapes_linkedin_only_when_url_found(self, mock_ig, mock_li):
        mock_ig.return_value = None
        mock_li.return_value = {"platform": "linkedin", "name": "Test Corp"}

        social_urls = {"linkedin": "https://linkedin.com/company/test"}
        result = scrape_social_profiles({"nome": "Test Corp", "cidade": "SP"}, social_urls)

        assert "linkedin" in result
        mock_li.assert_called_once()

    @patch("app.pipeline.enricher._search_linkedin_company")
    @patch("app.pipeline.enricher._scrape_instagram_profile")
    def test_preserves_urls_without_scraping(self, mock_ig, mock_li):
        """URLs found on site should be preserved even without Apify scraping."""
        mock_ig.return_value = None
        mock_li.return_value = None

        social_urls = {"facebook": "https://facebook.com/test", "tiktok": "https://tiktok.com/@test"}
        result = scrape_social_profiles({"nome": "Test"}, social_urls)

        assert result["facebook"]["url"] == "https://facebook.com/test"
        assert result["tiktok"]["url"] == "https://tiktok.com/@test"


# ---------------------------------------------------------------------------
# Tests: _scrape_instagram_profile
# ---------------------------------------------------------------------------

def test_enrich_writes_diagnostico_marketing_to_site_analysis():
    """Quando service_levels tem diagnostico_marketing, é copiado pra site_analysis."""
    from app.pipeline.diagnostic.state import (
        ServiceLevelAnalysis, NivelScore, MarketingDiagnostic,
        IAPotencial, FunnelStage, FunnelAction,
    )

    md = MarketingDiagnostic(
        resumo_executivo="r",
        momento_funil="descoberta",
        potencial_ia_automacao=IAPotencial(score=70, oportunidades=[], justificativa="j"),
        prioridades_top3=["a", "b", "c"],
        funil={"descoberta": FunnelStage(
            diagnostico="d",
            acoes_top2=[FunnelAction(acao="a", resultado_esperado="r", kpi="k")],
        )},
    )
    sla = ServiceLevelAnalysis(
        lp=NivelScore(score=60, sinais=[], oportunidades=[], justificativa=""),
        automacao_basica=NivelScore(score=60, sinais=[], oportunidades=[], justificativa=""),
        mapa_automacoes=NivelScore(score=60, sinais=[], oportunidades=[], justificativa=""),
        vertical_os=NivelScore(score=60, sinais=[], oportunidades=[], justificativa=""),
        nivel_recomendado="lp",
        qualificado=True,
        resumo_executivo="r",
        diagnostico_marketing=md,
    )

    with patch("app.pipeline.enricher.run_diagnostic", return_value=sla), \
         patch("app.pipeline.enricher.fetch_website", return_value={"status": "ok", "html": ""}), \
         patch("app.pipeline.enricher.check_pagespeed", return_value={}):

        result = enrich_lead_data(
            "http://example.com",
            lead_info={"nome": "T", "nicho": "x", "cidade": "y"},
        )

    assert "diagnostico_marketing" in result["site_analysis"]
    assert result["site_analysis"]["diagnostico_marketing"]["momento_funil"] == "descoberta"


class TestScrapeInstagram:
    @patch("app.pipeline.enricher.settings")
    def test_skips_without_apify_token(self, mock_settings):
        mock_settings.apify_token = ""
        assert _scrape_instagram_profile("https://instagram.com/test") is None

    @patch("app.pipeline.enricher.settings")
    def test_rejects_non_profile_urls(self, mock_settings):
        mock_settings.apify_token = "test"
        assert _scrape_instagram_profile("https://instagram.com/p/ABC123") is None
        assert _scrape_instagram_profile("https://instagram.com/reel/XYZ") is None
        assert _scrape_instagram_profile("https://instagram.com/explore") is None
        assert _scrape_instagram_profile("https://instagram.com/stories") is None

    @patch("app.pipeline.enricher.settings")
    def test_rejects_empty_url(self, mock_settings):
        mock_settings.apify_token = "test"
        assert _scrape_instagram_profile("") is None

    @patch("app.pipeline.enricher.settings")
    @patch("app.pipeline.enricher.requests.post")
    def test_success(self, mock_post, mock_settings):
        mock_settings.apify_token = "test-token"
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = [{
            "fullName": "Test Clinic",
            "biography": "Best clinic in town",
            "followersCount": 5000,
            "followsCount": 200,
            "postsCount": 150,
            "isBusinessAccount": True,
            "businessCategoryName": "Health",
            "externalUrl": "https://example.com",
            "verified": False,
        }]
        mock_post.return_value = mock_resp

        result = _scrape_instagram_profile("https://instagram.com/testclinic")
        assert result is not None
        assert result["username"] == "testclinic"
        assert result["followers"] == 5000
        assert result["is_business"] is True

    @patch("app.pipeline.enricher.settings")
    @patch("app.pipeline.enricher.requests.post")
    def test_api_failure_returns_none(self, mock_post, mock_settings):
        mock_settings.apify_token = "test-token"
        mock_post.side_effect = Exception("Connection timeout")

        result = _scrape_instagram_profile("https://instagram.com/testclinic")
        assert result is None


# ── Automation signals in analyze_html ────────────────────────────────────────

def test_analyze_html_booking_link():
    html = '<a href="https://calendly.com/empresa/reuniao">Agendar</a>'
    result = analyze_html(html)
    assert result["has_booking_link"] is True


def test_analyze_html_no_booking_link():
    html = "<p>Entre em contato pelo WhatsApp</p>"
    result = analyze_html(html)
    assert result["has_booking_link"] is False


def test_analyze_html_payment_link():
    html = '<script src="https://js.stripe.com/v3/"></script>'
    result = analyze_html(html)
    assert result["has_payment_link"] is True


def test_analyze_html_contact_form():
    html = "<form method='post'><input type='email'/><button>Enviar</button></form>"
    result = analyze_html(html)
    assert result["has_contact_form"] is True
    assert result["form_count"] == 1


def test_analyze_html_video():
    html = '<iframe src="https://www.youtube.com/embed/abc123"></iframe>'
    result = analyze_html(html)
    assert result["has_video"] is True


def test_analyze_html_contact_channels_count():
    html = """
    <a href="tel:+5511999998888">Ligar</a>
    <a href="https://wa.me/5511999998888">WhatsApp</a>
    <a href="mailto:contato@empresa.com">Email</a>
    <form><input/></form>
    """
    result = analyze_html(html)
    assert result["contact_channels_count"] >= 3


def test_analyze_html_empty_returns_new_fields():
    result = analyze_html("")
    assert "has_booking_link" in result
    assert "has_payment_link" in result
    assert "has_contact_form" in result
    assert "has_video" in result
    assert "contact_channels_count" in result
