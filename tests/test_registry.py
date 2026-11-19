#!/usr/bin/env python3
"""Bundle tests for consumer-registry — stdlib-only, no external dependencies.

Six checks adapted to the DSH-native bundle layout (ticket deliver/02);
the contract expectations stay verbatim from issue
ntin60775/sot-zcode-marketplace#7:
1. schema and template are valid JSON; the schema declares draft-07;
2. the template passes the bundle validator scripts/registry_check.py,
   with the default schema resolution and with an explicit schema argument;
   a foreign const in the explicit schema rejects the template (can-fail
   pin of the override);
3. the schema const and required lists match the contract verbatim, and the
   template's keys cover the schema's required keys;
4. the ZCode channel is removed: no bundle file mentions zcode (bytecode
   excluded), the channel files (.zcode-plugin/, deploy.json) are gone, and
   gitignore.snippet carries a whole line .agents/registry.local.json;
5. SKILL.md frontmatter follows the DSH idiom (name/description),
   description <= 500 chars (project limit), trigger in the first ~250 chars,
   the description names the new home .agents/registry.local.json, and the
   start step declares idempotence and the .agents removal warning;
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
BUNDLE = ROOT / "skills" / "consumer-registry"
SCHEMA_PATH = BUNDLE / "templates" / "registry.schema.json"
TEMPLATE_PATH = BUNDLE / "templates" / "registry.template.json"
SNIPPET_PATH = BUNDLE / "templates" / "gitignore.snippet"
SKILL_PATH = BUNDLE / "SKILL.md"
VALIDATOR_PATH = BUNDLE / "scripts" / "registry_check.py"

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


def run_validator(target, schema=None):
    argv = [sys.executable, str(VALIDATOR_PATH), str(target)]
    if schema is not None:
        argv.append(str(schema))
    return subprocess.run(argv, capture_output=True, text=True)


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
    # The validator accepts an explicit schema path as the second argument.
    explicit = run_validator(TEMPLATE_PATH, SCHEMA_PATH)
    assert explicit.returncode == 0, (
        f"validator rejected the template with an explicit schema "
        f"(exit {explicit.returncode}):\n{explicit.stdout}{explicit.stderr}"
    )
    # Can-fail pin of the override: a foreign const in the explicit schema
    # must reject the template — a validator ignoring argv[2] would pass.
    schema = load_json(SCHEMA_PATH)
    schema["properties"]["schema"]["const"] = "consumer-registry/2"
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    ) as handle:
        json.dump(schema, handle, ensure_ascii=False)
        foreign = Path(handle.name)
    try:
        rejected = run_validator(TEMPLATE_PATH, foreign)
        assert rejected.returncode == 1 and "expected const" in rejected.stdout, (
            f"explicit schema override did not take effect "
            f"(exit {rejected.returncode}):\n{rejected.stdout}{rejected.stderr}"
        )
    finally:
        foreign.unlink(missing_ok=True)


# Contract pins, verbatim from issue #7 — expected values independent of the
# schema file, so a weakened schema cannot pass by matching a weakened
# template. The const is part of the contract: consumer-registry/1.
CONTRACT_CONST = "consumer-registry/1"
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
    return full


def check_3():
    schema = load_json(SCHEMA_PATH)
    template = load_json(TEMPLATE_PATH)
    const = schema["properties"]["schema"].get("const")
    assert const == CONTRACT_CONST, (
        f"schema const is {const!r}, the contract says {CONTRACT_CONST!r}"
    )
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

    # Решение оператора: журнал приёмок не ведётся. Каркас нового реестра
    # его не несёт, поле схемы остаётся ради чтения старых реестров.
    assert "acceptance" not in template, "template must not carry acceptance"
    assert "не заполняется" in schema["properties"]["acceptance"]["description"], (
        "schema must mark acceptance as legacy/not filled"
    )


def check_4():
    # The ZCode channel is removed: no bundle content mentions it, and the
    # marketplace channel files are gone from the repo. The scan runs before
    # the snippet read so the base tree reds on the literals themselves.
    for path in sorted(BUNDLE.rglob("*")):
        if not path.is_file():
            continue
        # Bytecode is not bundle content — the installer EXCLUDES it too.
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        content = path.read_text(encoding="utf-8").lower()
        assert "zcode" not in content, f"bundle file mentions zcode: {path}"
    assert not (ROOT / ".zcode-plugin").exists(), ".zcode-plugin/ is still present"
    assert not (ROOT / "deploy.json").exists(), "deploy.json is still present"
    text = SNIPPET_PATH.read_text(encoding="utf-8")
    line_re = re.compile(r"^\s*\.agents/registry\.local\.json\s*$", re.MULTILINE)
    assert line_re.search(text), "snippet misses a whole line .agents/registry.local.json"


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


def check_5():
    text = SKILL_PATH.read_text(encoding="utf-8")
    slots = parse_frontmatter(text)
    # DSH idiom: the catalog routes by name/description.
    for slot in ("name", "description"):
        assert slot in slots, f"frontmatter misses slot {slot!r}"
    assert slots["name"] == "consumer-registry", (
        f"frontmatter name is {slots['name']!r}, expected 'consumer-registry'"
    )
    description = slots["description"]
    # Project limit 500 (text-style.md, «Frontmatter скилла»); the DSH
    # catalog limit 1024 is weaker and follows from it.
    assert len(description) <= 500, f"description is {len(description)} chars > 500"
    head = description[:250].lower()
    assert "реестр" in head or "registry" in head, (
        "no trigger word in the first ~250 chars of description"
    )
    # Criterion 5 (triage G-20, G-27): the start step declares idempotence
    # and warns that removing .agents destroys the registry, backup outside v1.
    assert "идемпотентен" in text, "start step does not declare idempotence"
    assert "уничтожает реестр" in text, "start step misses the .agents removal warning"
    assert "бэкап" in text, "warning does not name backup outside v1"
    # New-path pin (triage G-21, spec decision 4): the description names the
    # new home; the schema/template/docstring pins live in checks 3 and 4.
    assert ".agents/registry.local.json" in description, (
        "description does not name the new home .agents/registry.local.json"
    )


def check_6():
    template = load_json(TEMPLATE_PATH)
    full = sample_registry(template)

    ok = run_validator_on(full)
    assert ok.returncode == 0, (
        f"validator rejected the positive control (exit {ok.returncode}):\n"
        f"{ok.stdout}{ok.stderr}"
    )

    # Чтение старых реестров: запись приёмки в файле версии 1 остаётся
    # валидной, хотя новых журнал не пишет.
    legacy = json.loads(json.dumps(full))
    legacy["acceptance"] = [
        {
            "at": "2026-11-02T13:00:00Z",
            "consumer": "example-project",
            "kind": "smoke",
            "result": "green",
        }
    ]
    leg = run_validator_on(legacy)
    assert leg.returncode == 0, (
        f"validator rejected a legacy registry with acceptance (exit {leg.returncode}):\n"
        f"{leg.stdout}{leg.stderr}"
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


def check_7():
    """release rules are declared, and the version lives only in git.

    Цели: spec — README «Версии и релизы»; invariant — бандл не пинит
    версию литералом (иначе тег и текст разойдутся молча).
    """
    readme = re.sub(r"\s+", " ", (ROOT / "README.md").read_text(encoding="utf-8")).lower()
    agents = re.sub(r"\s+", " ", (ROOT / "AGENTS.md").read_text(encoding="utf-8")).lower()
    for phrase in ("## версии и релизы", "тег не переносится",
                   "consumer-registry/n+1", "ls-remote --tags"):
        assert phrase in readme, f"README misses release rule {phrase!r}"
    assert "тег не переносится" in agents, "AGENTS misses the tag rule"
    assert "consumer-registry/n+1" in agents, "AGENTS misses the contract bump rule"

    version_re = re.compile(r"\bv\d+\.\d+\.\d+\b")
    for path in sorted(BUNDLE.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.suffix == ".pyc":
            continue
        hit = version_re.search(path.read_text(encoding="utf-8"))
        assert hit is None, f"bundle pins a version literal: {path}: {hit.group(0)}"


def main():
    print(f"consumer-registry tests — root {ROOT}")
    run_check(1, "schema and template are valid JSON, schema declares draft-07", check_1)
    run_check(2, "template passes the bundle validator (default, explicit, foreign schema)", check_2)
    run_check(3, "schema const and required match the contract, template covers them", check_3)
    run_check(4, "ZCode channel removed: no zcode in bundle, snippet .agents line", check_4)
    run_check(5, "SKILL.md DSH frontmatter and start step: idempotence, warning, home path", check_5)
    run_check(6, "validator accepts a filled registry, rejects the negative probes", check_6)
    run_check(7, "release rules declared, version lives only in git", check_7)
    print()
    if failures:
        print(f"FAILED: {len(failures)} of 7 checks")
        return 1
    print("PASSED: 7/7 checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
