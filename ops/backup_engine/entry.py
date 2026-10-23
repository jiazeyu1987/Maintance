"""Versioned owner entry; normal arguments are passed unchanged to the owner CLI."""
import hashlib
import importlib
import json
from pathlib import Path
import runpy
import sys

root=Path(__file__).resolve().parent
version=json.loads((root/'package.json').read_bytes())
hashes=version['files']
actual=hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest()
if actual != version['packageSha256']:
    raise RuntimeError('ENGINE_PACKAGE_MANIFEST_MISMATCH')
for name, expected in hashes.items():
    path=root/name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise RuntimeError('ENGINE_PACKAGE_FILE_MISMATCH '+name)
role=Path(__file__).stem.removesuffix('_entry')
if role not in ('repository','recovery','control'):
    raise SystemExit('ENGINE_ROLE_REQUIRED')
modules={'repository':('common','repository_cli'), 'recovery':('common','recovery_minimal'),
         'control':('control','recovery_control_smallapp')}
directory, module=modules[role]
# Formal imports remain explicit inside the restore worker so origin checks hold.
sys.path[:0]=[str(root/'control'),str(root/'common')]
info=dict(commit=version['commit'],packageSha256=version['packageSha256'],role=role,
          entry=str(root/directory/(module+'.py')),
          files={name:hashes['common/'+name+'.py'] for name in
                 ('repository_records','repository_minimal','recovery_data','recovery_minimal_runtime','staging_cleanup')})
if sys.argv[1:]==['--script-version']:
    print(json.dumps(info,sort_keys=True));sys.exit(0)
if sys.argv[1:]==['--check-imports']:
    imported=importlib.import_module(module)
    info['imported']=str(Path(imported.__file__).resolve())
    if Path(imported.__file__).resolve()!=root/directory/(module+'.py'):
        raise RuntimeError('ENGINE_WRONG_IMPORT_ORIGIN')
    print(json.dumps(info,sort_keys=True));sys.exit(0)
print(json.dumps({'backupEngineVersion':info},sort_keys=True),flush=True)
runpy.run_path(str(root/directory/(module+'.py')),run_name='__main__')
