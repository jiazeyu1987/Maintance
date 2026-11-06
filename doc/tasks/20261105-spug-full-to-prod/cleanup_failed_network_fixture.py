"""Explicitly dispose only this task's failed network fixture rules; keep evidence."""
import json
import subprocess
import sys
from pathlib import Path

if '--inside' in sys.argv:
    sys.path.insert(0,'/source/ops/recovery')
    from recovery_engine import digest
    prefix='SF_'+digest('real-network-observation')[:20]+'_'
    removed=[]
    for tool in ('iptables','ip6tables'):
        import shlex
        rows=[shlex.split(line) for line in subprocess.check_output([tool,'-t','mangle','-S']).decode().splitlines()]
        owned={r[1] for r in rows if r[0]=='-N' and r[1].startswith(prefix)}
        for row in rows:
            if row[0]=='-A' and row[1] not in owned and row[-2:][0]=='-j' and row[-1] in owned:
                subprocess.run([tool,'-t','mangle','-D',*row[1:]],check=True)
        for row in rows:
            if row[0]=='-A' and row[1] in owned:
                subprocess.run([tool,'-t','mangle','-D',*row[1:]],check=True)
        for chain in sorted(owned):
            subprocess.run([tool,'-t','mangle','-X',chain],check=True);removed.append(dict(tool=tool,chain=chain))
    print(json.dumps(dict(scope='isolated-task-test-container-only',removed=removed,evidenceRetained=True)))
else:
    from prepare_network_linux import NETWORK
    from test_storage_linux import DOCKER,TASK
    row=json.loads(subprocess.check_output([DOCKER,'inspect',NETWORK]))[0]
    assert row['Config']['Labels']['codex.task']=='spug-full-to-prod-20261105'
    assert row['HostConfig']['NetworkMode']!='host'
    result=subprocess.run([DOCKER,'exec',NETWORK,'python','-B','/source/doc/tasks/20261105-spug-full-to-prod/cleanup_failed_network_fixture.py','--inside'],capture_output=True)
    (TASK/'linux-fence-failed-fixture-disposal.log').write_bytes(result.stdout+result.stderr)
    print(result.stdout.decode());print(result.stderr.decode());raise SystemExit(result.returncode)
