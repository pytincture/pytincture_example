# Browser runtime results

Both alternatives ran a useful slice of the real Book Library example without
loading Pyodide. MicroPython runs Python in a smaller WebAssembly interpreter;
Transcrypt compiles a supported subset of Python into JavaScript ahead of time.
Neither is a drop-in replacement for the complete existing application.

## Same application logic and features

All three execute the identical `src/client.py`, show the same 69 books using the
same DHTMLX grid, and call the same authenticated example BFF. The JavaScript
host handles DOM/widget wiring; a small adapter connects it to each runtime.
Times run from navigation to a populated grid, after two animation frames.

| Profile | Client | Cold median (range), seconds | Reload median (range), seconds | Cold / reload MiB |
|---|---|---:|---:|---:|
| local | pyodide | 1.156 (1.146–1.169) | 0.900 (0.843–1.001) | 13.69 / 10.22 |
| local | micropython | 0.137 (0.128–0.173) | 0.076 (0.074–0.091) | 2.51 / 2.51 |
| local | transcrypt | 0.137 (0.125–0.218) | 0.076 (0.074–0.081) | 2.04 / 2.04 |
| throttled | pyodide | 16.488 (16.421–16.652) | 12.730 (12.719–12.788) | 13.66 / 10.19 |
| throttled | micropython | 2.776 (2.768–2.789) | 2.522 (2.514–2.522) | 2.48 / 2.48 |
| throttled | transcrypt | 2.319 (2.310–2.393) | 2.095 (2.094–2.097) | 2.01 / 2.01 |

Each local cell uses five measurements; each throttled cell uses three.
Throttling is 10 Mbps down, 2 Mbps up, 40 ms latency and 4× CPU slowdown.
Cold runs each start a new Chromium process/context. Reloads immediately reuse
the tab; caching follows the actual server response headers. MiB is reported by
Resource Timing at grid readiness, including the document and shared widget assets.

## Full original application: separate comparison

These rows include the original toolbar, sidebar, chart, form, calendar, Python
widget wrappers, package loading and startup machinery. They are not a feature
equivalent comparison against the smaller clients above.

| Profile | Client | Cold median (range), seconds | Reload median (range), seconds | Cold / reload MiB |
|---|---|---:|---:|---:|
| local | full-example | 8.212 (8.054–8.277) | 7.814 (7.545–7.962) | 30.96 / 13.98 |
| local | full-no-sw | 3.060 (2.972–3.482) | 2.600 (2.539–2.935) | 18.34 / 13.98 |
| throttled | full-example | 38.752 (38.626–38.862) | 26.896 (26.733–27.478) | 30.58 / 13.98 |
| throttled | full-no-sw | 26.799 (25.932–26.866) | 22.176 (21.589–22.632) | 17.96 / 13.98 |

`full-no-sw` uses the original application with only `enableServiceWorker: false`
and `warmPyodideCache: false` injected into the HTML by the experiment server.
The unchanged baseline ran first; this additional comparison ran afterward.
It leaves the normal `/py_ui` response untouched and does not edit framework code.

The baseline lifecycle traces show a roughly five-second gap between preflight
completion and runtime loading. The framework awaits service-worker activation
and control in this interval, with five-second timeout fallbacks. Baseline
resource traces also contain both normal and cache-warmup requests for the WASM
binary and standard-library archive. The override tests both startup effects
together; it does not independently attribute the savings to each setting.

The separate [startup probe](results/startup-diagnostic.json) found an active
worker scoped to `/py_ui/`, while the document URL was `/py_ui` and its controller
was null. The document falls outside that scope, explaining why the control wait
reaches its timeout. A production fix should address scope/navigation and cache
behavior rather than blindly removing service-worker functionality.

## Functional results and compatibility

All three small clients passed loading 69 records, filtering to four Harry
matches, selecting a record, editing its title, saving through the actual BFF,
reloading to verify persistence, and restoring the original title. Invalid CSRF
updates returned 403; an unauthenticated dataset request returned 401.
See [functional.json](results/functional.json).

MicroPython imported `asyncio`, `inspect` and `js`; this build could not import
`dataclasses`, `typing` or `pyodide.ffi`. Import success alone does not establish
full module compatibility. Existing wrappers and proxy handling need adaptation.
Compiling the unchanged original `example/py_ui.py` with Transcrypt failed at
line 63; see [compiler output](results/original-transcrypt.log). The shared slice
compiled and its generated JavaScript passed the functional checks.

## Recommendation

First investigate the service-worker wait and duplicate cache warmup in the
existing startup path: that can improve the full app without porting its UI.
For a smaller Python-on-WASM option, MicroPython merits a runtime-adapter proof
of concept covering more of `dhxpyt`. Transcrypt is promising when ahead-of-time
JavaScript compilation and a restricted Python subset are acceptable. The
current measurements prove the core data/edit flow, not compatibility with all
widgets, Python packages, callbacks or arbitrary applications.

## Scope and reproducibility

- Framework `30fff4404bbbd392957997b57c4c2fff97340228`; example base `23688c094aaeb599e05de45f99cc61156292984c`.
- Pyodide 0.29.3, MicroPython npm build 1.29.0-6,
  Transcrypt 3.9.4, dhxpyt 0.9.19.
- Chromium 153.0.8010.12; macOS-26.6.2-arm64-arm-64bit-Mach-O, arm64.
- All timed runtime/widget assets were served from the same local origin.
  This server has no production CDN/compression setup. Transcrypt output is
  unminified. The shared DHTMLX payload dominates the two smaller clients.
- Login is excluded; normal session cookies and CSRF remain enabled. No saved
  authentication state, private credentials or databases are included.
- The dataset is small; no memory, sustained throughput, large-data, mobile
  hardware, Firefox or Safari comparison was performed. CPU/network emulation
  does not reproduce a real phone or production network.
- Transfers at readiness can omit unfinished background work and exclude HTTP
  transport overhead; they are not a packet capture. Warm pages may still
  transfer assets because of the existing cache policy.
- Full-app readiness uses a populated-grid predicate, rather than the small
  clients' explicit animation-frame marker. Only startup was measured for the
  full app; the full widget suite was not retested here.
- The prototype uses direct DHTMLX JavaScript widgets through an adapter,
  bypassing the existing `dhxpyt` Python wrappers. Its Pyodide row provides the
  comparable runtime baseline; comparing only against the full app would
  overstate savings attributable to the interpreter alone.
- This experiment changes no production application or framework files and
  publishes no release.

[Reproduction instructions and upstream references](README.md) ·
[Raw baseline measurements](results/benchmark.json) ·
[Raw startup-override measurements](results/no-sw.json) ·
[Asset hashes](results/assets.json)
