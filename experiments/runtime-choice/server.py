"""Authenticated feature-branch example with its own disposable database."""
import os
import secrets
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = Path.home()/'Library/Caches/pytincture-runtime-choice'
CACHE.mkdir(parents=True, exist_ok=True)
os.environ['PYTINCTURE_EXAMPLE_DB'] = str(CACHE/'books.db')
os.environ['PYTINCTURE_EXAMPLE_SESSION_SECRET'] = secrets.token_urlsafe(48)
sys.path.insert(0, str(HERE.parents[1]/'example'))
import run
from pytincture import create_app

base = run.app.state.pytincture_config
app = create_app(replace(
    base,
    default_application='runtime_books',
    browser_runtime=os.getenv('PYTINCTURE_BROWSER_RUNTIME', 'pyodide'),
    allow_runtime_selection=True,
    environment={**base.environment, 'PYTINCTURE_PUBLIC_ASSET_PATHS':
                 '{"runtime_books": ["runtime_books/*"]}'},
))
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8093)
