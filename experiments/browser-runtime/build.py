from pathlib import Path
import hashlib, json, shutil, subprocess, zipfile
LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
PUBLIC = LAB/'public'
subprocess.run([str(LAB/'.venv/bin/python'),'-m','transcrypt','-b','-n','-od',str(PUBLIC/'transcrypt'),str(LAB/'src/client.py')],check=True)
shutil.copyfile(LAB/'src/client.py',PUBLIC/'client.py')
shutil.copyfile(LAB/'src/interpreter_bridge.py',PUBLIC/'bridge.py')
wheel = ROOT/'example/dhxpyt-0.9.19-py3-none-any.whl'
with zipfile.ZipFile(wheel) as z:
    for name in z.namelist():
        if name.startswith('dhxpyt/dhxsrc/') and not name.endswith('/'):
            out=PUBLIC/'vendor/dhxpyt'/name.removeprefix('dhxpyt/dhxsrc/')
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_bytes(z.read(name))
mp=LAB/'node_modules/@micropython/micropython-webassembly-pyscript'
(PUBLIC/'vendor/micropython').mkdir(parents=True,exist_ok=True)
for name in ['micropython.mjs','micropython.wasm']:
    shutil.copyfile(mp/name,PUBLIC/'vendor/micropython'/name)
manifest={str(p.relative_to(PUBLIC)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in PUBLIC.rglob('*') if p.is_file() and p.name!='build.json'}
(PUBLIC/'build.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Built',len(manifest),'assets')
