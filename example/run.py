"""Run the authenticated Pytincture example service."""

import os

from pytincture import launch_service


DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo-password"


if __name__ == "__main__":
    launch_service(
        modules_folder=".",
        default_application="py_ui",
        env_vars={
            "ALLOWED_EMAILS": DEMO_EMAIL,
            "AUTH_PASSWORD_HASHES": (
                '{"demo@example.com":"$argon2id$v=19$m=65536,t=3,p=4$'
                "1nAFATBkZHf7FYm10EoAqw$"
                'bcQeiCVDJV5nH2dSoHhYtUlyLARtmS1ce7UBSUXokYQ"}'
            ),
            # The disposable example serves plain HTTP on localhost. Production
            # deployments must use HTTPS and leave secure cookies enabled.
            "AUTH_SESSION_HTTPS_ONLY": "false",
            "ENABLE_USER_LOGIN": "true",
            "LOGIN_HELP_TEXT": (
                f"Demo credentials: {DEMO_EMAIL} / {DEMO_PASSWORD}"
            ),
            "SAML_SECRET_KEY": os.getenv(
                "PYTINCTURE_EXAMPLE_SESSION_SECRET",
                "pytincture-example-session-secret-0123456789abcdef",
            ),
        },
    )
