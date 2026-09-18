export async function setup(context) {
    const main = document.getElementById('maindiv');
    main.innerHTML = `<main style="padding:24px;font-family:system-ui;max-width:1300px;margin:auto">
        <h1>Book Library</h1>
        <p>Experimental runtime choices · <a href="/py_ui">Open the complete Pyodide example</a></p>
        <label>Browser runtime <select id="runtime-choice"></select></label>
        <span id="startup" role="status"></span>
        <p>This preview supports browsing, filtering and editing book titles.</p>
        <label>Filter titles <input id="filter" style="padding:8px"></label>
        <label>Selected title <input id="title" style="padding:8px;width:400px"></label>
        <button id="save">Save</button><p id="status" role="status">Starting…</p>
        <div id="grid" style="height:550px"></div></main>`;
    const picker = document.getElementById('runtime-choice');
    const names = {pyodide:'Pyodide (CPython)',micropython:'MicroPython (WebAssembly)',transcrypt:'Transcrypt (compiled JavaScript)'};
    for (const engine of context.runtimes) picker.add(new Option(names[engine], engine));
    picker.value = context.engine;
    picker.addEventListener('change', () => {
        const url = new URL(location.href);
        url.searchParams.set('runtime', picker.value);
        location.assign(url);
    });
    window.labMetrics = {mode:context.engine};
    const dispatch = (name,payload='') => context.invoke(name,payload).catch(error => {
        window.labError = String(error);
        document.getElementById('status').textContent = String(error);
    });
    window.labBff = async(method,payload) => JSON.stringify(await context.callBff('py_ui_data','py_ui_data',method,JSON.parse(payload)));
    let grid;
    window.labGridCreate = rows => {
        grid = new dhx.Grid('grid',{columns:[
            {id:'title',header:[{text:'Title'}],width:440},
            {id:'authors',header:[{text:'Authors'}],width:280},
            {id:'average_rating',header:[{text:'Rating'}],width:100},
            {id:'publisher',header:[{text:'Publisher'}],width:280},
        ],selection:'row',data:JSON.parse(rows)});
        grid.events.on('cellClick',row=>dispatch('on_select',JSON.stringify(row)));
    };
    window.labGridRows = rows => grid.data.parse(JSON.parse(rows));
    window.labReady = count => requestAnimationFrame(()=>requestAnimationFrame(()=>{
        window.labMetrics.ready = performance.now();
        window.labMetrics.rowCount = count;
        window.labIsReady = true;
        document.getElementById('status').textContent = `Ready: ${count} books`;
        document.getElementById('startup').textContent = ` · Ready in ${(performance.now()/1000).toFixed(2)}s`;
    }));
    document.getElementById('filter').addEventListener('input',()=>dispatch('on_filter'));
    document.getElementById('save').addEventListener('click',()=>dispatch('on_save'));
}
