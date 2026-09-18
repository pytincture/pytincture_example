"""Cold browser process + immediate reload; shared authenticated backend."""
import argparse, json, os, platform, re, statistics, subprocess, signal
from pathlib import Path
from playwright.sync_api import sync_playwright
LAB=Path(__file__).resolve().parent
BASE='http://127.0.0.1:8092'
VARIANTS=['full-example','pyodide','micropython','transcrypt']
INIT='''window.labLifecycle=[];window.addEventListener('pytincture:lifecycle',e=>window.labLifecycle.push({...e.detail,at:performance.now()}));window.labLongTasks=[];new PerformanceObserver(list=>{for(const e of list.getEntries())window.labLongTasks.push({start:e.startTime,duration:e.duration});}).observe({type:'longtask',buffered:true});'''

def authenticate(pw):
    api=pw.request.new_context(base_url=BASE)
    response=api.get('/py_ui/login')
    token=re.search(r'name="login_csrf_token" value="([^"]+)"',response.text())[1]
    response=api.post('/py_ui/auth/user',form={'email':'demo@example.com','password':'demo-password','login_csrf_token':token},max_redirects=0)
    assert response.status==303
    state=api.storage_state()
    api.dispose()
    return state

def measure(page,mode,reload=False):
    if reload: page.reload(wait_until='domcontentloaded',timeout=180000)
    else:
        url = '/py_ui' if mode.startswith('full-') else '/lab/?engine='+mode
        if mode == 'full-no-sw': url += '?runtime_lab_no_sw=1'
        page.goto(BASE+url,wait_until='domcontentloaded',timeout=180000)
    if mode.startswith('full-'):
        page.wait_for_function("document.querySelectorAll('.dhx_grid-row').length>0 && document.body.innerText.includes('Book Details and Ratings')",timeout=180000)
    else:
        page.wait_for_function('window.labIsReady || window.labError',timeout=180000)
        assert page.evaluate('window.labError || null') is None,page.evaluate('window.labError')
        assert page.evaluate('window.labMetrics.rowCount')==69
    return page.evaluate('''() => {
        const resources=performance.getEntriesByType('resource');
        const nav=performance.getEntriesByType('navigation')[0];
        return {ready_ms:window.labMetrics?.ready??performance.now(),runtime_ready_ms:window.labMetrics?.runtimeReady??null,
            transfer_bytes:nav.transferSize+resources.reduce((s,r)=>s+r.transferSize,0),
            decoded_bytes:nav.decodedBodySize+resources.reduce((s,r)=>s+r.decodedBodySize,0),requests:resources.length+1,
            metrics:window.labMetrics||null,lifecycle:window.labLifecycle,
            long_task_ms:window.labLongTasks.reduce((s,r)=>s+r.duration,0),
            resources:resources.map(r=>({url:r.name.replace(location.origin,''),transfer:r.transferSize,decoded:r.decodedBodySize,duration:r.duration,start:r.startTime})),
            visible_rows:document.querySelectorAll('.dhx_grid-row').length};
    }''')

def main():
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit(143)))
    parser=argparse.ArgumentParser()
    parser.add_argument('--local-runs',type=int,default=5)
    parser.add_argument('--throttled-runs',type=int,default=3)
    parser.add_argument('--variants',nargs='+',choices=VARIANTS+['full-no-sw'],default=VARIANTS)
    parser.add_argument('--output',type=Path,default=LAB/'results/benchmark.json')
    args=parser.parse_args()
    variants=args.variants
    result={'environment':{'platform':platform.platform(),'machine':platform.machine(),'framework_commit':subprocess.check_output(['git','-C',str(Path(os.environ.get('PYTINCTURE_SOURCE', LAB.parents[2]/'pytincture'))),'rev-parse','HEAD'],text=True).strip(),'example_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=LAB,text=True).strip(),'pyodide':'0.29.3','micropython':'1.29.0-6','transcrypt':'3.9.4','dhxpyt':'0.9.19'},'method':{'cold':'new Chromium process and context; cookies supplied through API login; no prior navigation','warm':'immediate reload in same tab/context; actual caching governed by server headers','ready':'populated grid; common slices mark after two animation frames; full example detected populated grid','throttled':'10 Mbps down / 2 Mbps up, 40 ms latency, 4x CPU slowdown via CDP; localhost server','login':'excluded from timings; normal session and CSRF kept enabled'},'runs':[]}
    output=args.output
    output.parent.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as pw:
        state=authenticate(pw)
        for profile,reps in [('local',args.local_runs),('throttled',args.throttled_runs)]:
            for repetition in range(reps):
                offset=repetition%len(variants)
                order=variants[offset:]+variants[:offset]
                for mode in order:
                    browser=pw.chromium.launch()
                    result['environment']['browser']=browser.version
                    context=browser.new_context(storage_state=state,viewport={'width':1400,'height':900})
                    context.add_init_script(INIT)
                    page=context.new_page()
                    errors=[]
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    if profile=='throttled':
                        cdp=context.new_cdp_session(page)
                        cdp.send('Network.enable')
                        cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':40,'downloadThroughput':10_000_000/8,'uploadThroughput':2_000_000/8})
                        cdp.send('Emulation.setCPUThrottlingRate',{'rate':4})
                    try:
                        for cache in ['cold','warm']:
                            data=measure(page,mode,reload=cache=='warm')
                            data.update({'profile':profile,'run':repetition+1,'variant':mode,'cache':cache,'errors':list(errors)})
                            assert not errors,errors
                            result['runs'].append(data)
                            output.write_text(json.dumps(result,indent=2)+'\n')
                            print(profile,repetition+1,mode,cache,round(data['ready_ms']),round(data['transfer_bytes']/1048576,2),'MiB',flush=True)
                    finally: browser.close()
    summary=[]
    for profile in ['local','throttled']:
        for mode in variants:
            for cache in ['cold','warm']:
                rows=[r for r in result['runs'] if r['profile']==profile and r['variant']==mode and r['cache']==cache]
                if not rows: continue
                summary.append({'profile':profile,'variant':mode,'cache':cache,'n':len(rows),'median_ms':round(statistics.median(r['ready_ms'] for r in rows),1),'min_ms':round(min(r['ready_ms'] for r in rows),1),'max_ms':round(max(r['ready_ms'] for r in rows),1),'median_transfer_mib':round(statistics.median(r['transfer_bytes'] for r in rows)/1048576,3),'median_requests':statistics.median(r['requests'] for r in rows)})
    result['summary']=summary
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__': main()
