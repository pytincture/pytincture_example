"""Browser smoke test for the example UI.

Drives a real Chromium via Playwright against an already-running service and
asserts the things that have actually broken before:

  * widgets are built exactly once (a duplicate load_ui() call doubled them)
  * the grid is populated from the authenticated BFF
  * form controls actually render
  * the Reports sidebar item opens the modal and fills it
  * no console errors, no failed requests

Setup (once):
    .venv/bin/pip install '.[browser-test]'
    .venv/bin/playwright install chromium

Run (service must be up: cd example && ../.venv/bin/python run.py):
    .venv/bin/python tests/ui_smoke.py [--headed] [--screenshot-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8070"
EMAIL = "demo@example.com"
PASSWORD = "demo-password"
BOOT_TIMEOUT_MS = 180_000

# Console noise that is not the application's fault.
IGNORED_CONSOLE = ("preloaded using link preload",)


def wait_for_service(timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{BASE_URL}/healthz", timeout=1) as response:
                return json.load(response)
        except (OSError, URLError):
            time.sleep(0.25)
    raise SystemExit(
        f"No healthy service at {BASE_URL}. Start it with:\n"
        "    cd example && ../.venv/bin/python run.py"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--headed", action="store_true", help="show the browser")
    parser.add_argument("--screenshot-dir", type=Path, default=None)
    args = parser.parse_args()

    health = wait_for_service()
    print(f"service healthy: {health}")

    failures: list[str] = []
    console_errors: list[str] = []
    failed_requests: list[str] = []

    def check(label: str, actual, expected) -> None:
        ok = actual == expected
        print(f"  {'PASS' if ok else 'FAIL'}  {label}: {actual!r}"
              + ("" if ok else f" (expected {expected!r})"))
        if not ok:
            failures.append(f"{label}: got {actual!r}, expected {expected!r}")

    def check_at_least(label: str, actual: int, minimum: int) -> None:
        ok = actual >= minimum
        print(f"  {'PASS' if ok else 'FAIL'}  {label}: {actual}"
              + ("" if ok else f" (expected >= {minimum})"))
        if not ok:
            failures.append(f"{label}: got {actual}, expected >= {minimum}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.on(
            "console",
            lambda m: console_errors.append(m.text)
            if m.type == "error" and not any(n in m.text for n in IGNORED_CONSOLE)
            else None,
        )
        page.on("pageerror", lambda e: console_errors.append(str(e)))
        page.on("requestfailed", lambda r: failed_requests.append(r.url))

        print("\nlogin")
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.get_by_placeholder("Email").fill(EMAIL)
        page.get_by_placeholder("Password").fill(PASSWORD)
        page.get_by_role("button", name="Login with Email").click()

        print("waiting for the app (Pyodide boot)")
        page.get_by_text("Book Details and Ratings").wait_for(timeout=BOOT_TIMEOUT_MS)
        check("url after login", page.url, f"{BASE_URL}/py_ui")

        print("\nwidgets built exactly once")
        # The heading attaches slightly before the widgets finish painting.
        page.locator(".dhx_grid").first.wait_for(timeout=60_000)
        for selector in (".dhx_grid", ".dhx_toolbar", ".dhx_sidebar", ".dhx_tabbar"):
            check(f"{selector} count", page.locator(selector).count(), 1)

        print("\ngrid populated from the BFF")
        page.locator(".dhx_grid .dhx_grid-row").first.wait_for(timeout=30_000)
        check_at_least("grid rows", page.locator(".dhx_grid .dhx_grid-row").count(), 10)

        print("\nper-column header filters")
        filters = page.locator(".dhx_grid-header input")
        check("filter inputs", filters.count(), 10)
        unfiltered = page.locator(".dhx_grid .dhx_grid-row").count()
        filters.first.fill("potter")
        page.wait_for_timeout(1500)
        filtered = page.locator(".dhx_grid .dhx_grid-row").count()
        ok = 0 < filtered < unfiltered
        print(f"  {'PASS' if ok else 'FAIL'}  'potter' narrows rows: {unfiltered} -> {filtered}")
        if not ok:
            failures.append(f"filter did not narrow rows: {unfiltered} -> {filtered}")
        titles = [
            t.strip()
            for t in page.locator(
                ".dhx_grid .dhx_grid-row .dhx_grid-cell:nth-child(1)"
            ).all_inner_texts()
            if t.strip()
        ]
        ok = bool(titles) and all("potter" in t.lower() for t in titles)
        print(f"  {'PASS' if ok else 'FAIL'}  every visible title matches: {len(titles)} rows")
        if not ok:
            failures.append(f"non-matching rows survived the filter: {titles[:3]}")
        filters.first.fill("")
        page.wait_for_timeout(1200)
        check("rows restored after clearing", 
              page.locator(".dhx_grid .dhx_grid-row").count(), unfiltered)

        print("\nForm View tab renders controls")
        page.get_by_text("FORM VIEW").click()
        page.wait_for_timeout(1500)
        check_at_least("form inputs", page.locator(".dhx_form input").count(), 5)

        print("\nReports opens the modal")
        page.get_by_text("Reports", exact=True).first.click()
        page.locator(".dhx_window").wait_for(timeout=15_000)
        check("modal count", page.locator(".dhx_window").count(), 1)
        # The form is attached and then filled from the BFF; wait for the
        # controls to exist before counting them.
        page.locator(".dhx_window input").first.wait_for(timeout=15_000)
        check_at_least("modal inputs", page.locator(".dhx_window input").count(), 5)

        page.wait_for_timeout(2500)
        title = page.locator(".dhx_window input").first.input_value()
        ok = bool(title.strip())
        print(f"  {'PASS' if ok else 'FAIL'}  modal populated from BFF: {title!r}")
        if not ok:
            failures.append("modal first field empty")

        print("\ndouble-clicking a grid row opens that book")
        page.locator(".dhx_window .dhx_button[data-dhx-id='close']").click()
        page.wait_for_timeout(800)
        check("modal closed", page.locator(".dhx_window").count(), 0)

        page.get_by_text("GRID VIEW").click()
        page.wait_for_timeout(1000)
        target_row = page.locator(".dhx_grid .dhx_grid-row").nth(5)
        expected = target_row.locator(".dhx_grid-cell").first.inner_text().strip()
        target_row.dblclick()
        page.locator(".dhx_window input").first.wait_for(timeout=15_000)
        page.wait_for_timeout(1200)
        shown = page.locator(".dhx_window input").first.input_value().strip()
        # Rendered grid text collapses runs of whitespace; the input keeps the
        # raw value. Compare on collapsed whitespace.
        collapse = lambda text: " ".join(text.split())
        ok = bool(shown) and collapse(shown) == collapse(expected)
        print(f"  {'PASS' if ok else 'FAIL'}  form shows the double-clicked row: {shown!r}"
              + ("" if ok else f" (grid cell said {expected!r})"))
        if not ok:
            failures.append(f"dblclick row mismatch: form {shown!r} vs grid {expected!r}")

        print("\nediting and saving persists across a reload")
        import time as _time
        new_title = f"SMOKE {int(_time.time())}"
        page.locator(".dhx_window input").first.fill(new_title)
        page.get_by_role("button", name="Save").click()
        page.wait_for_timeout(2500)
        # The modal is showing the row double-clicked above (index 5), so assert
        # against that row, not row 0.
        edited_cell = lambda: page.locator(
            ".dhx_grid .dhx_grid-row").nth(5).locator(
            ".dhx_grid-cell").first.inner_text().strip()
        check("grid row updated after save", edited_cell(), new_title)

        page.reload(wait_until="domcontentloaded")
        page.get_by_text("Book Details and Ratings").wait_for(timeout=BOOT_TIMEOUT_MS)
        page.locator(".dhx_grid .dhx_grid-row").first.wait_for(timeout=30_000)
        page.wait_for_timeout(1500)
        check("survives reload (persisted to the store)", edited_cell(), new_title)

        if args.screenshot_dir:
            args.screenshot_dir.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=args.screenshot_dir / "ui_smoke.png")
            print(f"\nscreenshot -> {args.screenshot_dir / 'ui_smoke.png'}")

        browser.close()

    print("\nconsole errors:", console_errors or "none")
    print("failed requests:", failed_requests or "none")
    failures += [f"console error: {e}" for e in console_errors]
    failures += [f"failed request: {u}" for u in failed_requests]

    print()
    if failures:
        print(f"FAILED ({len(failures)})")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
