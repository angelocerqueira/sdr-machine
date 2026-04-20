import io
from unittest.mock import patch

import pytest

from tests.conftest import TestSession


@pytest.fixture(autouse=True)
def _no_runner_mock():
    """Override the autouse mock_runners fixture from test_csv_import.py.

    This module needs _run_csv_import to actually execute so the classification
    chain fires. We restore the real _RUNNERS here.
    """
    import app.routers.pipeline as pipeline_module

    real_runners = {
        "scrape": pipeline_module._run_scrape,
        "enrich": pipeline_module._run_enrich,
        "generate": pipeline_module._run_generate,
        "outreach": pipeline_module._run_outreach,
        "csv_import": pipeline_module._run_csv_import,
        "classification": pipeline_module._run_classify,
    }
    with patch.object(pipeline_module, "_RUNNERS", real_runners):
        yield


def test_csv_import_triggers_classification_job(client, db_session):
    csv_content = (
        "nome,telefone,rating,reviews_count,nicho\n"
        "Lead A,11999,4.5,50,Pizzaria\n"
        "Lead B,11888,4.7,80,Clinica Odontologica\n"
    )

    # Patch SessionLocal so both _run_csv_import and _run_classify share the test DB
    with patch("app.routers.pipeline.SessionLocal", new=TestSession):
        resp = client.post(
            "/api/pipeline/csv-import",
            files={"file": ("x.csv", io.BytesIO(csv_content.encode()), "text/csv")},
            data={"nicho": "pizzaria", "cidade": "sp"},
        )

    assert resp.status_code == 200

    from app.models import Job
    # Give the background thread a moment to complete (it runs synchronously in
    # the test because TestClient runs FastAPI background tasks inline)
    db_session.expire_all()
    jobs = db_session.query(Job).order_by(Job.id.desc()).limit(5).all()
    types = {j.type for j in jobs}
    # Both csv_import and classification jobs should have been created
    assert "csv_import" in types
    assert "classification" in types
