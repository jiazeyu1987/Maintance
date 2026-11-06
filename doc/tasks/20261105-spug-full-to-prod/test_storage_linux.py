"""Run current-goal storage admission tests on a task-owned Linux volume."""
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
TASK=Path(__file__).resolve().parent
DOCKER='C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
NAME='spug-prod-retained-storage-20261105'
if __name__=='__main__':
    phase=sys.argv[1]
    if phase=='red' and '--prepared' not in sys.argv:
        subprocess.run([DOCKER,'volume','create','--label','codex.task=spug-full-to-prod-20261105',NAME],check=True)
    common=subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-common-dir'],cwd=ROOT).decode().strip()
    gitdir=Path(subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-dir'],cwd=ROOT).decode().strip())
    relative=gitdir.relative_to(Path(common)).as_posix()
    tests=['scripts/tests/test_main_retained_authentication.py'] if '--auth' in sys.argv else ['scripts/tests/test_retained_application_storage.py']
    if '--packaging' in sys.argv:tests=['scripts/tests/test_restore_target_registration.py','scripts/tests/test_backup_variants.py']
    if '--endpoint' in sys.argv:tests=['scripts/tests/test_main_published_endpoint.py']
    if '--archive' in sys.argv:tests=['scripts/tests/test_main_archive_view.py']
    if '--resources' in sys.argv:tests=['scripts/tests/test_recovery_resource_budget.py','scripts/tests/test_recovery_resource_reservation.py']
    if '--scheduler' in sys.argv:tests=['scripts/tests/test_main_mysql_scheduler.py']
    if '--handoff' in sys.argv:tests=['scripts/tests/test_retained_replacement_retry.py','scripts/tests/test_backup_variants.py']
    if '--health' in sys.argv:tests=['scripts/tests/test_main_readiness.py']
    if phase.startswith('regression'):tests+=['scripts/tests/test_retained_application_storage.py','scripts/tests/test_replacement_storage.py','scripts/tests/test_main_restore_target.py',
        'scripts/tests/test_backup_variants.py','scripts/tests/test_retained_replacement_retry.py']
    if phase.startswith('regression'):tests+=['scripts/tests/test_main_retained_authentication.py','scripts/tests/test_main_published_endpoint.py','scripts/tests/test_restore_target_registration.py',
        'scripts/tests/test_retained_failure_reservation.py','scripts/tests/test_native_retained_failure.py']
    if phase.startswith('regression'):tests+=['scripts/tests/test_main_archive_view.py','scripts/tests/test_main_mysql_scheduler.py','scripts/tests/test_archive_view_protection_linux.py']
    if phase.startswith('regression') and '--resources' in sys.argv:tests+=['scripts/tests/test_recovery_resource_budget.py','scripts/tests/test_recovery_resource_reservation.py']
    if phase.startswith('regression'):tests+=['scripts/tests/test_main_readiness.py']
    tests=list(dict.fromkeys(tests))
    code='import sys;sys.path.insert(0,"/work/deps");import pytest;sys.exit(pytest.main('+repr(tests+['-q','-p','no:cacheprovider','--basetemp=/work/pytest-'+phase])+'))'
    if phase=='red' and '--prepared' not in sys.argv:
        code='import subprocess,sys,importlib;subprocess.run([sys.executable,"-m","pip","install","-q","--target","/work/deps","pytest","jsonschema"],check=True);importlib.invalidate_caches();'+code
    command=[DOCKER,'run','--rm','--name',NAME+'-'+phase,'--label','codex.task=spug-full-to-prod-20261105',
        '--cap-add','SYS_ADMIN','--mount','type=bind,source='+str(ROOT)+',target=/source,readonly',
        '--mount','type=bind,source='+common+',target=/git-common,readonly',
        '--mount','type=volume,source='+NAME+',target=/work',
        '-e','GIT_DIR=/git-common/'+relative,'-e','GIT_COMMON_DIR=/git-common','-e','GIT_WORK_TREE=/source',
        '-e','PYTHONPATH=/work/deps','-e','GIT_CONFIG_COUNT=1','-e','GIT_CONFIG_KEY_0=safe.directory','-e','GIT_CONFIG_VALUE_0=/source',
        '-w','/source','python:3.12-bookworm','python','-B','-c',code]
    result=subprocess.run(command,capture_output=True)
    label='health' if '--health' in sys.argv else ('scheduler' if '--scheduler' in sys.argv else ('resources' if '--resources' in sys.argv else ('archive-contract' if '--archive' in sys.argv else ('endpoint' if '--endpoint' in sys.argv else ('packaging' if '--packaging' in sys.argv else ('auth' if '--auth' in sys.argv else 'storage'))))))
    (TASK/('linux-'+label+'-'+phase+'.log')).write_bytes(result.stdout+result.stderr)
    print(result.stdout.decode('utf-8',errors='replace')[-5000:]);print(result.stderr.decode('utf-8',errors='replace')[-1000:])
    print('EXIT',result.returncode);sys.exit(result.returncode)
