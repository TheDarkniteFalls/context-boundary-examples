# Transition Receipt

A transition receipt is a small record that answers one question:

> Is the state proposed for the next model call still authoritative after
> everything that changed since the previous call?

This matters when user input, tool results, external state, or context
compaction can arrive while an agent run is still active. A transcript can be
well-formed while already being stale.

## Receipt Shape

The synthetic examples in this repository use these fields:

- `transition_id`: stable identity for the decision.
- `last_model_state`: the state, version, and content digest used by the
  previous model call.
- `changes`: events observed since that call.
- `current_state`: the latest visible and durable versions and content digests.
- `next_model_state`: the exact state proposed for continuation, or `null`.
- `decision`: `allow`, `repair`, or `block`.
- `decision_reason`: a short explanation of the decision.
- `evidence`: identifiers referenced by the states and changes.

Each change records:

- `id`, an ordered `sequence`, and `kind`;
- `provenance`;
- `status`: `pending`, `applied`, or `superseded`;
- `evidence_ref`;
- `applied_to_version`, when applied;
- `superseded_by`, when deliberately replaced by another recorded change.

## Decisions

- `allow`: every recorded change is reconciled and the next call will use the
  current visible and durable state.
- `repair`: continuation must wait while state is reconciled or made durable.
- `block`: continuation is unsafe without a new decision or external action.

## Invariants

The checker enforces a deliberately small boundary:

1. Every state and change has evidence identity; states also carry content
   digests so equal version numbers cannot conceal different content.
2. Every change has explicit order, provenance, and status.
3. Applied changes cannot move state backwards, and a superseding change must
   occur later than the change it replaces.
4. New user input must be applied; it cannot be silently superseded.
5. `allow` is invalid while any change remains pending.
6. `allow` requires visible and durable versions and content digests to agree.
7. The proposed next state must be the current state and cannot roll back to an
   older version.
8. `repair` and `block` must identify a real pending change or state mismatch.

This first version is conservative: every recorded change is relevant to the
transition. A context-changing compaction is recorded as `kind: "compaction"`
and must be `applied` before the next model request can be allowed.

## Example

```json
{
  "transition_id": "transition-002",
  "last_model_state": {
    "id": "state-4",
    "version": 4,
    "digest": "sha256:state-4",
    "evidence_ref": "state:4"
  },
  "changes": [
    {
      "id": "event-user-2",
      "sequence": 1,
      "kind": "user_input",
      "provenance": "channel:user",
      "status": "applied",
      "evidence_ref": "event:user-2",
      "applied_to_version": 5,
      "superseded_by": null
    }
  ],
  "current_state": {
    "visible_version": 5,
    "durable_version": 5,
    "visible_digest": "sha256:state-5",
    "durable_digest": "sha256:state-5",
    "evidence_ref": "state:5"
  },
  "next_model_state": {
    "id": "state-5",
    "version": 5,
    "digest": "sha256:state-5",
    "evidence_ref": "state:5"
  },
  "decision": "allow",
  "decision_reason": "The new user input is included in durable state 5.",
  "evidence": ["state:4", "event:user-2", "state:5"]
}
```

## What A Pass Establishes

A pass establishes that the supplied receipt is structurally complete and its
decision is consistent with the recorded versions, content digests, changes,
provenance, and evidence identifiers.

## What It Does Not Establish

The checker does not observe a real runtime. It cannot prove that every event
was captured, that evidence identifiers point to truthful records, that a tool
side effect was idempotent, or that persisted state can actually be restored.
Those claims require runtime instrumentation and integration tests.
