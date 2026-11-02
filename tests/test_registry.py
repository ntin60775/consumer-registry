#!/usr/bin/env python3
"""Plugin tests for consumer-registry — stdlib-only, no external dependencies.

Six checks from issue ntin60775/sot-zcode-marketplace#7:
1. schema and template are valid JSON; the schema declares draft-07;
2. the template passes scripts/registry_check.py;
3. the template's keys cover the schema's required keys, and the schema's
   required lists match the contract verbatim;
4. gitignore.snippet contains a whole line .zcode/registry.local.json;
5. SKILL.md frontmatter: slots name/description/when_to_use/license/metadata,
   description <= 1024 chars, trigger in the first ~250 chars;
6. the validator rejects: a foreign schema const, a result outside the enum,
   a consumer without kind/version/state, a non-ISO updated_at — and accepts
   a filled registry (positive control).

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


def run_validator_on(registry):
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    ) as handle:
        json.dump(registry, handle, ensure_ascii=False, indent=2)
        path = Path(handle.name)
    try:
        return run_validator(path)
    finally:
        path.unlink(missing_ok=True)


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


# Required lists of the contract, verbatim from issue #7 — an expected value
# independent of the schema file, so a weakened schema cannot pass by
# matching a weakened template.
CONTRACT_REQUIRED = {
    "$": ["schema", "machine", "project", "updated_at", "consumers", "deploy_log"],
    "$.machine": ["hostname"],
    "$.project": ["name"],
    "$.consumers[]": ["name", "kind", "version", "state"],
    "$.deploy_log[]": ["at", "actor", "action", "result"],
    "$.deploy_log[].followups[]": ["kind", "owner", "done"],
    "$.acceptance[]": ["at", "consumer", "kind", "result"],
}


def schema_required(schema):
    properties = schema["properties"]
    deploy_log_items = properties["deploy_log"]["items"]
    return {
        "$": schema.get("required", []),
        "$.machine": properties["machine"].get("required", []),
        "$.project": properties["project"].get("required", []),
        "$.consumers[]": properties["consumers"]["items"].get("required", []),
        "$.deploy_log[]": deploy_log_items.get("required", []),
        "$.deploy_log[].followups[]": deploy_log_items["properties"]["followups"][
            "items"
        ].get("required", []),
        "$.acceptance[]": properties["acceptance"]["items"].get("required", []),
    }


def sample_registry(template):
    """The template with one entry of each kind — the positive control."""
    full = json.loads(json.dumps(template))
    full["consumers"].append(
        {
            "name": "example-project",
            "kind": "project",
            "path": "/tmp/example-project",
            "version": "v1.2.3",
            "since": "2026-01-15",
            "state": "active",
            "note": "positive control",
        }
    )
    full["deploy_log"].append(
        {
            "at": "2026-11-02T12:00:00Z",
            "actor": "test",
            "action": "backfill",
            "consumer": "example-project",
            "from": "v1.2.2",
            "to": "v1.2.3",
            "result": "ok",
            "followups": [
                {"kind": "owner-acceptance", "owner": "human", "done": False}
            ],
        }
    )
    full["acceptance"].append(
        {
            "at": "2026-11-02T13:00:00Z",
            "consumer": "example-project",
            "kind": "smoke",
            "result": "green",
            "details": "positive control",
        }
    )
    return full


def check_3():
    schema = load_json(SCHEMA_PATH)
    template = load_json(TEMPLATE_PATH)
    actual = schema_required(schema)
    for node, expected in CONTRACT_REQUIRED.items():
        assert actual[node] == expected, (
            f"{node}: schema required is {actual[node]!r}, "
            f"the contract says {expected!r}"
        )

    def walk(schema_node, template_node, path):
        for key in schema_node.get("required", []):
            assert key in template_node, f"{path}: template misses required key {key!r}"
        for key, sub in schema_node.get("properties", {}).items():
            if not isinstance(sub, dict):
                continue
            child = template_node.get(key)
            if isinstance(child, dict):
                walk(sub, child, f"{path}.{key}")
            elif isinstance(child, list) and isinstance(sub.get("items"), dict):
                for index, item in enumerate(child):
                    if isinstance(item, dict):
                        walk(sub["items"], item, f"{path}.{key}[{index}]")

    walk(schema, template, "$")
    walk(schema, sample_registry(template), "$+samples")


def check_4():
    text = SNIPPET_PATH.read_text(encoding="utf-8")
    line_re = re.compile(r"^\s*\.zcode/registry\.local\.json\s*$", re.MULTILINE)
    assert line_re.search(text), "snippet misses a whole line .zcode/registry.local.json"


BLOCK_SCALARS = (">", ">-", ">+", "|", "|-", "|+")


def parse_frontmatter(text):
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    assert match, "SKILL.md has no frontmatter block"
    slots = {}
    last_key = None
    for line in match.group(1).splitlines():
        pair = re.match(r"([A-Za-z][\w-]*):\s*(.*)$", line)
        if pair:
            key, value = pair.group(1), pair.group(2).strip()
            assert value not in BLOCK_SCALARS, (
                f"frontmatter slot {key!r} uses a block scalar; "
                "this check reads plain values only"
            )
            last_key = key
            slots[key] = value.strip('"')
        elif re.match(r"\s+\S", line) and last_key:
            slots[last_key] += " " + line.strip()
        else:
            last_key = None
    return slots


def parse_flow_map(text):
    inner = text.strip()
    if inner.startswith("{") and inner.endswith("}"):
        inner = inner[1:-1]
    mapping = {}
    for part in inner.split(","):
        pair = part.split(":", 1)
        if len(pair) == 2:
            mapping[pair[0].strip()] = pair[1].strip()
    return mapping


def check_5():
    slots = parse_frontmatter(SKILL_PATH.read_text(encoding="utf-8"))
    for slot in ("name", "description", "when_to_use", "license", "metadata"):
        assert slot in slots, f"frontmatter misses slot {slot!r}"
    description = slots["description"]
    assert len(description) <= 1024, f"description is {len(description)} chars > 1024"
    head = description[:250].lower()
    assert "реестр" in head or "registry" in head, (
        "no trigger word in the first ~250 chars of description"
    )
    assert slots["license"] == "MIT", f"license is {slots['license']!r}, expected MIT"
    metadata = parse_flow_map(slots["metadata"])
    assert metadata.get("concern") == "process", (
        f"metadata concern is {metadata.get('concern')!r}, expected 'process'"
    )
    assert metadata.get("contract") == "consumer-registry/1", (
        f"metadata contract is {metadata.get('contract')!r}, "
        "expected 'consumer-registry/1'"
    )


def check_6():
    template = load_json(TEMPLATE_PATH)
    full = sample_registry(template)

    ok = run_validator_on(full)
    assert ok.returncode == 0, (
        f"validator rejected the positive control (exit {ok.returncode}):\n"
        f"{ok.stdout}{ok.stderr}"
    )

    def probe(title, bad, fragment):
        result = run_validator_on(bad)
        assert result.returncode == 1, (
            f"{title}: expected exit 1 (validation error), got {result.returncode}\n"
            f"{result.stdout}{result.stderr}"
        )
        assert "INVALID" in result.stdout, f"{title}: no INVALID verdict in output"
        assert fragment in result.stdout, f"{title}: output misses {fragment!r}"

    bad = json.loads(json.dumps(full))
    bad["schema"] = "consumer-registry/2"
    probe("foreign schema const", bad, "expected const")

    bad = json.loads(json.dumps(full))
    bad["deploy_log"][0]["result"] = "unknown"
    probe("result outside the enum", bad, "is not one of")

    for missing in ("kind", "version", "state"):
        bad = json.loads(json.dumps(full))
        del bad["consumers"][0][missing]
        probe(f"consumer without {missing}", bad, "missing required property")

    bad = json.loads(json.dumps(full))
    bad["updated_at"] = "02.11.2026"
    probe("non-ISO updated_at", bad, "not an ISO 8601 timestamp")

    bad = json.loads(json.dumps(full))
    bad["updated_at"] = "2026-11-02"
    probe("updated_at without a time part", bad, "not an ISO 8601 timestamp")


def main():
    print(f"consumer-registry tests — root {ROOT}")
    run_check(1, "schema and template are valid JSON, schema declares draft-07", check_1)
    run_check(2, "template passes scripts/registry_check.py", check_2)
    run_check(3, "schema required matches the contract, template covers it", check_3)
    run_check(4, "gitignore.snippet contains .zcode/registry.local.json", check_4)
    run_check(5, "SKILL.md frontmatter slots, limits and trigger", check_5)
    run_check(6, "validator accepts a filled registry, rejects the negative probes", check_6)
    print()
    if failures:
        print(f"FAILED: {len(failures)} of 6 checks")
        return 1
    print("PASSED: 6/6 checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
