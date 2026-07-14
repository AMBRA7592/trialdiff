#!/usr/bin/env python3
"""Validate committed Evidence Record files against schemas/*.schema.json.

Requires the ``jsonschema`` package (``pip install jsonschema``); exits 2
with a clear message when it is unavailable so callers can distinguish
"skipped" from "failed".
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

try:
    from jsonschema import Draft202012Validator
except ImportError:
    print("jsonschema is not installed; run: pip install jsonschema", file=sys.stderr)
    raise SystemExit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent

TARGETS = [
    ("schemas/alpha_demo_record.schema.json", "records/*.json"),
    ("schemas/evidence_record.schema.json", "event_class_records_v0.1.1/records/*.json"),
]


def main() -> int:
    failures = 0
    for schema_rel, pattern in TARGETS:
        schema_path = REPO_ROOT / schema_rel
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        files = sorted(REPO_ROOT.glob(pattern))
        if not files:
            print(f"{schema_rel}: no files match {pattern}", file=sys.stderr)
            failures += 1
            continue
        bad = 0
        for path in files:
            errors = list(validator.iter_errors(json.loads(path.read_text(encoding="utf-8"))))
            if errors:
                bad += 1
                first = errors[0]
                print(f"{path.relative_to(REPO_ROOT)}: {first.json_path}: {first.message}", file=sys.stderr)
        print(f"{schema_rel}: {len(files) - bad}/{len(files)} valid")
        failures += bad
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
