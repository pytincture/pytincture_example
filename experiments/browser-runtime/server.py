"""Isolated local experiment; original example service and database untouched."""
from pathlib import Path
import os, secrets, sys
LAB=Path(__file__).resolve().parent
ROOT=LAB.parents[1]
CACHE=Path(os.environ.get('PYTINCTURE_LAB_CACHE',str(Path.home()/'Library/Caches/pytincture-runtime-lab')))
CACHE.mkdir(parents=True,exist_ok=True)
os.environ['PYTINCTURE_EXAMPLE_DB']=str(CACHE/'books.db')
os.environ['PYTINCTURE_EXAMPLE_SESSION_SECRET']=secrets.token_urlsafe(48)
sys.path.insert(0,str(ROOT/'example'))
import run
from fastapi.staticfiles import StaticFiles
app=run.app
app.mount('/lab',StaticFiles(directory=LAB/'public',html=True),name='runtime-lab')
app.router.routes.insert(0,app.router.routes.pop())

class StartupOverride:
    """Test-only HTML flag override; normal example requests are untouched."""
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if (scope['type'] != 'http' or scope['path'] != '/py_ui'
                or scope.get('query_string') != b'runtime_lab_no_sw=1'):
            return await self.inner(scope, receive, send)
        messages = []
        async def capture(message):
            messages.append(message)
        await self.inner(scope, receive, capture)
        start = next(m for m in messages if m['type'] == 'http.response.start')
        body = b''.join(m.get('body', b'') for m in messages if m['type'] == 'http.response.body')
        original = b'enableServiceWorker: true,'
        if original in body:
            body = body.replace(original, b'enableServiceWorker: false, warmPyodideCache: false,', 1)
            start['headers'] = [(k,v) for k,v in start['headers'] if k.lower() != b'content-length']
            start['headers'].append((b'content-length', str(len(body)).encode()))
        await send(start)
        await send({'type':'http.response.body','body':body})

app = StartupOverride(app)
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8092)
