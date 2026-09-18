"""Read-only service-worker scope probe; run separately from benchmark timing."""
import json
from playwright.sync_api import sync_playwright
from benchmark import LAB, INIT, authenticate, measure

with sync_playwright() as pw:
    state = authenticate(pw)
    browser = pw.chromium.launch()
    context = browser.new_context(storage_state=state, viewport={'width':1400,'height':900})
    context.add_init_script(INIT)
    page = context.new_page()
    warnings = []
    page.on('console', lambda message: warnings.append(message.text) if message.type in ('warning','error') else None)
    data = measure(page, 'full-example')
    data['service_worker'] = page.evaluate('''async () => ({
        page: location.href,
        controller: navigator.serviceWorker.controller?.scriptURL || null,
        registrations: (await navigator.serviceWorker.getRegistrations()).map(r=>({
            scope:r.scope,active:r.active?.scriptURL||null,
            page_in_scope:location.href.startsWith(r.scope)
        }))
    })''')
    data['warnings'] = warnings
    (LAB/'results/startup-diagnostic.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(data['service_worker'],indent=2))
    browser.close()
