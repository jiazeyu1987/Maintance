"""Run actual POSIX component contracts in one task-owned local container."""
import json
import subprocess
import sys
from pathlib import Path

TASK=Path(__file__).resolve().parent
ROOT=TASK.parents[2]
NAME='spug-review-retry-unit-20261105'
DOCKER='C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
TESTS=['scripts/tests/test_retained_replacement_retry.py','scripts/tests/test_retained_failure_reservation.py',
       'scripts/tests/test_native_retained_failure.py','scripts/tests/test_smallapp_replacement.py',
       'scripts/tests/test_archive_path_fd_budget.py','scripts/tests/test_replacement_storage.py',
       'scripts/tests/test_backup_variants.py']

if __name__=='__main__':
    phase=sys.argv[1]
    if phase=='red':
        subprocess.run([DOCKER,'volume','create','--label','codex.task=spug-prod-full-to-review-20261105',NAME],check=True)
        subprocess.run([DOCKER,'create','--name',NAME,'--label','codex.task=spug-prod-full-to-review-20261105',
            '--cap-add','SYS_ADMIN','--mount','type=bind,source='+str(ROOT)+',target=/source,readonly',
            '--mount','type=volume,source='+NAME+',target=/work','-w','/source','python:3.12-bookworm','sleep','infinity'],check=True)
        subprocess.run([DOCKER,'start',NAME],check=True)
        subprocess.run([DOCKER,'exec',NAME,'python','-m','pip','install','-q','--target','/work/deps','pytest','jsonschema'],check=True)
    args=TESTS if phase=='regression' else [TESTS[-1]] if phase=='packaging' else [TESTS[0],'-k','before_mutation']
    code='import sys;sys.path.insert(0,"/work/deps");import pytest;sys.exit(pytest.main('+repr(args+['-q','-p','no:cacheprovider','--basetemp=/work/pytest-'+phase])+'))'
    if phase=='packaging':
        common=subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-common-dir'],cwd=ROOT).decode().strip()
        gitdir=Path(subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-dir'],cwd=ROOT).decode().strip())
        relative=gitdir.relative_to(Path(common)).as_posix()
        command=[DOCKER,'run','--rm','--name',NAME+'-packaging','--label','codex.task=spug-prod-full-to-review-20261105',
            '--mount','type=bind,source='+str(ROOT)+',target=/source,readonly',
            '--mount','type=bind,source='+common+',target=/git-common,readonly',
            '--mount','type=volume,source='+NAME+',target=/work',
            '-e','GIT_DIR=/git-common/'+relative,'-e','GIT_COMMON_DIR=/git-common','-e','GIT_WORK_TREE=/source',
            '-e','PYTHONPATH=/work/deps',
            '-e','GIT_CONFIG_COUNT=1','-e','GIT_CONFIG_KEY_0=safe.directory','-e','GIT_CONFIG_VALUE_0=/source',
            '-w','/source','python:3.12-bookworm','python','-B','-c',code]
    else:command=[DOCKER,'exec',NAME,'python','-B','-c',code]
    result=subprocess.run(command,capture_output=True)
    (TASK/('linux-'+phase+'.log')).write_bytes(result.stdout+result.stderr)
    print(result.stdout.decode('utf-8',errors='replace')[-5000:])
    print('EXIT',result.returncode)
    sys.exit(result.returncode)
