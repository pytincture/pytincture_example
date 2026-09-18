# Runtime-choice feature example

Use branch `feat/browser-runtime-choice` in both pytincture and this repository.
This example uses the framework's actual runtime setting, app manifest, public
asset delivery and BFF routes. The original `py_ui` application remains intact;
`runtime_books` is the portable subset with a runtime picker.

First install the dependencies listed in [the original experiment](../browser-runtime/README.md):
Python 3.11 with Transcrypt 3.9.4 in `../browser-runtime/.venv`, the locked npm
MicroPython package under `../browser-runtime/node_modules`, and a Python 3.13
environment with the feature-branch framework (`password` extra) and Playwright.

From this directory, using that Python 3.13 environment:

```sh
export PYTHONPATH="$HOME/repos/pytincture-runtime-choice"
python build.py
python server.py
```

Open <http://127.0.0.1:8093/runtime_books>. The login page shows the example's
public demo credentials: `demo@example.com` / `demo-password`. Choose **Pyodide**,
**MicroPython**, or **Transcrypt** in the browser-runtime picker. Changing engines
reloads the page and discards unsaved edits. The small timer is a convenient
observation, not a controlled benchmark.

The default is Pyodide. To try a different default, set
`PYTINCTURE_BROWSER_RUNTIME=micropython` before starting this server. The server
explicitly enables URL selection for this experiment. A new session secret is
generated on each start. Its disposable database is separate from the normal
example, at `~/Library/Caches/pytincture-runtime-choice/books.db`.

Run `python verify.py` with the server running to verify all engines, no Pyodide
downloads for the alternatives, filtering, save/reload, invalid-CSRF rejection,
anonymous denial, picker switching and startup of the full original example.
Results are saved in [results.json](results.json). Only Chromium is covered by
this example's acceptance script so far.

The build copies explicitly selected frontend files into ignored
`example/runtime_books/`. It does not copy backend Python into the public source
bundle. The existing public asset allowlist exposes this directory only for
`runtime_books`. No production service, database, main branch or release is
modified by running the example.
