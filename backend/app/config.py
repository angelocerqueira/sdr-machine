from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/sdr_machine"
    api_url: str = "http://localhost:8000"
    apify_token: str = ""
    llm_api_key: str = Field(default="", validation_alias=AliasChoices("LLM_API_KEY", "ANTHROPIC_API_KEY"))
    llm_model: str = "MiniMax-M2.7"
    llm_base_url: str = "https://api.minimax.io/v1"
    business_name: str = "Studio Digital"
    your_name: str = "Seu Nome"
    your_whatsapp: str = "5549999999999"
    your_email: str = "seu@email.com"
    your_website: str = "https://seuportfolio.com"
    target_niches: list[str] = [
        "dentista", "restaurante", "salão de beleza", "clínica estética",
        "pet shop", "academia", "barbearia", "clínica veterinária",
        "pizzaria", "loja de roupas",
    ]
    target_cities: list[str] = [
        "Chapecó SC", "Florianópolis SC", "Joinville SC",
        "Curitiba PR", "Cascavel PR",
    ]
    min_rating: float = 3.0
    max_results_per_search: int = 50
    opportunity_score_threshold: int = 40
    diagnostic_model: str = ""
    skip_ai_diagnostic: bool = False
    skip_social_scraping: bool = False
    ai_potential_threshold: int = 25
    disqualify_threshold: int = 25
    skip_service_level_analysis: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "sdr-machine"
    langsmith_tracing: bool = False
    frontend_url: str = "http://localhost:3000"

    model_config = {"env_file": ".env"}


settings = Settings()
