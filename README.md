# Pytincture authenticated example

This example qualifies the published Pytincture 1.0 release candidate with a
real [wapyt](https://github.com/WAwesome-AI/wa_pytincture_widgetset)
application and an authenticated backend-for-frontend call.

## Run locally

```bash
python3.13 -m venv .venv
.venv/bin/pip install .
cd example
../.venv/bin/python run.py
```

## The widgetset

The UI is built with wapyt, the MIT-licensed widgetset for Pytincture: a
sidebar, a toolbar with a light/dark toggle, and three tabs -- a book grid with
a filter box and a right-click menu, a form that mirrors the selected book, and
a media tab. Double-clicking a row (or Edit in the menu, or Reports in the
sidebar) opens the book in a modal form that saves through the BFF.

wapyt runs only in the browser, so it is not a Python dependency of the
example. Pytincture finds the pin by reading the literal `__widgetset__` and
`__version__` in `example/widget.py`, and installs the matching wheel served
from `example/`. Pytincture does not fetch a widgetset from PyPI by itself, so
the wheel is vendored: `wapyt-0.2.0-py3-none-any.whl`, the unmodified
[PyPI release](https://pypi.org/project/wapyt/0.2.0/), which carries its
own asset manifest.

Moving to another wapyt release means updating three things together: the
file in `example/`, `__version__` in `example/widget.py`, and the un-ignored
filename in `.gitignore`, which keeps stray development wheels out of git. To
fetch a release:

```bash
cd example
python3 -m pip download --no-deps wapyt==0.2.0 -d .
```

Open <http://localhost:8070/> and sign in with the credentials displayed on
the login page:

- email: `demo@example.com`
- password: `demo-password`

The browser address remains `/py_ui/` after login; cache-busting UUIDs are added
only to frontend and application-resource requests.

## The Media tab

The Media tab (also the sidebar's Media item) shows wapyt's `MediaPlayer` in
two of its shapes, built in `example/media_view.py`:

- **A docked audio bar.** Picking a reading queues all four and plays the one
  you picked in a bar at the foot of the window. The bar is mounted on
  `<body>`, so it keeps playing while you go back to the grid, and the layout
  shrinks to make room for it. It has a Like button of the app's own beside
  the standard controls.
- **A film clip in place**, with a WebVTT caption track. The two players share
  an exclusive group, so starting one pauses the other.

The titles and URLs come from the BFF (`py_ui_data.media_library`). The files
come from `/example-media/<name>`, a plain route in `example/media_library.py`
that checks the session itself and answers Range requests so the players can
seek.

Pytincture's Content-Security-Policy has no `media-src`, so `default-src
'self'` applies: media has to be a plain file on the app's own origin. HLS
streams (they need `blob:`) and media on a CDN are refused by that policy, so
the example shows neither.

The clips in `example/media/` are short excerpts (2.1 MB in total):

| Files | Source | Licence |
|---|---|---|
| `pride-and-prejudice.mp3`, `alice-in-wonderland.mp3`, `a-scandal-in-bohemia.mp3`, `moby-dick.mp3` | [LibriVox](https://librivox.org/) recordings, from archive.org | Public domain |
| `big-buck-bunny.mp4`, `big-buck-bunny.jpg` | [Big Buck Bunny](https://peach.blender.org/), (c) 2008 Blender Foundation | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) |
| `big-buck-bunny.en.vtt` | Descriptive captions written for this example | MIT, with the example |

## Run with Docker

```bash
docker build -t pytincture-example .
docker run --rm -p 8070:8070 pytincture-example
```

Set `PYTINCTURE_EXAMPLE_SESSION_SECRET` to a private value when exposing the
demo outside a disposable local environment. The launcher disables secure-only
cookies for its plain-HTTP localhost workflow; production deployments must use
HTTPS with `AUTH_SESSION_HTTPS_ONLY=true`.

## Public Fly.io demo and login counts

The live demo is <https://pytincture-example.fly.dev/>. It uses the demo
credentials above, HTTPS session cookies, and one Fly Machine in `iad` with
`min_machines_running = 0`: it stops while idle and starts on the next request.
The first visit after an idle stop can take a little longer.

Deploy from the latest `main`:

```bash
git pull --ff-only origin main
flyctl deploy --ha=false
```

Initial setup requires the `pytincture-example` app, one 1 GB `example_data`
volume in `iad`, and a random `PYTINCTURE_EXAMPLE_SESSION_SECRET` set as a Fly
secret. `fly.toml` configures the HTTPS origin, public bind address, health
check, and persistent paths. Keep one machine: each volume is local to its
machine, and independently scaled SQLite instances would have separate data.

Successful email/password logins are counted in `/data/login_metrics.sqlite3`
on the persistent volume. Counts survive idle stops and redeploys. View the
private all-time totals and daily counts for the last 30 UTC days with:

```bash
curl --fail --silent https://pytincture-example.fly.dev/healthz
flyctl ssh console -a pytincture-example -C "python -m example_metrics"
```

The health request wakes the machine if it is stopped. Add `--days 7` to the
Python command for a shorter daily report. There is no public metrics endpoint.
The report includes `successful_logins` and `unique_browsers`. Because the demo
account is shared, distinct browsers are an estimate of visitors rather than
identified people: clearing cookies or using another browser counts again.
A signed, HTTP-only visitor cookie lasts one year. Only hashes of random
browser/session identifiers and login times are stored; no emails, passwords
or IP addresses are recorded in the metrics database. Failed logins and page
refreshes are not counted.

For local tracking, set `PYTINCTURE_EXAMPLE_LOGIN_DB` to a database path outside
`example/`. Tracking is disabled locally when this variable is unset.

## Data store

The example stores books in SQLite by default. Nothing extra to install; the
database is created and seeded from `dataset.json` on first start.

BriskDB is available as a drop-in alternative, exercising the same BFF code
through a sharded-SQLite engine:

```bash
.venv/bin/pip install '.[briskdb]'
PYTINCTURE_EXAMPLE_STORE=briskdb ../.venv/bin/python run.py
```

| Variable | Default | Meaning |
|---|---|---|
| `PYTINCTURE_EXAMPLE_STORE` | `sqlite` | `sqlite` or `briskdb` |
| `PYTINCTURE_EXAMPLE_DB` | `/tmp/pytincture-example/books.db` | SQLite file |
| `PYTINCTURE_EXAMPLE_BRISKDB_DIR` | `/tmp/pytincture-example/briskdb` | BriskDB data directory |
| `PYTINCTURE_EXAMPLE_BRISKDB_SHARDS` | `4` | BriskDB shard count |

Both live outside the application directory, which Pytincture packages and
ships to the browser.

BriskDB is alpha software, which is why SQLite remains the default. Two of its
constraints are handled in `store_briskdb.py` and are worth knowing if you adapt
this code: sessions must be shared rather than opened per call, and schema
migration requires sole-process ownership (so `run.py` seeds at startup).

## Load test

The CI load profile creates 250 independent authenticated sessions, then runs
stages with 50, 100, and 250 active sessions. Each request exercises a realistic
server-paginated grid response containing the frontend maximum of 100 records.
Each session makes four calls, for 1,600 calls and 160,000 returned records over
the complete profile. Every stage requires zero errors, a p95 BFF latency no
greater than 1,000 ms, and at least 20 requests per second. Results are retained
as a JSON workflow artifact.

Run the same profile locally:

```bash
.venv/bin/pip install '.[load-test]'
.venv/bin/python tests/load_test.py --output load-results.json
```

The example endpoint caps `page_size` at 100 regardless of the caller's value.
These are regression thresholds for the GitHub runner and local development,
not production capacity guarantees. Use the command-line options to establish
deployment-specific stages, page sizes, latency, and throughput budgets.

## RC observation record

CI combines the authenticated browser result and paginated load result into a
versioned `rc1-observation.json` document. It records the exact example commit,
Pytincture candidate, widgetset pin (read from `example/widget.py`), UTC timestamp, Actions run URL,
environment, SHA-256 hash of each raw result, embedded measurements, and any
automatically detected findings. The document follows
[`contracts/rc-observation-v1.schema.json`](contracts/rc-observation-v1.schema.json)
and is retained as the `pytincture-rc1-observation` workflow artifact.

This is application observation evidence, not automatic release approval. A
reviewer must link an accepted run from the Pytincture qualification record;
failed observations or discovered P0/P1 defects remain release blockers.
