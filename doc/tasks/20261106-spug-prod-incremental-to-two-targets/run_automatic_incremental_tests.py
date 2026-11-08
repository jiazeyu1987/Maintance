"""Run affected contracts in offline Linux, each suite in a fresh interpreter."""
import argparse
import hashlib
import json
import subprocess
from common import TASK, PRIVATE, now, write

parser = argparse.ArgumentParser()
parser.add_argument('suite', choices=('stream-epoch', 'control', 'regression', 'deployment-contracts'))
parser.add_argument('--attempt', type=int, required=True)
args = parser.parse_args()
groups = {
    'deployment-contracts': ['test_automatic_incremental_plan.py', 'test_backup_epoch.py',
        'test_smallapp_replacement.py', 'test_main_restore_target.py', 'test_backup_variants.py',
        'test_automatic_incremental_resilience.py'],
    'stream-epoch': ['test_incremental_sql_stream.py', 'test_backup_epoch.py', 'test_smallapp_replacement.py',
        'test_automatic_incremental_resilience.py'],
    'control': ['test_automatic_incremental_plan.py', 'test_native_oom_target.py',
        'test_smallapp_terminal_query.py', 'test_restore_archive_catalogue.py', 'test_restore_target_http.py'],
    'regression': ['test_backup_variants.py', 'test_native_import_process_evidence.py',
        'test_native_retained_failure.py', 'test_retained_replacement_retry.py',
        'test_smallapp_binlog_ddl.py', 'test_main_restore_target.py', 'test_main_mysql_scheduler.py',
        'test_legacy_main_clearance.py', 'test_capture_request_binding.py', 'test_capture_redis_auth.py'],
}
tests = ['scripts/tests/' + name for name in groups[args.suite]]
root = TASK.parents[2]
assert all((root / name).is_file() for name in tests), 'TEST_INPUT_MISSING'
stem = 'automatic-incremental-' + args.suite + '-' + str(args.attempt)
assert not (TASK / (stem + '.json')).exists() and not (TASK / (stem + '.log')).exists()
name = 'spug-' + stem + '-20261107'
docker = 'C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
assert subprocess.run([docker, 'inspect', name], capture_output=True).returncode != 0
wheels = PRIVATE / 'linux-test-wheels'
wheel_pins = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in wheels.glob('*.whl')}
assert len(wheel_pins) == 12
inputs = sorted(set(tests + [str(path.relative_to(root)).replace('\\', '/')
    for folder in ('backend/src/main/resources', 'ops/recovery', 'ops/backup_engine')
    for path in (root / folder).rglob('*.py')]))
before = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in inputs}
script = '''import hashlib,os,pathlib,subprocess,sys
expected=WHEEL_PINS
assert {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path('/wheels').glob('*.whl')}==expected
subprocess.run([sys.executable,'-m','pip','install','--no-index','--find-links=/wheels','--quiet','--root-user-action=ignore','pytest==8.3.5','jsonschema==4.23.0','redis==5.2.1'],check=True)
subprocess.run(['git','init','--bare','-q','/tmp/test-git'],check=True)
os.environ.update(GIT_DIR='/tmp/test-git',GIT_COMMON_DIR='/tmp/test-git',GIT_WORK_TREE='/src',GIT_ALTERNATE_OBJECT_DIRECTORIES='/git-common/objects')
subprocess.run(['git','cat-file','-e',os.environ['EXPECTED_HEAD']+'^{commit}'],check=True)
subprocess.run(['git','update-ref','--no-deref','HEAD',os.environ['EXPECTED_HEAD']],check=True)
for test in TEST_FILES:
 print('INDEPENDENT_TEST_FILE '+test,flush=True)
 result=subprocess.run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','--tb=short',test])
 if result.returncode:raise SystemExit(result.returncode)
'''.replace('WHEEL_PINS', repr(wheel_pins)).replace('TEST_FILES', repr(tests))
command = [docker, 'run', '--rm', '-i', '--name', name, '--network', 'none',
    '--label', 'codex.task=20261106-spug-prod-incremental-to-two-targets',
    '--mount', 'type=bind,source=' + str(root) + ',target=/src,readonly',
    '--mount', 'type=bind,source=' + str(wheels) + ',target=/wheels,readonly',
    '--mount', 'type=bind,source=' + subprocess.check_output(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir']).decode().strip() + ',target=/git-common,readonly',
    '--env', 'EXPECTED_HEAD=' + subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip(),
    '--workdir', '/src', 'sha256:14a4933e6cef421424f7a66d89a3f4eafcbd0d90e0a822251f298e05132dc735',
    'python', '-B', '-']
result = subprocess.run(command, input=script.encode('utf-8'), capture_output=True)
raw = result.stdout + result.stderr
(TASK / (stem + '.log')).write_bytes(raw)
removed = subprocess.run([docker, 'inspect', name], capture_output=True).returncode != 0
unchanged = before == {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in inputs}
passed = result.returncode == 0 and raw.count(b' passed') == len(tests) and b' skipped' not in raw
report = dict(observedAt=now(), tests=tests, actualExitCode=result.returncode,
    allTestsActuallyExecuted=passed, containerRemoved=removed, inputFilesUnchanged=unchanged,
    testedInputSha256=before, outputSha256=hashlib.sha256(raw).hexdigest(),
    offlineWheelSha256=wheel_pins, networkDisabled=True)
write(TASK / (stem + '.json'), report)
print(raw.decode('utf-8')[-9000:])
print(json.dumps({key: value for key, value in report.items()
    if key not in ('testedInputSha256', 'offlineWheelSha256')}))
raise SystemExit(0 if passed and removed and unchanged else 1)
