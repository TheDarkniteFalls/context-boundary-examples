# Context Boundary Examples

<!-- toolkit-trust-card:start -->
> **Public contract:** Stable pattern · about 5 min · Python 3 · no model · no network
>
> **Operation:** Read-only check; examples may use temporary files
>
> **A pass establishes:** Expected answers cite only allowed sources and known unsupported or uncited outputs fail.
>
> **It does not establish:** Grounding to supplied snippets does not establish that those snippets are true or current.
>
> **First check:** `python3 context_boundary_check.py --self-test`
<!-- toolkit-trust-card:end -->

A tiny set of synthetic checks for assistant outputs and agent state transitions
that should stay inside supplied context.

The demos do not call a model. One checks whether an answer/refusal mode matches
the available evidence and verifies citations against supplied source IDs. The
other checks whether an agent can safely continue after user input, tool
results, external state, or compaction changes its context. Both are
deterministic and public-safe.

## Why It Exists

AI assistants should not answer from memory when a workflow asks them to use
only supplied evidence. They also should not continue from stale state after
their context changes. This repo shows both boundaries with small structural
checks.

## Run

```sh
python3 context_boundary_check.py examples/context_outputs.jsonl
python3 context_boundary_check.py --self-test
python3 transition_receipt_check.py examples/transition_receipts.jsonl
python3 transition_receipt_check.py --self-test
```

Expected result:

```text
PASS valid_grounded_answer
PASS valid_missing_evidence_refusal
PASS invalid_answers_without_evidence
PASS invalid_missing_required_citation
PASS invalid_unknown_citation
PASS valid_no_change_allow
PASS valid_reconciled_user_input
PASS valid_completed_compaction
PASS valid_block_unresolved_tool_side_effect
PASS valid_repair_visible_durable_mismatch
PASS valid_superseded_external_state
PASS invalid_stale_resume
PASS invalid_missing_provenance
PASS invalid_allow_pending_compaction
PASS invalid_superseded_user_input
PASS invalid_block_without_boundary
PASS valid_tool_result_then_late_user_input
PASS invalid_allow_pending_late_user_input
PASS invalid_out_of_order_changes
PASS invalid_allow_equal_version_digest_mismatch
```

## Supplied-Evidence Output Contract

Each sample `model_output` must be JSON with:

- `answer`: non-empty text.
- `refusal`: `true` when supplied evidence is missing, otherwise `false`.
- `citations`: source IDs from the current case.

Each fixture case declares whether evidence is available and which citations are
required. The checker treats mismatches as boundary failures.

## State-Transition Contract

[`TRANSITION_RECEIPT.md`](TRANSITION_RECEIPT.md) defines a compact receipt for
the boundary between one model call and the next. It records the last model
state, intervening changes and their provenance, visible and durable state,
the proposed next state, and an `allow`, `repair`, or `block` decision.

The checker rejects stale continuation, unresolved changes, missing provenance,
out-of-order events, silent loss of user input, and visible/durable version or
content mismatches presented as safe. It accepts honest repair and block
outcomes.

The [OpenAI Agents Python #2671 application note](applications/openai-agents-python-2671.md)
maps this generic contract to one current open-source lifecycle problem without
claiming that the local checker is an SDK implementation.

## How These Fit Together

This repo is one piece of a small public toolkit:

- [Public Repo Safety Kit](https://github.com/TheDarkniteFalls/public-repo-safety-kit)
  checks a public-candidate repo before publishing.
- [EvidenceGate](https://github.com/TheDarkniteFalls/evidencegate) records the
  evidence and checks behind an AI-assisted change.
- [Local Model Reliability Example](https://github.com/TheDarkniteFalls/local-model-reliability-example)
  validates structured model output and protected-path boundaries before
  trusting it.
- Context Boundary Examples checks whether an answer stays inside supplied
  evidence and whether an agent continues from reconciled state.
- [Green-Spine QA Pattern](https://github.com/TheDarkniteFalls/green-spine-qa-pattern)
  bundles the important path behind one repeatable command.
- [Codex Project Instructions Starter](https://github.com/TheDarkniteFalls/codex-project-instructions-starter)
  gives coding agents clear project rules before they work.

Together they show a practical pattern: publish safely, give agents clear
project rules, leave a reviewable receipt, validate model output, keep answers
grounded in supplied context, and keep the important path healthy.

## Public Data Notice

All examples are synthetic. Do not add private prompts, real assistant logs,
connector exports, credentials, or personal data.

## Scope

These are structural boundary checks, not a truth engine or runtime monitor.
They prove that supplied outputs and transition receipts have an internally
consistent shape. Human review and integration tests still decide whether the
answer, event record, and persisted state are actually correct.

## Quality Checks

```sh
python3 context_boundary_check.py --self-test
python3 context_boundary_check.py examples/context_outputs.jsonl
python3 transition_receipt_check.py --self-test
python3 transition_receipt_check.py examples/transition_receipts.jsonl
python3 -m py_compile context_boundary_check.py transition_receipt_check.py
```
