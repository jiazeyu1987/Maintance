"""Read only numeric scratch-directory metadata for the existing SQL readback."""
import json
from install_prod_control import TASK, remote

SCRIPT = r'''
import datetime,json,pathlib
operation=OPERATION_LITERAL
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3/recovery-operations')/operation/'database-000'/'database-readback'
assert root.is_dir() and not root.is_symlink(),'READBACK_SCRATCH_NOT_AVAILABLE'
parts=[p for p in root.iterdir() if p.name.isdecimal() and p.is_dir() and not p.is_symlink()]
tokens=[(p/'tokens.tsv').stat() for p in parts if (p/'tokens.tsv').is_file()]
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=operation,
    startedTableDirectories=len(parts),highestStartedTableIndex=max((int(p.name) for p in parts),default=None),
    tokenFiles=len(tokens),tokenBytes=sum(s.st_size for s in tokens),
    latestTokenWriteAt=datetime.datetime.fromtimestamp(max((s.st_mtime for s in tokens),default=root.stat().st_mtime),datetime.timezone.utc).isoformat(),
    databaseMutations=0,businessValuesRead=False,fullComparisonSuccessNotInferred=True)))
'''

if __name__ == '__main__':
    request=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']
    report=remote(SCRIPT.replace('OPERATION_LITERAL',repr(request['operationId'])),timeout=50)
    output=TASK/('database-readback-progress-'+request['operationId']+'.json')
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
