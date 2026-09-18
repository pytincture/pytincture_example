# Browser runtime experiment

This isolated Book Library experiment compares Pyodide, MicroPython WebAssembly,
and Python compiled to JavaScript with Transcrypt. See [REPORT.md](REPORT.md) for
measurements and limitations. Nothing here changes the framework or the normal
example entrypoint.

All three small clients run the identical [Python application](src/client.py):
fetch 69 books through the authenticated BFF, filter, select, edit a title, save,
and reload. They share DHTMLX assets and a JavaScript host, with small interpreter
and compiler adapters. They do not include the full example's other widgets or
use its existing `dhxpyt` Python wrappers.

## Reproduce

Prerequisites: Node/npm, uv, a checkout of pytincture, and Chromium supported by
Playwright. The original measurements used framework commit
`30fff4404bbbd392957997b57c4c2fff97340228` and example base
`23688c094aaeb599e05de45f99cc61156292984c`.

From this directory, set the framework checkout path and create two environments:

```sh
export PYTINCTURE_SOURCE="$HOME/repos/pytincture"
export PYTHONPATH="$PYTINCTURE_SOURCE"
uv venv --python 3.13 .runner
uv pip install --python .runner/bin/python -e "$PYTINCTURE_SOURCE[password]" playwright==1.63.0
.runner/bin/python -m playwright install chromium
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python Transcrypt==3.9.4
npm ci
.runner/bin/python build.py
.runner/bin/python server.py
```

The server binds only to `127.0.0.1:8092`. It uses a separate SQLite database under
`~/Library/Caches/pytincture-runtime-lab/`; override that directory using
`PYTINCTURE_LAB_CACHE`. Each server start generates an ephemeral session secret.
The example's normal database and service on port 8070 are untouched.

Log in at <http://127.0.0.1:8092/py_ui/login> using the example's public demo
credentials `demo@example.com` / `demo-password`, then open:

- <http://127.0.0.1:8092/lab/?engine=pyodide>
- <http://127.0.0.1:8092/lab/?engine=micropython>
- <http://127.0.0.1:8092/lab/?engine=transcrypt>
- Full original example: <http://127.0.0.1:8092/py_ui>
- Same full example, test-only service-worker and cache-warmup override:
  <http://127.0.0.1:8092/py_ui?runtime_lab_no_sw=1>

In a second shell, from this directory:

```sh
export PYTINCTURE_SOURCE="$HOME/repos/pytincture"
.runner/bin/python compatibility.py
.runner/bin/python benchmark.py --local-runs 5 --throttled-runs 3
.runner/bin/python benchmark.py --variants full-no-sw --local-runs 5 --throttled-runs 3 --output results/no-sw.json
.runner/bin/python startup_diagnostic.py
.runner/bin/python report.py
```

Run these sequentially, with other browser activity idle. Functional checks
temporarily edit the disposable database and restore the title after success.
Don't run them during timing. Failed checks can leave the disposable edit in
place; remove only this experiment's database before restarting if necessary.

`results/` includes raw measurements, functional outcomes and asset hashes.
Generated runtime assets, environments and npm dependencies are ignored; build
them locally instead of committing third-party bundles. The lab is a local
research tool, not a production deployment configuration.

## Sources

- [MicroPython WebAssembly port](https://github.com/micropython/micropython/blob/master/ports/webassembly/README.md)
- [PyScript: choosing a runtime](https://docs.pyscript.net/2026.3.1/user-guide/what/)
- [Transcrypt documentation](https://www.transcrypt.org/docs/html/what_why.html)
- [Transcrypt installation and compilation](https://www.transcrypt.org/docs/html/installation_use.html)
