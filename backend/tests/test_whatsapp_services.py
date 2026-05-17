import pytest

from app.models import Lead
from app.whatsapp.services import find_lead_by_phone


def _make_lead(db, *, telefone, status="outreach_sent", workspace_id=1):
    lead = Lead(nome="x", telefone=telefone, status=status)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def test_find_lead_by_phone_exact_match(db):
    lead = _make_lead(db, telefone="5544999990000")
    found = find_lead_by_phone(db, workspace_id=1, normalized_phone="5544999990000")
    assert found is not None
    assert found.id == lead.id


def test_find_lead_by_phone_with_masked_telefone(db):
    lead = _make_lead(db, telefone="(44) 99999-0000")
    found = find_lead_by_phone(db, workspace_id=1, normalized_phone="5544999990000")
    assert found is not None
    assert found.id == lead.id


def test_find_lead_by_phone_without_ddi_in_db(db):
    lead = _make_lead(db, telefone="44999990000")
    found = find_lead_by_phone(db, workspace_id=1, normalized_phone="5544999990000")
    assert found is not None
    assert found.id == lead.id


def test_find_lead_by_phone_no_match(db):
    _make_lead(db, telefone="5511888880000")
    found = find_lead_by_phone(db, workspace_id=1, normalized_phone="5544999990000")
    assert found is None


def test_find_lead_by_phone_multiple_candidates_returns_first(db):
    lead1 = _make_lead(db, telefone="5544999990000")
    _make_lead(db, telefone="(44)99999-0000")  # mesmo número, formato diferente
    found = find_lead_by_phone(db, workspace_id=1, normalized_phone="5544999990000")
    assert found is not None
    assert found.id == lead1.id
