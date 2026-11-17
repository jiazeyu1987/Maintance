"""Inventory existing service mounts; never emit user file names or contents."""
import collections
import json
import re
import sqlite3
import subprocess
from pathlib import Path

names=['erp-invoice-voucher-print-assistant','fenbeitong-assistant','intruoyi-onlyoffice']
containers=json.loads(subprocess.check_output(['docker','inspect',*names],timeout=10))
out={'serverWrites':False,'services':[]}
for c in containers:
    assert c['Name'].lstrip('/') in names and c['State']['Running']
    row={'name':c['Name'],'image':c['Config']['Image'],'workingDir':c['Config']['WorkingDir'],'mounts':[]}
    for m in c['Mounts']:
        p=Path(m['Source'])
        if not p.is_dir():continue
        files=[f for f in p.rglob('*') if f.is_file() and not f.is_symlink()]
        entry={'source':str(p),'destination':m['Destination'],'fileCount':len(files),'bytes':sum(f.stat().st_size for f in files),'extensions':dict(collections.Counter(f.suffix.lower() or '<no suffix>' for f in files).most_common(15)),'databases':[]}
        if c['Name']!='/intruoyi-onlyoffice':
            entry['controlFilePatterns']=sorted({re.sub(r'[0-9]+','<n>',f.name) for f in files if f.suffix in ['.sqlite','.sqlite3','.db','.json','.yaml','.yml'] and len(f.relative_to(p).parts)<=2})[:20]
            for f in files:
                if f.suffix not in ['.db','.sqlite','.sqlite3']:continue
                with f.open('rb') as stream:header=stream.read(16)
                if header!=b'SQLite format 3\x00':continue
                db=sqlite3.connect(f.as_uri()+'?mode=ro',uri=True,timeout=5)
                db.execute('PRAGMA query_only=ON')
                tables=db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
                table_out=[]
                for (name,) in tables:
                    ident='"'+name.replace('"','""')+'"'
                    cols=db.execute('PRAGMA table_info('+ident+')').fetchall()
                    count=db.execute('SELECT COUNT(*) FROM '+ident).fetchone()[0]
                    table_out.append({'name':name,'rows':count,'columns':[{'name':x[1],'type':x[2]} for x in cols]})
                db.close()
                entry['databases'].append({'relativePath':f.relative_to(p).as_posix(),'tables':table_out})
        row['mounts'].append(entry)
    out['services'].append(row)
invoice=containers[0]
for name in names[:2]:
    command=['docker','exec',name,'sh','-c',"find . -maxdepth 3 -type f \\( -name '*.py' -o -name 'package.json' -o -name 'README*' \\) | head -50"]
    p=subprocess.run(command,capture_output=True,timeout=10)
    assert p.returncode==0
    out[name+'CodeFiles']=p.stdout.decode('utf-8',errors='strict').splitlines()
print(json.dumps(out))
