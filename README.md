# Pytincture authenticated example

This example qualifies the published Pytincture 1.0 release candidate with a
real dhxpyt application and an authenticated backend-for-frontend call.

## Run locally

```bash
python3.13 -m venv .venv
.venv/bin/pip install --find-links example .
cd example
../.venv/bin/python run.py
```

`--find-links example` resolves the pinned `dhxpyt` from the wheel vendored in
`example/` rather than from PyPI. That same wheel is what the backend serves to
the browser, so the example installs and boots with no PyPI round-trip for the
widgetset -- previously it fetched dhxpyt from `files.pythonhosted.org` on every
cold start, which meant it could not boot offline.

Replacing the wheel means updating three things together: the file in
`example/`, the `dhxpyt==` pin in `pyproject.toml`, and `__version__` in
`example/widget.py`. The `.gitignore` un-ignores the pinned filename
specifically, so stray development wheels are still kept out of git.

Open <http://localhost:8070/> and sign in with the credentials displayed on
the login page:

- email: `demo@example.com`
- password: `demo-password`

The browser address remains `/py_ui` after login; cache-busting UUIDs are added
only to frontend and application-resource requests.

## Run with Docker

To disable Swagger and OpenAPI in production, start with
`PYTINCTURE_API_DOCS_MODE=disabled`. The example launcher reads this setting;
all docs/schema URLs return 404 while the application and BFF calls keep their
normal authentication. The local default is `public`; `authenticated` is also
available to require login for documentation.

```bash
docker build -t pytincture-example .
docker run --rm -p 8070:8070 pytincture-example
```

Set `PYTINCTURE_EXAMPLE_SESSION_SECRET` to a private value when exposing the
demo outside a disposable local environment. The launcher disables secure-only
cookies for its plain-HTTP localhost workflow; production deployments must use
HTTPS with `AUTH_SESSION_HTTPS_ONLY=true`.

## Data store

The example stores books in SQLite by default. Nothing extra to install; the
database is created and seeded from `dataset.json` on first start.

BriskDB is available as a drop-in alternative, exercising the same BFF code
through a sharded-SQLite engine:

```bash
.venv/bin/pip install --find-links example '.[briskdb]'
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
.venv/bin/pip install --find-links example '.[load-test]'
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

### App-branded module API documentation and tokens

Open `http://127.0.0.1:8070/py_ui/py_ui_data/bff-docs`. The title is
**Book Library API**, from `APP_TITLE` in `example/py_ui.py`. The application-wide
`/py_ui/bff-docs` and global docs URLs return 404. The module URL omits `.py`;
Swagger displays short paths such as `/py_ui_data/ping` relative to
the server/base `/py_ui/classcall/py_ui_data`. Existing `.py` call URLs still work.
Nested modules follow the same pattern, e.g. `/py_ui/services/catalog/bff-docs`.

Sign in directly in **API access** with `demo@example.com` / `demo-password`.
The login help message is also shown there. **Generate API token** creates a
credential valid for at most 15 minutes and fills Swagger's **Authorize** control.
Use `Authorization: Bearer <token>` in API clients; no browser cookie is needed.
Tokens are kept only in the tab's memory.

The `ping` and `dataset_page` methods in `example/py_ui_data.py` carry
`@bff_external`. That declaration replaces per-method environment allowlists:

```python
@backend_for_frontend
class py_ui_data:
    @bff_external
    def ping(self, value):
        return {"value": value}
```

The example enables `allow_development_auth_origin=True`, so Swagger includes
session-based `dataset` and `update_book` by default too. Outside explicit
development mode, an omitted flag hides session methods. Use
`@backend_for_frontend(include_session_methods_in_docs=False)` to show only
external methods even in development, or `True` to include session methods in
other modes. `None` inherits the mode. This does not let external-scoped tokens
invoke session-only methods. `PYTINCTURE_API_DOCS_SCOPE=public` always restricts
docs to external/public methods, including during development.

External methods require an API token for cookie-free requests; anonymous
requests return 401. Authenticated app calls keep using their normal session
and CSRF protection, so the grid and editing flows still work. Choose
**External methods only** in Swagger to generate the restricted token. Token
User-token issuance requires sign-in. Application credentials below do not.

This example explicitly sets `enable_bff_api_tokens=True`. Set
`ENABLE_BFF_API_TOKENS=false` to disable token issuance/acceptance, or
`PYTINCTURE_API_DOCS_MODE=disabled` to disable documentation while keeping API
access available. Framework applications opt in through
`PytinctureConfig(enable_bff_api_tokens=True, ...)`. Shared session revocation
is required for immediate revocation of issued copies; otherwise tokens expire
with their original session or after at most 15 minutes.

### Credentials for another application

This branch pins the exact RC7 framework source commit so its acceptance tests
can run before publication. Switch the dependency to `pytincture[password]==1.0.0rc7`
after the candidate is published and before merging this example update.

With the updated framework, register a client outside the served `example/`
directory. Run these commands from the repository root (using your environment's
Python with this framework version installed):

```sh
mkdir -p "$HOME/.local/share/pytincture-example"
chmod 700 "$HOME/.local/share/pytincture-example"
export BFF_API_CLIENT_REGISTRY="$HOME/.local/share/pytincture-example/clients.sqlite3"
.venv/bin/python -m pytincture.api_clients --registry "$BFF_API_CLIENT_REGISTRY" \
  create --application py_ui --client-id reporting-service \
  --allow py_ui_data:py_ui_data:dataset_page \
  --allow py_ui_data:py_ui_data:ping
```

Keep the generated secret securely on the consuming application's server.
Start/restart the example with `BFF_API_CLIENT_REGISTRY` set. In module Swagger,
expand **Application credentials**, enter the client ID and secret, and generate
an application token without signing in as a user. For automated access, send:

```http
POST /py_ui/auth/client-token
Content-Type: application/json

{"grant_type":"client_credentials","client_id":"reporting-service","client_secret":"<generated secret>"}
```

Use the returned access token as `Authorization: Bearer <access_token>` for
`/py_ui/classcall/py_ui_data/py_ui_data/dataset_page` or `ping`. It expires in
900 seconds; exchange the credentials again before expiry. `dataset` and
`update_book` remain unavailable to this client. A class grant such as
`--allow py_ui_data:py_ui_data` still only permits decorated external methods.

Manage the client without restarting the server:

```sh
.venv/bin/python -m pytincture.api_clients --registry "$BFF_API_CLIENT_REGISTRY" rotate reporting-service
.venv/bin/python -m pytincture.api_clients --registry "$BFF_API_CLIENT_REGISTRY" disable reporting-service
.venv/bin/python -m pytincture.api_clients --registry "$BFF_API_CLIENT_REGISTRY" enable reporting-service
.venv/bin/python -m pytincture.api_clients --registry "$BFF_API_CLIENT_REGISTRY" audit
```

Rotation, disabling/re-enabling, and `set-grants` invalidate earlier client tokens
on the next call. Existing in-flight calls may finish. All workers must use the
same local registry; distributed deployments need a shared registry provider.
Leave the registry setting empty to disable this feature. To disable all BFF
tokens, clear it and set `ENABLE_BFF_API_TOKENS=false`. Production requires HTTPS
and a strong persistent signing secret; this example's HTTP exception is
restricted to localhost. Never use its demo signing secret in production.
