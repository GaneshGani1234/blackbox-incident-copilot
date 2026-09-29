"""
Blackbox agent loop.

  analyze()  : new incident -> RECALL from Hindsight -> LLM diagnosis grounded in recalled incidents
  resolve()  : engineer confirms root cause and fix -> RETAIN the postmortem back into Hindsight
  patterns() : REFLECT / mental model -> patterns the agent discovered on its own

Every response includes a `memory_trace` so the UI can show exactly what memory contributed.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Optional

from .config import settings
from .llm import LLMError, complete_json
from .memory import incident_to_query
from .prompts import SYSTEM_COLD, SYSTEM_WARM, render_incident, render_memory

GENERIC_STEPS = [
    "Check whether a deploy, config change or feature flag change happened shortly before the alert.",
    "Compare resource metrics (CPU, memory, connections) against a normal day for the affected service.",
    "Inspect application logs for the first occurrence of the error and what changed at that time.",
    "If a recent change is suspected, roll it back first and investigate afterwards.",
]


def _mock_diagnosis(inc: dict, hits: list[dict], use_memory: bool) -> dict:
    """Deterministic offline answer (LLM_MODE=mock). Used for tests and when no API key is available."""
    if not use_memory or not hits or hits[0]["score"] <= 0:
        return {
            "summary": f"{inc['service']} is degraded: {inc['title']}.",
            "likely_root_cause": "Unknown without history. Most incidents like this follow a recent change.",
            "matched_incidents": [], "recommended_steps": GENERIC_STEPS, "avoid": [],
            "suggested_owner": None, "confidence": "low", "confidence_reason": "No team history available.",
        }
    top = hits[0]
    text = top["text"]
    root = re.search(r"Confirmed root cause: (.+)", text)
    fix = re.search(r"Fix that worked: (.+)", text)
    owner = re.search(r"owner: ([\w\.\-]+)", text)
    return {
        "summary": f"{inc['service']} looks similar to {top['incident_id']}.",
        "likely_root_cause": root.group(1) if root else "See matched incident.",
        "matched_incidents": [{"id": h["incident_id"], "similarity": "high" if i == 0 else "medium", "why": "Recalled from memory"} for i, h in enumerate(hits[:3])],
        "recommended_steps": [fix.group(1)] if fix else GENERIC_STEPS,
        "avoid": [], "suggested_owner": owner.group(1) if owner else None,
        "confidence": "high" if top["score"] > 0.3 else "medium", "confidence_reason": "Mock mode heuristic on retrieval score.",
    }


def _clean(diag: dict, hits: list[dict]) -> tuple[dict, list[str]]:
    """Guardrails: drop any cited incident id that memory did not actually return."""
    valid = {h["incident_id"] for h in hits}
    removed: list[str] = []
    kept = []
    for m in diag.get("matched_incidents") or []:
        mid = m.get("id") if isinstance(m, dict) else None
        if mid in valid:
            kept.append(m)
        elif mid:
            removed.append(mid)
    diag["matched_incidents"] = kept
    if removed and not kept:
        diag["confidence"] = "low"
    for key in ("recommended_steps", "avoid"):
        if not isinstance(diag.get(key), list):
            diag[key] = []
    diag.setdefault("confidence", "low")
    return diag, removed


async def analyze(memory, incident: dict, use_memory: bool) -> dict:
    t0 = time.perf_counter()
    hits: list[dict] = []
    recall_ms = 0
    query = incident_to_query(incident)
    if use_memory:
        r0 = time.perf_counter()
        hits = await memory.recall(query, limit=5)
        recall_ms = int((time.perf_counter() - r0) * 1000)

    user_msg = f"NEW INCIDENT\n{render_incident(incident)}\n\n" + (render_memory(hits) if use_memory else "")
    system = SYSTEM_WARM if use_memory else SYSTEM_COLD
    model_used, error = "mock", None
    if settings.llm_mode == "mock":
        diag = _mock_diagnosis(incident, hits, use_memory)
    else:
        try:
            diag, model_used = await complete_json(system, user_msg)
        except LLMError as e:  # degrade gracefully so the demo never shows a stack trace
            error = str(e)
            diag = _mock_diagnosis(incident, hits, use_memory)
            diag["confidence_reason"] = "LLM unavailable, answer built directly from recalled memory. " + diag["confidence_reason"]
            model_used = "fallback-heuristic"

    diag, removed = _clean(diag, hits)
    return {
        "mode": "warm" if use_memory else "cold",
        "diagnosis": diag,
        "memory_trace": {
            "query": query if use_memory else None,
            "hits": [{"incident_id": h["incident_id"], "score": h["score"], "occurred": h.get("occurred"),
                      "excerpt": (h["text"] or "")[:420], "facts": h.get("facts", [])[:4]} for h in hits],
            "recall_ms": recall_ms,
            "backend": getattr(memory, "name", "unknown"),
        },
        "meta": {"model": model_used, "total_ms": int((time.perf_counter() - t0) * 1000),
                 "hallucinated_ids_removed": removed, "llm_error": error},
    }


async def resolve(memory, incident: dict, root_cause: str, fix: str, owner: str,
                  minutes: Optional[int], steps: list[dict], deploy: Optional[str]) -> dict:
    """Close the loop: this is the moment the agent learns."""
    inc = dict(incident)
    inc["id"] = inc.get("id") or f"LIVE-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    inc["date"] = inc.get("date") or datetime.now(timezone.utc).isoformat()
    inc.update({"root_cause": root_cause, "fix": fix, "owner": owner, "minutes_to_resolve": minutes,
                "diagnostic_steps": steps, "deploy_related": deploy})
    await memory.retain_incident(inc)
    return {"retained": True, "incident_id": inc["id"], "stats": await memory.stats()}
