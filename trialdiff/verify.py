"""Standalone verification of exported TrialDiff Evidence Record files.

Any holder of a record file can re-derive its integrity properties without
database access:

- ``trialdiff.evidence_record`` (event-class packages): the file bytes are
  the canonical serialization; their SHA-256 is the citable record hash.
  The embedded patch re-hashes to ``provenance.patch_hash`` and the
  ``event_id`` re-derives from the record's own fields.
- ``trialdiff.alpha_demo_record`` (frozen v0.1-alpha wrapper): the embedded
  ``canonical_evidence_record`` re-hashes to
  ``provenance.evidence_canonical_hash`` and the patch re-hashes to
  ``provenance.patch_hash``. Alpha ``event_id`` values were derived by the
  frozen v0.1-alpha generation scheme (before ``event_classes`` entered the
  digest) and are intentionally not re-derived here.

Trust scope: these checks are recomputed from the record's own contents,
so they prove canonical form and internal self-consistency — not
authenticity. An edited record that is re-serialized canonically (with
self-referential hashes re-derived) passes. Authenticity comes from
comparing the file hash against an external anchor: the package
``MANIFEST.sha256`` or the database ``canonical_hash``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any

from trialdiff.evidence import build_event_id
from trialdiff.provenance import canonical_json, sha256_json, sha256_text


@dataclass
class VerificationResult:
    path: Path
    schema: str | None = None
    checks: list[tuple[str, bool, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self.checks.append((name, passed, detail))

    @property
    def ok(self) -> bool:
        return bool(self.checks) and all(passed for _name, passed, _detail in self.checks)


def verify_record_file(path: str | Path) -> VerificationResult:
    path = Path(path)
    result = VerificationResult(path=path)
    try:
        payload = path.read_bytes()
    except OSError as exc:
        result.add("readable", False, str(exc))
        return result
    try:
        text = payload.decode("utf-8")
        record = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        result.add("valid_utf8_json", False, str(exc))
        return result
    if not isinstance(record, dict):
        result.add("valid_utf8_json", False, "top level is not a JSON object")
        return result

    schema = record.get("schema")
    result.schema = schema
    try:
        if schema == "trialdiff.evidence_record":
            verify_evidence_record(result, payload, record)
        elif schema == "trialdiff.alpha_demo_record":
            verify_alpha_demo_record(result, record)
        else:
            result.add("known_schema", False, f"unrecognized schema {schema!r}")
    except (TypeError, KeyError, AttributeError, ValueError) as exc:
        # A shape-malformed record must fail its own verification, never
        # abort the rest of the batch.
        result.add("well_formed", False, f"{type(exc).__name__}: {exc}")
    return result


def verify_evidence_record(result: VerificationResult, payload: bytes, record: dict[str, Any]) -> None:
    canonical_text = canonical_json(record)
    file_hash = hashlib.sha256(payload).hexdigest()
    result.add(
        "canonical_bytes",
        payload.decode("utf-8") == canonical_text,
        f"file sha256 {file_hash}",
    )
    result.notes.append(f"record_hash={sha256_text(canonical_text)}")

    provenance = record.get("provenance") or {}
    patch = record.get("patch")
    result.add(
        "patch_hash",
        patch is not None and sha256_json(patch) == provenance.get("patch_hash"),
        f"stored {provenance.get('patch_hash')}",
    )

    classification = record.get("classification") or {}
    try:
        derived_event_id = build_event_id(
            nct_id=record["trial"]["nct_id"],
            from_version=record["versions"]["from_version"],
            to_version=record["versions"]["to_version"],
            patch_hash=provenance["patch_hash"],
            category=classification["category"],
            changed_paths=record["changed_paths"],
            event_classes=classification.get("event_classes") or [],
            rule_set_hash=classification["rule_set_hash"],
            evidence_version=record["evidence_version"],
        )
    except KeyError as exc:
        result.add("event_id", False, f"missing field {exc}")
        return
    result.add(
        "event_id",
        derived_event_id == record.get("event_id"),
        f"derived {derived_event_id}",
    )
    result.add(
        "filename_matches_event_id",
        result.path.stem == record.get("event_id"),
        f"filename {result.path.name}",
    )


def verify_alpha_demo_record(result: VerificationResult, record: dict[str, Any]) -> None:
    provenance = record.get("provenance") or {}
    canonical_record = record.get("canonical_evidence_record")
    if canonical_record is None:
        result.add("canonical_evidence_record_present", False, "field absent")
        return
    recomputed = sha256_json(canonical_record)
    result.add(
        "evidence_canonical_hash",
        recomputed == provenance.get("evidence_canonical_hash"),
        f"recomputed {recomputed}",
    )
    patch = record.get("patch")
    result.add(
        "patch_hash",
        patch is not None and sha256_json(patch) == provenance.get("patch_hash"),
        f"stored {provenance.get('patch_hash')}",
    )
    result.add(
        "filename_matches_event_id",
        result.path.stem == record.get("event_id"),
        f"filename {result.path.name}",
    )
    result.notes.append(
        "event_id derivation for alpha records predates the current scheme; "
        "integrity is carried by evidence_canonical_hash instead"
    )
