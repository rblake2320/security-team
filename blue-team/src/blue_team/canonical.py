"""Bounded canonicalization helpers used at every trust boundary."""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from .errors import ValidationError

MAX_EVENT_BYTES = 64 * 1024
MAX_DEPTH = 8
MAX_COLLECTION_ITEMS = 256
MAX_STRING_CHARS = 16_384
MAX_KEY_CHARS = 128


def _clean_string(value: str, *, key: bool = False) -> str:
    limit = MAX_KEY_CHARS if key else MAX_STRING_CHARS
    normalized = unicodedata.normalize("NFKC", value)
    if len(normalized) > limit:
        raise ValidationError(f"string exceeds {limit} characters")
    if any(ord(char) < 32 and char not in "\t\n\r" for char in normalized):
        raise ValidationError("string contains disallowed control characters")
    return normalized


def normalize(value: Any, *, depth: int = 0) -> Any:
    """Return a deterministic, bounded JSON-compatible value."""
    if depth > MAX_DEPTH:
        raise ValidationError("object nesting exceeds the safety limit")
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationError("non-finite numbers are not allowed")
        return value
    if isinstance(value, str):
        return _clean_string(value)
    if isinstance(value, Mapping):
        if len(value) > MAX_COLLECTION_ITEMS:
            raise ValidationError("object has too many fields")
        result: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str):
                raise ValidationError("object keys must be strings")
            key = _clean_string(raw_key, key=True)
            if key in result:
                raise ValidationError("keys collide after Unicode normalization")
            result[key] = normalize(raw_value, depth=depth + 1)
        return result
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        if len(value) > MAX_COLLECTION_ITEMS:
            raise ValidationError("array has too many items")
        return [normalize(item, depth=depth + 1) for item in value]
    raise ValidationError(f"unsupported JSON value: {type(value).__name__}")


def loads_bounded(raw: bytes) -> Any:
    if len(raw) > MAX_EVENT_BYTES:
        raise ValidationError(f"event exceeds {MAX_EVENT_BYTES} bytes")
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("event is not valid UTF-8 JSON") from exc
    return normalize(parsed)


def canonical_json(value: Any) -> str:
    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
