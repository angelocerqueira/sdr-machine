import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Lead, Job

TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_lead(db):
    lead = Lead(
        nome="Odonto Sorriso",
        telefone="49999887766",
        website="http://odontosorriso.com.br",
        endereco="Rua Marechal Floriano, 456",
        cidade="Chapecó SC",
        nicho="dentista",
        categoria="Dentista",
        rating=4.7,
        reviews_count=123,
        status="scraped",
        opportunity_score=65,
        opportunity_reasons=["Sem HTTPS/SSL", "Não é responsivo"],
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead
