from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import FetchLog, Location, Review, ReviewAnalysis
from app.db.session import get_session_factory
from app.services.review_service import latest_analysis_subquery


class SummaryService:
    def __init__(self, company_id: int | None = None, session_factory: sessionmaker[Session] | None = None):
        self.company_id = company_id
        self.session_factory = session_factory or get_session_factory()

    def overall_summary(self) -> dict:
        latest = latest_analysis_subquery()
        with self.session_factory() as session:
            location_count_stmt = select(func.count(Location.id))
            if self.company_id is not None:
                location_count_stmt = location_count_stmt.where(Location.company_id == self.company_id)
            total_locations = int(session.scalar(location_count_stmt) or 0)

            review_count_stmt = select(func.count(Review.id))
            if self.company_id is not None:
                review_count_stmt = review_count_stmt.where(Review.company_id == self.company_id)
            total_reviews = int(session.scalar(review_count_stmt) or 0)

            analyzed_stmt = select(func.count()).select_from(latest)
            if self.company_id is not None:
                analyzed_stmt = analyzed_stmt.join(Review, Review.id == latest.c.review_id).where(Review.company_id == self.company_id)
            analyzed = int(session.scalar(analyzed_stmt) or 0)

            sentiment_stmt = (
                select(ReviewAnalysis.sentiment, func.count(ReviewAnalysis.id))
                .join(latest, latest.c.analysis_id == ReviewAnalysis.id)
            )
            if self.company_id is not None:
                sentiment_stmt = sentiment_stmt.join(Review, Review.id == ReviewAnalysis.review_id).where(Review.company_id == self.company_id)
            sentiment_rows = session.execute(sentiment_stmt.group_by(ReviewAnalysis.sentiment)).all()

            issue_stmt = (
                select(ReviewAnalysis.issue_category, func.count(ReviewAnalysis.id))
                .join(latest, latest.c.analysis_id == ReviewAnalysis.id)
            )
            if self.company_id is not None:
                issue_stmt = issue_stmt.join(Review, Review.id == ReviewAnalysis.review_id).where(Review.company_id == self.company_id)
            issue_rows = session.execute(
                issue_stmt.group_by(ReviewAnalysis.issue_category)
                .order_by(func.count(ReviewAnalysis.id).desc())
                .limit(5)
            ).all()

            critical_stmt = (
                select(func.count(ReviewAnalysis.id))
                .join(latest, latest.c.analysis_id == ReviewAnalysis.id)
                .where(ReviewAnalysis.urgency.in_(["high", "critical"]))
            )
            if self.company_id is not None:
                critical_stmt = critical_stmt.join(Review, Review.id == ReviewAnalysis.review_id).where(Review.company_id == self.company_id)
            critical_count = int(session.scalar(critical_stmt) or 0)

            fetch_stmt = select(func.max(FetchLog.finished_at))
            if self.company_id is not None:
                fetch_stmt = fetch_stmt.where(FetchLog.company_id == self.company_id)
            latest_fetch = session.scalar(fetch_stmt)

        sentiments = {
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "mixed": 0,
            "unknown": 0,
        }
        sentiments.update({key or "unknown": count for key, count in sentiment_rows})
        return {
            "total_locations": total_locations,
            "total_reviews": total_reviews,
            "analyzed_reviews": analyzed,
            "pending_analysis": total_reviews - analyzed,
            "sentiments": sentiments,
            "top_issues": issue_rows,
            "critical_issues": critical_count,
            "latest_fetch": latest_fetch,
        }

    def location_summary(self, location_id: int) -> dict:
        latest = latest_analysis_subquery()
        with self.session_factory() as session:
            location = session.get(Location, location_id)
            if location is None or (self.company_id is not None and location.company_id != self.company_id):
                raise ValueError("Location not found.")
            total_reviews, average_rating = session.execute(
                select(func.count(Review.id), func.avg(Review.rating)).where(
                    Review.location_id == location_id
                )
            ).one()
            sentiment_rows = session.execute(
                select(ReviewAnalysis.sentiment, func.count(ReviewAnalysis.id))
                .join(latest, latest.c.analysis_id == ReviewAnalysis.id)
                .join(Review, Review.id == ReviewAnalysis.review_id)
                .where(Review.location_id == location_id)
                .group_by(ReviewAnalysis.sentiment)
            ).all()
            issue_rows = session.execute(
                select(
                    ReviewAnalysis.issue_category, func.count(ReviewAnalysis.id)
                )
                .join(latest, latest.c.analysis_id == ReviewAnalysis.id)
                .join(Review, Review.id == ReviewAnalysis.review_id)
                .where(Review.location_id == location_id)
                .group_by(ReviewAnalysis.issue_category)
                .order_by(func.count(ReviewAnalysis.id).desc())
                .limit(5)
            ).all()
            critical_count = int(
                session.scalar(
                    select(func.count(ReviewAnalysis.id))
                    .join(latest, latest.c.analysis_id == ReviewAnalysis.id)
                    .join(Review, Review.id == ReviewAnalysis.review_id)
                    .where(
                        Review.location_id == location_id,
                        ReviewAnalysis.urgency.in_(["high", "critical"]),
                    )
                )
                or 0
            )
            negative_examples = session.execute(
                select(Review.review_text)
                .join(latest, latest.c.review_id == Review.id)
                .join(ReviewAnalysis, ReviewAnalysis.id == latest.c.analysis_id)
                .where(
                    Review.location_id == location_id,
                    ReviewAnalysis.sentiment == "negative",
                )
                .order_by(Review.id.desc())
                .limit(3)
            ).scalars().all()
            focus = session.execute(
                select(ReviewAnalysis.recommended_action)
                .join(latest, latest.c.analysis_id == ReviewAnalysis.id)
                .join(Review, Review.id == ReviewAnalysis.review_id)
                .where(
                    Review.location_id == location_id,
                    ReviewAnalysis.recommended_action.is_not(None),
                )
                .distinct()
                .limit(3)
            ).scalars().all()

        sentiments = {
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "mixed": 0,
            "unknown": 0,
        }
        sentiments.update({key or "unknown": count for key, count in sentiment_rows})
        return {
            "location_id": location.id,
            "location_name": location.branch_name,
            "total_reviews": int(total_reviews or 0),
            "average_rating": (
                round(float(average_rating), 2) if average_rating is not None else None
            ),
            "sentiments": sentiments,
            "top_issues": issue_rows,
            "critical_issues": critical_count,
            "negative_examples": list(negative_examples),
            "management_focus": list(focus),
        }

    def critical_issues(self) -> list[dict]:
        latest = latest_analysis_subquery()
        statement = (
            select(Review, Location.branch_name, ReviewAnalysis)
            .join(Location, Location.id == Review.location_id)
            .join(latest, latest.c.review_id == Review.id)
            .join(ReviewAnalysis, ReviewAnalysis.id == latest.c.analysis_id)
            .where(ReviewAnalysis.urgency.in_(["high", "critical"]))
            .order_by(ReviewAnalysis.urgency, Review.id.desc())
        )
        if self.company_id is not None:
            statement = statement.where(Review.company_id == self.company_id)
        with self.session_factory() as session:
            return [
                {
                    "location": location_name,
                    "rating": review.rating,
                    "review_text": review.review_text,
                    "issue_category": analysis.issue_category,
                    "urgency": analysis.urgency,
                    "recommended_action": analysis.recommended_action,
                }
                for review, location_name, analysis in session.execute(statement)
            ]

    def negative_reviews(self) -> list[dict]:
        latest = latest_analysis_subquery()
        statement = (
            select(Review, Location.branch_name, ReviewAnalysis)
            .join(Location, Location.id == Review.location_id)
            .join(latest, latest.c.review_id == Review.id)
            .join(ReviewAnalysis, ReviewAnalysis.id == latest.c.analysis_id)
            .where(ReviewAnalysis.sentiment == "negative")
            .order_by(Review.id.desc())
        )
        if self.company_id is not None:
            statement = statement.where(Review.company_id == self.company_id)
        with self.session_factory() as session:
            return [
                {
                    "location": location_name,
                    "rating": review.rating,
                    "review_text": review.review_text,
                    "issue_category": analysis.issue_category,
                    "urgency": analysis.urgency,
                }
                for review, location_name, analysis in session.execute(statement)
            ]
