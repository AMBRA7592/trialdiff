from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


class MissingValue:
    def __repr__(self) -> str:
        return "<MISSING>"


MISSING = MissingValue()


class JsonPatchError(ValueError):
    pass


@dataclass(frozen=True)
class PatchValueContext:
    op: str
    path: str
    old_value: Any
    new_value: Any


def parse_pointer(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise JsonPatchError(f"Invalid JSON Pointer: {pointer}")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def format_pointer(parts: list[str]) -> str:
    if not parts:
        return ""
    return "/" + "/".join(part.replace("~", "~0").replace("/", "~1") for part in parts)


def resolve_pointer(document: Any, pointer: str, default: Any = MISSING) -> Any:
    current = document
    for part in parse_pointer(pointer):
        try:
            if isinstance(current, list):
                if part == "-":
                    return default
                current = current[int(part)]
            elif isinstance(current, dict):
                current = current[part]
            else:
                return default
        except (KeyError, IndexError, ValueError):
            return default
    return current


def _parent_and_key(document: Any, pointer: str) -> tuple[Any, str]:
    parts = parse_pointer(pointer)
    if not parts:
        raise JsonPatchError("Root-level patch operations are not supported in the MVP utility")
    parent = document
    for part in parts[:-1]:
        if isinstance(parent, list):
            parent = parent[int(part)]
        elif isinstance(parent, dict):
            parent = parent[part]
        else:
            raise JsonPatchError(f"Cannot traverse through non-container at {pointer}")
    return parent, parts[-1]


def apply_single_patch(document: Any, operation: dict[str, Any]) -> Any:
    op = operation.get("op")
    path = operation.get("path")
    if not isinstance(op, str) or not isinstance(path, str):
        raise JsonPatchError(f"Invalid patch operation: {operation}")
    parent, key = _parent_and_key(document, path)
    if op == "replace":
        if isinstance(parent, list):
            parent[int(key)] = operation.get("value")
        elif isinstance(parent, dict):
            if key not in parent:
                raise JsonPatchError(f"Cannot replace missing path: {path}")
            parent[key] = operation.get("value")
        else:
            raise JsonPatchError(f"Cannot replace path: {path}")
    elif op == "add":
        if isinstance(parent, list):
            if key == "-":
                parent.append(operation.get("value"))
            else:
                parent.insert(int(key), operation.get("value"))
        elif isinstance(parent, dict):
            parent[key] = operation.get("value")
        else:
            raise JsonPatchError(f"Cannot add path: {path}")
    elif op == "remove":
        if isinstance(parent, list):
            del parent[int(key)]
        elif isinstance(parent, dict):
            if key not in parent:
                raise JsonPatchError(f"Cannot remove missing path: {path}")
            del parent[key]
        else:
            raise JsonPatchError(f"Cannot remove path: {path}")
    else:
        raise JsonPatchError(f"Unsupported patch op in MVP utility: {op}")
    return document


def apply_patch(document: Any, patch: list[dict[str, Any]]) -> Any:
    next_document = deepcopy(document)
    for operation in patch:
        apply_single_patch(next_document, operation)
    return next_document


def build_value_contexts(from_document: Any, patch: list[dict[str, Any]]) -> list[PatchValueContext]:
    working = deepcopy(from_document)
    contexts: list[PatchValueContext] = []
    for operation in patch:
        op = operation["op"]
        path = operation["path"]
        old_value = resolve_pointer(working, path)
        apply_single_patch(working, operation)
        new_value = MISSING if op == "remove" else resolve_pointer(working, path)
        contexts.append(PatchValueContext(op=op, path=path, old_value=old_value, new_value=new_value))
    return contexts


def generate_patch(old: Any, new: Any, path: str = "") -> list[dict[str, Any]]:
    if type(old) is not type(new):
        return [{"op": "replace", "path": path, "value": new}]
    if isinstance(old, dict):
        operations: list[dict[str, Any]] = []
        old_keys = set(old)
        new_keys = set(new)
        for key in sorted(old_keys - new_keys):
            operations.append({"op": "remove", "path": format_pointer(parse_pointer(path) + [key])})
        for key in sorted(new_keys - old_keys):
            operations.append({"op": "add", "path": format_pointer(parse_pointer(path) + [key]), "value": new[key]})
        for key in sorted(old_keys & new_keys):
            operations.extend(generate_patch(old[key], new[key], format_pointer(parse_pointer(path) + [key])))
        return operations
    if isinstance(old, list):
        if len(old) != len(new):
            return [{"op": "replace", "path": path, "value": new}]
        operations = []
        for index, (old_item, new_item) in enumerate(zip(old, new, strict=True)):
            operations.extend(generate_patch(old_item, new_item, format_pointer(parse_pointer(path) + [str(index)])))
        return operations
    if old != new:
        return [{"op": "replace", "path": path, "value": new}]
    return []
