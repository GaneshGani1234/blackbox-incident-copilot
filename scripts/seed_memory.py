"""Load the synthetic incident history into Hindsight.

Usage:
    python -m scripts.seed_memory            # add incidents (safe to re-run, document_id makes retains idempotent)
    python -m scripts.seed_memory --reset    # delete the bank first for a perfectly clean demo
"""
import argparse
import asyncio
import json
import time

from app.config import settings
from app.memory import build_memory


async def main(reset: bool) -> None:
    mem = build_memory()
    print(f"Backend: {mem.name} | bank: {mem.bank_id}")
    await mem.ensure_ready()
    if reset:
        print("Resetting bank...")
        await mem.reset()
    incidents = json.loads((settings.data_dir / "incidents.json").read_text())
    t0 = time.time()

    async def progress(done: int, total: int) -> None:
        print(f"  retained {done}/{total}", end="\r", flush=True)

    await mem.retain_many(incidents, progress)
    print(f"\nRetained {len(incidents)} incidents in {time.time() - t0:.1f}s")
    print("Stats:", await mem.stats())
    print("Tip: Hindsight consolidates memories in the background. Wait about a minute before showing the patterns panel.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    asyncio.run(main(ap.parse_args().reset))
