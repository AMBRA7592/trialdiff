from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Mapping


def semantic_source_hash(sources: Mapping[str, Path]) -> str:
    """Hash normalized Python ASTs without leaking machine-local paths."""

    normalized = []
    for label, path in sorted(sources.items()):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=label)
        normalized.append(
            {
                "module": label,
                "ast": ast.dump(tree, annotate_fields=True, include_attributes=False),
            }
        )
    payload = json.dumps(normalized, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
