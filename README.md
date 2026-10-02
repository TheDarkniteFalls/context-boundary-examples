# Context Boundary Examples

Check two common problems: an answer cites information it was not given, or an
agent continues from a version of the conversation that is no longer current.
These small Python examples use synthetic records, so you can try the checks
without calling a model or a network service.

The first checker compares an answer’s citations and refusal mode with the
supplied evidence. The second checks a record of changes between model calls,
including new user input, tool results and saved state. They check the records
you provide; they do not monitor a running agent.

## Try The Examples

You need Python 3. Run these commands from the repository root:

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
PASS valid_allow_matching_fingerprints
PASS invalid_allow_equal_version_fingerprint_mismatch
PASS invalid_allow_partial_fingerprints
PASS valid_repair_equal_version_fingerprint_mismatch
```

`PASS invalid_unknown_citation` means the checker correctly rejected that
invalid example. It does not mean the answer was accepted. Likewise, an
expected `repair` or `block` decision can pass the transition check: stopping
can be the correct result.

<!-- toolkit-trust-card:placement -->

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

## What The Answer Check Requires

Each sample `model_output` must be JSON with:

- `answer`: non-empty text.
- `refusal`: `true` when supplied evidence is missing, otherwise `false`.
- `citations`: source IDs from the current case.

Each fixture case declares whether evidence is available and which citations are
required. The checker treats mismatches as boundary failures.

## Check The State Before Continuing

[`TRANSITION_RECEIPT.md`](TRANSITION_RECEIPT.md) defines a compact receipt for
the boundary between one model call and the next. A receipt is a record of
what changed, where each change came from, and whether the state visible to
the agent agrees with the state saved for later use. It also records the last
model state, the proposed next state, and an `allow`, `repair`, or `block` decision.

The checker rejects stale continuation, unresolved changes, missing provenance,
out-of-order events, silent loss of user input, and visible/durable mismatches
presented as safe. Optional producer-supplied content fingerprints can detect
divergent content behind equal versions. The checker accepts honest repair and
block outcomes.

The [OpenAI Agents Python #2671 application note](applications/openai-agents-python-2671.md)
maps this contract to a lifecycle problem at its dated source snapshot. It is
a historical application note, not evidence of current SDK behavior or an SDK
implementation.

## Related Tools

For other parts of an AI-assisted workflow, these examples cover related checks:

- [Public Repo Safety Kit](https://github.com/TheDarkniteFalls/public-repo-safety-kit)
  checks a public-candidate repo before publishing.
- [EvidenceGate](https://github.com/TheDarkniteFalls/evidencegate) records the
  evidence and checks behind an AI-assisted change.
- [Local Model Reliability Example](https://github.com/TheDarkniteFalls/local-model-reliability-example)
  validates structured model output and protected-path boundaries before
  trusting it.
- [Green-Spine QA Pattern](https://github.com/TheDarkniteFalls/green-spine-qa-pattern)
  puts checks for an important workflow behind one repeatable command.
- [Codex Project Instructions Starter](https://github.com/TheDarkniteFalls/codex-project-instructions-starter)
  gives coding agents clear project rules before they work.

## Public Data Notice

All examples are synthetic. Do not add private prompts, real assistant logs,
connector exports, credentials, or personal data.

## What These Examples Show

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
