// Runs the Python simulation in the browser for the static build (no server).
// main.js starts this worker only when /api/* isn't reachable, sends
// {type: 'init', bundleUrl} once, then {id, method, path, body} per API call;
// each reply is {id, response} where response is app/browser_api.handle()'s JSON.
// Progress messages ({type: 'status', text}) drive the loading overlay.

import { loadPyodide } from 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs';

const PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/';

let api = null;

async function init(bundleUrl) {
  postMessage({ type: 'status', text: 'Loading Python runtime…' });
  const pyodide = await loadPyodide();
  postMessage({ type: 'status', text: 'Loading numpy & networkx…' });
  const [, bundle] = await Promise.all([
    (async () => {
      await pyodide.loadPackage(['numpy', 'pydantic', 'micropip']);
      // Pyodide's networkx package depends on matplotlib (~10 MB) for drawing, which
      // the app never does; install the wheel by URL so its deps are skipped
      // (browser_api.py stubs pyplot instead).
      await pyodide.pyimport('micropip').install.callKwargs(
        `${PYODIDE_URL}networkx-3.6.1-py3-none-any.whl`, { deps: false });
    })(),
    fetch(bundleUrl).then((r) => {
      if (!r.ok) throw new Error(`could not fetch ${bundleUrl}: ${r.status}`);
      return r.arrayBuffer();
    }),
  ]);
  pyodide.unpackArchive(bundle, 'zip');  // into the cwd, so repo-relative data paths resolve
  pyodide.runPython('import os, sys; sys.path.insert(0, os.getcwd())');
  api = pyodide.pyimport('app.browser_api');
  postMessage({ type: 'status', text: 'Building networks…' });
}

let ready = null;

self.onmessage = async ({ data }) => {
  if (data.type === 'init') {
    ready = init(data.bundleUrl);
    return;
  }
  const { id, method, path, body } = data;
  try {
    await ready;
    const response = api.handle(method, path, body === undefined ? null : JSON.stringify(body));
    postMessage({ id, response });
  } catch (err) {
    postMessage({ id, response: JSON.stringify({ ok: false, detail: String(err.message ?? err) }) });
  }
};
