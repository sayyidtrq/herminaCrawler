"""Signed, opaque keyset cursors for the OneBox integration pull.

The cursor carries the tenant and the active filter, not just a position. That is
the whole point: an unsigned cursor is a request parameter, and a request
parameter that names a position in someone's table is an invitation to page
through another tenant's reviews by editing it. Every field below is covered by
the HMAC, and decode refuses a cursor whose tenant or filter does not match the
caller presenting it.

To OneBox this is an opaque string. The layout here may change freely (it is not
part of contract v1) as long as encode/decode stay in step.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

CURSOR_VERSION = 1

# Bounds cursor replay. Read-only and idempotent, so this is a backstop rather
# than a correctness requirement; a consumer stalled this long should bootstrap.
MAX_CURSOR_AGE = timedelta(days=30)


class InvalidCursorError(Exception):
    """Raised for every rejection reason.

    Deliberately carries no detail: telling a caller whether the signature, the
    tenant, or the version failed hands them an oracle for probing the format.
    """


@dataclass(frozen=True)
class CursorPosition:
    sync_updated_at: datetime
    id: int

    def as_tuple(self) -> tuple[datetime, int]:
        return (self.sync_updated_at, self.id)


@dataclass(frozen=True)
class IntegrationCursor:
    version: int
    company_id: int
    # Carried, not hashed: the contract says a follow-up page sends only the
    # cursor, so the filter has to be recoverable from it. A hash would only be
    # checkable against a location_id the consumer is not required to resend.
    # The HMAC is what makes it tamper-proof.
    location_id: int | None
    lower: CursorPosition  # exclusive
    upper: CursorPosition  # inclusive
    issued_at: datetime

    @property
    def is_checkpoint(self) -> bool:
        """Snapshot exhausted: the next cycle re-opens an upper bound from here."""
        return self.lower.as_tuple() == self.upper.as_tuple()


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _sign(payload: bytes, secret: str) -> bytes:
    return hmac.new(secret.encode(), payload, hashlib.sha256).digest()


def encode_cursor(cursor: IntegrationCursor, secret: str) -> str:
    payload = json.dumps(
        {
            "v": cursor.version,
            "c": cursor.company_id,
            "loc": cursor.location_id,
            "lt": _to_utc(cursor.lower.sync_updated_at).isoformat(),
            "li": cursor.lower.id,
            "ut": _to_utc(cursor.upper.sync_updated_at).isoformat(),
            "ui": cursor.upper.id,
            "iat": _to_utc(cursor.issued_at).isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return f"{_b64encode(payload)}.{_b64encode(_sign(payload, secret))}"


def decode_cursor(
    raw: str,
    secret: str,
    expected_company_id: int,
) -> IntegrationCursor:
    """Verify signature, version, tenant and age.

    location_id is returned unchecked: the caller decides what to do when the
    request also names one. That is not an oracle — the signature has already
    proven this is a cursor we issued to this tenant.
    """
    try:
        encoded_payload, encoded_signature = raw.split(".", 1)
        payload = _b64decode(encoded_payload)
        signature = _b64decode(encoded_signature)
    except (ValueError, binascii.Error) as exc:
        raise InvalidCursorError from exc

    # Constant-time: a byte-by-byte comparison leaks how much of a forged
    # signature was correct, which is enough to reconstruct one.
    if not hmac.compare_digest(signature, _sign(payload, secret)):
        raise InvalidCursorError

    try:
        body = json.loads(payload)
        location_id = body["loc"]
        cursor = IntegrationCursor(
            version=int(body["v"]),
            company_id=int(body["c"]),
            location_id=None if location_id is None else int(location_id),
            lower=CursorPosition(
                sync_updated_at=_to_utc(datetime.fromisoformat(body["lt"])),
                id=int(body["li"]),
            ),
            upper=CursorPosition(
                sync_updated_at=_to_utc(datetime.fromisoformat(body["ut"])),
                id=int(body["ui"]),
            ),
            issued_at=_to_utc(datetime.fromisoformat(body["iat"])),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InvalidCursorError from exc

    if cursor.version != CURSOR_VERSION:
        raise InvalidCursorError
    # A validly signed cursor is still not usable by a different tenant: tokens
    # get rotated and reissued, and the signature alone does not prove ownership.
    if cursor.company_id != expected_company_id:
        raise InvalidCursorError
    if datetime.now(timezone.utc) - cursor.issued_at > MAX_CURSOR_AGE:
        raise InvalidCursorError

    return cursor


def fingerprint(raw: str) -> str:
    """Short, non-reversible tag for logs — never log the cursor itself."""
    return hashlib.sha256(raw.encode()).hexdigest()[:8]
