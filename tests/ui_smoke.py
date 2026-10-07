"""Browser smoke test for the example UI.

Drives a real Chromium via Playwright against an already-running service and
asserts the things that have actually broken before:

  * widgets are built exactly once (a duplicate load_ui() call doubled them)
  * the grid is populated from the authenticated BFF
  * only the active tab is shown
  * clicking a row highlights exactly one row and mirrors it into Form View
  * the grid filter narrows and restores the rows
  * double-click and the right-click menu open the row in the modal
  * saving keeps the publication date intact (M/D/YYYY in the store, ISO in
    the native date picker)
  * light/dark follows the OS, toggles, and is remembered
  * the Reports sidebar item opens the modal and fills it
  * a successful save closes the modal
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

# The grid's body rows; the header row carries no data-row-id.
ROWS = ".wapyt-datatable tbody tr[data-row-id]"
SELECTED = ".wapyt-datatable tbody tr[data-selected='true']"
# The Form View tab's form, as opposed to the one in the modal.
FORM_VIEW = ".wapyt-tab-panel .wapyt-form"
MODAL = ".wapyt-modal"


def collapse(text: str) -> str:
    return " ".join(text.split())


# Console noise that is not the application's fault.
IGNORED_CONSOLE = ("preloaded using link preload",)


def _is_expected_request_failure(request) -> bool:
    """True for aborts the runtime makes on purpose.

    Pytincture probes for a backend-served widgetset wheel with a HEAD it
    aborts once the headers arrive, so Chromium reports net::ERR_ABORTED even
    though the server answered 200. This only shows up when a wheel is served
    from modules_path -- the PyPI path does no probe -- so it would fail the
    suite for anyone developing against a locally built widgetset.
    """
    failure = (request.failure or "") if hasattr(request, "failure") else ""
    return "ERR_ABORTED" in failure and ".whl" in request.url


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
        page.on(
            "requestfailed",
            lambda r: None if _is_expected_request_failure(r)
            else failed_requests.append(r.url),
        )

        def cell_text(row: int, column: int) -> str:
            return page.locator(ROWS).nth(row).locator("td").nth(column).inner_text().strip()

        def field_value(scope: str, field: str) -> str:
            return page.locator(f'{scope} [data-field-id="{field}"] input').first.input_value()

        def modal_visible() -> bool:
            # A hidden modal stays in the DOM; only its overlay's display changes.
            return page.locator(".wapyt-modal-overlay").first.is_visible()

        print("\nlogin")
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.get_by_placeholder("Email").fill(EMAIL)
        page.get_by_placeholder("Password").fill(PASSWORD)
        page.get_by_role("button", name="Login with Email").click()

        print("waiting for the app (Pyodide boot)")
        page.get_by_text("Book Details and Ratings").wait_for(timeout=BOOT_TIMEOUT_MS)
        # Since rc12 the app page lives at /py_ui/ (the bare path 307s there).
        check("url after login", page.url, f"{BASE_URL}/py_ui/")

        print("\nwidgets built exactly once")
        # The heading attaches slightly before the widgets finish painting.
        page.locator(".wapyt-datatable").first.wait_for(timeout=60_000)
        for selector in (".wapyt-datatable", ".wapyt-toolbar", ".wapyt-sidebar", ".wapyt-tabwidget"):
            check(f"{selector} count", page.locator(selector).count(), 1)

        print("\ngrid populated from the BFF")
        page.locator(ROWS).first.wait_for(timeout=30_000)
        check_at_least("grid rows", page.locator(ROWS).count(), 10)

        print("\nonly the active tab is shown")
        # Form and DataTable take over the display of the element they mount
        # on; mounted straight onto a tab panel they un-hid the inactive tab.
        check("form view hidden behind the grid", page.locator(FORM_VIEW).is_visible(), False)

        print("\nrow selection highlight")
        check("nothing selected before clicking", page.locator(SELECTED).count(), 0)
        page.locator(ROWS).nth(2).locator("td").first.click()
        page.wait_for_timeout(500)
        check("one row highlighted after click", page.locator(SELECTED).count(), 1)
        selected_title = cell_text(2, 0)

        print("\ngrid filter")
        filters = page.locator(".wapyt-datatable-filter")
        check("filter inputs", filters.count(), 1)
        unfiltered = page.locator(ROWS).count()
        filters.fill("potter")
        page.wait_for_timeout(800)
        filtered = page.locator(ROWS).count()
        ok = 0 < filtered < unfiltered
        print(f"  {'PASS' if ok else 'FAIL'}  'potter' narrows rows: {unfiltered} -> {filtered}")
        if not ok:
            failures.append(f"filter did not narrow rows: {unfiltered} -> {filtered}")
        # The filter matches across every column; each of these books has
        # "Potter" in its title.
        titles = [cell_text(index, 0) for index in range(filtered)]
        ok = bool(titles) and all("potter" in t.lower() for t in titles)
        print(f"  {'PASS' if ok else 'FAIL'}  every visible title matches: {len(titles)} rows")
        if not ok:
            failures.append(f"non-matching rows survived the filter: {titles[:3]}")
        filters.fill("")
        page.wait_for_timeout(800)
        check("rows restored after clearing", page.locator(ROWS).count(), unfiltered)

        print("\nForm View tab mirrors the selected row")
        page.locator(".wapyt-tab", has_text="Form View").click()
        page.wait_for_timeout(800)
        check("form view visible", page.locator(FORM_VIEW).is_visible(), True)
        check("grid hidden behind the form", page.locator(".wapyt-datatable").is_visible(), False)
        check_at_least("form inputs", page.locator(f"{FORM_VIEW} input").count(), 5)
        shown = field_value(FORM_VIEW, "title")
        check("form shows the selected book", collapse(shown), collapse(selected_title))
        # The store keeps M/D/YYYY; the native date picker needs ISO.
        date = field_value(FORM_VIEW, "publication_date")
        ok = len(date) == 10 and date[4] == "-" and date[7] == "-"
        print(f"  {'PASS' if ok else 'FAIL'}  date reaches the picker as ISO: {date!r}")
        if not ok:
            failures.append(f"publication date not ISO in the form: {date!r}")
        page.locator(".wapyt-tab", has_text="Grid View").click()
        page.wait_for_timeout(500)

        print("\nReports opens the modal")
        page.locator(".wapyt-sidebar-item", has_text="Reports").click()
        page.locator(MODAL).wait_for(timeout=15_000)
        check("modal visible", modal_visible(), True)
        # The form is filled from the BFF; wait for the title to arrive.
        page.wait_for_function(
            f"""() => document.querySelector('{MODAL} [data-field-id="title"] input')?.value""",
            timeout=15_000,
        )
        check_at_least("modal inputs", page.locator(f"{MODAL} input").count(), 5)
        title = field_value(MODAL, "title")
        ok = bool(title.strip())
        print(f"  {'PASS' if ok else 'FAIL'}  modal populated from BFF: {title!r}")
        if not ok:
            failures.append("modal first field empty")

        print("\ndouble-clicking a grid row opens that book")
        page.locator(".wapyt-modal-close").click()
        page.wait_for_timeout(500)
        check("modal closed", modal_visible(), False)

        expected = cell_text(5, 0)
        page.locator(ROWS).nth(5).locator("td").first.dblclick()
        page.wait_for_timeout(1000)
        shown = field_value(MODAL, "title")
        # Rendered grid text collapses runs of whitespace; the input keeps the
        # raw value. Compare on collapsed whitespace.
        ok = bool(shown) and collapse(shown) == collapse(expected)
        print(f"  {'PASS' if ok else 'FAIL'}  form shows the double-clicked row: {shown!r}"
              + ("" if ok else f" (grid cell said {expected!r})"))
        if not ok:
            failures.append(f"dblclick row mismatch: form {shown!r} vs grid {expected!r}")

        print("\nthe grid context menu opens a row")
        page.locator(".wapyt-modal-close").click()
        page.wait_for_timeout(500)
        expected = cell_text(7, 0)
        page.locator(ROWS).nth(7).locator("td").first.click(button="right")
        page.locator(".wapyt-cmenu").wait_for(timeout=5_000)
        page.get_by_role("menuitem", name="Edit").click()
        page.wait_for_timeout(1000)
        check("modal opened from the menu", modal_visible(), True)
        shown = field_value(MODAL, "title")
        check("menu opens the right-clicked row", collapse(shown), collapse(expected))
        page.locator(".wapyt-modal-close").click()
        page.wait_for_timeout(500)

        print("\nediting and saving persists across a reload")
        page.locator(ROWS).nth(5).locator("td").first.dblclick()
        page.wait_for_timeout(1000)
        new_title = f"SMOKE {int(time.time())}"
        saved_date = cell_text(5, 3)
        page.locator(f'{MODAL} [data-field-id="title"] input').fill(new_title)
        page.locator(MODAL).get_by_role("button", name="Save").click()
        page.wait_for_timeout(2500)
        # Closing is the only save confirmation, so it is part of the contract:
        # the modal stays put on a rejected write.
        check("modal closes after a successful save", modal_visible(), False)
        check("grid row updated after save", cell_text(5, 0), new_title)
        # The date goes through the picker as ISO and must come back as the
        # store's M/D/YYYY, not rewritten.
        check("publication date survives the save", cell_text(5, 3), saved_date)

        page.reload(wait_until="domcontentloaded")
        page.get_by_text("Book Details and Ratings").wait_for(timeout=BOOT_TIMEOUT_MS)
        page.locator(ROWS).first.wait_for(timeout=30_000)
        page.wait_for_timeout(1000)
        check("survives reload (persisted to the store)", cell_text(5, 0), new_title)

        print("\nlight / dark mode")
        theme = lambda: page.evaluate(
            "() => document.documentElement.getAttribute('data-wapyt-theme')"
        )
        theme_button = page.locator(".wapyt-toolbar-btn[data-id='theme']")
        # Chromium defaults to prefers-color-scheme: light and nothing has been
        # stored yet, so the app should have started from the OS preference.
        check("starts from the OS preference", theme(), "light")
        check("toggle offers Dark", theme_button.inner_text().strip(), "Dark")
        theme_button.click()
        page.wait_for_timeout(600)
        check("toggle switches to dark", theme(), "dark")
        check("toggle now offers Light", theme_button.inner_text().strip(), "Light")
        check("choice remembered",
              page.evaluate("() => localStorage.getItem('py_ui.theme')"), "dark")
        # wapyt themes are CSS-only, so widgets built earlier must survive it.
        check_at_least("grid survives the switch", page.locator(ROWS).count(), 10)
        page.emulate_media(color_scheme="dark")
        page.emulate_media(color_scheme="light")
        page.wait_for_timeout(600)
        check("an explicit choice pins the mode", theme(), "dark")

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
