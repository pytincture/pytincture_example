"""Exercise the published Pytincture RC through the representative example."""

from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "example"
BASE_URL = "http://127.0.0.1:8070"


def wait_for_service(timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{BASE_URL}/healthz", timeout=1) as response:
                return json.load(response)
        except (OSError, URLError):
            time.sleep(0.25)
    raise RuntimeError("Pytincture example did not become healthy")


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("acceptance-results.json")
    )
    args = parser.parse_args()
    began = time.perf_counter()
    evidence = {
        "schema_version": 1,
        "started_at": timestamp(),
        "target": BASE_URL,
        "status": "failed",
    }
    service = subprocess.Popen(
        [sys.executable, "run.py"],
        cwd=EXAMPLE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        health = wait_for_service()
        evidence["health"] = health
        # Assert against the installed release rather than a hard-pinned
        # version, so the check survives a Pytincture upgrade.
        from pytincture import __version__ as pytincture_version

        assert health == {"status": "ok", "version": pytincture_version}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.add_init_script(
                """
                window.__exampleLifecycle = [];
                window.addEventListener(
                    "pytincture:lifecycle",
                    event => window.__exampleLifecycle.push(event.detail),
                );
                """
            )
            console_errors: list[str] = []
            failed_requests: list[str] = []
            page.on(
                "console",
                lambda message: console_errors.append(message.text)
                if message.type == "error"
                else None,
            )
            page.on("pageerror", lambda error: console_errors.append(str(error)))
            page.on("requestfailed", lambda request: failed_requests.append(request.url))

            page.goto(BASE_URL, wait_until="domcontentloaded")
            page.get_by_text(
                "Demo credentials: demo@example.com / demo-password"
            ).wait_for()
            page.get_by_placeholder("Email").fill("demo@example.com")
            page.get_by_placeholder("Password").fill("demo-password")
            page.get_by_role("button", name="Login with Email").click()

            page.get_by_text("Book Details and Ratings").wait_for(timeout=120_000)
            assert page.url == f"{BASE_URL}/py_ui"
            assert page.locator(".dhx_grid").count() == 1

            bff = page.evaluate(
                """async () => {
                    const csrf = document.cookie
                        .split(';')
                        .map(value => value.trim().split('='))
                        .find(([name]) => name === 'pytincture_csrf')
                        ?.slice(1).join('=') || '';
                    const response = await fetch(
                        '/classcall/py_ui_data.py/py_ui_data/dataset',
                        {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRF-Token': csrf,
                            },
                            body: JSON.stringify({kwargs: {}}),
                        },
                    );
                    return {status: response.status, body: await response.text()};
                }"""
            )
            assert bff["status"] == 200
            assert isinstance(json.loads(bff["body"]), str)
            assert not console_errors, console_errors
            assert not failed_requests, failed_requests
            lifecycle = page.evaluate("() => window.__exampleLifecycle || []")
            ready = next(
                event
                for event in reversed(lifecycle)
                if event.get("type") == "ready"
            )
            evidence.update(
                {
                    "status": "passed",
                    "browser": "chromium",
                    "visible_url": page.url,
                    "clean_address_bar": "?" not in page.url,
                    "login_help_visible": True,
                    "authenticated_email": "demo@example.com",
                    "grid_count": page.locator(".dhx_grid").count(),
                    "bff_status": bff["status"],
                    "console_errors": console_errors,
                    "failed_requests": failed_requests,
                    "compatibility": ready.get("compatibility", {}),
                }
            )
            browser.close()
    except Exception as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        service.send_signal(signal.SIGINT)
        try:
            output, _ = service.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            service.kill()
            output, _ = service.communicate()
        if service.returncode not in (0, -signal.SIGINT):
            service_error = RuntimeError(
                f"Pytincture example exited with {service.returncode}:\n{output}"
            )
            evidence["status"] = "failed"
            evidence["error"] = f"RuntimeError: {service_error}"
        else:
            service_error = None
        evidence["completed_at"] = timestamp()
        evidence["duration_ms"] = round((time.perf_counter() - began) * 1000)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{json.dumps(evidence, indent=2)}\n")
        if service_error is not None:
            raise service_error


if __name__ == "__main__":
    main()
