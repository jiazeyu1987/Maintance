"""Compare full type diagnostics with pinned baseline, restoring exact task bytes."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path('C:/SpugHandoff/release/fenbeitong-runtime-url-20261125')
TASK = Path(__file__).resolve().parent
BASE = '01c362bff'
paths = ['IntRuoyiFronted/src/api/login/index.ts',
         'IntRuoyiFronted/src/views/erp/finance/fenbeitong-voucher/index.vue',
         'IntRuoyiFronted/types/env.d.ts']
saved = {p:(ROOT/p).read_bytes() for p in paths}

def run(label):
    env = dict(os.environ, NODE_OPTIONS='--max-old-space-size=8192')
    result = subprocess.run(['node', 'node_modules/vue-tsc/bin/vue-tsc.js', '--noEmit', '-p', 'tsconfig.relaxed.json'],
                            cwd=ROOT/'IntRuoyiFronted', env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout.decode('utf-8', errors='strict').replace('\r\n', '\n')
    (TASK/(label+'-typecheck.txt')).write_text(output,encoding='utf-8',newline='\n')
    diagnostics = [s for s in output.splitlines() if re.match(r'^src/.*error TS\d+:',s)]
    print(label, 'exit',result.returncode, 'diagnostics',len(diagnostics),flush=True)
    return {'exitCode':result.returncode,'diagnostics':diagnostics}

try:
    for path in paths:
        original=subprocess.run(['git','-C',str(ROOT),'show',BASE+':'+path],capture_output=True,check=True).stdout
        (ROOT/path).write_bytes(original)
    baseline=run('baseline')
finally:
    for path,raw in saved.items():
        (ROOT/path).write_bytes(raw)
    assert all((ROOT/path).read_bytes()==raw for path,raw in saved.items())

fixed=run('fixed')
assert baseline==fixed, 'Type diagnostics differ; inspect exact outputs before integration'
assert fixed['diagnostics'] and all('src/views/crm/' in s and 'checkPermi' in s for s in fixed['diagnostics'])
summary={'baselineCommit':BASE,'sameDiagnostics':True,'diagnosticCount':len(fixed['diagnostics']),
         'baselineExit':baseline['exitCode'],'fixedExit':fixed['exitCode'],
         'restoredFiles':{p:hashlib.sha256(raw).hexdigest() for p,raw in saved.items()}}
(TASK/'typecheck-comparison.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print('PASS: baseline and fixed diagnostics are identical; original task bytes restored')
