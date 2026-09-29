# Blackbox: Step-by-Step Guide (pin to pin)

Follow the phases in order. Every phase ends with a **Checkpoint**. Do not move on until the checkpoint passes. If a checkpoint fails, jump to the Troubleshooting table at the bottom.

Total time if nothing goes wrong: about 2 hours to a working demo, then the rest of the hackathon goes into polish, content and submission.

---

## Phase 0: Before you write code (30 minutes)

- [ ] **Agree roles.** Suggested split for 3 to 4 people (adjust to your team):
  - **Memory and backend lead:** owns `app/memory.py`, `app/agent.py`, Hindsight setup.
  - **Data and eval lead:** owns `data/`, the learning curve numbers, realism of the incidents.
  - **Frontend and demo lead:** owns `app/static/index.html`, deployment, the live demo flow.
  - **Story and content lead:** owns the demo video, article, social post (see `05_CONTENT_DELIVERABLES.md`).
- [ ] **Read the official Content Guide** linked in the hackathon brief. It was not part of the document this project was built from, so `05_CONTENT_DELIVERABLES.md` is a template you must check against it.
- [ ] **Create accounts** (all of them, now, not at 3am):
  - Hindsight Cloud: https://ui.hindsight.vectorize.io
  - Groq: https://groq.com (open the console and create an API key)
  - GitHub: create an empty **public** repository named `blackbox-incident-copilot`
  - Join the Hindsight Community Slack from the link on the hackathon page
- [ ] **Install tools:** Python 3.11 or newer (tested on 3.12), Git, and any editor.

**Checkpoint 0:** every teammate can run `python --version` and `git --version`, and you have a Hindsight account, a Groq account and an empty GitHub repo.

---

## Phase 1: Project setup (20 minutes)

1. Unzip the project folder and open a terminal inside it.
2. Create and activate a virtual environment.
   - macOS / Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows PowerShell:
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create your environment file:
   ```bash
   cp .env.example .env        # Windows: copy .env.example .env
   ```
5. Run the tests. They use the offline fallback and need no keys:
   ```bash
   pytest -q
   ```
6. Connect the folder to your GitHub repo and make the first commit. `.gitignore` already excludes `.env`.
   ```bash
   git init
   git add .
   git commit -m "Initial Blackbox scaffold"
   git branch -M main
   git remote add origin https://github.com/<your-username>/blackbox-incident-copilot.git
   git push -u origin main
   ```

**Checkpoint 1:** `pytest -q` prints `4 passed`, and your repo on GitHub shows the code but **not** a `.env` file.

---

## Phase 2: Hindsight Cloud (15 minutes)

1. Register at https://ui.hindsight.vectorize.io.
2. **After registering**, open the **billing** section and enter the promo code `MEMHACK99` to receive the $50 of free credits mentioned in the hackathon brief. It must be added after you register.
3. Open the **Connect** page. It shows your API endpoint and an API key. The Hindsight Cloud endpoint is `https://api.hindsight.vectorize.io`.
4. **Copy the API key immediately.** It is shown only once. If you lose it, create a new one under **Manage API Keys**.
5. Put both into `.env`:
   ```
   HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io
   HINDSIGHT_API_KEY=<the key you copied>
   HINDSIGHT_BANK_ID=checkout-team
   MEMORY_BACKEND=hindsight
   ```
6. Share the key with teammates through a password manager or private message, never in the repo or a public chat. Each teammate should use a different `HINDSIGHT_BANK_ID` (for example `checkout-team-alex`) while developing, so nobody wipes anyone else's memory.

**Checkpoint 2:** `.env` has a real Hindsight key and `MEMORY_BACKEND=hindsight`.

---

## Phase 3: Groq LLM (10 minutes)

1. In the Groq console, create an API key.
2. Add it to `.env`:
   ```
   GROQ_API_KEY=<your key>
   LLM_MODEL=openai/gpt-oss-120b
   LLM_FALLBACK_MODEL=qwen/qwen3-32b
   LLM_MODE=groq
   ```
   These are the two models the hackathon brief recommends. The code already retries and falls back from one to the other, and it does **not** rely on function calling (the brief warns about function calling errors), so a flaky tool call cannot break the demo.

**Checkpoint 3:** `.env` has both keys. Nothing has been tested yet, that is the next phase.

---

## Phase 4: Prove your keys work (10 minutes)

1. Generate the dataset (the JSON files are already included, this just proves the generator runs):
   ```bash
   python data/generate_incidents.py
   ```
   Expected: `Wrote 18 incidents, 4 demo incidents, 6 eval incidents` and a list of clusters.
2. Run the smoke test:
   ```bash
   python -m scripts.smoke_test
   ```
   Expected output (numbers will differ):
   ```
   [PASS] connected to memory and bank ready
   [PASS] retain worked
   [PASS] recall returned 1 hit(s); top = SMOKE-1 score 0.xx
   [PASS] LLM responded via openai/gpt-oss-120b: {'ok': True}
   ```
   The smoke test uses a separate temporary bank and deletes it, so it never touches your demo bank.

