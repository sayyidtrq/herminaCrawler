"""Import an APIFY Google review fixture into the Crawler database.

The command is intentionally dry-run by default. It is an operational bridge
for a provider outage, not the APIFY runtime adapter. The normal path remains:
OneBox master locations -> Crawler worklist -> Crawler reviews -> OneBox pull.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db.models import Company, FetchLog, Location, Review
from app.db.session import get_session_factory
from app.utils.date_parser import parse_datetime
from app.utils.hashing import generate_review_hash


DEFAULT_SOURCE = "apify_google_maps"
DEFAULT_MANIFEST = Path(__file__).with_name("astra_location_manifest.json")
DEFAULT_ANONYMOUS_NAME = "Anonymous"


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_provider_datetime(record: dict[str, Any], absolute_key: str) -> datetime | None:
    return parse_datetime(record.get(absolute_key))


def _review_identity(place_id: str, review_id: str) -> tuple[str, str]:
    return place_id, review_id


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    locations = payload.get("locations") if isinstance(payload, dict) else payload
    if not isinstance(locations, list) or not locations:
        raise ValueError("Manifest must contain a non-empty locations list.")

    normalized: list[dict[str, Any]] = []
    seen_places: set[str] = set()
    for expected_sequence, raw in enumerate(locations, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Manifest row {expected_sequence} is not an object.")
        sequence = int(raw.get("sequence", expected_sequence))
        branch_name = _text(raw.get("branch_name"))
        place_id = _text(raw.get("external_place_id"))
        if sequence != expected_sequence:
            raise ValueError("Manifest sequence must be contiguous and start at 1.")
        if not branch_name or not place_id:
            raise ValueError(f"Manifest row {sequence} needs branch_name and external_place_id.")
        if place_id in seen_places:
            raise ValueError(f"Duplicate manifest place ID: {place_id}")
        seen_places.add(place_id)
        normalized.append(
            {
                "sequence": sequence,
                "branch_name": branch_name,
                "external_place_id": place_id,
                "hospital_name": _text(raw.get("hospital_name")) or "Asuransi Astra",
            }
        )
    return normalized


def _load_records(data_dir: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if not data_dir.is_dir():
        raise ValueError(f"Data directory does not exist: {data_dir}")
    records: list[dict[str, Any]] = []
    file_counts: dict[str, int] = {}
    files = sorted(data_dir.glob("*.json"))
    if not files:
        raise ValueError(f"No JSON files found in {data_dir}")

    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Expected a JSON array in {path.name}")
        file_counts[path.name] = len(payload)
        for index, raw in enumerate(payload, start=1):
            if not isinstance(raw, dict):
                raise ValueError(f"{path.name} item {index} is not an object.")
            item = dict(raw)
            item["_source_file"] = path.name
            item["_source_index"] = index
            records.append(item)
    return records, file_counts


def _quality_key(record: dict[str, Any]) -> tuple[int, int, int, int, str, str]:
    review_time = _parse_provider_datetime(record, "reviewed_at_date")
    scraped_at = parse_datetime(record.get("scraped_at"))
    return (
        int(bool(_text(record.get("content")))),
        int(review_time is not None),
        int(bool(_text(record.get("owner_response")))),
        len(record.get("review_photos_urls") or []),
        int(scraped_at.timestamp()) if scraped_at else 0,
        _text(record.get("_source_file")),
    )


def _bounded_raw_payload(record: dict[str, Any], source_file: str) -> dict[str, Any]:
    allowed = (
        "review_id",
        "review_url",
        "review_position",
        "place_id",
        "place_name",
        "place_rating",
        "place_reviews_count",
        "place_photo_url",
        "review_photos_urls",
        "category",
        "categories",
        "address",
        "full_address",
        "neighborhood",
        "street",
        "city",
        "postal_code",
        "state",
        "country",
        "website",
        "phone",
        "location",
        "language",
        "content_language",
        "content_translated",
        "translated_language",
        "owner_response_translated",
        "owner_response_at",
        "owner_response_at_date",
        "reviewed_at",
        "reviewed_at_date",
        "visited_in",
        "fid",
        "knowledge_graph_id",
        "cid",
    )
    payload = {key: record.get(key) for key in allowed if key in record}
    payload["provider"] = "apify"
    payload["source_file"] = source_file
    return payload


def _normalize_record(
    record: dict[str, Any],
    location: Location,
    source: str,
    anonymous_name: str,
    imported_at: datetime,
) -> tuple[dict[str, Any], str]:
    place_id = _text(record.get("place_id"))
    review_id = _text(record.get("review_id"))
    if not review_id:
        raise ValueError("review_id is required for the APIFY Astra fixture.")
    rating = _optional_int(record.get("rating"))
    if rating is not None and not 1 <= rating <= 5:
        rating = None

    review_time = _parse_provider_datetime(record, "reviewed_at_date")
    scraped_at = parse_datetime(record.get("scraped_at")) or imported_at
    owner_response_time = _parse_provider_datetime(record, "owner_response_at_date")
    reviewer_total_reviews = _optional_int(record.get("reviewer_reviews_count"))
    reviewer_name = _text(record.get("reviewer_name")) or anonymous_name
    review_text = _text(record.get("content"))

    data = {
        "company_id": location.company_id,
        "location_id": location.id,
        "source": source,
        "external_place_id": place_id,
        "external_review_id": review_id,
        "reviewer_name": reviewer_name,
        "reviewer_profile_url": record.get("reviewer_url"),
        "reviewer_photo_url": record.get("reviewer_photo_url"),
        "reviewer_local_guide_level": "Local Guide"
        if record.get("is_local_guide")
        else None,
        "reviewer_total_reviews": reviewer_total_reviews,
        "rating": rating,
        "review_text": review_text,
        "review_time": review_time,
        "review_relative_time": record.get("reviewed_at"),
        "review_language": _text(record.get("content_language"))
        or _text(record.get("language"))
        or "unknown",
        "language": _text(record.get("language")) or "unknown",
        "like_count": max(0, _optional_int(record.get("likes_count")) or 0),
        "owner_response_text": _text(record.get("owner_response")) or None,
        "owner_response_time": owner_response_time,
        "scraped_at": scraped_at,
        "raw_payload": _bounded_raw_payload(record, _text(record.get("_source_file"))),
        "sync_updated_at": imported_at,
        "analysis_status": "pending",
    }
    data["review_hash"] = generate_review_hash(data)
    return data, _review_identity(place_id, review_id)


def _select_batch(manifest: list[dict[str, Any]], batch: int | None, batch_size: int) -> list[dict[str, Any]]:
    if batch is None:
        return manifest
    if batch < 1:
        raise ValueError("--batch must be 1 or greater.")
    start = (batch - 1) * batch_size
    selected = manifest[start : start + batch_size]
    if not selected:
        raise ValueError(f"Batch {batch} is outside the manifest.")
    return selected


def _location_map(
    session,
    company_id: int,
    selected: list[dict[str, Any]],
) -> dict[str, Location]:
    place_ids = [row["external_place_id"] for row in selected]
    company = session.get(Company, company_id)
    if company is None:
        raise ValueError(f"Crawler company_id={company_id} does not exist.")
    rows = list(
        session.scalars(
            select(Location).where(
                Location.company_id == company_id,
                Location.external_place_id.in_(place_ids),
            )
        )
    )
    by_place: dict[str, Location] = {}
    for location in rows:
        if location.external_place_id in by_place:
            raise ValueError(
                f"Multiple crawler locations found for place ID {location.external_place_id}."
            )
        by_place[location.external_place_id] = location
    missing = [place_id for place_id in place_ids if place_id not in by_place]
    if missing:
        raise ValueError(
            "Crawler worklist is incomplete; missing place IDs: " + ", ".join(missing)
        )
    unmapped = [
        location.branch_name
        for location in by_place.values()
        if location.onebox_connection_id is None or location.onebox_location_id is None
    ]
    if unmapped:
        raise ValueError(
            "Crawler locations are missing onebox_connection_id or onebox_location_id: "
            + ", ".join(unmapped)
        )
    return by_place


def _canonical_records(
    records: list[dict[str, Any]],
    selected_places: set[str],
    manifest_places: set[str],
) -> tuple[
    dict[tuple[str, str], dict[str, Any]],
    Counter[str],
    int,
    int,
    int,
    int,
]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    unknown_rows = 0
    out_of_batch_rows = 0
    selected_raw_rows = 0
    for record in records:
        place_id = _text(record.get("place_id"))
        if place_id not in manifest_places:
            if place_id:
                unknown_rows += 1
            continue
        if place_id not in selected_places:
            out_of_batch_rows += 1
            continue
        selected_raw_rows += 1
        review_id = _text(record.get("review_id"))
        if not review_id:
            raise ValueError(
                f"Missing review_id in {record.get('_source_file')} item {record.get('_source_index')}"
            )
        grouped[_review_identity(place_id, review_id)].append(record)

    canonical: dict[tuple[str, str], dict[str, Any]] = {}
    duplicate_groups = 0
    duplicate_rows = 0
    conflicting_groups = 0
    for identity, variants in grouped.items():
        if len(variants) > 1:
            duplicate_groups += 1
            duplicate_rows += len(variants) - 1
            fingerprints = {
                json.dumps(
                    {
                        "content": _text(item.get("content")),
                        "rating": item.get("rating"),
                        "reviewed_at_date": item.get("reviewed_at_date"),
                        "owner_response": _text(item.get("owner_response")),
                        "review_url": _text(item.get("review_url")),
                    },
                    sort_keys=True,
                    ensure_ascii=True,
                )
                for item in variants
            }
            if len(fingerprints) > 1:
                conflicting_groups += 1
        canonical[identity] = max(variants, key=_quality_key)

    stats = Counter(
        duplicate_review_id_groups=duplicate_groups,
        duplicate_rows=duplicate_rows,
        conflicting_duplicate_groups=conflicting_groups,
    )
    content_groups: dict[tuple[str, str], set[str]] = defaultdict(set)
    for identity, record in grouped.items():
        content = _text(record[0].get("content"))
        if content:
            content_groups[(identity[0], content)].add(identity[1])
    content_duplicate_groups = sum(len(ids) > 1 for ids in content_groups.values())
    return (
        canonical,
        stats,
        unknown_rows,
        content_duplicate_groups,
        selected_raw_rows,
        out_of_batch_rows,
    )


def _existing_identities(
    session,
    company_id: int,
    target_place_ids: list[str],
):
    rows = list(
        session.scalars(
            select(Review).where(
                Review.company_id == company_id,
                Review.external_place_id.in_(target_place_ids),
            )
        )
    )
    identities = {
        _review_identity(_text(row.external_place_id), _text(row.external_review_id))
        for row in rows
        if row.external_place_id and row.external_review_id
    }
    hashes = {row.review_hash for row in rows}
    return identities, hashes


def import_fixture(args: argparse.Namespace) -> dict[str, Any]:
    manifest = _load_manifest(Path(args.manifest).resolve())
    selected = _select_batch(manifest, args.batch, args.batch_size)
    selected_places = {row["external_place_id"] for row in selected}
    manifest_places = {row["external_place_id"] for row in manifest}
    records, file_counts = _load_records(Path(args.data_dir).resolve())
    (
        canonical,
        dedupe_stats,
        unknown_rows,
        content_duplicate_groups,
        selected_raw_rows,
        out_of_batch_rows,
    ) = _canonical_records(
        records, selected_places, manifest_places
    )
    imported_at = datetime.now(timezone.utc)

    session_factory = get_session_factory()
    with session_factory() as session:
        locations = _location_map(session, args.company_id, selected)
        normalized: list[tuple[dict[str, Any], tuple[str, str]]] = []
        for identity, record in canonical.items():
            location = locations[identity[0]]
            data, normalized_identity = _normalize_record(
                record,
                location,
                args.source,
                args.anonymous_name,
                imported_at,
            )
            if normalized_identity != identity:
                raise ValueError("Internal identity mismatch while normalizing fixture.")
            normalized.append((data, identity))

        target_place_ids = [row["external_place_id"] for row in manifest]
        existing_identities, existing_hashes = _existing_identities(
            session, args.company_id, target_place_ids
        )
        candidate_hashes = {data["review_hash"] for data, _ in normalized}
        global_hash_rows = list(
            session.scalars(select(Review).where(Review.review_hash.in_(candidate_hashes)))
        )
        global_hashes = {row.review_hash for row in global_hash_rows}

        to_insert: list[Review] = []
        skipped_existing = 0
        skipped_hash = 0
        seen_identities = set(existing_identities)
        seen_hashes = set(existing_hashes)
        per_location = Counter()
        for data, identity in sorted(normalized, key=lambda item: item[1]):
            if identity in seen_identities:
                skipped_existing += 1
                continue
            if data["review_hash"] in seen_hashes:
                skipped_hash += 1
                continue
            if data["review_hash"] in global_hashes:
                raise ValueError(
                    "A candidate review_hash already belongs to another crawler row; "
                    "stop and investigate before importing."
                )
            to_insert.append(Review(**data))
            seen_identities.add(identity)
            seen_hashes.add(data["review_hash"])
            per_location[identity[0]] += 1

        result: dict[str, Any] = {
            "status": "dry_run" if not args.commit else "committed",
            "company_id": args.company_id,
            "batch": args.batch,
            "batch_size": args.batch_size,
            "locations": len(selected),
            "raw_rows": selected_raw_rows,
            "canonical_rows": len(canonical),
            "to_insert": len(to_insert),
            "skipped_existing": skipped_existing,
            "skipped_hash": skipped_hash,
            "unknown_place_rows": unknown_rows,
            "out_of_batch_rows": out_of_batch_rows,
            "content_duplicate_groups": content_duplicate_groups,
            "duplicate_review_id_groups": dedupe_stats["duplicate_review_id_groups"],
            "duplicate_rows": dedupe_stats["duplicate_rows"],
            "conflicting_duplicate_groups": dedupe_stats["conflicting_duplicate_groups"],
            "file_counts": file_counts,
            "per_location_new": dict(sorted(per_location.items())),
        }

        if args.commit:
            session.add_all(to_insert)
            session.flush()
            raw_by_place = Counter(
                _text(record.get("place_id"))
                for record in records
                if _text(record.get("place_id")) in selected_places
            )
            canonical_by_place = Counter(identity[0] for identity in canonical)
            for manifest_row in selected:
                place_id = manifest_row["external_place_id"]
                location = locations[place_id]
                new_count = per_location.get(place_id, 0)
                session.add(
                    FetchLog(
                        company_id=args.company_id,
                        location_id=location.id,
                        source=args.source,
                        status="success",
                        total_fetched=raw_by_place.get(place_id, 0),
                        total_inserted=new_count,
                        total_duplicate=(
                            raw_by_place.get(place_id, 0)
                            - canonical_by_place.get(place_id, 0)
                            + canonical_by_place.get(place_id, 0)
                            - new_count
                        ),
                        total_failed=0,
                        metadata_json={
                            "fixture_import": True,
                            "provider": "apify",
                            "batch": args.batch,
                            "manifest_sequence": manifest_row["sequence"],
                            "raw_rows": raw_by_place.get(place_id, 0),
                            "canonical_rows": canonical_by_place.get(place_id, 0),
                            "out_of_batch_rows": out_of_batch_rows,
                            "content_duplicate_groups": content_duplicate_groups,
                            "conflicting_duplicate_groups": dedupe_stats[
                                "conflicting_duplicate_groups"
                            ],
                            "imported_at": imported_at.isoformat(),
                        },
                        started_at=imported_at,
                        finished_at=imported_at,
                    )
                )
            session.commit()
        return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dry-run or import APIFY Astra reviews into Crawler reviews."
    )
    parser.add_argument("--data-dir", required=True, help="Directory containing APIFY JSON arrays.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Location manifest JSON.")
    parser.add_argument("--company-id", type=int, required=True)
    parser.add_argument("--batch", type=int, help="1-based batch number; each batch has 12 manifest rows.")
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--anonymous-name", default=DEFAULT_ANONYMOUS_NAME)
    parser.add_argument("--commit", action="store_true", help="Persist reviews and fetch logs. Omit for dry-run.")
    parser.add_argument("--report-json", type=Path, help="Write the summary report to this path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.batch_size <= 0:
        print("--batch-size must be greater than zero.", file=sys.stderr)
        return 2
    try:
        result = import_fixture(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"IMPORT BLOCKED: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True)
    print(rendered)
    if args.report_json:
        args.report_json.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
