# Architecture

## What Blackbox does

An incident copilot for on-call engineers. When an incident starts it **recalls** similar past incidents from Hindsight, asks an LLM to diagnose using that evidence, and shows the engineer exactly which memories were used. When the incident is solved, the postmortem is **retained** back into memory, so the next incident starts smarter. In the background Hindsight consolidates memories into a **mental model** of recurring failure patterns.

## Components

```
Browser UI (app/static/index.html)
   |  REST
   v
FastAPI server (app/main.py)
   |
   +--> Agent loop (app/agent.py)
   |       1. build query from the incident
   |       2. RECALL from memory
   |       3. prompt the LLM with recalled incidents as evidence
   |       4. guardrail: remove any cited incident id memory did not return
   |       5. return diagnosis + memory_trace
   |
   +--> Memory layer (app/memory.py)
   |       HindsightMemory  -> Hindsight Cloud or self-hosted (retain / recall / reflect / mental model)
   |       LocalMemory      -> offline fallback for tests only
   |
   +--> LLM wrapper (app/llm.py)
           Groq, OpenAI compatible. JSON in plain text, tolerant parsing, retry, second model fallback.
```

## Request flows

**Analyze** (`POST /api/analyze`)
1. UI sends the incident and whether memory is on.
2. If on, the agent calls `recall` with a query built from service, title, symptoms and error signature. Results are grouped by incident (`document_id`), scored and trimmed.
3. The LLM receives the incident plus the recalled incident text and a strict system prompt (cite only ids you were given; say so when nothing matches).
4. The guardrail removes unverified ids and lowers confidence if that leaves no matches.
5. The response contains `diagnosis`, `memory_trace` (query, hits, scores, recall latency) and `meta` (model, timing). The UI draws the answer on the left and the memory trace and timeline on the right.

**Resolve** (`POST /api/resolve`): the engineer confirms root cause and fix. The agent converts it to a postmortem narrative and calls `retain` with the incident id as `document_id`, the incident time as `timestamp`, and tags for service, severity and deploy relation.

**Patterns** (`GET /api/patterns`, `POST /api/patterns/refresh`): returns the content of the "Recurring failure patterns" mental model. If the model has no content yet it falls back to a `reflect` call.

**Seed** (`POST /api/seed`): retains the 18 synthetic incidents in a background task. Status polling drives the progress bar.

## Design decisions worth explaining to judges

| Decision | Reason |
|---|---|
| No function calling | The brief warns about function calling errors. Plain JSON with tolerant parsing plus a fallback model is more reliable. |
| Memory trace returned on every call | Memory is 25 percent of the score. The UI must prove memory did the work, so the API exposes it. |
| Hallucinated id guardrail | An on-call engineer acting on a fake incident reference is worse than no answer. |
| "No real match" is a first-class outcome | Forcing matches is how memory systems lose trust. |
| The synthetic `cluster` label is never retained | Otherwise the eval is trivial. Memory has to find the pattern from the text. |
| Incident id as `document_id` | Retaining the same incident twice updates it instead of duplicating it. |
| Dedicated bank per environment | Isolation between developers, the public demo and the eval run. |
| Local fallback backend | Lets the team develop and run CI without credits. It is labelled everywhere and must never be used in the demo. |

## Data model of a retained incident

Retained as one natural-language postmortem per incident. Hindsight extracts facts, entities and time from it.

```
Incident INC-0012 (SEV1) on checkout-service, occurred Friday 2026-01-16 17:12 UTC.
Title: ...
Symptoms: ...
Error signature: ...
Diagnostic steps tried:
  1. Checked CPU -> Normal, ruled out resource starvation
  ...
Confirmed root cause: ...
Fix that worked: ...
Resolved by / owner: priya.nair.
Time to resolve: 47 minutes.
Deploy context: Deploy at 16:45 on a Friday.
```

Failed diagnostic steps are stored on purpose: knowing what did **not** work is memory the team normally loses.

## Configuration (environment variables)

| Variable | Purpose |
|---|---|
| `HINDSIGHT_BASE_URL`, `HINDSIGHT_API_KEY`, `HINDSIGHT_BANK_ID` | Where memory lives and which bank |
| `MEMORY_BACKEND` | `hindsight` (real) or `local` (dev only) |
| `GROQ_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_FALLBACK_MODEL` | The LLM |
| `LLM_MODE` | `groq` or `mock` (offline, tests) |
| `ALLOW_RESET` | `false` on the public demo |

## Roadmap (ideas, not built)

Pick **one** only if the core is finished and rehearsed.

1. **Feedback loop.** Thumbs up or down on each suggested step, retained as memory ("step X did not help on incident Y"). Strong learning story. Add a `POST /api/feedback` endpoint that calls `retain` with a short note and the incident id.
2. **Slack intake.** A Slack app posts new alerts to `/api/analyze` and replies in thread with the diagnosis and matched incident links.
3. **Two teams, two banks.** Payments team and platform team with separate `bank_id`s. Show that the payments agent does not leak platform incidents. Good enterprise angle.
4. **Real alert ingestion.** Accept a PagerDuty style JSON payload and map it to the incident schema.
5. **Runbook links.** Store a runbook URL in incident metadata and show it in the answer.
