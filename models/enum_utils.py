"""Shared enum deserialization helpers."""

import logging
from enum import Enum
from typing import Type, TypeVar

_E = TypeVar("_E", bound=Enum)
_log = logging.getLogger(__name__)


def safe_enum(cls: Type[_E], value: str, default: _E) -> _E:
    """Deserialise an enum value without crashing on unknown strings.

    JSONL files outlive code — a value written by an older or newer version of
    the code may not exist in the current enum. Returning a safe default keeps
    the server running; the warning tells us to add the missing member.
    """
    try:
        return cls(value)
    except ValueError:
        _log.warning(
            "Unknown %s value %r in stored data — using %r as fallback",
            cls.__name__, value, default.value,
        )
        return default
