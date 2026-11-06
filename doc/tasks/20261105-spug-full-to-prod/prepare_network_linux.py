"""Create only this goal's isolated network test environment."""
import json
import subprocess
from pathlib import Path
from test_storage_linux import ROOT,TASK,DOCKER,NAME

NETWORK='spug-prod-published-network-env-20261105'
if __name__=='__main__':
    command=[DOCKER,'run','-d','--name',NETWORK,'--label','codex.task=spug-full-to-prod-20261105',
        '--cap-add','NET_ADMIN','--cap-add','SYS_ADMIN',
        '--mount','type=bind,source='+str(ROOT)+',target=/source,readonly',
        '--mount','type=volume,source='+NAME+',target=/work',
        '-e','PYTHONPATH=/source/ops/recovery:/work/deps','-w','/source',
        'python:3.12-bookworm','sleep','21600']
    created=subprocess.run(command,capture_output=True)
    if created.returncode:raise RuntimeError('OWNED_NETWORK_ENV_CREATE_FAILED')
    code='import subprocess;subprocess.run(["apt-get","update","-qq"],check=True);subprocess.run(["apt-get","install","-y","-qq","iptables","iproute2"],check=True)'
    installed=subprocess.run([DOCKER,'exec',NETWORK,'python','-c',code],capture_output=True)
    (TASK/'linux-network-environment.log').write_bytes(created.stdout+created.stderr+installed.stdout+installed.stderr)
    print(json.dumps(dict(container=NETWORK,installed=installed.returncode==0)))
    print(installed.stderr.decode('utf-8',errors='replace')[-1000:])
    raise SystemExit(installed.returncode)
