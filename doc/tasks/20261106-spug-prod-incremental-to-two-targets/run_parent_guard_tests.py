"""Run genuine Linux parent-guard tests in a disposable local carrier."""
import argparse
import hashlib
import json
import subprocess

from common import TASK, now, write


parser = argparse.ArgumentParser()
parser.add_argument('--phase', choices=('red', 'red-init', 'green', 'regression'), required=True)
parser.add_argument('--attempt', type=int, default=1)
args = parser.parse_args()
assert args.attempt >= 1
suffix = '' if args.attempt == 1 else '-' + str(args.attempt)
docker = 'C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
name = 'spug-parent-input-guard-' + args.phase + suffix + '-20261107'
assert subprocess.run([docker, 'inspect', name], capture_output=True).returncode != 0
tests = ['scripts/tests/test_capture_parent_guard.py']
if args.phase == 'red':
    tests = [tests[0] + '::' + test for test in (
        'test_per_buffer_checks_do_not_reopen_parent_bytes_or_scan_all_parent_paths',
        'test_parent_files_and_all_ancestors_are_leased_until_explicit_close')]
elif args.phase == 'regression':
    tests = ['scripts/tests/test_archive_path_fd_budget.py']
elif args.phase == 'red-init':
    tests = [tests[0] + '::test_semantic_constructor_failure_after_parent_acquisition_closes_leases']
command = [docker, 'run', '-i', '--rm', '--name', name,
           '--label', 'codex.task=20261106-spug-prod-incremental-to-two-targets',
           '--mount', 'type=bind,source=' + str(TASK.parents[2]) + ',target=/src,readonly',
           '--workdir', '/src',
           'sha256:14a4933e6cef421424f7a66d89a3f4eafcbd0d90e0a822251f298e05132dc735',
           'sh', '-ec', 'pip install --quiet --root-user-action=ignore pytest==8.3.5 jsonschema==4.23.0 redis==5.2.1; exec python -B -']
script = 'import pytest\nraise SystemExit(pytest.main(' + repr(['-q', '-p', 'no:cacheprovider', '--tb=short', *tests]) + '))\n'
report_path = TASK / ('parent-guard-' + args.phase + suffix + '.json')
assert not report_path.exists(), 'ORIGINAL_TEST_REPORT_ALREADY_EXISTS'
result = subprocess.run(command, input=script.encode(), capture_output=True)
raw = result.stdout + result.stderr
(TASK / ('parent-guard-' + args.phase + suffix + '.log')).write_bytes(raw)
removed = subprocess.run([docker, 'inspect', name], capture_output=True).returncode != 0
expected = (result.returncode == 1 and b'2 failed' in result.stdout and
            b'parent metadata must not be reread per pipe buffer' in result.stdout and
            b'each parent path must retain its Linux lease' in result.stdout) if args.phase == 'red' else (
                result.returncode == 0 and b' passed' in result.stdout and b' skipped' not in result.stdout)
if args.phase == 'red-init':
    expected = result.returncode == 1 and b'1 failed' in result.stdout and b'semantic constructor failure leaked parent leases' in result.stdout
report = dict(observedAt=now(), phase=args.phase, actualPytestExitCode=result.returncode,
              expectedResultObserved=expected, containerRemoved=removed, tests=tests,
              outputSha256=hashlib.sha256(raw).hexdigest(), diagnosticOnly=True,
              productionRecoveryAcceptance=False)
write(report_path, report)
print(raw.decode()); print(json.dumps(report))
raise SystemExit(0 if expected and removed else 1)
