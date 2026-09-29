import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import agent
from .config import settings
from .memory import build_memory
from .schemas import AnalyzeRequest, ReflectRequest, ResolveRequest, SeedRequest

STATIC = Path(__file__).parent / "static"
state: dict = {"memory": None, "registry": {}, "seed": {"running": False, "done": 0, "total": 0, "error": None}}


def _load(name: str) -> list[dict]:
    p = settings.data_dir / name
    if not p.exists():
        raise HTTPException(500, f"{name} missing. Run: python data/generate_incidents.py")
    return json.loads(p.read_text())


@asynccontextmanager
async def lifespan(app: FastAPI):
    mem = build_memory()
    state["memory"] = mem
    try:
        await mem.ensure_ready()
        if (await mem.stats())["memory_units"] > 0:  # memory already seeded in a previous run
            for i in _load("incidents.json"):
                state["registry"][i["id"]] = {k: i[k] for k in ("id", "date", "service", "title")}
    except Exception as e:  # keep the server up so /api/health can explain what is wrong
        state["startup_error"] = str(e)
    yield


app = FastAPI(title="Blackbox", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def mem():
    return state["memory"]


@app.get("/api/health")
async def health():
    stats = await mem().stats()
    return {
        "ok": "startup_error" not in state,
        "startup_error": state.get("startup_error"),
        "memory": stats,
        "llm_mode": settings.llm_mode,
        "llm_key_present": bool(settings.llm_api_key),
        "model": settings.llm_model,
    }


@app.get("/api/demo-incidents")
async def demo_incidents():
    return _load("demo_incidents.json")


@app.get("/api/timeline")
async def timeline():
    items = sorted(state["registry"].values(), key=lambda x: x["date"])
    return {"incidents": items}


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    incident = req.incident.model_dump()
    try:
        return await agent.analyze(mem(), incident, req.use_memory)
    except Exception as e:
        raise HTTPException(502, f"Analysis failed: {e}")


@app.post("/api/resolve")
async def resolve(req: ResolveRequest):
    try:
        out = await agent.resolve(
            mem(), req.incident.model_dump(), req.root_cause, req.fix, req.owner,
            req.minutes_to_resolve, [s.model_dump() for s in req.diagnostic_steps], req.deploy_related,
        )
    except Exception as e:
        raise HTTPException(502, f"Could not retain postmortem: {e}")
    inc = req.incident
    state["registry"][out["incident_id"]] = {
        "id": out["incident_id"], "date": inc.date or "", "service": inc.service, "title": inc.title,
    }
    return out


async def _seed_job(reset: bool):
    s = state["seed"]
    s.update({"running": True, "done": 0, "error": None})
    try:
        if reset:
            await mem().reset()
            state["registry"].clear()
        incidents = _load("incidents.json")
        s["total"] = len(incidents)

        async def progress(done: int, total: int):
            s["done"] = done

        await mem().retain_many(incidents, progress)
        for i in incidents:
            state["registry"][i["id"]] = {k: i[k] for k in ("id", "date", "service", "title")}
    except Exception as e:
        s["error"] = str(e)
    finally:
        s["running"] = False


@app.post("/api/seed")
async def seed(req: SeedRequest):
    if req.reset and not settings.allow_reset:
        raise HTTPException(403, "Reset is disabled on this deployment (ALLOW_RESET=false).")
    if state["seed"]["running"]:
        return state["seed"]
    asyncio.create_task(_seed_job(req.reset))
    return {**state["seed"], "running": True}


@app.get("/api/seed/status")
async def seed_status():
    return {**state["seed"], "stats": await mem().stats()}


@app.get("/api/patterns")
async def patterns():
    return await mem().patterns()


@app.post("/api/patterns/refresh")
async def refresh_patterns():
    return await mem().refresh_patterns()


@app.post("/api/reflect")
async def reflect(req: ReflectRequest):
    return await mem().reflect(req.question)


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")
