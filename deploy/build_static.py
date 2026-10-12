"""
Build the interactive app as a static site (no server needed).

The page is app/static/index.html with app/static/ beside it; the simulation
runs in the visitor's browser (app/static/js/pyodide-worker.js loads Pyodide and
unpacks py-bundle.zip: app/'s Python, the research modules it imports, and the
high-school network data). Output goes to deploy/site/, which any static host can
serve; deploy/push_to_hf.py publishes it to a Hugging Face Space.

Run from the repo root:  python deploy/build_static.py
Preview:                 python -m http.server -d deploy/site 8001
"""

import os
import shutil
import sys
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
from app.networks import HS_BINS, HS_DIR, HS_SOCIAL_PATH  # noqa: E402

SITE_DIR = os.path.join(REPO_ROOT, "deploy", "site")
SPACE_FILES_DIR = os.path.join(REPO_ROOT, "deploy", "hf_space")

PY_BUNDLE = [
    "app/__init__.py",
    "app/browser_api.py",
    "app/core.py",
    "app/engine.py",
    "app/networks.py",
    "IM.py",
    "SIR.py",
    "correlated_graphs.py",
    "find_seeds.py",
    "network_setup.py",
    HS_SOCIAL_PATH,
    *(f"{HS_DIR}/high_school_contact_bin{b}.gml" for b in HS_BINS),
]


def build(site_dir=SITE_DIR):
    if os.path.exists(site_dir):
        shutil.rmtree(site_dir)
    static_src = os.path.join(REPO_ROOT, "app", "static")
    shutil.copytree(static_src, os.path.join(site_dir, "static"),
                    ignore=shutil.ignore_patterns("index.html", "__pycache__"))
    shutil.copy(os.path.join(static_src, "index.html"), site_dir)
    for name in os.listdir(SPACE_FILES_DIR):
        shutil.copy(os.path.join(SPACE_FILES_DIR, name), site_dir)
    with zipfile.ZipFile(os.path.join(site_dir, "py-bundle.zip"), "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in PY_BUNDLE:
            zf.write(os.path.join(REPO_ROOT, rel), rel)
    return site_dir


if __name__ == "__main__":
    print(f"Built static site in {build()}")