**Checkpoint 4:** all four lines say `PASS`. If recall says nothing came back, wait 20 seconds and rerun, because Hindsight processes a retained memory before it becomes searchable.

---

## Phase 5: Run the app and load history (15 minutes)

1. Start the server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
2. Open http://localhost:8000. You should see the Blackbox header, a memory switch, an empty timeline and the message "No incidents remembered yet".
3. Select **Load 6 months of history**. A progress bar runs while each of the 18 incidents is retained into Hindsight (retaining uses an LLM to extract facts, so expect roughly one to two minutes in total).
4. When it finishes, the counter in the header shows how many memory units Hindsight created. This is likely **more than 18**, because Hindsight extracts several facts from each postmortem. The timeline shows 18 dots.

   Alternative from the terminal, useful for a clean reset before a recording:
   ```bash
   python -m scripts.seed_memory --reset
   ```
5. Wait about a minute, then look at **Patterns Blackbox learned on its own** at the bottom and select **Refresh patterns**. Hindsight consolidates memories in the background and updates a mental model called "Recurring failure patterns".

**Checkpoint 5:** the timeline shows 18 dots, the counter is above 0, and the patterns panel shows text about recurring problems such as connection pool exhaustion.

---

## Phase 6: Prove that memory changes the answer (20 minutes)

This is the exact story your demo tells. Do it once yourself in this order.

1. **Cold run.** Set the switch to **Without memory**, keep scenario 1 ("Checkout is slowing down"), select **Analyze incident**. You should see generic advice, low confidence, no matched incidents and no owner.
2. **Warm run.** Set the switch to **With memory**, analyze the same scenario. You should see:
   - matches such as INC-0012, INC-0019 and INC-0041 as blue chips,
   - the timeline lighting up the matching past incidents,
   - a specific fix (roll back the deploy, release connections properly, check the pool) instead of generic advice,
   - a suggested owner (the person who fixed it before),
   - a "Without memory it said" strip for direct comparison.
3. **Hover a chip.** The matching memory card on the right highlights, so a viewer sees which memory produced which claim.
4. **Novel incident.** Choose scenario 3 ("Something the team has never seen") and analyze with memory on. Blackbox should say nothing is a real match and give low confidence rather than inventing one. This demonstrates the honesty guardrail (the code also strips any incident id the model cites that memory did not return).
5. **Teach it.** Go back to scenario 1, analyze, then in the **Resolved? Teach Blackbox** card select **Save postmortem to memory**. The counter goes up and a new dot appears.
6. **Generalisation.** Choose scenario 4 ("Same pattern, different service"), a connection pool problem on a service the team has not had before, and analyze. It should still connect to the checkout pool incidents, and now also to the one you just saved.
7. **Measure it.** Run the learning curve:
   ```bash
   python -m scripts.eval_learning_curve
   ```
   It feeds incidents into a separate bank in chronological batches and reports how often the right kind of past incident appears in the top 3 results. It takes a few minutes on Hindsight Cloud. Screenshot the table. It is your "Interaction 1 generic, Interaction 20 knows you" evidence and it belongs in the article and the video. The result is written to `docs/eval_results.json`.

**Checkpoint 6:** cold and warm answers are clearly different, the novel incident is not force-matched, the saved postmortem raises the counter, and you have a learning curve table.

---

## Phase 7: Make it yours (2 to 4 hours)

The brief says realistic data is the number one thing that makes a project look real. Do these in priority order:

1. **Rename the world.** Edit `data/generate_incidents.py`: change service names, people and error signatures to something that fits the story you will tell (for example a fintech, a logistics company or a game studio). Rerun `python data/generate_incidents.py`, then `python -m scripts.seed_memory --reset`.
2. **Add two more incident clusters** with 3 incidents each. Keep the same fields. Each cluster needs different symptoms wording per incident so recall has to work, not just match keywords.
3. **Add your own demo scenarios** to the `DEMO` list. Keep one that is a recurring problem, one that is brand new, and one that recurs on a *different* service.
4. **Pick one ambitious extension** (optional, see `02_ARCHITECTURE.md`, section "Roadmap"): Slack intake, engineer thumbs up and down feedback stored as memory, or two teams with two banks to show isolation.
5. **Commit often.** At least once per phase.

**Checkpoint 7:** the demo scenarios still behave as in Phase 6 with your new data.

---

## Phase 8: Deploy a live demo link (45 minutes)

Judges like clicking a real URL. Hindsight Cloud is external, so you only deploy the small web app. The included `Procfile` works with Railway; on Render use the settings below.

1. Push your latest code to GitHub.
2. On Render or Railway, create a **new web service** from your GitHub repo.
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add environment variables in the platform dashboard (never in the repo):
   `HINDSIGHT_BASE_URL`, `HINDSIGHT_API_KEY`, `HINDSIGHT_BANK_ID`, `MEMORY_BACKEND=hindsight`, `GROQ_API_KEY`, `LLM_MODEL`, `LLM_FALLBACK_MODEL`, `LLM_MODE=groq`, and `ALLOW_RESET=false`.
