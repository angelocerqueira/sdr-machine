from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/sdr_machine"
    api_url: str = "http://localhost:8000"
    apify_token: str = ""
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
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
    frontend_url: str = "http://localhost:3000"

    model_config = {"env_file": ".env"}


settings = Settings()
