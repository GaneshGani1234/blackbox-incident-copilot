"""Measure how memory quality improves as the agent remembers more incidents.

Feeds incidents to a SEPARATE eval bank in chronological batches. After each batch, runs the held-out
eval incidents and checks whether one of the top-3 recalled past incidents belongs to the expected
failure cluster (hit@3). The result is your learning curve for the demo, README and article.

    python -m scripts.eval_learning_curve
"""
import asyncio
import json
from pathlib import Path

from app.config import settings
from app.memory import build_memory, incident_to_query

STAGES = [0, 2, 4, 6, 12, 18]


async def main() -> None:
    incidents = sorted(json.loads((settings.data_dir / "incidents.json").read_text()), key=lambda i: i["date"])
    cluster_of = {i["id"]: i["cluster"] for i in incidents}
    evals = json.loads((settings.data_dir / "eval_set.json").read_text())

    mem = build_memory()
    mem.bank_id = f"{settings.bank_id}-eval"
    await mem.ensure_ready()
    await mem.reset()
    print(f"Eval bank: {mem.bank_id} ({mem.name})\n")

    rows, retained = [], 0
    for stage in STAGES:
        if stage > retained:
            await mem.retain_many(incidents[retained:stage])
            retained = stage
            await asyncio.sleep(2 if mem.name == "local" else 25)  # let Hindsight finish indexing
        hits_at_3 = 0
        for ev in evals:
            hits = await mem.recall(incident_to_query(ev), limit=3)
            if any(cluster_of.get(h["incident_id"]) == ev["expected_cluster"] for h in hits):
                hits_at_3 += 1
        pct = round(100 * hits_at_3 / len(evals))
        rows.append({"incidents_remembered": stage, "hit_at_3": hits_at_3, "of": len(evals), "percent": pct})
        print(f"{stage:>2} incidents remembered -> hit@3 = {hits_at_3}/{len(evals)} ({pct}%)")

    out = Path(settings.data_dir.parent / "docs" / "eval_results.json")
    out.write_text(json.dumps({"backend": mem.name, "results": rows}, indent=2))
    print(f"\nSaved {out}. Screenshot this table for your article and demo video.")
    try:
        if hasattr(mem, "client"):
            await mem.client.adelete_bank(mem.bank_id)
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
