"""Lightweight owner entry: load the chosen engine without file integrity scans."""
import importlib
import json
from pathlib import Path
import runpy
import sys

root = Path(__file__).resolve().parent
version = json.loads((root/'package.json').read_bytes())
role = Path(__file__).stem.removesuffix('_entry')
modules = {'repository': ('common', 'repository_cli'),
           'recovery': ('common', 'recovery_minimal'),
           'control': ('control', 'recovery_control_smallapp')}
directory, module = modules[role]
sys.path[:0] = [str(root/'control'), str(root/'common')]
info = dict(commit=version['commit'], packageSha256=version['packageSha256'],
            variant='lightweight', fileVerification=False, role=role,
            entry=str(root/directory/(module+'.py')))
if sys.argv[1:] == ['--script-version']:
    print(json.dumps(info)); sys.exit(0)
if sys.argv[1:] == ['--check-imports']:
    imported = importlib.import_module(module)
    info['imported'] = str(Path(imported.__file__).resolve())
    print(json.dumps(info)); sys.exit(0)
print(json.dumps({'backupEngineVersion': info}), flush=True)
runpy.run_path(str(root/directory/(module+'.py')), run_name='__main__')
