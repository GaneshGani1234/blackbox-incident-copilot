# Demo script

Target length: **3 minutes** for the video, **5 minutes** live (with questions). Judges decide within 60 seconds, so the first minute carries the story.

## Setup before every run (do this, do not skip)

1. `python -m scripts.seed_memory --reset` on your demo bank, then wait 60 to 90 seconds.
2. Open the app, confirm the header says `(hindsight)` and shows a memory count above 0.
3. Set the switch to **Without memory**. Select scenario 1.
4. Browser zoom 110 to 125 percent, notifications off, one tab only.
5. Have scenario 4 and your learning curve screenshot ready.

## Beat sheet (3 minutes)

| Time | On screen | Say |
|---|---|---|
| 0:00 to 0:20 | Title, then the app | "It is 4:52 on a Friday. Checkout is failing. Every engineer has lived this: you are re-debugging something your team already solved months ago. This is Blackbox, an incident copilot with memory." |
| 0:20 to 0:50 | **Without memory**, scenario 1, Analyze | "First, Blackbox with no memory. Reasonable advice, low confidence, no owner, no history. It is a new hire on day one." |
| 0:50 to 1:10 | Click **Load 6 months of history** (or show it already loaded) | "Now we give it the team's last six months of postmortems through Hindsight. Each incident is retained as memory." Point at the timeline filling with dots. |
| 1:10 to 1:55 | **With memory**, same scenario, Analyze | "Same incident. Watch the right side. Before the model writes anything, Hindsight recalls the closest past incidents: the same pool exhaustion after a Friday deploy, again and again. It gives the exact fix that worked, who fixed it, and what not to waste time on." Hover a chip to highlight the memory card. Point at the timeline lighting up. Point at the "Without memory it said" strip. |
| 1:55 to 2:15 | Scenario 3 (never seen before) | "It is also honest. For an incident it has never seen, it says nothing matches and does not invent an answer." |
| 2:15 to 2:40 | Save the postmortem, then run scenario 4 | "The engineer closes the incident and Blackbox retains the postmortem. A week later a different service shows the same pattern, and it connects the dots, including to the incident we just saved." |
| 2:40 to 3:00 | Patterns panel, then learning curve screenshot | "Nobody wrote these rules. Hindsight consolidated them: pool exhaustion follows Friday deploys. And here is the learning curve from our evaluation: [say your real numbers, for example: with no memory it finds the right past incident 0 out of 6 times, with all 18 incidents remembered it finds it N out of 6]. Every incident makes it smarter." |

## Closing line

"Blackbox is the senior engineer who never leaves the company."

## Live demo extras (5 minutes)

- After the beat sheet, open the memory panel and explain `retain`, `recall` and the mental model in one sentence each.
- Show `docs/03_HINDSIGHT_MEMORY_DESIGN.md` briefly.
- Have the backup video ready to play if the network fails.

## Likely judge questions and short answers

| Question | Answer |
|---|---|
| Why not just RAG over postmortems? | Hindsight extracts facts, entities and time, and consolidates them into mental models. Plain RAG cannot tell you the pattern that Friday deploys cause pool exhaustion. That pattern appeared without anyone writing it. |
| Is the data real? | Synthetic but modelled on real failure families (connection pool leaks, cache stampede, Kafka poison messages, memory leaks, expired certificates). The mechanism is what we demonstrate. |
| What if memory returns a wrong match? | The model must cite only returned incident ids, unverified ids are stripped, and "no match" is a valid answer with low confidence. |
| Does it act on production? | No. It advises. A human confirms the fix, which is also how new memory is created. |
| How would this scale? | Banks per team give isolation. Postmortems are the natural unit of memory. Ingestion can come from an incident tool or Slack. |
| What happens when Groq is down? | Retry, second model, then an answer built from memory alone, labelled as such. |
| Why is this better than a chatbot? | It is proactive at the moment of pain, it cites evidence, it learns from outcomes, and the memory is inspectable. |

## Things that go wrong on stage

- **First request slow:** you did not warm the deployed app. Open it five minutes early.
- **Answer says `fallback-heuristic`:** Groq rate limit. Wait 10 seconds and rerun, or switch to the backup video.
- **Patterns panel empty:** consolidation has not finished. Do not open it first. Show it last, after other steps have given it time.
- **Someone asks you to try their own incident:** great. Type it in. The scenario form is editable.
