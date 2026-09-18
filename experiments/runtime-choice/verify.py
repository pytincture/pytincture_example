"""Browser acceptance for the actual framework runtime-selection path."""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8093'
HERE = Path(__file__).resolve().parent
results = {}

def login(context, application):
    response = context.request.get(f'{BASE}/{application}/login')
    token = re.search(r'name="login_csrf_token" value="([^"]+)"', response.text())[1]
    response = context.request.post(f'{BASE}/{application}/auth/user', form={
        'email':'demo@example.com', 'password':'demo-password', 'login_csrf_token':token,
    }, max_redirects=0)
    assert response.status == 303
    return response.headers['location']

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    context = browser.new_context(viewport={'width':1450,'height':950})
    assert context.request.get(BASE+'/runtime_books?runtime=micropython',max_redirects=0).status in (302,307)
    assert login(context, 'runtime_books') == '/runtime_books?runtime=micropython'
    results['login_preserves_runtime'] = True
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    for engine in ['pyodide','micropython','transcrypt']:
        errors.clear()
        response = page.goto(f'{BASE}/runtime_books?runtime={engine}')
        assert response.status == 200
        page.wait_for_function('window.labIsReady || window.labError || document.body.innerText.includes("Failed during")', timeout=60000)
        assert not errors, errors
        assert page.evaluate('window.labIsReady'), page.locator('body').inner_text()
        assert page.evaluate('window.labMetrics.rowCount') == 69
        urls = page.evaluate("performance.getEntriesByType('resource').map(r=>r.name)")
        loaded_pyodide = any('/pyodide/' in url for url in urls)
        assert loaded_pyodide == (engine == 'pyodide'), urls
        assert page.locator('#runtime-choice').input_value() == engine
        page.locator('.dhx_grid-row').first.click()
        page.wait_for_function('document.getElementById("title").value.length>0')
        original = page.locator('#title').input_value()
        page.locator('#filter').fill('Harry')
        page.wait_for_function('document.getElementById("status").textContent==="Showing 4 books"')
        page.locator('#filter').fill('')
        page.wait_for_function('document.getElementById("status").textContent==="Showing 69 books"')
        updated = original + ' [runtime choice test]'
        try:
            page.locator('#title').fill(updated)
            page.locator('#save').click()
            page.wait_for_function('document.getElementById("status").textContent==="Saved 1"')
            page.reload()
            page.wait_for_function('window.labIsReady', timeout=60000)
            page.locator('.dhx_grid-row').first.click()
            page.wait_for_function('(title)=>document.getElementById("title").value===title', arg=updated)
        finally:
            page.locator('#title').fill(original)
            page.locator('#save').click()
            page.wait_for_function('document.getElementById("status").textContent==="Saved 1"')
        bad_csrf = page.evaluate('''async()=> (await fetch('/runtime_books/classcall/py_ui_data/py_ui_data/update_book', {
            method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':'invalid'},
            body:JSON.stringify({book_id:1,fields:{title:'must not persist'}})
        })).status''')
        assert bad_csrf == 403
        assert not errors, errors
        results[engine] = {'rows':69,'filter':True,'select':True,'save_reload_restore':True,
                           'bad_csrf_status':bad_csrf,'loaded_pyodide':loaded_pyodide}
        print(engine, results[engine], flush=True)
    page.locator('#runtime-choice').select_option('micropython')
    page.wait_for_url('**/runtime_books?runtime=micropython')
    page.wait_for_function('window.labIsReady', timeout=60000)
    assert page.locator('#runtime-choice').input_value() == 'micropython'
    results['picker_switch'] = True
    page.screenshot(path=str(HERE/'preview.png'),full_page=True)
    # Exercise the distributed bundle as well as the raw runtime source.
    page.route('**/frontend/pytincture.js?*', lambda route: route.continue_(url=route.request.url.replace('/frontend/pytincture.js','/frontend/dist/pytincture.min.js')))
    for engine in ['micropython','transcrypt']:
        page.goto(f'{BASE}/runtime_books?runtime={engine}')
        page.wait_for_function('window.labIsReady',timeout=60000)
        assert page.evaluate('window.labMetrics.rowCount') == 69
    page.unroute('**/frontend/pytincture.js?*')
    results['minified_bundle'] = True
    assert context.request.get(BASE+'/runtime_books?runtime=unknown').status == 422
    anon = pw.request.new_context()
    assert anon.get(BASE+'/runtime_books?runtime=micropython',max_redirects=0).status in (302,307)
    assert anon.post(BASE+'/runtime_books/classcall/py_ui_data/py_ui_data/dataset',data='{}',headers={'Content-Type':'application/json'}).status == 401
    anon.dispose()
    # The original application still uses the packaged Pyodide entrypoint.
    login(context, 'py_ui')
    page.goto(BASE+'/py_ui')
    page.wait_for_function("document.querySelectorAll('.dhx_grid-row').length>0 && document.body.innerText.includes('Book Details and Ratings')", timeout=120000)
    results['original_full_example'] = True
    browser.close()
(HERE/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print('All framework runtime-choice checks passed.', flush=True)
