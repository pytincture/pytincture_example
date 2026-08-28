"""Exercise the published Pytincture RC through the representative example."""

from __future__ import annotations

import json
import signal
import subprocess
import sys
import time
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


def main() -> None:
    service = subprocess.Popen(
        [sys.executable, "run.py"],
        cwd=EXAMPLE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        health = wait_for_service()
        assert health == {"status": "ok", "version": "1.0.0rc1"}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
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
            browser.close()
    finally:
        service.send_signal(signal.SIGINT)
        try:
            output, _ = service.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            service.kill()
            output, _ = service.communicate()
        if service.returncode not in (0, -signal.SIGINT):
            raise RuntimeError(
                f"Pytincture example exited with {service.returncode}:\n{output}"
            )


if __name__ == "__main__":
    main()
