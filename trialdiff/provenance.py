from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from typing import Any

from trialdiff.constants import Source


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_text(canonical_json(value))


@dataclass(frozen=True)
class Provenance:
    source: Source
    source_url: str
    fetched_at: str
    raw_hash: str
    source_version: str | None = None

    @classmethod
    def from_payload(
        cls,
        *,
        source: Source,
        source_url: str,
        payload: Any,
        source_version: str | None = None,
    ) -> "Provenance":
        return cls(
            source=source,
            source_url=source_url,
            fetched_at=utc_now_iso(),
            raw_hash=sha256_json(payload),
            source_version=source_version,
        )
