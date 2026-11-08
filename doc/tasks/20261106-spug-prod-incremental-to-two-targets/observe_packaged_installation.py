"""Observe exact installation checkpoints; no writes or service calls."""
import json
from common import remote
script="""import json,pathlib
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
generation='packaged-frontend-0c5828a'
paths={'custody':root/'configuration'/('failure-custody-'+generation+'.json'),
 'engine':root/('engine-'+generation),'owner':root/'configuration'/('main-recovery-'+generation+'.json'),
 'constructorGate':root/'configuration'/('constructor-gate-'+generation)/'constructor-verification.json'}
rows=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdecimal():continue
 try:
  if not (p/'comm').read_text().startswith('python3.12'):continue
  status=(p/'status').read_text().splitlines()
  rows.append({'pid':int(p.name),'state':next(s.split(':',1)[1].strip() for s in status if s.startswith('State:')),
   'io':dict(s.split(': ',1) for s in (p/'io').read_text().splitlines() if s.startswith(('rchar:','read_bytes:'))),
   'wait':(p/'wchan').read_text().strip()})
 except (FileNotFoundError,ProcessLookupError):continue
print(json.dumps({'checkpoints':{k:p.exists() for k,p in paths.items()},'pythonProcesses':rows}))
"""
print(json.dumps(remote('172.30.30.58',script,40)))
