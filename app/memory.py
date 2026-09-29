"""
Memory layer for Blackbox.

HindsightMemory  -> the real thing: retain / recall / reflect / mental models on Hindsight.
LocalMemory      -> tiny in-process fallback (token overlap) so the team can develop offline
                    and run tests. It exists only for dev and CI. Demo and submit with Hindsight.

Both expose the same async interface so the agent code never cares which one is active.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

from .config import settings

PATTERNS_NAME = "Recurring failure patterns"
PATTERNS_QUERY = (
    "What recurring failure patterns, root causes and risky conditions show up across our incidents? "
    "Group them by pattern, say which services and which days or deploy types are involved, "
    "and state the fix that worked most reliably for each. Note patterns that are not yet well supported by evidence."
)
BANK_MISSION = (
    "You are the institutional memory of a site reliability engineering team. You remember every incident, "
    "the symptoms, the diagnostic steps that were tried (including dead ends), the confirmed root cause, "
    "the fix that worked and who owned it. Your job is to help engineers recognise when a new incident "
    "resembles an old one and to surface patterns across incidents."
)

_STOP = set("the a an and or of to in on for with at by is was were be it this that from as after before during into over under".split())


# ----------------------------------------------------------------------------------------------
# Shared helpers
# ----------------------------------------------------------------------------------------------
def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def incident_to_document(inc: dict) -> str:
    """Turn a structured incident into the postmortem narrative that gets retained.

    IMPORTANT: never include the synthetic 'cluster' label here. The eval script measures whether
    memory can find the right past incidents without being handed the answer.
    """
    when = parse_dt(inc["date"])
    lines = [
        f"Incident {inc['id']} ({inc.get('severity', 'SEV?')}) on {inc['service']}, "
        f"occurred {when.strftime('%A %Y-%m-%d %H:%M')} UTC.",
        f"Title: {inc['title']}",
        f"Symptoms: {inc.get('symptoms', '')}",
    ]
    if inc.get("error_signature"):
        lines.append(f"Error signature: {inc['error_signature']}")
    steps = inc.get("diagnostic_steps") or []
    if steps:
        lines.append("Diagnostic steps tried:")
        for n, s in enumerate(steps, 1):
            lines.append(f"  {n}. {s['action']} -> {s['result']}")
    if inc.get("root_cause"):
        lines.append(f"Confirmed root cause: {inc['root_cause']}")
    if inc.get("fix"):
        lines.append(f"Fix that worked: {inc['fix']}")
    if inc.get("owner"):
        lines.append(f"Resolved by / owner: {inc['owner']}.")
    if inc.get("minutes_to_resolve") is not None:
        lines.append(f"Time to resolve: {inc['minutes_to_resolve']} minutes.")
    if inc.get("deploy_related"):
        lines.append(f"Deploy context: {inc['deploy_related']}.")
    return "\n".join(lines)


def incident_to_query(inc: dict) -> str:
    parts = [inc.get("service", ""), inc.get("title", ""), inc.get("symptoms", ""), inc.get("error_signature", "")]
    return ". ".join(p for p in parts if p)


def incident_tags(inc: dict) -> list[str]:
    tags = ["postmortem", inc["service"], inc.get("severity", "SEV?")]
    if inc.get("deploy_related"):
        tags.append("deploy-related")
    return tags


def _incident_id(document_id: Optional[str], text: str = "") -> str:
    if document_id:
        return document_id
    m = re.search(r"\b(INC-\d{4}|DEMO-[A-Z]|LIVE-[\w-]+)\b", text)
    return m.group(1) if m else "unknown"


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_\-\.]+", text.lower()) if t not in _STOP and len(t) > 2]


ProgressCb = Optional[Callable[[int, int], Awaitable[None]]]


# ----------------------------------------------------------------------------------------------
# Real Hindsight backend
# ----------------------------------------------------------------------------------------------
class HindsightMemory:
    name = "hindsight"

    def __init__(self) -> None:
        from hindsight_client import Hindsight  # imported lazily so local mode needs no server

        self.bank_id = settings.bank_id
        self.client = Hindsight(
            base_url=settings.hindsight_base_url,
            api_key=settings.hindsight_api_key,
            timeout=180.0,
        )
        self._patterns_id: Optional[str] = None

    async def ensure_ready(self) -> None:
        try:
            await self.client.acreate_bank(
                self.bank_id,
                name="Blackbox incident memory",
                mission=BANK_MISSION,
                reflect_mission=BANK_MISSION,
            )
        except Exception:
            # Bank already exists (or the server does not support the optional fields). Both are fine.
            try:
                await self.client.acreate_bank(self.bank_id, name="Blackbox incident memory")
            except Exception:
                pass
        await self._ensure_patterns_model()

    async def _ensure_patterns_model(self) -> None:
        try:
            listed = await self.client.alist_mental_models(self.bank_id)
            for m in getattr(listed, "items", []) or []:
                if getattr(m, "name", "") == PATTERNS_NAME:
                    self._patterns_id = m.id
                    return
        except Exception:
            pass
        try:
            created = await self.client.acreate_mental_model(
                self.bank_id,
                name=PATTERNS_NAME,
                source_query=PATTERNS_QUERY,
                trigger={"refresh_after_consolidation": True},  # keeps the model current as memories change
            )
            self._patterns_id = created.mental_model_id
        except Exception:
            try:
                created = await self.client.acreate_mental_model(
                    self.bank_id, name=PATTERNS_NAME, source_query=PATTERNS_QUERY
                )
                self._patterns_id = created.mental_model_id
            except Exception:
                self._patterns_id = None  # patterns() falls back to reflect

    async def retain_incident(self, inc: dict) -> None:
        await self.client.aretain(
            self.bank_id,
            content=incident_to_document(inc),
            timestamp=parse_dt(inc["date"]),
            context="Incident postmortem",
            document_id=inc["id"],
            tags=incident_tags(inc),
            metadata={"service": inc["service"], "severity": inc.get("severity", ""), "source": "blackbox"},
        )

    async def retain_many(self, incidents: list[dict], progress: ProgressCb = None) -> None:
        total = len(incidents)
        for i, inc in enumerate(incidents, 1):
            await self.retain_incident(inc)
            if progress:
                await progress(i, total)

    async def recall(self, query: str, limit: int = 6) -> list[dict]:
        resp = await self.client.arecall(
            self.bank_id,
            query=query,
            budget="mid",
            max_tokens=3500,
            include_chunks=True,
            max_chunk_tokens=6000,
        )
        results = getattr(resp, "results", resp) or []
        chunks = getattr(resp, "chunks", None) or {}
        grouped: dict[str, dict[str, Any]] = {}
        for r in results:
            scores = getattr(r, "scores", None)
            score = float(getattr(scores, "final", 0.0) or 0.0) if scores else 0.0
            doc_id = _incident_id(getattr(r, "document_id", None), getattr(r, "text", ""))
            g = grouped.setdefault(
                doc_id,
                {"incident_id": doc_id, "score": 0.0, "facts": [], "text": "", "occurred": None, "kind": getattr(r, "type", None)},
            )
            g["score"] = max(g["score"], score)
            g["facts"].append(r.text)
            occurred = getattr(r, "occurred_start", None)
            if occurred and not g["occurred"]:
                g["occurred"] = occurred.isoformat() if hasattr(occurred, "isoformat") else str(occurred)
            cid = getattr(r, "chunk_id", None)
            if cid and not g["text"]:
                ch = chunks.get(cid) if isinstance(chunks, dict) else None
                if ch is not None:
                    g["text"] = getattr(ch, "text", "") or ""
        hits = sorted(grouped.values(), key=lambda h: h["score"], reverse=True)[:limit]
        for h in hits:
            if not h["text"]:
                h["text"] = "\n".join(h["facts"])
        return hits

    async def reflect(self, question: str) -> dict:
        resp = await self.client.areflect(self.bank_id, query=question, budget="mid")
        return {"text": getattr(resp, "text", str(resp)), "sources": None}

    async def patterns(self) -> dict:
        if self._patterns_id:
            try:
                mm = await self.client.aget_mental_model(self.bank_id, self._patterns_id)
                content = getattr(mm, "content", "") or ""
                if content.strip():
                    refreshed = getattr(mm, "last_refreshed_at", None)
                    return {"name": PATTERNS_NAME, "content": content, "refreshed_at": str(refreshed) if refreshed else None, "source": "mental_model"}
            except Exception:
                pass
        r = await self.reflect(PATTERNS_QUERY)
        return {"name": PATTERNS_NAME, "content": r["text"], "refreshed_at": None, "source": "reflect"}

    async def refresh_patterns(self) -> dict:
        if self._patterns_id:
            try:
                await self.client.arefresh_mental_model(self.bank_id, self._patterns_id)
            except Exception:
                pass
        return await self.patterns()

    async def stats(self) -> dict:
        count = 0
        try:
            r = await self.client.alist_memories(self.bank_id, limit=1)
            count = int(getattr(r, "total", 0) or 0)
        except Exception:
            pass
        return {"backend": self.name, "bank_id": self.bank_id, "memory_units": count}

    async def reset(self) -> None:
        try:
            await self.client.adelete_bank(self.bank_id)
        except Exception:
            pass
        self._patterns_id = None
        await self.ensure_ready()


# ----------------------------------------------------------------------------------------------
# Local fallback (dev / tests only)
# ----------------------------------------------------------------------------------------------
class LocalMemory:
    name = "local"

    def __init__(self) -> None:
        self.bank_id = settings.bank_id
        self.docs: dict[str, dict] = {}

    async def ensure_ready(self) -> None:
        return None

    async def retain_incident(self, inc: dict) -> None:
        text = incident_to_document(inc)
        self.docs[inc["id"]] = {"inc": inc, "text": text, "tokens": Counter(_tokens(text))}

    async def retain_many(self, incidents: list[dict], progress: ProgressCb = None) -> None:
        for i, inc in enumerate(incidents, 1):
            await self.retain_incident(inc)
            if progress:
                await progress(i, len(incidents))

    async def recall(self, query: str, limit: int = 6) -> list[dict]:
        if not self.docs:
            return []
        n = len(self.docs)
        df: Counter = Counter()
        for d in self.docs.values():
            df.update(d["tokens"].keys())
        q = Counter(_tokens(query))
        qnorm = math.sqrt(sum((c * math.log(1 + n / (1 + df[t]))) ** 2 for t, c in q.items())) or 1.0
        scored = []
        for doc_id, d in self.docs.items():
            dot = sum(
                (q[t] * math.log(1 + n / (1 + df[t]))) * (d["tokens"][t] * math.log(1 + n / (1 + df[t])))
                for t in q
                if t in d["tokens"]
            )
            dnorm = math.sqrt(sum((c * math.log(1 + n / (1 + df[t]))) ** 2 for t, c in d["tokens"].items())) or 1.0
            scored.append((dot / (qnorm * dnorm), doc_id))
        scored.sort(reverse=True)
        hits = []
        for score, doc_id in scored[:limit]:
            if score <= 0:
                continue
            d = self.docs[doc_id]
            hits.append({"incident_id": doc_id, "score": round(score, 4), "facts": [], "text": d["text"], "occurred": d["inc"]["date"], "kind": "local"})
        return hits

    async def reflect(self, question: str) -> dict:
        return {"text": (await self.patterns())["content"], "sources": None}

    async def patterns(self) -> dict:
        if not self.docs:
            return {"name": PATTERNS_NAME, "content": "No incidents in memory yet.", "refreshed_at": None, "source": "local"}
        by_service: dict[str, list[str]] = defaultdict(list)
        deploy = fri = 0
        for d in self.docs.values():
            inc = d["inc"]
            by_service[inc["service"]].append(inc["id"])
            if inc.get("deploy_related"):
                deploy += 1
                if parse_dt(inc["date"]).weekday() == 4:
                    fri += 1
        repeated = {s: ids for s, ids in by_service.items() if len(ids) > 1}
        lines = [f"(Local fallback summary, not Hindsight.) {len(self.docs)} incidents remembered."]
        for s, ids in sorted(repeated.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"- {s} has {len(ids)} incidents: {', '.join(ids)}")
        if deploy:
            lines.append(f"- {deploy} incidents were deploy related, {fri} of them on a Friday.")
        return {"name": PATTERNS_NAME, "content": "\n".join(lines), "refreshed_at": None, "source": "local"}

    async def refresh_patterns(self) -> dict:
        return await self.patterns()

    async def stats(self) -> dict:
        return {"backend": self.name, "bank_id": self.bank_id, "memory_units": len(self.docs)}

    async def reset(self) -> None:
        self.docs.clear()


def build_memory():
    if settings.memory_backend == "local":
        return LocalMemory()
    return HindsightMemory()
