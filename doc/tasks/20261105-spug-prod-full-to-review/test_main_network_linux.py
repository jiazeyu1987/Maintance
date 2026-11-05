"""Run exact MAIN network lifecycle and affected real package tests on Linux."""
import subprocess
import sys
from pathlib import Path
from test_recovery_linux import DOCKER, ROOT, TASK

NAME='spug-review-network-unit-20261105'
if __name__ == '__main__':
    phase=sys.argv[1]
    if phase=='red' and '--prepared' not in sys.argv:
        subprocess.run([DOCKER,'volume','create','--label','codex.task=spug-prod-full-to-review-20261105',NAME],check=True)
    common=subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-common-dir'],cwd=ROOT).decode().strip()
    gitdir=Path(subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-dir'],cwd=ROOT).decode().strip())
    relative=gitdir.relative_to(Path(common)).as_posix()
    tests=['scripts/tests/test_main_restore_target.py']
    if phase in ('red','green'):tests+=['-k','dynamic_attachment']
    else:tests+=['scripts/tests/test_backup_variants.py','scripts/tests/test_retained_replacement_retry.py','scripts/tests/test_retained_failure_reservation.py','scripts/tests/test_native_retained_failure.py']
    code='import sys;sys.path.insert(0,"/work/deps");import pytest;sys.exit(pytest.main('+repr(tests+['-q','-p','no:cacheprovider','--basetemp=/work/pytest-'+phase])+'))'
    if phase=='red' and '--prepared' not in sys.argv:code='import subprocess,sys,importlib;subprocess.run([sys.executable,"-m","pip","install","-q","--target","/work/deps","pytest","jsonschema"],check=True);importlib.invalidate_caches();'+code
    command=[DOCKER,'run','--rm','--name',NAME+'-'+phase,'--label','codex.task=spug-prod-full-to-review-20261105',
        '--cap-add','SYS_ADMIN','--mount','type=bind,source='+str(ROOT)+',target=/source,readonly',
        '--mount','type=bind,source='+common+',target=/git-common,readonly',
        '--mount','type=volume,source='+NAME+',target=/work',
        '-e','GIT_DIR=/git-common/'+relative,'-e','GIT_COMMON_DIR=/git-common','-e','GIT_WORK_TREE=/source',
        '-e','PYTHONPATH=/work/deps','-e','GIT_CONFIG_COUNT=1','-e','GIT_CONFIG_KEY_0=safe.directory','-e','GIT_CONFIG_VALUE_0=/source',
        '-w','/source','python:3.12-bookworm','python','-B','-c',code]
    result=subprocess.run(command,capture_output=True)
    (TASK/('linux-network-'+phase+'.log')).write_bytes(result.stdout+result.stderr)
    print(result.stdout.decode('utf-8',errors='replace')[-6500:]);print(result.stderr.decode('utf-8',errors='replace')[-1500:]);print('EXIT',result.returncode)
    sys.exit(result.returncode)
