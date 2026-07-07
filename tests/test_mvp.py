from __future__ import annotations

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.db.models import Company, FetchLog, Review, ReviewAnalysis
from app.integrations.mock_gemini_client import MockGeminiClient
from app.services.analysis_service import AnalysisService
from app.services.export_service import ExportService
from app.services.fetch_service import FetchService
from app.services.location_service import LocationService
from app.services.summary_service import SummaryService
from app.utils.hashing import generate_review_hash


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture()
def settings(tmp_path):
    return Settings(
        app_env="test",
        app_name="Hermina Review Intelligence",
        log_level="INFO",
        export_dir=tmp_path / "exports",
        database_url="sqlite+pysqlite:///:memory:",
        cors_allowed_origins=("http://localhost:3000",),
        review_source_mode="mock",
        google_maps_api_key=None,
        google_places_language_code="id",
        google_places_region_code="ID",
        local_llm_base_url="http://localhost:11434/v1/",
        local_llm_api_key="test",
        local_llm_model="mock",
        fetch_limit_per_location=50,
        fetch_timeout_seconds=1,
        fetch_max_retry=0,
        selenium_headless=True,
        selenium_default_target_reviews=100,
        selenium_max_target_reviews=300,
        selenium_scroll_delay_seconds=2,
        selenium_max_scroll_attempts=100,
        selenium_wait_timeout_seconds=20,
        selenium_user_data_dir=None,
        analysis_batch_size=3,
        prompt_version="v1",
        page_size=20,
        show_raw_payload=False,
    )


@pytest.fixture()
def company_id(session_factory):
    with session_factory() as session:
        company = Company(
            name="Test Company",
            ai_enable_flag=True,
            total_enable_review=100,
            analyze_competitor_flag=False,
        )
        session.add(company)
        session.commit()
        session.refresh(company)
        return company.id


def add_location(session_factory, company_id):
    return LocationService(
        company_id=company_id, session_factory=session_factory
    ).add_location(
        hospital_name="Hermina",
        branch_name="Hermina Depok",
        city="Depok",
        address="Jl. Siliwangi",
        latitude="",
        longitude="",
        source="google_places",
        external_place_id="mock-hermina-depok",
        is_active=True,
    )


def test_hash_is_deterministic():
    review = {
        "source": "mock",
        "external_place_id": "place-1",
        "external_review_id": "review-1",
        "reviewer_name": "Andi",
        "rating": 5,
        "review_text": "Baik",
        "review_time": "2026-06-19T09:00:00+07:00",
    }
    assert generate_review_hash(review) == generate_review_hash(dict(review))


def test_fetch_deduplicates_and_dry_run_does_not_insert(
    session_factory, settings, company_id
):
    location = add_location(session_factory, company_id)
    service = FetchService(
        company_id=company_id, session_factory=session_factory, settings=settings
    )

    first = service.fetch_location(location.id)
    second = service.fetch_location(location.id)
    dry_run = service.dry_run_location(location.id)

    assert first["status"] == "success"
    assert first["total_inserted"] == 10
    assert second["total_inserted"] == 0
    assert second["total_duplicate"] == 10
    assert dry_run["total_fetched"] == 10

    with session_factory() as session:
        assert session.scalar(select(func.count(Review.id))) == 10
        assert session.scalar(select(func.count(FetchLog.id))) == 3
        statuses = list(
            session.scalars(select(FetchLog.status).order_by(FetchLog.id))
        )
        assert statuses == ["success", "success", "dry_run"]


def test_analysis_is_structured_and_rerun_is_append_only(
    session_factory, settings, company_id
):
    location = add_location(session_factory, company_id)
    FetchService(
        company_id=company_id, session_factory=session_factory, settings=settings
    ).fetch_location(location.id)
    analysis = AnalysisService(
        company_id=company_id,
        session_factory=session_factory,
        settings=settings,
        client=MockGeminiClient(),
    )

    initial = analysis.analyze_pending()
    rerun = analysis.rerun_review(1)

    assert initial["success"] == 10
    assert initial["failed"] == 0
    assert rerun["success"] == 1
    with session_factory() as session:
        assert session.scalar(select(func.count(ReviewAnalysis.id))) == 11
        assert (
            session.scalar(
                select(func.count(ReviewAnalysis.id)).where(
                    ReviewAnalysis.review_id == 1
                )
            )
            == 2
        )


def test_summary_and_exports(session_factory, settings, company_id):
    location = add_location(session_factory, company_id)
    FetchService(
        company_id=company_id, session_factory=session_factory, settings=settings
    ).fetch_location(location.id)
    AnalysisService(
        company_id=company_id,
        session_factory=session_factory,
        settings=settings,
        client=MockGeminiClient(),
    ).analyze_pending()

    summary = SummaryService(
        company_id=company_id, session_factory=session_factory
    ).overall_summary()
    export = ExportService(
        company_id=company_id, session_factory=session_factory, settings=settings
    )
    reviews_csv = export.export_all_reviews_csv()
    location_csv = export.export_location_reviews_csv(location.id)
    summary_csv = export.export_analysis_summary_csv()
    raw_json = export.export_raw_reviews_json()

    assert summary["total_locations"] == 1
    assert summary["total_reviews"] == 10
    assert summary["analyzed_reviews"] == 10
    assert summary["pending_analysis"] == 0
    assert all(
        path.exists()
        for path in [reviews_csv, location_csv, summary_csv, raw_json]
    )
