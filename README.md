# Pytincture authenticated example

This example qualifies the published Pytincture 1.0 release candidate with a
real dhxpyt application and an authenticated backend-for-frontend call.

## Run locally

```bash
python3.13 -m venv .venv
.venv/bin/pip install .
cd example
../.venv/bin/python run.py
```

Open <http://localhost:8070/> and sign in with the credentials displayed on
the login page:

- email: `demo@example.com`
- password: `demo-password`

The browser address remains `/py_ui` after login; cache-busting UUIDs are added
only to frontend and application-resource requests.

## Run with Docker

```bash
docker build -t pytincture-example .
docker run --rm -p 8070:8070 pytincture-example
```

Set `PYTINCTURE_EXAMPLE_SESSION_SECRET` to a private value when exposing the
demo outside a disposable local environment. The launcher disables secure-only
cookies for its plain-HTTP localhost workflow; production deployments must use
HTTPS with `AUTH_SESSION_HTTPS_ONLY=true`.

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
Pytincture candidate, dhxpyt widgetset, UTC timestamp, Actions run URL,
environment, SHA-256 hash of each raw result, embedded measurements, and any
automatically detected findings. The document follows
[`contracts/rc-observation-v1.schema.json`](contracts/rc-observation-v1.schema.json)
and is retained as the `pytincture-rc1-observation` workflow artifact.

This is application observation evidence, not automatic release approval. A
reviewer must link an accepted run from the Pytincture qualification record;
failed observations or discovered P0/P1 defects remain release blockers.
