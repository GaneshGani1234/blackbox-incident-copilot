import json
import os

os.environ["MEMORY_BACKEND"] = "local"
os.environ["LLM_MODE"] = "mock"

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.llm import extract_json
from app.main import app


def test_extract_json_handles_think_tags_and_fences():
    raw = '<think>hmm</think>\n```json\n{"a": 1, "b": {"c": 2}}\n```'
    assert extract_json(raw) == {"a": 1, "b": {"c": 2}}


def test_extract_json_with_leading_prose():
    assert extract_json('Sure! {"ok": true} hope that helps')["ok"] is True


def test_end_to_end_cold_vs_warm_and_learning():
    with TestClient(app) as c:
        assert c.get("/api/health").json()["ok"] is True
        demo = c.get("/api/demo-incidents").json()
        checkout = next(d for d in demo if d["id"] == "DEMO-A")
        novel = next(d for d in demo if d["id"] == "DEMO-C")
        payload = lambda d, mem: {"incident": {k: d[k] for k in ("id", "date", "service", "title", "severity", "symptoms", "error_signature")}, "use_memory": mem}

        # cold: nothing recalled
        cold = c.post("/api/analyze", json=payload(checkout, False)).json()
        assert cold["mode"] == "cold" and cold["memory_trace"]["hits"] == []

        # seed and wait
        c.post("/api/seed", json={"reset": True})
        import time
        for _ in range(50):
            if not c.get("/api/seed/status").json()["running"] and c.get("/api/seed/status").json()["stats"]["memory_units"] >= 18:
                break
            time.sleep(0.1)

        warm = c.post("/api/analyze", json=payload(checkout, True)).json()
        ids = [h["incident_id"] for h in warm["memory_trace"]["hits"]]
        assert ids and ids[0] in {"INC-0012", "INC-0019", "INC-0027", "INC-0041"}
        assert warm["diagnosis"]["matched_incidents"]

        # resolving retains a new memory
        before = c.get("/api/health").json()["memory"]["memory_units"]
        r = c.post("/api/resolve", json={"incident": payload(checkout, True)["incident"], "root_cause": "leak", "fix": "rollback", "owner": "priya.nair", "minutes_to_resolve": 30})
        assert r.status_code == 200 and r.json()["retained"]
        assert c.get("/api/health").json()["memory"]["memory_units"] == before + 1

        # patterns endpoint works
        assert "incidents" in c.get("/api/patterns").json()["content"]


def test_hallucinated_ids_are_removed():
    from app.agent import _clean
    diag, removed = _clean({"matched_incidents": [{"id": "INC-9999"}, {"id": "INC-0012"}]}, [{"incident_id": "INC-0012"}])
    assert removed == ["INC-9999"] and len(diag["matched_incidents"]) == 1
