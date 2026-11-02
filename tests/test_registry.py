#!/usr/bin/env python3
"""Plugin tests for consumer-registry — stdlib-only, no external dependencies.

Six checks from issue ntin60775/sot-zcode-marketplace#7:
1. schema and template are valid JSON; the schema declares draft-07;
2. the template passes scripts/registry_check.py;
3. the template's keys cover the schema's required keys;
4. gitignore.snippet contains the line .zcode/registry.local.json;
5. SKILL.md frontmatter: slots name/description/when_to_use/license/metadata,
   description <= 1024 chars, trigger in the first ~250 chars;
6. the validator rejects: a foreign schema const, a result outside the enum,
   a consumer without kind/version/state, a non-ISO updated_at.

Run: python3 tests/test_registry.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "templates" / "registry.schema.json"
TEMPLATE_PATH = ROOT / "templates" / "registry.template.json"
SNIPPET_PATH = ROOT / "templates" / "gitignore.snippet"
SKILL_PATH = ROOT / "skills" / "consumer-registry" / "SKILL.md"
VALIDATOR_PATH = ROOT / "scripts" / "registry_check.py"

failures = []


def run_check(number, title, fn):
    try:
        fn()
    except AssertionError as exc:
        failures.append(number)
        print(f"FAIL [{number}] {title}: {exc}")
    except Exception as exc:  # an unexpected error is a failure too
        failures.append(number)
        print(f"FAIL [{number}] {title}: unexpected {type(exc).__name__}: {exc}")
    else:
        print(f"ok   [{number}] {title}")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_validator(target):
    return subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), str(target)],
        capture_output=True,
        text=True,
    )


def check_1():
    schema = load_json(SCHEMA_PATH)
    template = load_json(TEMPLATE_PATH)
    assert isinstance(schema, dict), "schema is not a JSON object"
    assert isinstance(template, dict), "template is not a JSON object"
    declared = schema.get("$schema", "")
    assert "draft-07" in declared, f"schema does not declare draft-07: {declared!r}"


def check_2():
    result = run_validator(TEMPLATE_PATH)
    assert result.returncode == 0, (
        f"validator rejected the template (exit {result.returncode}):\n"
        f"{result.stdout}{result.stderr}"
    )


def check_3():
    schema = load_json(SCHEMA_PATH)
    template = load_json(TEMPLATE_PATH)

    def walk(schema_node, template_node, path):
        for key in schema_node.get("required", []):
            assert key in template_node, f"{path}: template misses required key {key!r}"
        for key, sub in schema_node.get("properties", {}).items():
            if isinstance(sub, dict) and isinstance(template_node.get(key), dict):
                walk(sub, template_node[key], f"{path}.{key}")

    walk(schema, template, "$")


def check_4():
    text = SNIPPET_PATH.read_text(encoding="utf-8")
    assert ".zcode/registry.local.json" in text, (
        "snippet misses the line .zcode/registry.local.json"
    )


def check_5():
    text = SKILL_PATH.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    assert match, "SKILL.md has no frontmatter block"
    slots = {}
    for line in match.group(1).splitlines():
        pair = re.match(r"([A-Za-z][\w-]*):\s*(.*)$", line)
        if pair:
            slots[pair.group(1)] = pair.group(2).strip().strip('"')
    for slot in ("name", "description", "when_to_use", "license", "metadata"):
        assert slot in slots, f"frontmatter misses slot {slot!r}"
    description = slots["description"]
    assert len(description) <= 1024, f"description is {len(description)} chars > 1024"
    head = description[:250].lower()
    assert "реестр" in head or "registry" in head, (
        "no trigger word in the first ~250 chars of description"
    )
    assert slots["license"] == "MIT", f"license is {slots['license']!r}, expected MIT"
    metadata = slots["metadata"]
    assert "concern: process" in metadata, f"metadata misses concern: process: {metadata!r}"
    assert "contract: consumer-registry/1" in metadata, (
        f"metadata misses contract: consumer-registry/1: {metadata!r}"
    )


def check_6():
    template = load_json(TEMPLATE_PATH)

    def probe(title, mutate):
        bad = json.loads(json.dumps(template))
        mutate(bad)
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as handle:
            json.dump(bad, handle, ensure_ascii=False, indent=2)
            path = Path(handle.name)
        try:
            result = run_validator(path)
            assert result.returncode != 0, f"{title}: validator accepted it (exit 0)"
        finally:
            path.unlink(missing_ok=True)

    probe("foreign schema const", lambda r: r.__setitem__("schema", "consumer-registry/2"))
    probe(
        "result outside the enum",
        lambda r: r["deploy_log"].append(
            {"at": "2026-11-02T12:00:00Z", "actor": "test", "action": "backfill", "result": "unknown"}
        ),
    )
    probe(
        "consumer without kind/version/state",
        lambda r: r["consumers"].append({"name": "incomplete"}),
    )
    probe("non-ISO updated_at", lambda r: r.__setitem__("updated_at", "02.11.2026"))


def main():
    print(f"consumer-registry tests — root {ROOT}")
    run_check(1, "schema and template are valid JSON, schema declares draft-07", check_1)
    run_check(2, "template passes scripts/registry_check.py", check_2)
    run_check(3, "template keys cover the schema required keys", check_3)
    run_check(4, "gitignore.snippet contains .zcode/registry.local.json", check_4)
    run_check(5, "SKILL.md frontmatter slots, limits and trigger", check_5)
    run_check(6, "validator rejects the four negative probes", check_6)
    print()
    if failures:
        print(f"FAILED: {len(failures)} of 6 checks")
        return 1
    print("PASSED: 6/6 checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
