#!/usr/bin/env python3
"""registry_check.py — stdlib-only validator for consumer-registry/1 registries.

Usage:
    python3 scripts/registry_check.py <registry.json> [schema.json]

The schema path defaults to templates/registry.schema.json resolved relative
to this script (works both in the repo and in a deployed plugin layout
.zcode/registry/scripts -> .zcode/registry/templates); the second argument
overrides it.

Implements the draft-07 keyword subset used by the contract schema: type,
const, enum, required, properties, additionalProperties, items. On top of
the schema it enforces the ISO 8601 formats declared in field descriptions
(updated_at, consumers[].since).

Exit codes: 0 — valid; 1 — validation errors; 2 — usage, I/O or JSON error.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

USAGE = "usage: python3 scripts/registry_check.py <registry.json> [schema.json]"

TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    # draft-07: any number with a zero fractional part is an integer (1.0 too)
    "integer": lambda v: (isinstance(v, int) and not isinstance(v, bool))
    or (isinstance(v, float) and v.is_integer()),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "null": lambda v: v is None,
}

TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})?$"
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def json_equal(a, b):
    """JSON equality: booleans are distinct from numbers (bool subclasses int)."""
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return a == b


def validate_node(instance, schema, path, errors):
    """Validate instance against the draft-07 keyword subset of the schema."""
    expected = schema.get("type")
    if expected is not None:
        # draft-07 allows a union of types: ["integer", "null"]
        types = expected if isinstance(expected, list) else [expected]
        checks = [TYPE_CHECKS.get(name) for name in types]
        if not types or any(check is None for check in checks):
            errors.append(f"{path}: schema uses unsupported type {expected!r}")
            return
        if not any(check(instance) for check in checks):
            errors.append(
                f"{path}: expected type {expected!r}, got {type(instance).__name__}"
            )
            return

    if "const" in schema and not json_equal(instance, schema["const"]):
        errors.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")

    enum = schema.get("enum")
    if enum is not None and not any(json_equal(instance, option) for option in enum):
        errors.append(f"{path}: value {instance!r} is not one of {enum!r}")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required property {key!r}")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in properties:
                validate_node(value, properties[key], f"{path}.{key}", errors)
            elif additional is False:
                errors.append(f"{path}: unexpected property {key!r}")
            elif isinstance(additional, dict):
                validate_node(value, additional, f"{path}.{key}", errors)

    if isinstance(instance, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for index, value in enumerate(instance):
                validate_node(value, items, f"{path}[{index}]", errors)
        elif isinstance(items, list):
            # Tuple validation (draft-07); items beyond the tuple stay allowed
            # unless additionalItems says otherwise, which this subset skips.
            for index, value in enumerate(instance):
                if index < len(items) and isinstance(items[index], dict):
                    validate_node(value, items[index], f"{path}[{index}]", errors)


def is_iso_timestamp(value):
    """ISO 8601 moment — date and time, e.g. 2026-11-02T12:00:00Z."""
    if not TIMESTAMP_RE.match(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def is_iso_date(value):
    """ISO 8601 calendar date only, e.g. 2026-11-02."""
    if not DATE_RE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def check_formats(root, errors):
    """Enforce the ISO 8601 formats the schema declares in descriptions."""
    updated_at = root.get("updated_at")
    if isinstance(updated_at, str) and not is_iso_timestamp(updated_at):
        errors.append(f"$.updated_at: not an ISO 8601 timestamp: {updated_at!r}")
    consumers = root.get("consumers")
    if isinstance(consumers, list):
        for index, consumer in enumerate(consumers):
            since = consumer.get("since") if isinstance(consumer, dict) else None
            if isinstance(since, str) and not is_iso_date(since):
                errors.append(
                    f"$.consumers[{index}].since: not an ISO 8601 date: {since!r}"
                )


def load_json(path):
    """Return parsed JSON or raise UsageError with a readable message."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UsageError(f"cannot read {path}: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise UsageError(f"{path} is not valid JSON: {exc}") from exc


class UsageError(Exception):
    """Usage, I/O or JSON error — reported on stderr, exit code 2."""


def main(argv):
    if len(argv) < 2 or len(argv) > 3:
        print(f"registry_check: {len(argv) - 1} arguments, expected 1 or 2", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2

    registry_path = Path(argv[1])
    if len(argv) == 3:
        schema_path = Path(argv[2])
    else:
        schema_path = (
            Path(__file__).resolve().parent.parent / "templates" / "registry.schema.json"
        )

    try:
        registry = load_json(registry_path)
        schema = load_json(schema_path)
    except UsageError as exc:
        print(f"registry_check: {exc}", file=sys.stderr)
        return 2

    errors = []
    validate_node(registry, schema, "$", errors)
    if isinstance(registry, dict):
        check_formats(registry, errors)

    if errors:
        print(f"INVALID: {registry_path}")
        for error in errors:
            print(f"  - {error}")
        return 1

    schema_const = registry.get("schema") if isinstance(registry, dict) else None
    print(f"OK: {registry_path} ({schema_const})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
