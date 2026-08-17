from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from typing import Any

from .errors import ConfigurationError

MAX_BYTES = 1_000_000
MAX_DEPTH = 16
MAX_ITEMS = 10_000
MAX_STRING = 16_384


def load_json_bounded(raw: bytes, *, max_bytes: int = MAX_BYTES) -> Any:
    if len(raw) > max_bytes:
        raise ConfigurationError(f"JSON exceeds {max_bytes} byte limit")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError("JSON is not valid UTF-8 JSON") from exc
    return normalize(value)


def normalize(value: Any, *, _depth: int = 0) -> Any:
    if _depth > MAX_DEPTH:
        raise ConfigurationError("JSON nesting limit exceeded")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ConfigurationError("non-finite numbers are forbidden")
        return value
    if isinstance(value, str):
        normalized = unicodedata.normalize("NFKC", value)
        if len(normalized) > MAX_STRING:
            raise ConfigurationError("string limit exceeded")
        if any(ord(char) < 32 and char not in "\t\n\r" for char in normalized):
            raise ConfigurationError("unsafe control character")
        return normalized
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_ITEMS:
            raise ConfigurationError("collection limit exceeded")
        return [normalize(item, _depth=_depth + 1) for item in value]
    if isinstance(value, dict):
        if len(value) > MAX_ITEMS:
            raise ConfigurationError("collection limit exceeded")
        result: dict[str, Any] = {}
        collision_keys: set[str] = set()
        for raw_key, item in value.items():
            if not isinstance(raw_key, str):
                raise ConfigurationError("object keys must be strings")
            key = normalize(raw_key, _depth=_depth + 1)
            collision_key = key.casefold()
            if collision_key in collision_keys:
                raise ConfigurationError("normalized object-key collision")
            collision_keys.add(collision_key)
            result[key] = normalize(item, _depth=_depth + 1)
        return result
    raise ConfigurationError(f"unsupported JSON value: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
