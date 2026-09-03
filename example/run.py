"""Run the authenticated Pytincture example service.

Uses the Pytincture 1.0 ASGI factory (`create_app` + `PytinctureConfig`), which
owns its own configuration, BFF registry and state rather than mutating global
environment settings.

Two supported entrypoints:

    python run.py                      # this file, binds 127.0.0.1:8070
    uvicorn run:app --host 127.0.0.1   # the module-level ASGI app
"""

import os
from pathlib import Path

import store
from pytincture import PytinctureConfig, create_app


HERE = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8070

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo-password"
DEMO_PASSWORD_HASH = (
    '{"demo@example.com":"$argon2id$v=19$m=65536,t=3,p=4$'
    "1nAFATBkZHf7FYm10EoAqw$"
    'bcQeiCVDJV5nH2dSoHhYtUlyLARtmS1ce7UBSUXokYQ"}'
)

# Seed the store before anything else opens it. BriskDB requires sole-process
# ownership for schema migration, so this cannot be left to the first BFF call.
store.initialise()
print(f"example store: {store.describe()}", flush=True)

app = create_app(
    PytinctureConfig(
        modules_path=str(HERE),
        default_application="py_ui",
        enable_user_login=True,
        # ALLOWED_EMAILS, AUTH_PASSWORD_HASHES and LOGIN_HELP_TEXT are not typed
        # PytinctureConfig fields. create_app() gives the backend a module-local
        # environment facade built from this config and never reads the
        # process-global environment, so they are passed here rather than set on
        # os.environ; PytinctureConfig.to_environ() seeds from this mapping.
        environment={
            "ALLOWED_EMAILS": DEMO_EMAIL,
            "AUTH_PASSWORD_HASHES": DEMO_PASSWORD_HASH,
            "LOGIN_HELP_TEXT": f"Demo credentials: {DEMO_EMAIL} / {DEMO_PASSWORD}",
        },
        # The disposable example serves plain HTTP on localhost. Production
        # deployments must use HTTPS and leave secure cookies enabled.
        #
        # Pytincture 1.0.0rc4 fails startup for authenticated deployments unless
        # allowed_hosts holds exact hostnames and canonical_origin is one HTTPS
        # origin. allow_development_auth_origin is the documented loopback-only
        # opt-out for local HTTP auth testing; it requires session_https_only to
        # be False and cannot be combined with trusted proxy headers or the
        # production host/origin controls.
        allow_development_auth_origin=True,
        session_https_only=False,
        session_secret=os.getenv(
            "PYTINCTURE_EXAMPLE_SESSION_SECRET",
            "pytincture-example-session-secret-0123456789abcdef",
        ),
    )
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
