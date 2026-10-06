"""Isi `review_photo_urls` / `review_url` baris lama dari `raw_payload` Apify.

Review yang disimpan sebelum normalizer membawa foto punya kolom kosong, tapi
item Apify aslinya utuh di `raw_payload`. Jalankan sekali setelah deploy fix
itu supaya tidak perlu menarik ulang (dan membayar) Apify.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import func, select

from app.db.models import Review
from app.db.session import get_db_session
from app.services.review_repository import backfill_missing_fields

BATCH = 500
FIELDS = ("review_url", "review_photo_urls")


def backfill(session, *, company_id=None, location_id=None, dry_run=False) -> dict:
    stats = {"scanned": 0, "updated": 0, "photos": 0}
    # Ekspresi yang sama dengan jalur re-crawl (review_service.enrich).
    bump = (
        func.clock_timestamp()
        if session.bind.dialect.name == "postgresql"
        else datetime.now(timezone.utc)
    )
    last_id = 0
    while True:
        query = select(Review).where(Review.id > last_id).order_by(Review.id).limit(BATCH)
        if company_id is not None:
            query = query.where(Review.company_id == company_id)
        if location_id is not None:
            query = query.where(Review.location_id == location_id)
        rows = session.scalars(query).all()
        if not rows:
            return stats
        for review in rows:
            payload = review.raw_payload or {}
            incoming = SimpleNamespace(
                review_url=payload.get("review_url"),
                review_photo_urls=payload.get("review_photos_urls") or [],
            )
            if backfill_missing_fields(session, review, incoming, FIELDS):
                # OneBox hanya menarik ulang baris yang sync_updated_at-nya maju.
                review.sync_updated_at = bump
                stats["updated"] += 1
                stats["photos"] += len(review.review_photo_urls)
        stats["scanned"] += len(rows)
        last_id = rows[-1].id
        session.rollback() if dry_run else session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--company-id", type=int)
    parser.add_argument("--location-id", type=int, help="crawler locations.id")
    parser.add_argument("--dry-run", action="store_true", help="hitung saja, tanpa menulis")
    args = parser.parse_args()
    with get_db_session() as session:
        stats = backfill(
            session,
            company_id=args.company_id,
            location_id=args.location_id,
            dry_run=args.dry_run,
        )
    print(("DRY RUN " if args.dry_run else "") + " ".join(f"{k}={v}" for k, v in stats.items()))


if __name__ == "__main__":
    main()
