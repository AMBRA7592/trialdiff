from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping


def implementation_source_hash(sources: Mapping[str, Path]) -> str:
    """Hash normalized source bytes without leaking machine-local paths."""

    normalized = []
    for label, path in sorted(sources.items()):
        source = path.read_text(encoding="utf-8")
        source = source.replace("\r\n", "\n").replace("\r", "\n")
        normalized.append(
            {
                "module": label,
                "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            }
        )
    payload = json.dumps(normalized, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