4. Use a **dedicated bank id for the public demo** (for example `blackbox-public-demo`) and seed it once from your laptop by setting that bank id in `.env` and running `python -m scripts.seed_memory --reset`.
5. Open the deployed URL, run scenarios 1 and 2, and confirm the header shows your bank name with the Hindsight backend.
6. Free tiers sleep when idle. **Open the URL five minutes before you present** so the first request is not slow.

**Checkpoint 8:** the public URL works from a different device and network, and the header says `(hindsight)`, not `(local)`.

---

## Phase 9: Rehearse and record the demo (2 hours)

1. Follow `04_DEMO_SCRIPT.md`. Rehearse the three-minute version at least three times with a timer.
2. Before every take, reset to a clean state: `python -m scripts.seed_memory --reset`, then wait a minute for patterns.
3. Record the screen with a tool such as OBS or the built-in recorder. Record at 1080p, keep the browser zoom at 110 to 125 percent so text is readable in a video.
4. Record a **backup take** in case the live demo has network trouble. Keep it on your laptop offline.

**Checkpoint 9:** a demo video under three minutes exists on your laptop, and the script has been performed live without reading it.

---

## Phase 10: Content deliverables (3 hours)

The rules say every team member must complete an article, a social media post and a video as described in the official content guide.

1. Open `05_CONTENT_DELIVERABLES.md`. It has ready-to-edit drafts.
2. **Check every requirement against the official Content Guide** (length, platform, hashtags, tagging, deadlines) and adjust. The guide was not available when this kit was written.
3. Each teammate should personalise their own version with their own experience. Duplicated posts look like duplicated posts.
4. Paste your real learning curve numbers from Phase 6 and a screenshot of the timeline lighting up.

**Checkpoint 10:** every teammate has a draft article, a post and a video plan, and each one has been checked against the Content Guide.

---

## Phase 11: Submission freeze (1 hour)

Use `06_SUBMISSION_CHECKLIST.md`. In short:

- [ ] Public GitHub repo with README, docs and clean code, and no secrets in the history.
- [ ] Demo video uploaded.
- [ ] Live demo URL working.
- [ ] `03_HINDSIGHT_MEMORY_DESIGN.md` linked from the README (this is the written explanation of how Hindsight memory is used).
- [ ] All content deliverables published and linked.
- [ ] Freeze the code one hour before the deadline. After the freeze, only fix something that is broken, never add features.

---

## Timeline at a glance

| Hackathon length | Setup + first working demo | Data + polish | Deploy + rehearse | Content + submit |
|---|---|---|---|---|
| 24 hours | Hours 0 to 3 | Hours 3 to 12 | Hours 12 to 18 | Hours 18 to 24 |
| 36 hours | Hours 0 to 3 | Hours 3 to 20 | Hours 20 to 28 | Hours 28 to 36 |
| 48 hours | Hours 0 to 3 | Hours 3 to 28 | Hours 28 to 38 | Hours 38 to 48 |

Sleep is also a deliverable. A rested team demos better.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Banner: "Memory backend not reachable" | Wrong `HINDSIGHT_BASE_URL` or `HINDSIGHT_API_KEY` | Recopy them from the Connect page. For Docker self-hosting the URL is `http://localhost:8888`. |
| 401 or 403 from Hindsight | Key typo or expired key | Create a new key under Manage API Keys, paste it, restart the server. |
| Smoke test: recall returns nothing | Retained memory not indexed yet | Wait 20 seconds and rerun. |
| Banner: "GROQ_API_KEY is missing" | `.env` not loaded or key empty | Check `.env` is in the project root and restart. Answers still work from memory but without model synthesis. |
| Answers show `fallback-heuristic` as the model | Groq rate limit or timeout | Wait a moment, or switch `LLM_MODEL` and `LLM_FALLBACK_MODEL`. Never leave this on during a recording. |
| Patterns panel empty or thin | Consolidation still running | Wait one to two minutes after seeding, then press Refresh patterns. |
| Warm answer has no matches for scenario 1 | History not loaded, or wrong bank | Check the header counter is above 0 and the bank name is the one you seeded. |
| Two teammates see each other's incidents | Same `HINDSIGHT_BANK_ID` | Use a different bank id per developer. |
| Timeline empty after a server restart | Registry rebuilds only if the bank already has memories | Confirm the counter is above 0. If the counter is 0, reseed. |
| `ModuleNotFoundError: app` | Running from the wrong folder | `cd` into the project root and use `python -m scripts.<name>`. |
| Public deploy is slow on the first request | Free tier was asleep | Open the URL before presenting. |
| Everything is broken 20 minutes before judging | Network or keys | Play the backup video, then explain the architecture. Judges reward composure. |

---

## Rules of thumb

- **One workflow, done brilliantly.** Do not add a fifth feature the night before.
- **Memory must be visible.** If a viewer cannot see the memory panel working, the 25 percent memory score is at risk.
- **Never demo the local fallback.** It exists for development. The submission must use Hindsight.
- **Never commit keys.** If you do, rotate the key immediately and rewrite history or create a new repo.
