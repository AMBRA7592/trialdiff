from __future__ import annotations

from trialdiff.jsonpatch import parse_pointer


def match_path(pattern: str, path: str) -> bool:
    pattern_parts = parse_pointer(pattern)
    path_parts = parse_pointer(path)
    return _match_parts(pattern_parts, path_parts)


def _match_parts(pattern_parts: list[str], path_parts: list[str]) -> bool:
    if not pattern_parts:
        return not path_parts
    head, *tail = pattern_parts
    if head == "**":
        if not tail:
            return True
        return any(_match_parts(tail, path_parts[index:]) for index in range(len(path_parts) + 1))
    if not path_parts:
        return False
    if head == "*" or head == path_parts[0]:
        return _match_parts(tail, path_parts[1:])
    return False
