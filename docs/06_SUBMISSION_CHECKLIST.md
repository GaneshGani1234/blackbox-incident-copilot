# Submission checklist

Print this or paste it into your team chat. Tick items as they are done.

## Required by the hackathon rules

- [ ] **GitHub repository**, public, with clean and documented code
- [ ] **Demo video** showing the agent in action (see `04_DEMO_SCRIPT.md`)
- [ ] **Live project demo** ready for judges (deployed URL plus a backup video)
- [ ] **Content deliverables** from every team member: article, social media post and video (see `05_CONTENT_DELIVERABLES.md`, checked against the official Content Guide)
- [ ] **Explanation of how Hindsight memory is used** (`03_HINDSIGHT_MEMORY_DESIGN.md`, linked from the README)
- [ ] Project **clearly demonstrates Hindsight memory** (memory panel, timeline, patterns, learning curve)
- [ ] Built **using Hindsight** (`MEMORY_BACKEND=hindsight` in the demo)

## Repository quality (Technical Implementation, 20 percent)

- [ ] README explains the problem, the demo and how to run it in under 5 minutes
- [ ] `.env.example` present, `.env` absent from the repo and from git history
- [ ] `pytest -q` passes
- [ ] No leftover debug code, no commented-out blocks
- [ ] Architecture and memory design docs in `docs/`
- [ ] `docs/eval_results.json` committed with real numbers

## Demo quality (Innovation, UX, Impact)

- [ ] First 60 seconds tell the problem, the agent and the payoff
- [ ] Cold versus warm comparison shown on the same incident
- [ ] Novel incident handled honestly (no forced match)
- [ ] Save postmortem then a follow-up incident shows learning
- [ ] Patterns panel shown last, after consolidation has had time
- [ ] Header shows `(hindsight)`, not `(local)`, in every recording

## Final 60 minutes

- [ ] Code freeze (fixes only)
- [ ] Reseed the demo bank: `python -m scripts.seed_memory --reset`
- [ ] Open the deployed URL to warm it
- [ ] Play the backup video once to confirm it works offline
- [ ] All links tested in a private browser window
- [ ] Rotate any key that was ever pasted somewhere public

## Judging map

| Criterion | Weight | Where Blackbox shows it |
|---|---|---|
| Innovation | 30% | Institutional memory for incidents, failed steps remembered, honest no-match, generalisation across services |
| Use of Hindsight memory | 25% | Retain, recall, reflect and a mental model, all visible in the UI; learning curve; memory trace in every response |
| Technical implementation | 20% | Async architecture, retry and fallback, hallucinated-id guardrail, idempotent retains, tests, evaluation script |
| User experience | 15% | Two-panel layout, cold versus warm switch, timeline, hover linking between claims and memories |
| Real-world impact | 10% | Every engineering team has repeat incidents; path to Slack and incident-tool integration |

## Team roles for the last day

| Person | Owns |
|---|---|
| Memory and backend | Keeps the server healthy, watches Groq limits, handles the reseed |
| Frontend and demo | Drives the live demo, has the backup video ready |
| Data and eval | Owns the numbers in the article, video and README |
| Story and content | Publishes posts, checks links, submits the form |
