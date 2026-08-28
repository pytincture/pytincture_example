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
demo outside a disposable local environment.
