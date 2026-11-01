"""Click the requested existing Spug control using real Playwright UI."""
import json
from pathlib import Path
import subprocess
import sys

task=Path(__file__).parent
assert len(sys.argv)>1
command=sys.argv[1]
private=Path('C:/SpugHandoff/release/private/acceptance/schema-20261101')
private.mkdir(parents=True,exist_ok=True)
result=subprocess.run(['node',str(task/'spug-ui.cjs'),*sys.argv[1:]],cwd=task,capture_output=True,encoding='utf-8',timeout=180)
(private/(command+'-ui.private.log')).write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
for line in (result.stdout+'\n'+result.stderr).splitlines():
    if not line.strip():
        continue
    row=json.loads(line)
    if 'clicked' in row or row.get('status')=='FAIL':
        print(json.dumps(row,ensure_ascii=False))
    elif command in ('status','build-view','login'):
        print(json.dumps({k:row[k] for k in ('application','active','environments','candidate','commits') if k in row},ensure_ascii=False))
print('UI exit='+str(result.returncode))
sys.exit(result.returncode)
