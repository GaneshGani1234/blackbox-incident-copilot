# Blackbox: the on-call teammate that never forgets an outage

An incident-response copilot built on **Hindsight** (Vectorize) memory. When an incident starts, Blackbox recalls the closest past incidents, explains its diagnosis with evidence, and learns from every postmortem. Built for the *AI Agents That Learn Using Hindsight* hackathon.

**Live demo:** _add your URL_  |  **Demo video:** _add your link_  |  **Article:** _add your link_

## The problem

Incident knowledge lives in postmortems nobody reads at 3 am and in the heads of engineers who leave. A stateless assistant starts from zero every time, so teams re-debug problems they already solved.

## What it does

1. **Recall:** a new incident triggers a Hindsight recall of similar past incidents (symptoms, error signatures, root causes, fixes, owners).
2. **Diagnose with evidence:** the model answers using those incidents, cites only ids memory returned, and says "no real match" when nothing fits.
3. **Show the memory:** the UI puts the recalled incidents and a timeline next to the answer, and highlights which memory supports which claim.
4. **Learn:** when an incident is resolved, the postmortem is retained, so the next incident starts smarter.
5. **Discover patterns:** Hindsight consolidates memories into a mental model of recurring failure patterns that nobody wrote by hand.

## How Hindsight memory is used

| Hindsight operation | Where | Purpose |
|---|---|---|
| `retain` | `app/memory.py` | Store each postmortem, including failed diagnostic steps, with timestamp, tags and idempotent document ids |
| `recall` | `app/memory.py`, `app/agent.py` | Find similar past incidents; results and scores are shown in the UI |
| Mental model + `reflect` | `app/memory.py` | Synthesise recurring failure patterns across incidents |

Full explanation: [docs/03_HINDSIGHT_MEMORY_DESIGN.md](docs/03_HINDSIGHT_MEMORY_DESIGN.md).

## Quick start (about 5 minutes)

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                                  # add your Hindsight and Groq keys
python -m scripts.smoke_test                          # proves keys and the memory round trip
python -m scripts.seed_memory --reset                 # loads 18 synthetic incidents
uvicorn app.main:app --reload --port 8000             # open http://localhost:8000
```

Get a Hindsight Cloud key at https://ui.hindsight.vectorize.io (Connect page). The Cloud API endpoint is `https://api.hindsight.vectorize.io`. Self-hosting with Docker is also supported at `http://localhost:8888`.

Full pin-to-pin instructions: [docs/01_STEP_BY_STEP_GUIDE.md](docs/01_STEP_BY_STEP_GUIDE.md).

## Try the story

1. Switch to **Without memory**, analyze scenario 1. Generic advice, low confidence.
2. Switch to **With memory**, analyze it again. Matches, exact fix, owner, and the timeline lights up.
3. Analyze scenario 3 (never seen before). It refuses to force a match.
4. Save a postmortem, then analyze scenario 4 (same pattern, different service).
5. Read the patterns panel and run `python -m scripts.eval_learning_curve` for the learning curve.

## Evaluation

`scripts/eval_learning_curve.py` measures whether the right failure family appears in the top 3 recalled incidents for six held-out incidents as memory grows. Results are saved to `docs/eval_results.json`.

| Incidents remembered | Correct family in top 3 |
|---|---|
| _run the script and paste your numbers_ | |

## Project structure

```
app/            FastAPI server, agent loop, memory layer, LLM wrapper, UI (app/static)
data/           Dataset generator and generated incidents, demo scenarios, eval set
scripts/        smoke_test, seed_memory, eval_learning_curve
tests/          Offline tests (local memory + mock LLM)
docs/           Step-by-step guide, architecture, memory design, demo script, content, checklist
```

## Tests

```bash
pytest -q
```

Tests run offline with `MEMORY_BACKEND=local` and `LLM_MODE=mock`. The local backend is for development only. Demo and submission use Hindsight.

## Limitations

The incident data is synthetic (modelled on real failure families). Blackbox recommends actions and does not execute them. Mental model consolidation is asynchronous, so patterns can lag the latest retain by a minute.

## Stack

Python, FastAPI, Hindsight (retain / recall / reflect / mental models), Groq (`openai/gpt-oss-120b`, fallback `qwen/qwen3-32b`), vanilla JS frontend.

## Docs

- [Step-by-step guide](docs/01_STEP_BY_STEP_GUIDE.md)
- [Architecture](docs/02_ARCHITECTURE.md)
- [Hindsight memory design](docs/03_HINDSIGHT_MEMORY_DESIGN.md)
- [Demo script](docs/04_DEMO_SCRIPT.md)
- [Content deliverables](docs/05_CONTENT_DELIVERABLES.md)
- [Submission checklist](docs/06_SUBMISSION_CHECKLIST.md)
