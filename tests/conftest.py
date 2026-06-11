"""Test harness: real Postgres (make test-db → :5433), schema via the actual Alembic
migration, truncation between tests. DATABASE_URL must be set before any server import."""

import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postcard:postcard@localhost:5433/postcard_test",
)

from datetime import date, timedelta

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from server.db import SessionLocal, engine
from server.models import Base
from server.services import businesses as business_service, campaigns as campaign_service
from server.services.settings import get_settings


@pytest.fixture(scope="session", autouse=True)
def schema():
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    command.upgrade(Config("alembic.ini"), "head")
    yield


@pytest.fixture(autouse=True)
def clean_db(schema):
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.connect() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))
        conn.commit()


@pytest.fixture
def session():
    with SessionLocal() as s:
        yield s
        s.commit()


RESEARCH = {
    "premise": "Residential roofing contractor serving Tippecanoe County; primarily asphalt shingle replacement and storm repair.",
    "hooks": ["family-owned 22 years", "4.9 stars across 210 Google reviews"],
    "evidence_urls": ["https://summitroofing.example.com/about"],
    "contacts": [
        {
            "name": "Dana Summit",
            "title": "owner",
            "email": "dana@summitroofing.example.com",
            "email_source": "https://summitroofing.example.com/contact",
            "email_confidence": "listed",
        }
    ],
}


def make_lead(session, name="Summit Roofing", category="roofer", website="https://summitroofing.example.com"):
    result = business_service.stage_leads(session, [{"name": name, "category": category, "website": website}])
    assert result["staged"], result["rejected"]
    return result["staged"][0]


def make_researched(session, name="Summit Roofing", category="roofer"):
    lead = make_lead(session, name=name, category=category, website=f"https://{name.replace(' ', '').lower()}.example.com")
    business_service.claim_lead(session, lead["id"])
    return business_service.submit_research(session, lead["id"], dict(RESEARCH))


def make_campaign(session, **overrides):
    get_settings(session)
    kwargs = dict(month=date(2026, 7, 1), deadline=date.today() + timedelta(days=10))
    kwargs.update(overrides)
    return campaign_service.create_campaign(session, **kwargs)


@pytest.fixture
def researched(session):
    return make_researched(session)


@pytest.fixture
def campaign(session):
    return make_campaign(session)
