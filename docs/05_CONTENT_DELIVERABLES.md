# Content deliverables (article, social post, video)

The hackathon rules say **every team member** must complete an article, a social media post and a video "as described in the content guide".

**Important:** the official Content Guide was not part of the document this kit was built from. Open it first and check length, platform, hashtags, tagging and deadlines. Treat everything below as an editable first draft, and personalise it. Each teammate should write from their own experience, because identical posts from one team read as copy paste.

Fill the `[brackets]` with your real numbers before publishing. Do not publish a number you did not measure.

---

## 1. Article draft (about 700 words)

**Title options**
- I built an AI on-call teammate that never forgets an outage
- What happens when your incident bot has memory (I measured it)
- Stateless chatbots lose incidents. Here is what changed when I gave one Hindsight memory

**Structure**

**Hook (3 lines).** It is Friday, 4:52 pm. Checkout latency is climbing. Somebody says "hasn't this happened before?" Nobody remembers. Forty minutes later the fix is the same one from March.

**The problem.** Incident knowledge lives in postmortems nobody reads at 3 am and in the heads of engineers who eventually leave. Generic AI assistants do not help because they start from zero every time.

**The idea.** Blackbox is an incident copilot with memory built on Hindsight by Vectorize. It does three things:
1. Recalls the closest past incidents when a new one starts.
2. Explains its diagnosis with evidence and shows which memories it used.
3. Learns from every resolved incident.

**How Hindsight is used** (one short paragraph each)
- Retain: every postmortem, including failed diagnostic steps.
- Recall: the query is built from the live incident, and results are shown next to the answer.
- Reflect and mental models: Hindsight consolidated the incidents into a "recurring failure patterns" model. Nobody wrote the rule "[insert a real pattern your app found]".

**The result.** Include your learning curve table and screenshots: the same incident without memory and with memory, and the timeline lighting up.
> With no memory, the correct past incident appeared in the top three results [0] out of 6 times. After [18] incidents, [N] out of 6.

**What surprised me.** Pick real ones, for example: failed steps were as valuable as successful ones; "no match" answers built more trust than confident guesses; retain quality depended on how the postmortem was written.

**What I would do next.** Feedback loop on suggested steps, Slack intake, one memory bank per team.

**Call to action.** Link to the repo and the live demo. Thank Vectorize and the hackathon organisers.

**Screenshots to include:** cold answer, warm answer, timeline with lit dots, patterns panel, learning curve table, architecture diagram.

---

## 2. Social post draft (LinkedIn style, about 150 words)

> Every on-call engineer has lived this: prod is down, and you are re-debugging something your team already solved months ago.
>
> This weekend I built **Blackbox**, an incident copilot with memory, on Hindsight by Vectorize.
>
> What it does:
> - recalls similar past incidents the moment a new one starts
> - shows exactly which memories informed its answer
> - retains every resolved postmortem so it gets smarter
>
> Result: [N] out of 6 held-out incidents matched to the right failure family after remembering [18] incidents, versus [0] with no memory.
>
> The part I like most: nobody wrote the rule that "[your real pattern]". Hindsight found it.
>
> Demo and code: [link]
> Built at [hackathon name]. Thanks to @Vectorize and the organisers.
>
> #AIAgents #Hindsight #SRE #DevOps [plus hashtags required by the content guide]

Attach: 30 to 45 second screen recording or one strong screenshot (timeline lit up).

**Short variant (X or Twitter style):**
> My incident bot forgot everything between outages. So I gave it Hindsight memory. Now it says "this is INC-0012 again, same fix, ask Priya." Demo: [link] #AIAgents #Hindsight

---

## 3. Video (project demo and personal video)

Two videos may be required (a project demo and a personal content video). Check the guide.

**Project demo video (under 3 minutes):** follow `04_DEMO_SCRIPT.md`.

**Personal or content video (about 60 to 90 seconds), speaker to camera or voiceover**

| Time | Content |
|---|---|
| 0:00 to 0:10 | Hook: "Your AI assistant forgets every outage. Mine does not." |
| 0:10 to 0:30 | The problem in your own words, ideally a real story of re-solving something. |
| 0:30 to 0:55 | Screen capture of the same incident without and with memory. |
| 0:55 to 1:15 | One thing you learned about building agents with memory. |
| 1:15 to 1:30 | Where to find the code and demo. |

Recording tips: record voiceover separately for clean audio, add captions (most people watch muted), keep cuts every few seconds, end on the URL.

---

## 4. Personalisation checklist for each teammate

- [ ] My article names **my** part of the build and one thing I personally learned.
- [ ] My post is in my own words and tags what the content guide asks for.
- [ ] Numbers in my article and post match `docs/eval_results.json`.
- [ ] Links to the repo and live demo work when opened in a private browser window.
- [ ] I checked every requirement in the official Content Guide.
