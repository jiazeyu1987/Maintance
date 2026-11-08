"""Inspect only proc metadata for the exact active incremental importer."""
import argparse
import json

from common import TASK, remote, write, restore_kind

SCRIPT = r'''
import datetime,json,os,pathlib,time
root=pathlib.Path(ROOT)
expected=root/'recovery-operations'/OPERATION/'database-001/incremental.sql'
deadline=time.monotonic()+8
matches=[];visited=0;complete=True
for proc in pathlib.Path('/proc').iterdir():
 if not proc.name.isdecimal():continue
 try:command=(proc/'cmdline').read_bytes()
 except (FileNotFoundError,ProcessLookupError):continue
 if b'recovery_minimal_worker.py' not in command or OPERATION.encode() not in command:continue
 for fd in (proc/'fd').iterdir():
  if time.monotonic()>deadline:complete=False;break
  visited+=1
  try:
   if os.readlink(fd)!=str(expected):continue
   info=dict(line.split(':',1) for line in (proc/'fdinfo'/fd.name).read_text().splitlines())
   flags=int(info['flags'].strip(),8)
   if flags & getattr(os,'O_PATH',0):continue
   matches.append(dict(pid=int(proc.name),fd=int(fd.name),position=int(info['pos']),bytes=expected.stat().st_size))
  except (OSError,KeyError):continue
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=OPERATION,fdEntriesExamined=visited,allMatchingWorkerFdsExamined=complete,incrementalSqlReaders=matches,wholeOperationProgressPercentageClaimed=False)))
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('suffix', choices=['58', '59'])
    args = parser.parse_args()
    submission = json.loads((TASK / (restore_kind(args.suffix) + '-ui-submission.json')).read_text(encoding='utf-8'))
    operation = submission['request']['operationId']
    root = ('/mnt/intruoyi-data/' if args.suffix == '59' else '/var/lib/docker/intruoyi-data/') + 'spug-main-restore-20261104-v3'
    value = remote('172.30.30.' + args.suffix, 'ROOT=' + repr(root) + '\nOPERATION=' + repr(operation) + '\n' + SCRIPT, 25)
    write(TASK / (restore_kind(args.suffix) + '-incremental-reader.json'), value)
    print(json.dumps(value))
