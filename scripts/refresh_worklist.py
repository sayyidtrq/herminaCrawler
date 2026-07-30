"""Manually refresh the OneBox-owned crawl worklist."""

from __future__ import annotations

import argparse
import json

from app.services.worklist_sync_service import WorklistSyncError, WorklistSyncService


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh the OneBox VOC worklist cache")
    parser.add_argument("--company-id", type=int, help="VoC company tenant; defaults to ONEBOX_COMPANY_ID")
    parser.add_argument("--json", action="store_true", help="print machine-readable output")
    args = parser.parse_args()
    try:
        result = WorklistSyncService(company_id=args.company_id).refresh().as_dict()
    except WorklistSyncError as exc:
        raise SystemExit(str(exc)) from exc
    if args.json:
        print(json.dumps(result, indent=2))
        return
    print(
        f"status={result['status']} company_id={result['company_id']} "
        f"site_id={result['site_id']} fetched={result['fetched']} "
        f"upserted={result['upserted']} deactivated={result['deactivated']}"
    )
    if result["cache_age_seconds"] is not None:
        print(f"cache_age_seconds={result['cache_age_seconds']}")
    if result["warning"]:
        print(f"warning={result['warning']}")


if __name__ == "__main__":
    main()
