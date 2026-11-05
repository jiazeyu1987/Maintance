"""Inspect installed restore acceptance return shapes without running them."""
import json
from repair_preflight import remote, TASK

SCRIPT=r'''
import ast,json,pathlib
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3/engine/common')
selected={'recovery_minimal_runtime.py':{'database_readback','physical_object_chain','start_application'},'recovery_data.py':{'database_readback','consistency'},'recovery_minimal_redis_dump.py':{'restore'},'recovery_minimal_derived.py':{'rebuild'}}
out=[]
for name,functions in selected.items():
 text=(root/name).read_text(encoding='utf-8');tree=ast.parse(text)
 for node in ast.walk(tree):
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in functions:
   out.append({'file':name,'function':node.name,'returns':[ast.unparse(s.value) for s in ast.walk(node) if isinstance(s,ast.Return)]})
print(json.dumps(out))
'''
if __name__=='__main__':
    result=remote('172.30.30.58',SCRIPT,timeout=25)
    (TASK/'installed-restore-return-shapes.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result))
