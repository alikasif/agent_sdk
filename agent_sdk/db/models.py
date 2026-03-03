"""Helpers for converting between SQLite rows (dicts) and Pydantic models."""

from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# Fields that are stored as JSON text in SQLite
_JSON_FIELDS = frozenset(
    {
        "metadata",
        "tool_calls",
        "tool_results",
        "input_messages",
        "output_message",
        "tags",
        "tools",
        "details",
        "tool_arguments",
        "result",
    }
)


def row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    """Decode JSON text columns in a raw SQLite row."""
    decoded: dict[str, Any] = {}
    for key, value in row.items():
        if key in _JSON_FIELDS and isinstance(value, str):
            try:
                decoded[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                decoded[key] = value
        else:
            decoded[key] = value
    return decoded


def row_to_model(row: dict[str, Any], model_class: type[T]) -> T:
    """Convert a SQLite row dict to a Pydantic model."""
    decoded = row_to_dict(row)
    return model_class.model_validate(decoded)


def model_to_row(model: BaseModel, *, json_fields: frozenset[str] | None = None) -> dict[str, Any]:
    """Convert a Pydantic model to a dict suitable for SQLite insertion.

    Complex fields are serialized as JSON strings.
    """
    fields = json_fields or _JSON_FIELDS
    data = model.model_dump(mode="python")
    row: dict[str, Any] = {}
    for key, value in data.items():
        if key in fields and not isinstance(value, (str, bytes, type(None))):
            row[key] = json.dumps(value, default=str)
        else:
            row[key] = value
    return row
