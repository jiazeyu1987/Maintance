"""Real shipped lease tests using read-only Windows Git metadata mappings."""
import json
import subprocess
import sys
from pathlib import Path
from test_recovery_linux import DOCKER,ROOT,TASK

NAME='spug-review-deps-unit-20261105'
if __name__=='__main__':
    phase=sys.argv[1]
    if phase=='red':
        subprocess.run([DOCKER,'volume','create','--label','codex.task=spug-prod-full-to-review-20261105',NAME],check=True)
    common=subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-common-dir'],cwd=ROOT).decode().strip()
    gitdir=Path(subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-dir'],cwd=ROOT).decode().strip())
    relative=gitdir.relative_to(Path(common)).as_posix()
    tests=['scripts/tests/test_backup_variants.py']
    if phase!='regression':tests+=['-k','registered_main_archive_inputs']
    else:tests+=['scripts/tests/test_main_restore_target.py','scripts/tests/test_retained_replacement_retry.py','scripts/tests/test_archive_path_fd_budget.py']
    code='import sys;import pytest;sys.exit(pytest.main('+repr(tests+['-q','-p','no:cacheprovider','--basetemp=/work/pytest-'+phase])+'))'
    if phase=='red':code='import subprocess,sys;subprocess.run([sys.executable,"-m","pip","install","-q","--target","/work/deps","pytest","jsonschema"],check=True);sys.path.insert(0,"/work/deps");'+code
    command=[DOCKER,'run','--rm','--name',NAME+'-'+phase,'--label','codex.task=spug-prod-full-to-review-20261105',
        '--cap-add','SYS_ADMIN','--mount','type=bind,source='+str(ROOT)+',target=/source,readonly',
        '--mount','type=bind,source='+common+',target=/git-common,readonly',
        '--mount','type=volume,source='+NAME+',target=/work',
        '-e','GIT_DIR=/git-common/'+relative,'-e','GIT_COMMON_DIR=/git-common','-e','GIT_WORK_TREE=/source',
        '-e','PYTHONPATH=/work/deps','-e','GIT_CONFIG_COUNT=1','-e','GIT_CONFIG_KEY_0=safe.directory','-e','GIT_CONFIG_VALUE_0=/source',
        '-w','/source','python:3.12-bookworm','python','-B','-c',code]
    result=subprocess.run(command,capture_output=True)
    (TASK/('linux-main-'+phase+'.log')).write_bytes(result.stdout+result.stderr)
    print(result.stdout.decode('utf-8',errors='replace')[-5000:]);print('EXIT',result.returncode)
    sys.exit(result.returncode)
