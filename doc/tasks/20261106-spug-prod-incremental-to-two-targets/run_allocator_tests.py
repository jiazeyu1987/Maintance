"""Run allocator and affected package tests in an isolated Linux carrier."""
import argparse
import hashlib
import json
import subprocess
from common import TASK, PRIVATE, now, write

parser = argparse.ArgumentParser()
parser.add_argument('phase', choices=['red', 'green', 'regression'])
parser.add_argument('--attempt', type=int, default=1)
parser.add_argument('--entry', action='store_true')
parser.add_argument('--legacy', action='store_true')
parser.add_argument('--frontend-health', action='store_true')
parser.add_argument('--quiescence', action='store_true')
parser.add_argument('--packaged-frontend', action='store_true')
parser.add_argument('--offline-wheels', action='store_true')
args = parser.parse_args()
stem = ('allocator-entry-' if args.entry else 'allocator-') + args.phase + '-' + str(args.attempt)
if args.legacy:stem='legacy-clearance-'+args.phase+'-'+str(args.attempt)
if args.frontend_health:stem='frontend-health-'+args.phase+'-'+str(args.attempt)
if args.quiescence:stem='inherited-quiescence-'+args.phase+'-'+str(args.attempt)
if args.packaged_frontend:stem='packaged-frontend-'+args.phase+'-'+str(args.attempt)
assert not (TASK / (stem + '.json')).exists()
name = 'spug-' + stem + '-20261107'
docker = 'C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
tests = ['scripts/tests/test_frozen_auto_increment.py']
if args.entry:tests=['scripts/tests/test_backup_variants.py::test_packaged_minimal_runtime_loads_real_allocator_dependency']
if args.legacy:tests=['scripts/tests/test_legacy_main_clearance.py']
if args.frontend_health:tests=['scripts/tests/test_main_readiness.py']
if args.quiescence:tests=['scripts/tests/test_retained_replacement_retry.py']
if args.packaged_frontend:tests=['scripts/tests/test_backup_variants.py::test_packaged_constructor_binds_only_requested_frontend_readiness']
if args.phase == 'regression':
    tests += ['scripts/tests/test_backup_variants.py', 'scripts/tests/test_native_import_process_evidence.py',
              'scripts/tests/test_native_retained_failure.py', 'scripts/tests/test_retained_replacement_retry.py',
              'scripts/tests/test_smallapp_binlog_ddl.py']
    if args.legacy:tests+=['scripts/tests/test_main_mysql_scheduler.py']
    if args.frontend_health:tests+=['scripts/tests/test_main_restore_target.py','scripts/tests/test_main_mysql_scheduler.py','scripts/tests/test_legacy_main_clearance.py']
assert subprocess.run([docker, 'inspect', name], capture_output=True).returncode != 0
script = '''import os,subprocess
subprocess.run(['git','init','--bare','-q','/tmp/test-git'],check=True)
os.environ.update(GIT_DIR='/tmp/test-git',GIT_COMMON_DIR='/tmp/test-git',GIT_WORK_TREE='/src',GIT_ALTERNATE_OBJECT_DIRECTORIES='/git-common/objects')
subprocess.run(['git','cat-file','-e',os.environ['EXPECTED_HEAD']+'^{commit}'],check=True)
subprocess.run(['git','update-ref','--no-deref','HEAD',os.environ['EXPECTED_HEAD']],check=True)
assert subprocess.check_output(['git','-C','/src','rev-parse','HEAD']).decode().strip()==os.environ['EXPECTED_HEAD']
import pytest
for name in TEST_FILES:
 print('INDEPENDENT_TEST_FILE '+name,flush=True)
 result=subprocess.run([os.sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','--tb=short',name])
 if result.returncode:raise SystemExit(result.returncode)
'''.replace('TEST_FILES', repr(tests))
inputs = list(dict.fromkeys(['ops/backup_engine/formal/formal_schema_evidence.py', 'ops/recovery/recovery_data.py',
          'ops/recovery/recovery_minimal_runtime.py', 'ops/recovery/recovery_main_health.py', 'ops/recovery/recovery_retained_retry.py', 'ops/backup_engine/standard_fixes.py', *[n.split('::')[0] for n in tests]]))
