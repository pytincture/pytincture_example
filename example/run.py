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
from urllib.parse import urlsplit

import store
from pytincture import PytinctureConfig, create_app


HERE = Path(__file__).resolve().parent
HOST = os.getenv("PYTINCTURE_EXAMPLE_HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8070"))
PUBLIC_ORIGIN = os.getenv("PYTINCTURE_EXAMPLE_PUBLIC_ORIGIN", "").rstrip("/")
SESSION_SECRET = os.getenv("PYTINCTURE_EXAMPLE_SESSION_SECRET", "")
if PUBLIC_ORIGIN and not SESSION_SECRET:
    raise RuntimeError("Public deployment requires PYTINCTURE_EXAMPLE_SESSION_SECRET")
SESSION_SECRET = SESSION_SECRET or "pytincture-example-session-secret-0123456789abcdef"

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


def limit_overrides() -> dict:
    """Forward resource limits from the environment, when set.

    These are typed PytinctureConfig fields, and create_app() reads its
    configuration from that object rather than from the process environment,
    so setting the variables alone has no effect -- they have to be passed
    through explicitly. Unset means Pytincture's own default.

    The load profile uses this to widen four limits that its shape collides
    with: it signs in one session per simulated user (login throttle, argon2
    admission gate) and drives every session from one host (BFF ingress
    concurrency, which is capped per peer). Nothing else should touch them --
    the defaults are the protection, and a real deployment sees many peers.
    """
    fields = (
        ("login_rate_limit_attempts", "AUTH_LOGIN_RATE_LIMIT_ATTEMPTS", int),
        (
            "login_rate_limit_window_seconds",
            "AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS",
            int,
        ),
        ("password_hash_max_concurrency", "AUTH_PASSWORD_HASH_MAX_CONCURRENCY", int),
        (
            "password_hash_queue_timeout_seconds",
            "AUTH_PASSWORD_HASH_QUEUE_TIMEOUT_SECONDS",
            float,
        ),
        ("bff_max_concurrency", "BFF_MAX_CONCURRENCY", int),
        ("bff_max_queue", "BFF_MAX_QUEUE", int),
        ("bff_queue_timeout_seconds", "BFF_QUEUE_TIMEOUT_SECONDS", float),
        (
            "bff_request_ingress_max_concurrency",
            "BFF_REQUEST_INGRESS_MAX_CONCURRENCY",
            int,
        ),
        (
            "bff_request_ingress_max_concurrency_per_peer",
            "BFF_REQUEST_INGRESS_MAX_CONCURRENCY_PER_PEER",
            int,
        ),
        ("bff_request_ingress_max_queue", "BFF_REQUEST_INGRESS_MAX_QUEUE", int),
        (
            "bff_request_ingress_queue_timeout_seconds",
            "BFF_REQUEST_INGRESS_QUEUE_TIMEOUT_SECONDS",
            float,
        ),
    )
    overrides = {}
    for field, variable, cast in fields:
        value = os.getenv(variable, "").strip()
        if value:
            overrides[field] = cast(value)
    if overrides:
        print(f"limit overrides: {overrides}", flush=True)
    return overrides


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
        # Fly terminates HTTPS; local development keeps its loopback HTTP flow.
        allow_development_auth_origin=not bool(PUBLIC_ORIGIN),
        session_https_only=bool(PUBLIC_ORIGIN),
        allowed_hosts=(urlsplit(PUBLIC_ORIGIN).hostname,) if PUBLIC_ORIGIN else (),
        canonical_origin=PUBLIC_ORIGIN or None,
        trusted_proxy_headers=bool(PUBLIC_ORIGIN),
        session_secret=SESSION_SECRET,
        api_docs_mode=os.getenv("PYTINCTURE_API_DOCS_MODE", "public"),
        diagnostic_details_mode="minimal" if PUBLIC_ORIGIN else "public",
        **limit_overrides(),
    )
)

LOGIN_DATABASE = os.getenv("PYTINCTURE_EXAMPLE_LOGIN_DB", "")
if LOGIN_DATABASE:
    from example_metrics import LoginMetricsMiddleware, LoginStore

    app.add_middleware(
        LoginMetricsMiddleware,
        store=LoginStore(LOGIN_DATABASE),
        secret=SESSION_SECRET,
        secure=bool(PUBLIC_ORIGIN),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host=HOST, port=PORT,
        proxy_headers=bool(PUBLIC_ORIGIN),
        forwarded_allow_ips="*" if PUBLIC_ORIGIN else "127.0.0.1",
    )
