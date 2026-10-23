"""Final read-only verification of real UI-created Spug tasks and records."""
import datetime
import argparse
import json
import shlex
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, default=Path('doc/tasks/20261010-spug-integration/code-only-readonly-audit-20261011.json'))
parser.add_argument('--live', action='store_true')
args = parser.parse_args()
OUTPUT = args.output
code = "from apps.schedule.models import Task,History; import json; print(json.dumps({'tasks':[{'id':t.id,'name':t.name,'active':t.is_active,'targets':t.targets,'command':t.command} for t in Task.objects.all()], 'histories':[{'id':h.id,'task':h.task_id,'status':h.status} for h in History.objects.all()]},ensure_ascii=False))"
r = subprocess.run(['docker', 'exec', 'intruoyi-spug-spug-1', 'bash', '-lc',
                    'cd /data/spug/spug_api; python3 manage.py shell -c ' + shlex.quote(code)],
                   capture_output=True, encoding='utf-8', timeout=25, check=True)
data = json.loads(next(v for v in r.stdout.splitlines() if v.startswith('{"tasks"')))
assert len(data['tasks']) == 4
assert all(not t['active'] and json.loads(t['targets']) == ['local'] for t in data['tasks'])
expected_commands = {
    '发布状态查询': 'python3 /opt/intruoyi-spug/release_adapter.py --target ALL --mode status',
    '发布测试服': 'python3 /opt/intruoyi-spug/release_adapter.py --target TEST --mode ' + ('check' if args.live else 'publish'),
    '发布备份服': 'python3 /opt/intruoyi-spug/release_adapter.py --target BACKUP --mode publish',
    '发布正式服': 'python3 /opt/intruoyi-spug/release_adapter.py --target PROD --mode publish',
}
assert {t['name']: t['command'] for t in data['tasks']} == expected_commands
assert len(data['histories']) >= 12
private = Path('E:/Int/CacheData/IntRuoyi/spug-integration-20261010')
config = json.loads((private / 'backend.private.json').read_text(encoding='utf-8-sig'))
assert config['publishEnabled'] is False and config['productionPaused'] is True
try:
    with urllib.request.urlopen('http://127.0.0.1:18080/api/schedule/', timeout=10) as response:
        raise AssertionError('Anonymous task access was not refused')
except urllib.error.HTTPError as error:
    assert error.code == 401
data.update(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            anonymousHttpStatus=401, verifiedAfterServiceRestart=False,
            publishEnabled=False, productionPaused=True, realDeploymentVerified=False)
if args.live:
    selection = json.loads((private / 'candidate.private.json').read_text(encoding='utf-8-sig'))
    assert selection['workflowId'] == 'rw-5d206b23d31a'
    assert selection['observedTestOperationId'] == 'bf37637e-1059-4255-be00-36bc46818cde'
    persistence = json.loads(Path('doc/tasks/20261010-spug-integration/live-real-ui-persistence-20261012.json').read_text(encoding='utf-8'))
    assert len(persistence) == 4
    for result in persistence:
        assert result['readAfterFreshLogin'] is True and result['deploymentSubmitted'] is False
        assert any(h['id'] == result['historyId'] for h in data['histories'])
    # Inspect only task-owned query snapshots; no server receipts or DB success records are created.
    script = ('import pathlib,json; p=pathlib.Path("/var/lib/intruoyi-spug"); '
              'print(json.dumps({"submissionReceiptCount":len(list(p.glob("*.json"))), '
              '"queries":[json.loads(v.read_text()) for v in (p/"queries").glob("*.json")]}))')
    snapshots = subprocess.run(['docker', 'exec', 'intruoyi-spug-spug-1', 'python3', '-c', script],
                               capture_output=True, encoding='utf-8', timeout=15, check=True)
    durable = json.loads(snapshots.stdout)
    assert durable['submissionReceiptCount'] == 0
    assert len(durable['queries']) == 2
    assert all(s['deploymentSubmitted'] is False for s in durable['queries'])
    assert all(r['method'] == 'GET' or r['path'] == '/system/auth/login'
               for s in durable['queries'] for r in s['requests'])
    data.update(selection={k: selection[k] for k in ('workflowId', 'releaseTag', 'packageDigest', 'manifestDigest',
                                                    'applicationCommit', 'observedTestOperationId')},
                persistentQueries=durable, realFreshLoginHistoryReadVerified=True,
                originalTaskIdsPreserved=[t['id'] for t in data['tasks']])
OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('Read-only audit passed: four original inactive tasks, explicit fixed candidate, persisted histories; anonymous access returns 401.')
