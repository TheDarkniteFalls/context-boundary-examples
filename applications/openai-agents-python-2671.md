# OpenAI Agents Python #2671: Residual-Gap Note

Status: public application note; bounded proposal posted upstream on 2026-07-17.

Audit date: 2026-07-17. Source snapshot:
[`965335aba6f6c71500e0b8cdb4e9e495f5801d4d`](https://github.com/openai/openai-agents-python/tree/965335aba6f6c71500e0b8cdb4e9e495f5801d4d).

## Finding

[Issue #2671](https://github.com/openai/openai-agents-python/issues/2671)
remains open and the use case remains valid, but the implementation baseline has
moved since the issue was filed. The SDK now covers part of the requested
lifecycle. A useful contribution should target the remaining boundary instead
of proposing a second cancellation system.

| Needed capability | Current evidence | Assessment |
| --- | --- | --- |
| Finish the active turn and stop before the next one | [`cancel(mode="after_turn")`](https://github.com/openai/openai-agents-python/blob/965335aba6f6c71500e0b8cdb4e9e495f5801d4d/src/agents/result.py#L648-L692) and its [streaming guide](https://github.com/openai/openai-agents-python/blob/965335aba6f6c71500e0b8cdb4e9e495f5801d4d/docs/streaming.md#L60-L70) | Supported for streamed runs |
| Capture a `RunState` snapshot | [`RunResultStreaming.to_state()`](https://github.com/openai/openai-agents-python/blob/965335aba6f6c71500e0b8cdb4e9e495f5801d4d/src/agents/result.py#L889-L934) | Available; the docs emphasize approval interruptions, and the audited soft-cancel tests do not combine `after_turn`, `to_state()`, and resume |
| Compact session history before later requests | [`OpenAIResponsesCompactionSession`](https://github.com/openai/openai-agents-python/blob/965335aba6f6c71500e0b8cdb4e9e495f5801d4d/src/agents/memory/openai_responses_compaction_session.py) | Supported as a session capability |
| Add late user input to a stopped `RunState` before resuming | The audited class exposes [`approve` and `reject`](https://github.com/openai/openai-agents-python/blob/965335aba6f6c71500e0b8cdb4e9e495f5801d4d/src/agents/run_state.py#L336-L370) for interruption decisions but no public add-input operation | Residual gap |
| Define guardrail behavior for injected input | Resumed runs currently skip entry input guardrails in the [streaming loop](https://github.com/openai/openai-agents-python/blob/965335aba6f6c71500e0b8cdb4e9e495f5801d4d/src/agents/run_internal/run_loop.py#L686-L694) | Semantics needed before an injection API |

The existing manual continuation path is useful, but it starts a follow-up from
normalized input or a session. It does not provide a public operation that says,
"this late input belongs inside the paused run state before its next model
call."

## Smallest Upstream Contract

Define behavior with conformance tests before choosing a large lifecycle API.
The capability under test should let a host:

1. Request a graceful stop after the active model/tool turn.
2. Drain the stream and capture a resumable state.
3. Apply an ordered batch of late changes, including new user input, before the
   next model request.
4. Complete any required compaction before that request.
5. Resume without repeating an already completed tool call or losing its
   output.
6. Re-run the appropriate input guardrails for newly injected user content.
7. Preserve or explicitly link trace identity across the pause.

The contract should make the host choose one conversation-state owner. It must
not silently combine local replay, an SDK session, and server-managed
continuation.

## Proposed Conformance Cases

| Case | Required observation |
| --- | --- |
| Tool result, then late user input | Both appear once in the next model input, in recorded order |
| Late input fails a guardrail | Resume stops before a model request |
| Compaction requested at the boundary | Compaction finishes before the succeeding request |
| Tool side effect is unresolved | Host can block rather than resume from an assumed result |
| Serialization between stop and resume | Late-change order and provenance survive round-trip |
| Server-managed continuation | No acknowledged item is replayed and no late item is dropped |

The local transition-receipt fixtures
[`valid_tool_result_then_late_user_input`](../examples/transition_receipts.jsonl)
and `invalid_allow_pending_late_user_input` are deterministic, SDK-independent
examples of the first boundary. They do not prove the SDK behavior.

## API Shape Deliberately Left Open

Possible implementations include a method on `RunState`, a runner callback at
the post-tool/pre-model boundary, or a higher-level active-run object. This note
does not select among them. The conformance cases are the portable contribution;
the maintainers can choose the smallest API consistent with the SDK's state,
session, tracing, and guardrail models.

## Posted Upstream Comment

The maintainer question is live at
[issuecomment-5002979430](https://github.com/openai/openai-agents-python/issues/2671#issuecomment-5002979430):

It records the audited source snapshot and asks whether a test-first pull
request would be useful for four behaviors: ordered tool result plus late user
input, compaction before resume, guardrail failure before the next model call,
and no replay of completed tool calls. It deliberately leaves the public API
shape open.

No upstream implementation or pull request should begin unless maintainers
confirm that this contribution shape is useful or redirect it to a smaller
agreed slice.
