import ast,json,sys
from pathlib import Path
root=Path(__file__).parent
sys.path.insert(0,'C:/Spug/runtime/private/spug-backup59-mvp-20261116')
import collect59
collect59.PY='/mnt/intruoyi-data/recovery-tools/python/bin/python3.12'
old=collect59.remote("import json,pathlib; c=json.loads(pathlib.Path('/mnt/intruoyi-data/recovery-tools/prepare-target.private.json').read_bytes()); print(json.dumps({'points':{k:{'fileStorage':v.get('fileStorage')} for k,v in c['points'].items()}}))")
baseline=json.loads((root/'acceptance/selected-chain-acceptance-baseline.private.json').read_text(encoding='utf-8'))
tree=ast.parse((root/'register_prepare_point.py').read_text(encoding='utf-8'))
assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='entry' for t in n.targets))
entry=eval(compile(ast.Expression(assignment.value),'<selection>','eval'),{'old':old,'baseline':baseline})
assert baseline['chainBindingVerified']
assert entry.get('fileStorage')==old['points'][baseline['parentBackupId']]['fileStorage'], 'PARENT_STORAGE_POLICY_LOST'
print('PASS: actual registered parent storage policy retained')
