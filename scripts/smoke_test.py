"""Run this BEFORE anything else. It proves your keys and the memory round trip work.

    python -m scripts.smoke_test
"""
import asyncio
import sys

from app.config import settings
from app.llm import LLMError, complete_json
from app.memory import build_memory

OK, BAD = "PASS", "FAIL"


async def main() -> int:
    failures = 0
    print("== Blackbox smoke test ==")
    print(f"memory backend : {settings.memory_backend} ({settings.hindsight_base_url})")
    print(f"llm mode       : {settings.llm_mode} ({settings.llm_model})\n")

    mem = build_memory()
    mem.bank_id = f"{settings.bank_id}-smoke"  # never touch the real demo bank
    try:
        await mem.ensure_ready()
        print(f"[{OK}] connected to memory and bank ready")
        await mem.retain_incident({
            "id": "SMOKE-1", "date": "2026-01-01T10:00:00Z", "service": "demo-service", "severity": "SEV3",
            "title": "Demo pool exhaustion", "symptoms": "requests time out waiting for a database connection",
            "error_signature": "connection pool exhausted", "root_cause": "connection leak in new code",
            "fix": "rolled back the release", "owner": "test.user", "minutes_to_resolve": 10, "diagnostic_steps": [],
        })
        print(f"[{OK}] retain worked")
        await asyncio.sleep(3)
        hits = await mem.recall("database connection pool exhausted timeouts")
        if hits:
            print(f"[{OK}] recall returned {len(hits)} hit(s); top = {hits[0]['incident_id']} score {hits[0]['score']:.2f}")
        else:
            print(f"[{BAD}] recall returned nothing. If you just retained, wait 10 to 20 seconds and re-run.")
            failures += 1
    except Exception as e:
        print(f"[{BAD}] memory error: {e}")
        failures += 1
    finally:
        try:
            if hasattr(mem, "client"):
                await mem.client.adelete_bank(mem.bank_id)
            else:
                await mem.reset()
        except Exception:
            pass

    if settings.llm_mode == "mock":
        print("[SKIP] llm mock mode")
    else:
        try:
            data, model = await complete_json('Reply with JSON only.', 'Return {"ok": true}')
            print(f"[{OK}] LLM responded via {model}: {data}")
        except LLMError as e:
            print(f"[{BAD}] LLM error: {e}")
            failures += 1

    print("\nAll good. Next: python -m scripts.seed_memory" if not failures else f"\n{failures} check(s) failed. See docs/01_STEP_BY_STEP_GUIDE.md, Troubleshooting.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
