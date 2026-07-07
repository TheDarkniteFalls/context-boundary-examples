#!/usr/bin/env python3
"""Check whether sample assistant outputs stay inside supplied context."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_cases(path: Path):
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            yield line_no, json.loads(line)


def validate_output(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        output = json.loads(case.get("model_output", ""))
    except json.JSONDecodeError as exc:
        return [f"model_output is not valid JSON: {exc.msg}"]

    if not isinstance(output, dict):
        return ["model_output must be a JSON object"]

    answer = output.get("answer")
    refusal = output.get("refusal")
    citations = output.get("citations")
    source_ids_raw = case.get("source_ids", [])
    required_citations_raw = case.get("required_citations", [])
    source_ids = set(source_ids_raw) if isinstance(source_ids_raw, list) else set()
    required_citations = (
        set(required_citations_raw) if isinstance(required_citations_raw, list) else set()
    )
    evidence_available = case.get("evidence_available")

    if not isinstance(answer, str) or not answer.strip():
        errors.append("answer must be non-empty text")
    if not isinstance(refusal, bool):
        errors.append("refusal must be true or false")
    if not isinstance(citations, list) or not all(isinstance(item, str) for item in citations):
        errors.append("citations must be a list of source IDs")
        citations = []
    if not isinstance(source_ids_raw, list) or not all(
        isinstance(item, str) for item in source_ids_raw
    ):
        errors.append("source_ids must be a list of source IDs")
    if not isinstance(required_citations_raw, list) or not all(
        isinstance(item, str) for item in required_citations_raw
    ):
        errors.append("required_citations must be a list of source IDs")
    if not isinstance(evidence_available, bool):
        errors.append("evidence_available must be true or false")

    unknown = sorted(set(citations) - source_ids)
    if unknown:
        errors.append(f"unknown citations: {', '.join(unknown)}")

    if evidence_available is True:
        missing = sorted(required_citations - set(citations))
        if refusal is True:
            errors.append("must answer when required evidence is available")
        if missing:
            errors.append(f"missing required citations: {', '.join(missing)}")
    elif evidence_available is False:
        if refusal is not True:
            errors.append("must refuse when required evidence is missing")
        if citations:
            errors.append("missing-evidence refusal must not cite unrelated sources")

    return errors


def run_check(path: Path) -> int:
    failed = False
    for line_no, case in load_cases(path):
        name = case.get("case", f"line_{line_no}")
        expected_valid = case.get("expected_valid")
        if not isinstance(expected_valid, bool):
            print(f"FAIL {name}: expected_valid must be true or false")
            failed = True
            continue

        errors = validate_output(case)
        actual_valid = not errors
        if actual_valid == expected_valid:
            print(f"PASS {name}")
            continue

        failed = True
        expected = "valid" if expected_valid else "invalid"
        actual = "valid" if actual_valid else f"invalid ({'; '.join(errors)})"
        print(f"FAIL {name}: expected {expected}, got {actual}")
    return 1 if failed else 0


def self_test() -> None:
    valid_case = {
        "evidence_available": True,
        "source_ids": ["doc:policy"],
        "required_citations": ["doc:policy"],
        "model_output": json.dumps(
            {
                "answer": "Refunds are available within 30 days.",
                "refusal": False,
                "citations": ["doc:policy"],
            }
        ),
    }
    refusal_case = {
        "evidence_available": False,
        "source_ids": ["doc:policy"],
        "required_citations": [],
        "model_output": json.dumps(
            {
                "answer": "I do not have enough supplied evidence to answer.",
                "refusal": True,
                "citations": [],
            }
        ),
    }
    bad_case = {
        "evidence_available": True,
        "source_ids": ["doc:policy"],
        "required_citations": ["doc:policy"],
        "model_output": json.dumps(
            {
                "answer": "Premium support is included.",
                "refusal": False,
                "citations": ["doc:missing"],
            }
        ),
    }
    assert validate_output(valid_case) == []
    assert validate_output(refusal_case) == []
    assert validate_output(bad_case)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("self-test passed")
        return 0
    if not args.path:
        parser.error("path is required unless --self-test is used")
    return run_check(Path(args.path))


if __name__ == "__main__":
    raise SystemExit(main())
