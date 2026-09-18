import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright
LAB=Path(__file__).resolve().parent
BASE='http://127.0.0.1:8092'
results={}
with sync_playwright() as pw:
    browser=pw.chromium.launch()
    ctx=browser.new_context()
    page=ctx.new_page()
    # Authenticate through the unchanged example login endpoint.
    response=ctx.request.get(BASE+'/py_ui/login')
    token=re.search(r'name="login_csrf_token" value="([^"]+)"',response.text())[1]
    assert ctx.request.post(BASE+'/py_ui/auth/user',form={'email':'demo@example.com','password':'demo-password','login_csrf_token':token},max_redirects=0).status==303
    for mode in ['pyodide','micropython','transcrypt']:
        page.goto(BASE+'/lab/?engine='+mode)
        page.wait_for_function('window.labIsReady || window.labError',timeout=120000)
        assert not page.evaluate('window.labError || null')
        page.locator('.dhx_grid-row').first.click()
        page.wait_for_function('document.getElementById("title").value.length>0')
        original=page.locator('#title').input_value()
        page.locator('#filter').fill('Harry')
        page.wait_for_function('document.getElementById("status").textContent==="Showing 4 books"')
        page.locator('#filter').fill('')
        page.wait_for_function('document.getElementById("status").textContent==="Showing 69 books"')
        updated=original+' [isolated runtime verification]'
        page.locator('#title').fill(updated)
        page.locator('#save').click()
        page.wait_for_function('document.getElementById("status").textContent==="Saved 1"')
        page.reload()
        page.wait_for_function('window.labIsReady',timeout=120000)
        page.locator('.dhx_grid-row').first.click()
        page.wait_for_function('(expected)=>document.getElementById("title").value===expected',arg=updated)
        page.locator('#title').fill(original)
        page.locator('#save').click()
        page.wait_for_function('document.getElementById("status").textContent==="Saved 1"')
        response=page.evaluate('''async()=>{
            const r=await fetch('/py_ui/classcall/py_ui_data/py_ui_data/update_book',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':'invalid'},body:JSON.stringify({book_id:1,fields:{title:'must not persist'}})});return r.status;
        }''')
        assert response==403,response
        results[mode]={'rows':69,'filter_matches':4,'select':True,'save_and_reload':True,'restored':True,'bad_csrf_status':response}
        if mode!='transcrypt':
            results[mode]['imports']=page.evaluate('''async()=>{
                await window.labRuntime.runPythonAsync(`
import json
_checks={}
for _name in ('asyncio','dataclasses','typing','inspect','pyodide.ffi','js'):
    try:
        __import__(_name)
        _checks[_name]='ok'
    except Exception as _error:
        _checks[_name]=type(_error).__name__+': '+str(_error)
_checks_json=json.dumps(_checks)
`);
                return JSON.parse(window.labRuntime.globals.get('_checks_json'));
            }''')
        print(mode,results[mode],flush=True)
    anon=pw.request.new_context()
    denied=anon.post(BASE+'/py_ui/classcall/py_ui_data/py_ui_data/dataset',data='{}',headers={'Content-Type':'application/json'})
    assert denied.status in (401,403),denied.status
    results['anonymous_dataset_status']=denied.status
    anon.dispose()
    browser.close()
(LAB/'results/functional.json').write_text(json.dumps(results,indent=2)+'\n')
