const mode = new URLSearchParams(location.search).get('engine') || 'transcrypt';
document.getElementById('engine').textContent = mode;
window.labMetrics = {mode, scriptStart: performance.now()};
let grid;
let invoke;
let chain = Promise.resolve();
const dispatch = (name, payload='') => {
    chain = chain.then(() => invoke(name, payload)).catch(error => {window.labError=String(error); console.error(error);});
    return chain;
};
window.labBff = async (method, payload) => {
    const cookie = document.cookie.split('; ').find(x => x.startsWith('pytincture-dev-csrf='));
    const response = await fetch(`/py_ui/classcall/py_ui_data/py_ui_data/${method}`, {
        method: 'POST', credentials:'same-origin',
        headers: {'Content-Type':'application/json','X-CSRF-Token':decodeURIComponent(cookie?.split('=').slice(1).join('=')||'')},
        body:payload,
    });
    if (!response.ok) throw new Error(`BFF ${method}: ${response.status}`);
    return JSON.stringify(await response.json());
};
window.labGridCreate = rows => {
    grid = new dhx.Grid('grid', {columns:[
        {id:'title',header:[{text:'Title'}],width:440},
        {id:'authors',header:[{text:'Authors'}],width:280},
        {id:'average_rating',header:[{text:'Rating'}],width:100},
        {id:'publisher',header:[{text:'Publisher'}],width:280},
    ],selection:'row',data:JSON.parse(rows)});
    grid.events.on('cellClick', row => dispatch('on_select',JSON.stringify(row)));
};
window.labGridRows = rows => grid.data.parse(JSON.parse(rows));
window.labReady = count => {
    window.labMetrics.rowCount=count;
    requestAnimationFrame(() => requestAnimationFrame(() => {
        window.labMetrics.ready=performance.now();
        document.getElementById('status').textContent=`Ready: ${count} books`;
        window.labIsReady=true;
    }));
};
document.getElementById('filter').addEventListener('input',()=>dispatch('on_filter'));
document.getElementById('save').addEventListener('click',()=>dispatch('on_save'));
async function loadScript(url){await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=url;s.onload=resolve;s.onerror=reject;document.head.appendChild(s);});}
try {
    if(mode==='transcrypt') {
        const client=await import('./transcrypt/client.js');
        window.labMetrics.runtimeReady=performance.now();
        invoke=(name,payload)=>client[name](payload);
        await client.main();
    } else {
        let runtime;
        if(mode==='pyodide') {
            await loadScript('/frontend/pyodide/0.29.3/full/pyodide.js');
            runtime=await loadPyodide({indexURL:'/frontend/pyodide/0.29.3/full/'});
        } else if(mode==='micropython') {
            const {loadMicroPython}=await import('./vendor/micropython/micropython.mjs');
            runtime=await loadMicroPython({url:'/lab/vendor/micropython/micropython.wasm',heapsize:8*1024*1024});
        } else throw new Error('Unknown runtime');
        window.labRuntime=runtime;
        window.labMetrics.runtimeReady=performance.now();
        const [client,bridge]=await Promise.all(['client.py','bridge.py'].map(async path=>(await fetch(path)).text()));
        runtime.FS.writeFile('/client.py',client);
        runtime.FS.writeFile('/bridge.py',bridge);
        invoke=async(name,payload)=>{runtime.globals.set('_lab_payload',payload);await runtime.runPythonAsync(`await client.${name}(_lab_payload)`);};
        await runtime.runPythonAsync('import sys\nsys.path.insert(0, "/")\nimport client\nawait client.main()');
    }
} catch(error) {window.labError=String(error); document.getElementById('status').textContent=String(error); console.error(error);}
