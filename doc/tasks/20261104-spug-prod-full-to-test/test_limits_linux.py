"""Run isolated local Linux component tests; never connects to target servers."""
import json
import subprocess
from pathlib import Path

DOCKER='C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
NAME='spug-readback-limits-unit-20261105'
ROOT=Path(__file__).resolve().parents[3]
IMAGE='python:3.12-bookworm'
def run(args,**kw):
    return subprocess.run([DOCKER,*args],check=True,**kw)
if __name__=='__main__':
    run(['volume','create','--label','codex.task=spug-prod-full-to-test-20261104',NAME])
    run(['create','--name',NAME,'--label','codex.task=spug-prod-full-to-test-20261104',
         '--cap-add','SYS_ADMIN','--mount','type=bind,source='+str(ROOT)+',target=/source,readonly',
         '--mount','type=volume,source='+NAME+',target=/work',
         '-w','/source',IMAGE,'python','-B','-c',
         "import subprocess,sys;subprocess.run([sys.executable,'-m','pip','install','-q','--target','/work/deps','pytest','jsonschema'],check=True);"
         "sys.path.insert(0,'/work/deps');import pytest;"
         "sys.exit(pytest.main(['scripts/tests/test_backup_variants.py','scripts/tests/test_retained_replacement_retry.py',"
         "'scripts/tests/test_replacement_storage.py','scripts/tests/test_smallapp_replacement.py',"
         "'scripts/tests/test_retained_failure_reservation.py','scripts/tests/test_native_retained_failure.py',"
         "'-q','-p','no:cacheprovider','--basetemp=/work/pytest']))"])
    result=subprocess.run([DOCKER,'start','-a',NAME])
    state=json.loads(subprocess.check_output([DOCKER,'inspect',NAME]))[0]
    Path(__file__).with_name('limits-linux-verification.json').write_text(json.dumps(
        {'container':NAME,'image':IMAGE,'state':state['State'],'exitCode':state['State']['ExitCode'],
         'scope':'LOCAL_COMPONENTS_NOT_SERVER_RESTORE'},indent=2),encoding='utf-8')
    assert result.returncode==0 and state['State']['ExitCode']==0,'LINUX_COMPONENT_TEST_FAILED'
