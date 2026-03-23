from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SECRET_KEYS = {
    "authorization",
    "gemini_api_key",
    "geminiapikey",
    "apikey",
    "api_key",
    "token",
    "x-api-key",
}


def is_secret_key(key: str) -> bool:
    normalized = key.replace("-", "_").lower()
    return normalized in SECRET_KEYS or normalized.endswith("_token")


def redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: ("[REDACTED]" if is_secret_key(str(key)) else redact_value(item)) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_value(item) for item in value]
    return value


def redact_error_message(message: str) -> str:
    lowered = message.lower()
    if "key" in lowered or "token" in lowered or "authorization" in lowered:
        return "Secret-bearing request failed."
    return message
