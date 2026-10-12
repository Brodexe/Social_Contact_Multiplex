"""
FastAPI backend for the interactive multiplex SIRS viewer.

Holds one MultiplexSIRS simulation per browser tab (keyed by the X-Session-Id
header the front end sends; least-recently-used sessions are evicted past
MAX_SESSIONS) and exposes it over a small JSON API:

    GET  /api/options   network choices + default scenario config
    POST /api/reset     build a new simulation from a scenario config; returns the
                        static network payload (nodes, edges, layouts, centrality
                        metrics) plus the t=0 snapshot
    POST /api/step      advance one tick; returns the new snapshot

Run from the repo root:  python -m app.server   (then open http://127.0.0.1:8000)
Set HOST=0.0.0.0 to serve beyond localhost. deploy/push_to_hf.py publishes a static
build that runs the same simulation in the browser instead (app/browser_api.py).
"""

import os
import sys
import threading
from collections import OrderedDict
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
os.chdir(REPO_ROOT)  # network_setup / dataset paths are relative to the repo root

from app.core import ScenarioConfig, Session, options as scenario_options  # noqa: E402

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
MAX_SESSIONS = 64


# The simulation draws from the global random / np.random state, so all resets and
# steps are serialized; otherwise concurrent visitors would interleave draws and
# break rng_seed reproducibility.
sim_lock = threading.Lock()
sessions = OrderedDict()


def _session(session_id, create=False):
    """Look up (and mark as recently used) the caller's session; caller holds sim_lock."""
    key = (session_id or "default")[:64]
    if key in sessions:
        sessions.move_to_end(key)
    elif create:
        sessions[key] = Session()
        while len(sessions) > MAX_SESSIONS:
            sessions.popitem(last=False)
    return sessions.get(key)


app = FastAPI(title="Multiplex SIRS")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/options")
def options():
    return scenario_options()


@app.post("/api/reset")
def reset(cfg: ScenarioConfig, x_session_id: Optional[str] = Header(None)):
    with sim_lock:
        session = _session(x_session_id, create=True)
        try:
            session.reset(cfg)
        except Exception as exc:  # surface bad scenario combos to the UI instead of a bare 500
            raise HTTPException(status_code=400, detail=f"{type(exc).__name__}: {exc}")
        return session.reset_payload()


@app.post("/api/step")
def step(x_session_id: Optional[str] = Header(None)):
    with sim_lock:
        session = _session(x_session_id)
        if session is None or session.sim is None:
            raise HTTPException(status_code=409, detail="No simulation; call /api/reset first")
        try:
            session.sim.step()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")
        return session.snapshot()


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))
    print(f"Multiplex SIRS viewer: http://127.0.0.1:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")
