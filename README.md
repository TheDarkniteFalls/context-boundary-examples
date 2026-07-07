# Context Boundary Examples

A tiny, synthetic checker for assistant outputs that should stay inside supplied
context.

The demo does not call a model. It reads sample outputs, checks whether the
answer/refusal mode matches the available evidence, and verifies citations
against the supplied source IDs. This keeps the example deterministic and
public-safe.

## Why It Exists

AI assistants should not answer from memory when a workflow asks them to use
only supplied evidence. This repo shows a small boundary: answer with citations
when required evidence is present, and refuse when it is missing.

## Run

```sh
python3 context_boundary_check.py examples/context_outputs.jsonl
python3 context_boundary_check.py --self-test
```

Expected result:

```text
PASS valid_grounded_answer
PASS valid_missing_evidence_refusal
PASS invalid_answers_without_evidence
PASS invalid_missing_required_citation
PASS invalid_unknown_citation
```

## Output Contract

Each sample `model_output` must be JSON with:

- `answer`: non-empty text.
- `refusal`: `true` when supplied evidence is missing, otherwise `false`.
- `citations`: source IDs from the current case.

Each fixture case declares whether evidence is available and which citations are
required. The checker treats mismatches as boundary failures.

## How These Fit Together

This repo is one piece of a small public toolkit:

- [Public Repo Safety Kit](https://github.com/TheDarkniteFalls/public-repo-safety-kit)
  checks a public-candidate repo before publishing.
- [EvidenceGate](https://github.com/TheDarkniteFalls/evidencegate) records the
  evidence and checks behind an AI-assisted change.
- [Local Model Reliability Example](https://github.com/TheDarkniteFalls/local-model-reliability-example)
  validates structured model output before trusting it.
- Context Boundary Examples checks whether an answer stays inside supplied
  evidence.
- [Green-Spine QA Pattern](https://github.com/TheDarkniteFalls/green-spine-qa-pattern)
  bundles the important path behind one repeatable command.

Together they show a practical pattern: publish safely, leave a reviewable
receipt, validate model output, keep answers grounded in supplied context, and
keep the important path healthy.

## Public Data Notice

All examples are synthetic. Do not add private prompts, real assistant logs,
connector exports, credentials, or personal data.

## Scope

This is a structural boundary check, not a truth engine. It proves the output
uses the expected answer/refusal and citation shape. Human review still decides
whether the answer is actually correct.

## Quality Checks

```sh
python3 context_boundary_check.py --self-test
python3 context_boundary_check.py examples/context_outputs.jsonl
python3 -m py_compile context_boundary_check.py
```
