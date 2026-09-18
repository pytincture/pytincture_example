"""Build explicitly public frontend assets; never copy backend modules."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / 'browser-runtime'
OUT = HERE.parents[1] / 'example/runtime_books'
subprocess.run([sys.executable, str(LAB/'build.py')], check=True)
OUT.mkdir(parents=True, exist_ok=True)
for name in ['transcrypt', 'vendor']:
    shutil.copytree(LAB/'public'/name, OUT/name, dirs_exist_ok=True)
shutil.copyfile(HERE/'host.js', OUT/'host.js')
(OUT/'sources.json').write_text(json.dumps({'files': {
    'client.py': (LAB/'src/client.py').read_text(),
    'bridge.py': (LAB/'src/interpreter_bridge.py').read_text(),
}}))
(OUT/'manifest.json').write_text(json.dumps({
    'schema': 1,
    'runtimes': ['pyodide', 'micropython', 'transcrypt'],
    'host': 'host.js',
    'scripts': ['vendor/dhxpyt/suite.js'],
    'styles': ['vendor/dhxpyt/suite.css'],
    'sources': 'sources.json',
    'entrypoint': 'client',
    'compiled': 'transcrypt/client.js',
    'micropython': {
        'module': 'vendor/micropython/micropython.mjs',
        'wasm': 'vendor/micropython/micropython.wasm',
        'heapBytes': 8 * 1024 * 1024,
    },
}, indent=2)+'\n')
print('Built runtime choices at', OUT)
