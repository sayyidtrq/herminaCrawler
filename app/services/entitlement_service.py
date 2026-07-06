from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Company
from app.db.session import get_session_factory


class EntitlementError(Exception):
    """Raised when a company is not entitled to use a gated feature."""


class EntitlementService:
    def __init__(
        self,
        company_id: int,
        session_factory: sessionmaker[Session] | None = None,
    ):
        self.company_id = company_id
        self.session_factory = session_factory or get_session_factory()

    def get_company(self) -> Company | None:
        with self.session_factory() as session:
            return session.get(Company, self.company_id)

    def require_ai_enabled(self) -> Company:
        company = self.get_company()
        if company is None:
            raise EntitlementError("Company not found.")
        if not company.ai_enable_flag:
            raise EntitlementError("AI analysis is not enabled for this company.")
        return company

    def require_competitor_enabled(self) -> Company:
        company = self.get_company()
        if company is None:
            raise EntitlementError("Company not found.")
        if not company.analyze_competitor_flag:
            raise EntitlementError("Competitor analysis is not enabled for this company.")
        return company

    def review_quota(self) -> int:
        """Max reviews this company is entitled to fetch per crawl job. 0 means unset/no quota."""
        company = self.get_company()
        if company is None:
            return 0
        return max(0, company.total_enable_review)

    def clamp_review_target(self, requested: int) -> int:
        quota = self.review_quota()
        if quota <= 0:
            return requested
        return min(requested, quota)
