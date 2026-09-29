# How Blackbox uses Hindsight memory

This is the written explanation required by the hackathon submission rules. It is also the document to point judges to for the 25 percent "Use of Hindsight Memory" criterion.

## The one-sentence version

Blackbox turns every incident postmortem into Hindsight memory, recalls the most relevant past incidents the moment a new one starts, and lets Hindsight consolidate those memories into a mental model of recurring failure patterns, so the agent measurably gets better with every incident.

## Without memory versus with memory

| | Without memory | With memory |
|---|---|---|
| Diagnosis | Generic checklist | Names the closest past incidents and their confirmed root cause |
| Fix | "Check logs, consider rollback" | The exact fix that worked before |
| Dead ends | Repeats them | Tells the engineer what already failed |
| Owner | None | The person who fixed the closest past incident |
| Confidence | Low | High when several past incidents agree, low when none match |
| New incident type | Same generic answer | Says clearly that nothing similar exists |

## The three Hindsight operations, and where each one appears

### Retain: `HindsightMemory.retain_incident` in `app/memory.py`
- Each incident becomes one postmortem narrative (symptoms, error signature, diagnostic steps including failed ones, root cause, fix, owner, time to resolve, deploy context).
- `document_id` is the incident id, so retaining the same incident again updates it instead of duplicating it.
- `timestamp` is when the incident happened, so Hindsight can reason about time ("what happened after Friday deploys").
- `tags` carry service, severity and deploy relation. `metadata` carries the same for filtering.
- Two moments call retain: bulk loading the history, and the live "Save postmortem to memory" action after an incident is solved. The second is the learning moment in the demo.

### Recall: `HindsightMemory.recall` in `app/memory.py`, used by `agent.analyze`
- Query is built from the new incident (service, title, symptoms, error signature).
- Recall runs with `include_chunks=True` so the agent receives the original postmortem text, not just extracted facts.
- Results are grouped by incident, scored using Hindsight's final relevance score, and passed to the model as evidence.
- The full trace (query, hits, scores, latency) is returned to the UI, which shows it beside the answer and lights up the matching past incidents on a timeline.

### Reflect and mental models: `patterns()` and `refresh_patterns()`
- A mental model named "Recurring failure patterns" is created on bank setup with a source query asking for recurring root causes, affected services, risky days or deploy types, and the most reliable fixes.
- It is created with the option to refresh after consolidation, so it updates as new incidents arrive.
- The UI shows its content under "Patterns Blackbox learned on its own". Nobody wrote these rules. A statement such as "connection pool exhaustion follows Friday deploys" is synthesised from the incidents.
- If the mental model has no content yet, Blackbox falls back to a `reflect` call with the same question.

## Memory bank design

- One bank per team (`HINDSIGHT_BANK_ID`), configured with a mission that describes the role: institutional memory of an SRE team.
- Separate banks for each developer, the public demo and the evaluation run, so experiments never pollute the demo.

## Evidence that memory improves the agent

`scripts/eval_learning_curve.py` feeds incidents to a separate bank in chronological batches and, after each batch, checks whether the top 3 recalled incidents include one from the expected failure family for six held-out incidents. The result is saved to `docs/eval_results.json`.

Paste your real numbers here after running it:

| Incidents remembered | Correct family in top 3 |
|---|---|
| 0 | _fill in_ |
| 2 | _fill in_ |
| 4 | _fill in_ |
| 6 | _fill in_ |
| 12 | _fill in_ |
| 18 | _fill in_ |

The synthetic `cluster` label is never stored in memory, so the retrieval must succeed from the incident text alone.

## Edge cases handled

- **Nothing similar in memory:** the prompt requires the model to say so, set low confidence and avoid forcing a match. The UI states it plainly.
- **Hallucinated incident ids:** any id the model cites that memory did not return is removed and reported.
- **LLM failure or rate limit:** retry, then a second model, then an answer built directly from recalled memory, labelled as such.
- **Duplicate retains:** idempotent through `document_id`.
- **Memory backend down at startup:** the server stays up and `/api/health` and the UI banner explain what is wrong.
- **Reset protection:** `ALLOW_RESET=false` prevents visitors from wiping a public demo bank.

## Honest limitations

- The dataset is synthetic. It is written to be realistic, but the accuracy numbers are a demonstration of the mechanism, not a claim about production performance.
- The agent recommends. It does not execute fixes. A human confirms and closes the loop.
- Consolidation into mental models is asynchronous, so patterns can lag a minute behind the latest retain.
