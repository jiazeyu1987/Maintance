"""Commit only verified scheduler/control implementation and its direct tests."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
from install_prod_control import TASK,PRIVATE
from verify_task_records import secrets

ROOT=TASK.parents[2]
FILES=['ops/backup_engine/files.json','ops/backup_engine/standard_fixes.py',
 'ops/recovery/recovery_mysql_scheduler.py','ops/recovery/recovery_main_target.py',
 'ops/recovery/recovery_retained_retry.py','scripts/tests/test_main_mysql_scheduler.py',
 'scripts/tests/test_main_restore_target.py','scripts/tests/test_main_archive_view.py',
 'scripts/tests/test_retained_replacement_retry.py','scripts/tests/test_backup_variants.py']
BASE='9b3a298ce378b3ac565792a3bc3b92f1e5208898'


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)


if __name__=='__main__':
 assert git('rev-parse','HEAD').decode().strip()==BASE
 assert not git('diff','--cached','--name-only'),'EXISTING_STAGED_CHANGES'
 assert '399 passed' in (TASK/'linux-scheduler-regression-complete.log').read_text(encoding='utf-8')
 real=json.loads((TASK/'real-mysql-scheduler-verification.json').read_text(encoding='utf-8'))
 assert real['status']=='PASS' and real['realMysql'] and real['ownedContainerRemoved']
 known=set()
 for path in PRIVATE.glob('*.json'):
  if path.stat().st_size<32*1024*1024:secrets(json.loads(path.read_text(encoding='utf-8-sig')),known)
 for name in ['spug-login.private.json','loginCredentials.json']:
  secrets(json.loads((Path('C:/SpugHandoff/release/private')/name).read_text(encoding='utf-8-sig')),known)
 assert known
 pins=[]
 for name in FILES:
  raw=(ROOT/name).read_bytes();text=raw.decode('utf-8')
  assert '\ufffd' not in text and not text.startswith('\ufeff')
  assert not any(value in text for value in known),'KNOWN_PRIVATE_VALUE_FOUND'
  if name.endswith('.py'):ast.parse(text)
  else:json.loads(text)
  pins.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
 git('diff','--check')
 all_names=git('status','--porcelain=v1','-uall').decode('utf-8').splitlines()
 excluded={line[3:]:hashlib.sha256((ROOT/line[3:]).read_bytes()).hexdigest() for line in all_names
           if line[3:] not in FILES and (ROOT/line[3:]).is_file()}
 git('add','--',*FILES)
 staged=set(git('diff','--cached','--name-only').decode().splitlines());assert staged==set(FILES)
 committed=subprocess.run(['git','commit','-m','任务: 补齐主实例恢复调度器与失败保护交接'],cwd=ROOT,capture_output=True)
 (PRIVATE/'scheduler-implementation-commit.private.log').write_bytes(committed.stdout+committed.stderr)
 assert committed.returncode==0,'IMPLEMENTATION_COMMIT_FAILED_SEE_PRIVATE_LOG'
 commit=git('rev-parse','HEAD').decode().strip()
 assert git('rev-parse','HEAD^').decode().strip()==BASE
 assert set(git('show','--format=','--name-only',commit).decode().splitlines())==set(FILES)
 assert not git('diff','--cached','--name-only')
 assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value for name,value in excluded.items()),'EXCLUDED_FILE_CHANGED'
 report=dict(status='PASS',sourceCommit=commit,parentCommit=BASE,implementationFiles=pins,
  regressionPassed=399,realMysqlVerified=True,utf8AndSyntaxVerified=True,
  knownPrivateValuesChecked=len(known),privateValuesFound=0,excludedFileCount=len(excluded),excludedFilesUnchanged=True)
 (TASK/'scheduler-implementation-commit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='implementationFiles'}))
