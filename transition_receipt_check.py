#!/usr/bin/env python3
"""Check whether synthetic state-transition receipts are safe to act on."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ALLOWED_DECISIONS = {"allow", "repair", "block"}
ALLOWED_KINDS = {
    "user_input",
    "tool_result",
    "tool_side_effect",
    "compaction",
    "external_state",
}
ALLOWED_STATUSES = {"pending", "applied", "superseded"}


def is_non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_version(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_state(
    value: Any,
    *,
    name: str,
    evidence: set[str],
) -> list[str]:
    if not isinstance(value, dict):
        return [f"{name} must be an object"]

    errors: list[str] = []
    if not is_non_empty_text(value.get("id")):
        errors.append(f"{name}.id must be non-empty text")
    if not is_version(value.get("version")):
        errors.append(f"{name}.version must be a non-negative integer")
    if "content_fingerprint" in value and not is_non_empty_text(
        value.get("content_fingerprint")
    ):
        errors.append(f"{name}.content_fingerprint must be non-empty text when supplied")

    evidence_ref = value.get("evidence_ref")
    if not is_non_empty_text(evidence_ref):
        errors.append(f"{name}.evidence_ref must be non-empty text")
    elif evidence_ref not in evidence:
        errors.append(f"{name}.evidence_ref is not listed in evidence")
    return errors


def validate_current_state(value: Any, evidence: set[str]) -> list[str]:
    if not isinstance(value, dict):
        return ["current_state must be an object"]

    errors: list[str] = []
    for field in ("visible_version", "durable_version"):
        if not is_version(value.get(field)):
            errors.append(f"current_state.{field} must be a non-negative integer")
    for field in ("visible_fingerprint", "durable_fingerprint"):
        if field in value and not is_non_empty_text(value.get(field)):
            errors.append(f"current_state.{field} must be non-empty text when supplied")

    evidence_ref = value.get("evidence_ref")
    if not is_non_empty_text(evidence_ref):
        errors.append("current_state.evidence_ref must be non-empty text")
    elif evidence_ref not in evidence:
        errors.append("current_state.evidence_ref is not listed in evidence")
    return errors


def validate_receipt(receipt: Any) -> list[str]:
    if not isinstance(receipt, dict):
        return ["receipt must be an object"]

    errors: list[str] = []
    if not is_non_empty_text(receipt.get("transition_id")):
        errors.append("transition_id must be non-empty text")

    evidence_raw = receipt.get("evidence")
    if not isinstance(evidence_raw, list) or not all(
        is_non_empty_text(item) for item in evidence_raw
    ):
        errors.append("evidence must be a list of non-empty identifiers")
        evidence: set[str] = set()
    else:
        evidence = set(evidence_raw)
        if len(evidence) != len(evidence_raw):
            errors.append("evidence identifiers must be unique")
        if not evidence:
            errors.append("evidence must not be empty")

    last_model_state = receipt.get("last_model_state")
    errors.extend(
        validate_state(last_model_state, name="last_model_state", evidence=evidence)
    )
    errors.extend(validate_current_state(receipt.get("current_state"), evidence))

    decision = receipt.get("decision")
    if decision not in ALLOWED_DECISIONS:
        errors.append("decision must be allow, repair, or block")
    if not is_non_empty_text(receipt.get("decision_reason")):
        errors.append("decision_reason must be non-empty text")

    changes_raw = receipt.get("changes")
    if not isinstance(changes_raw, list):
        errors.append("changes must be a list")
        changes: list[dict[str, Any]] = []
    else:
        changes = [item for item in changes_raw if isinstance(item, dict)]
        if len(changes) != len(changes_raw):
            errors.append("every change must be an object")

    change_ids: list[str] = []
    change_sequences: list[int] = []
    for index, change in enumerate(changes):
        prefix = f"changes[{index}]"
        change_id = change.get("id")
        if not is_non_empty_text(change_id):
            errors.append(f"{prefix}.id must be non-empty text")
        else:
            change_ids.append(change_id)

        sequence = change.get("sequence")
        if not is_version(sequence):
            errors.append(f"{prefix}.sequence must be a non-negative integer")
        else:
            change_sequences.append(sequence)

        if change.get("kind") not in ALLOWED_KINDS:
            errors.append(f"{prefix}.kind is not supported")
        if not is_non_empty_text(change.get("provenance")):
            errors.append(f"{prefix}.provenance must be non-empty text")

        status = change.get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{prefix}.status is not supported")

        evidence_ref = change.get("evidence_ref")
        if not is_non_empty_text(evidence_ref):
            errors.append(f"{prefix}.evidence_ref must be non-empty text")
        elif evidence_ref not in evidence:
            errors.append(f"{prefix}.evidence_ref is not listed in evidence")

        applied_to_version = change.get("applied_to_version")
        superseded_by = change.get("superseded_by")
        if status == "applied":
            if not is_version(applied_to_version):
                errors.append(
                    f"{prefix}.applied_to_version is required for an applied change"
                )
            if superseded_by is not None:
                errors.append(f"{prefix}.superseded_by must be null when applied")
        elif status == "pending":
            if applied_to_version is not None:
                errors.append(f"{prefix}.applied_to_version must be null when pending")
            if superseded_by is not None:
                errors.append(f"{prefix}.superseded_by must be null when pending")
        elif status == "superseded":
            if applied_to_version is not None:
                errors.append(
                    f"{prefix}.applied_to_version must be null when superseded"
                )
            if not is_non_empty_text(superseded_by):
                errors.append(
                    f"{prefix}.superseded_by is required for a superseded change"
                )
            if change.get("kind") == "user_input":
                errors.append("user_input changes must be applied, not superseded")

    if len(set(change_ids)) != len(change_ids):
        errors.append("change identifiers must be unique")
    if len(set(change_sequences)) != len(change_sequences):
        errors.append("change sequences must be unique")
    if change_sequences != sorted(change_sequences):
        errors.append("changes must be ordered by ascending sequence")

    changes_by_id = {
        change.get("id"): change
        for change in changes
        if is_non_empty_text(change.get("id"))
    }
    for index, change in enumerate(changes):
        if change.get("status") != "superseded":
            continue
        superseded_by = change.get("superseded_by")
        replacement = changes_by_id.get(superseded_by)
        if replacement is None:
            errors.append(f"changes[{index}].superseded_by must reference another change")
        elif superseded_by == change.get("id"):
            errors.append(f"changes[{index}] cannot supersede itself")
        elif replacement.get("status") != "applied":
            errors.append(
                f"changes[{index}].superseded_by must reference an applied change"
            )
        elif (
            is_version(change.get("sequence"))
            and is_version(replacement.get("sequence"))
            and replacement["sequence"] <= change["sequence"]
        ):
            errors.append(
                f"changes[{index}].superseded_by must reference a later change"
            )

    current_state = receipt.get("current_state")
    visible_version = (
        current_state.get("visible_version") if isinstance(current_state, dict) else None
    )
    durable_version = (
        current_state.get("durable_version") if isinstance(current_state, dict) else None
    )
    visible_fingerprint = (
        current_state.get("visible_fingerprint")
        if isinstance(current_state, dict)
        else None
    )
    durable_fingerprint = (
        current_state.get("durable_fingerprint")
        if isinstance(current_state, dict)
        else None
    )
    last_version = (
        last_model_state.get("version") if isinstance(last_model_state, dict) else None
    )

    highest_current_version = None
    if is_version(visible_version) and is_version(durable_version):
        highest_current_version = max(visible_version, durable_version)
        if is_version(last_version) and highest_current_version < last_version:
            errors.append("current state cannot be older than last_model_state")

    for index, change in enumerate(changes):
        applied_to_version = change.get("applied_to_version")
        if (
            change.get("status") == "applied"
            and is_version(applied_to_version)
            and highest_current_version is not None
            and applied_to_version > highest_current_version
        ):
            errors.append(
                f"changes[{index}].applied_to_version is newer than current state"
            )
        if (
            change.get("status") == "applied"
            and is_version(applied_to_version)
            and is_version(last_version)
            and applied_to_version < last_version
        ):
            errors.append(
                f"changes[{index}].applied_to_version is older than last_model_state"
            )

    applied_versions = [
        change["applied_to_version"]
        for change in changes
        if change.get("status") == "applied"
        and is_version(change.get("sequence"))
        and is_version(change.get("applied_to_version"))
    ]
    if applied_versions != sorted(applied_versions):
        errors.append("applied change versions must not move backwards")

    next_model_state = receipt.get("next_model_state")
    if decision == "allow":
        errors.extend(
            validate_state(
                next_model_state,
                name="next_model_state",
                evidence=evidence,
            )
        )
        if any(change.get("status") == "pending" for change in changes):
            errors.append("allow is invalid while a change is pending")
        if is_version(visible_version) and is_version(durable_version):
            if visible_version != durable_version:
                errors.append("allow requires visible and durable state to agree")
        next_version = (
            next_model_state.get("version")
            if isinstance(next_model_state, dict)
            else None
        )
        if is_version(next_version) and is_version(visible_version):
            if next_version != visible_version:
                errors.append("next_model_state must use the current visible version")
        if is_version(next_version) and is_version(durable_version):
            if next_version != durable_version:
                errors.append("next_model_state must use the current durable version")
        next_fingerprint = (
            next_model_state.get("content_fingerprint")
            if isinstance(next_model_state, dict)
            else None
        )
        fingerprints_supplied = [
            is_non_empty_text(visible_fingerprint),
            is_non_empty_text(durable_fingerprint),
            is_non_empty_text(next_fingerprint),
        ]
        if any(fingerprints_supplied) and not all(fingerprints_supplied):
            errors.append(
                "allow fingerprints must include visible, durable, and next model state"
            )
        elif all(fingerprints_supplied) and len(
            {visible_fingerprint, durable_fingerprint, next_fingerprint}
        ) != 1:
            errors.append(
                "allow requires visible, durable, and next fingerprints to agree"
            )
        if isinstance(next_model_state, dict) and isinstance(current_state, dict):
            if next_model_state.get("evidence_ref") != current_state.get("evidence_ref"):
                errors.append("next_model_state must use current_state evidence")
        if is_version(next_version) and is_version(last_version):
            if next_version < last_version:
                errors.append("next_model_state cannot roll back to an older version")
        for index, change in enumerate(changes):
            applied_to_version = change.get("applied_to_version")
            if (
                change.get("status") == "applied"
                and is_version(applied_to_version)
                and is_version(next_version)
                and applied_to_version > next_version
            ):
                errors.append(
                    f"changes[{index}] is not included in next_model_state"
                )
    elif decision in {"repair", "block"}:
        if next_model_state is not None:
            errors.append(f"next_model_state must be null when decision is {decision}")
        current_fingerprints_supplied = [
            is_non_empty_text(visible_fingerprint),
            is_non_empty_text(durable_fingerprint),
        ]
        if any(current_fingerprints_supplied) and not all(
            current_fingerprints_supplied
        ):
            errors.append("current_state fingerprints must be supplied together")
        mismatch = (
            is_version(visible_version)
            and is_version(durable_version)
            and (
                visible_version != durable_version
                or (
                    all(current_fingerprints_supplied)
                    and visible_fingerprint != durable_fingerprint
                )
            )
        )
        pending = any(change.get("status") == "pending" for change in changes)
        if not mismatch and not pending:
            errors.append(f"{decision} requires a pending change or state mismatch")

    return errors


def load_cases(path: Path):
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            yield line_no, json.loads(line)
        except json.JSONDecodeError as exc:
            yield line_no, {"case": f"line_{line_no}", "parse_error": exc.msg}


def run_check(path: Path) -> int:
    failed = False
    for line_no, case in load_cases(path):
        name = case.get("case", f"line_{line_no}") if isinstance(case, dict) else f"line_{line_no}"
        if not isinstance(case, dict):
            print(f"FAIL {name}: case must be an object")
            failed = True
            continue
        if case.get("parse_error"):
            print(f"FAIL {name}: invalid JSON: {case['parse_error']}")
            failed = True
            continue

        expected_valid = case.get("expected_valid")
        if not isinstance(expected_valid, bool):
            print(f"FAIL {name}: expected_valid must be true or false")
            failed = True
            continue

        expected_error = case.get("expected_error")
        if expected_valid and expected_error is not None:
            print(f"FAIL {name}: valid cases must not declare expected_error")
            failed = True
            continue
        if not expected_valid and not is_non_empty_text(expected_error):
            print(f"FAIL {name}: invalid cases must declare expected_error")
            failed = True
            continue

        errors = validate_receipt(case.get("receipt"))
        actual_valid = not errors
        expected_error_found = expected_valid or (
            not actual_valid
            and any(expected_error in error for error in errors)
        )
        if actual_valid == expected_valid and expected_error_found:
            print(f"PASS {name}")
            continue

        failed = True
        expected = "valid" if expected_valid else "invalid"
        actual = "valid" if actual_valid else f"invalid ({'; '.join(errors)})"
        if not expected_error_found:
            actual += f"; missing expected error: {expected_error}"
        print(f"FAIL {name}: expected {expected}, got {actual}")
    return 1 if failed else 0


def self_test() -> None:
    valid = {
        "transition_id": "transition-test-1",
        "last_model_state": {
            "id": "state-1",
            "version": 1,
            "evidence_ref": "state:1",
        },
        "changes": [],
        "current_state": {
            "visible_version": 1,
            "durable_version": 1,
            "evidence_ref": "state:1",
        },
        "next_model_state": {
            "id": "state-1",
            "version": 1,
            "evidence_ref": "state:1",
        },
        "decision": "allow",
        "decision_reason": "No state changed.",
        "evidence": ["state:1"],
    }
    pending = json.loads(json.dumps(valid))
    pending["changes"] = [
        {
            "id": "event-1",
            "sequence": 1,
            "kind": "compaction",
            "provenance": "runtime:compactor",
            "status": "pending",
            "evidence_ref": "event:1",
            "applied_to_version": None,
            "superseded_by": None,
        }
    ]
    pending["evidence"].append("event:1")

    matching_fingerprints = json.loads(json.dumps(valid))
    matching_fingerprints["current_state"]["visible_fingerprint"] = "fingerprint:1"
    matching_fingerprints["current_state"]["durable_fingerprint"] = "fingerprint:1"
    matching_fingerprints["next_model_state"]["content_fingerprint"] = "fingerprint:1"

    fingerprint_mismatch = json.loads(json.dumps(matching_fingerprints))
    fingerprint_mismatch["current_state"]["visible_fingerprint"] = "fingerprint:visible"

    partial_fingerprints = json.loads(json.dumps(matching_fingerprints))
    del partial_fingerprints["next_model_state"]["content_fingerprint"]

    assert validate_receipt(valid) == []
    assert validate_receipt(matching_fingerprints) == []
    assert "allow is invalid while a change is pending" in validate_receipt(pending)
    assert (
        "allow requires visible, durable, and next fingerprints to agree"
        in validate_receipt(fingerprint_mismatch)
    )
    assert (
        "allow fingerprints must include visible, durable, and next model state"
        in validate_receipt(partial_fingerprints)
    )


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
