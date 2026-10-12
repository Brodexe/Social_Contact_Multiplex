"""
In-browser counterpart of app/server.py for the static (Pyodide) build.

app/static/js/pyodide-worker.js unpacks the repo's runtime files into Pyodide's
filesystem, imports this module, and forwards each API call the front end makes
to handle(), which mirrors server.py's routes for a single local session and
returns the response as a JSON string: {"ok": true, "data": ...} or
{"ok": false, "detail": "..."}.
"""

import json
import sys
import types

try:
    import matplotlib.pyplot  # noqa: F401
except ImportError:
    # SIR.py / correlated_graphs.py import pyplot at module level but the app never
    # plots; stub it so the browser needn't download matplotlib.
    _plt = types.ModuleType("matplotlib.pyplot")
    _plt.__getattr__ = lambda name: (lambda *a, **k: None)
    _mpl = types.ModuleType("matplotlib")
    _mpl.pyplot = _plt
    sys.modules.update({"matplotlib": _mpl, "matplotlib.pyplot": _plt})

from pydantic import ValidationError  # noqa: E402

from app import core  # noqa: E402

_session = core.Session()


def _json_default(obj):
    if hasattr(obj, "item"):  # numpy scalar
        return obj.item()
    raise TypeError(f"{type(obj).__name__} is not JSON serializable")


def _error(detail):
    return json.dumps({"ok": False, "detail": detail})


def handle(method, path, body_json=None):
    try:
        if method == "GET" and path == "/api/options":
            data = core.options()
        elif method == "POST" and path == "/api/reset":
            try:
                cfg = core.ScenarioConfig.model_validate_json(body_json or "{}")
            except ValidationError as exc:
                return _error("; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}"
                                        for e in exc.errors()))
            _session.reset(cfg)
            data = _session.reset_payload()
        elif method == "POST" and path == "/api/step":
            if _session.sim is None:
                return _error("No simulation; call /api/reset first")
            _session.sim.step()
            data = _session.snapshot()
        else:
            return _error(f"Unknown route {method} {path}")
    except Exception as exc:
        return _error(f"{type(exc).__name__}: {exc}")
    return json.dumps({"ok": True, "data": data}, default=_json_default)