before = {name: hashlib.sha256((TASK.parents[2] / name).read_bytes()).hexdigest() for name in inputs}
carrier=[]
entry=['sh','-ec','pip install --quiet --root-user-action=ignore pytest==8.3.5 jsonschema==4.23.0 redis==5.2.1; exec python -B -']
wheel_pins=None
if args.offline_wheels:
    wheels=PRIVATE/'linux-test-wheels';wheel_pins={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in wheels.glob('*.whl')}
    assert len(wheel_pins)==12 and all(any(n.startswith(package+'-') for n in wheel_pins) for package in ('pytest','jsonschema','redis'))
    carrier=['--network','none','--mount','type=bind,source='+str(wheels)+',target=/wheels,readonly']
    entry=['python','-B','-']
    script='''import pathlib,hashlib,subprocess,sys
expected=WHEEL_PINS
assert {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path('/wheels').glob('*.whl')}==expected
subprocess.run([sys.executable,'-m','pip','install','--no-index','--find-links=/wheels','--quiet','--root-user-action=ignore','pytest==8.3.5','jsonschema==4.23.0','redis==5.2.1'],check=True)
'''.replace('WHEEL_PINS',repr(wheel_pins))+script
result = subprocess.run([docker, 'run', '--rm', '-i', '--name', name,
    '--label', 'codex.task=20261106-spug-prod-incremental-to-two-targets',
    '--mount', 'type=bind,source=' + str(TASK.parents[2]) + ',target=/src,readonly',
    '--mount', 'type=bind,source=' + subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-common-dir']).decode().strip() + ',target=/git-common,readonly',
    '--env', 'EXPECTED_HEAD=' + subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),
    '--workdir', '/src',
    *carrier,
    'sha256:14a4933e6cef421424f7a66d89a3f4eafcbd0d90e0a822251f298e05132dc735',
    *entry],
    input=script.encode(), capture_output=True)
raw = result.stdout + result.stderr
(TASK / (stem + '.log')).write_bytes(raw)
removed = subprocess.run([docker, 'inspect', name], capture_output=True).returncode != 0
expected = result.returncode == 0 and raw.count(b' passed') == len(tests) and b' skipped' not in raw
if args.phase == 'red':
    expected = (result.returncode == 1 and b'PACKAGED_FRONTEND_PROFILE_NOT_PROPAGATED' in raw and b'1 failed, 1 passed' in raw) if args.packaged_frontend else \
        (result.returncode == 1 and b'INHERITED_TARGET_MUST_STAY_QUIESCED' in raw and b'4 failed' in raw) if args.quiescence else \
        (result.returncode == 1 and b'MAIN_HEALTH_ENDPOINT_INVALID' in raw and b'2 failed' in raw) if args.frontend_health else \
        (result.returncode == 1 and b'KeyError' in raw and b'mainProtectionRecoveryPin' in raw and b'failed' in raw) if args.legacy else \
        (result.returncode == 1 and b'KeyError' in raw and b'formal_schema_evidence' in raw and b'2 failed' in raw) if args.entry else \
        (result.returncode == 2 and b'cannot import name' in raw and b'frozen_auto_increment_plan' in raw)
report = dict(observedAt=now(), phase=args.phase, actualExitCode=result.returncode,
    expectedResultObserved=expected, containerRemoved=removed, tests=tests,
    outputSha256=hashlib.sha256(raw).hexdigest(), testedInputSha256=before,
    isolatedProcesses=True,
    offlineWheelSha256=wheel_pins,networkDisabled=args.offline_wheels,
    inputFilesUnchanged=before == {name: hashlib.sha256((TASK.parents[2] / name).read_bytes()).hexdigest() for name in inputs})
write(TASK / (stem + '.json'), report)
print(raw.decode('utf8', 'strict')[-9000:]);print(json.dumps(report))
raise SystemExit(0 if expected and removed and report['inputFilesUnchanged'] else 1)
