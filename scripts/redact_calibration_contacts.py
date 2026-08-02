#!/usr/bin/env python3
"""Deterministically redact person-level contact data from calibration
review packages.

The blinded review/adjudication packages embed full ClinicalTrials.gov
records and patch payloads, which carry site-contact names, emails, and
phone numbers. Those values never influence classification (rules match
paths, not contact values) and are unnecessary personal data in a research
artifact. This script replaces them with fixed tokens, in place, using the
packages' own canonical serialization (sorted keys, compact separators,
ASCII escapes), and prints a per-file report of replaced values and
before/after SHA-256 hashes.

The transform is deterministic and idempotent: re-running it produces
byte-identical output. Originals remain available in git history; the
redaction is recorded in CALIBRATION_DATA.md and the re-generated
MANIFEST.calibration.sha256.

Frozen evidence-record packages (records/, event_class_records_*) are
intentionally NOT touched: their bytes are hash-pinned and cited.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

EMAIL_TOKEN = "redacted@invalid.example"
TEXT_TOKEN = "REDACTED"
PERSON_SIBLINGS = {"role", "email", "phone", "phoneExt"}
CONTACT_PATH_MARKERS = ("centralContacts", "overallOfficials", "/contacts/")
CONTACT_FIELD_SUFFIXES = ("/email", "/phone", "/phoneExt", "/name")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

DEFAULT_TARGETS = [
    "CALIBRATION_REVIEW_PACKAGE_v0.2.jsonl",
    "CALIBRATION_REVIEW_PACKAGE_v0.2.1.jsonl",
    "CALIBRATION_REVIEW_ADJUDICATION_PACKAGE_v0.2.1.jsonl",
    "CALIBRATION_REVIEW_CRITICAL_STRATUM_ADJUDICATION_PACKAGE_v0.2.1.jsonl",
]


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def is_contact_pointer(path: str) -> bool:
    return any(marker in path for marker in CONTACT_PATH_MARKERS)


def redact_scalar_for_pointer(pointer: str, item: str, counts: Counter) -> str | None:
    if pointer.endswith("/email"):
        counts["email"] += 1
        return EMAIL_TOKEN
    if pointer.endswith("/phone") or pointer.endswith("/phoneExt"):
        counts["phone"] += 1
        return TEXT_TOKEN
    if pointer.endswith("/name") and is_contact_pointer(pointer):
        counts["name"] += 1
        return TEXT_TOKEN
    return None


def redact_free_text(item: str, counts: Counter) -> str:
    # Any email address anywhere — including sponsor-published free text — is
    # contact data with no analytical role in these packages.
    redacted, n = EMAIL_RE.subn(EMAIL_TOKEN, item)
    if n and item != redacted:
        counts["email_in_text"] += n
    return redacted


def redact(value: object, counts: Counter) -> object:
    if isinstance(value, list):
        return [redact(item, counts) for item in value]
    if isinstance(value, str):
        return redact_free_text(value, counts)
    if not isinstance(value, dict):
        return value

    result: dict = {}
    keys = set(value.keys())
    person_context = bool(keys & PERSON_SIBLINGS)
    # Two pointer-carrying shapes exist: patch operations
    # {"op", "path", "value"} and value contexts
    # {"path", "old_value", "new_value"}; the pointer names the contact field
    # and the scalar rides alongside.
    pointer = value.get("path") if isinstance(value.get("path"), str) else None

    for key, item in value.items():
        if key == "email" and isinstance(item, str) and item:
            result[key] = EMAIL_TOKEN
            counts["email"] += 1
        elif key in {"phone", "phoneExt"} and isinstance(item, str) and item:
            result[key] = TEXT_TOKEN
            counts["phone"] += 1
        elif key == "name" and isinstance(item, str) and item and person_context:
            result[key] = TEXT_TOKEN
            counts["name"] += 1
        elif (
            key in {"value", "old_value", "new_value"}
            and pointer is not None
            and isinstance(item, str)
            and item
        ):
            replacement = redact_scalar_for_pointer(pointer, item, counts)
            result[key] = replacement if replacement is not None else redact(item, counts)
        elif key == "path" and isinstance(item, str):
            # JSON Pointers are structural, never contact data; keep verbatim
            # so rule/path analyses stay byte-stable.
            result[key] = item
        else:
            result[key] = redact(item, counts)
    return result


def redact_file(path: Path) -> dict:
    original = path.read_bytes()
    counts: Counter = Counter()
    out_lines = []
    for line in original.decode("utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        out_lines.append(canonical_json(redact(record, counts)))
    redacted = ("\n".join(out_lines) + "\n").encode("utf-8")
    path.write_bytes(redacted)
    return {
        "file": str(path),
        "replacements": dict(counts),
        "sha256_before": hashlib.sha256(original).hexdigest(),
        "sha256_after": hashlib.sha256(redacted).hexdigest(),
        "changed": hashlib.sha256(original).hexdigest() != hashlib.sha256(redacted).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="*", default=DEFAULT_TARGETS, help="JSONL package files to redact in place.")
    args = parser.parse_args()
    for target in args.targets:
        report = redact_file(Path(target))
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
