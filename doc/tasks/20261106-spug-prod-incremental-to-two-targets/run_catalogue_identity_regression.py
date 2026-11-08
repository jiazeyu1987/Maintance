"""Local-only fixed suite with frozen source hashes and captured UTF-8 output."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from common import TASK, PRIVATE, now, write

ROOT = TASK.parents[2]
SOURCE = ROOT / 'ops/spug/release-center'
FILES = ['application_registry.py', 'executor.py', 'release_http.py', 'package_catalog.py',
         'package_presence.py', 'test_release_identity.py', 'test_package_catalog.py',
         'test_package_presence.py', 'test_commit_catalog.py', 'README.md']
SUITE = ['test_release_identity', 'test_applications', 'test_package_catalog', 'test_package_presence',
         'test_state', 'test_commit_catalog', 'test_current_versions', 'test_database_versions']


def pins():
    return {name: {'bytes': (SOURCE/name).stat().st_size,
                   'sha256': hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()} for name in FILES}


def main():
    before = pins()
    env = dict(os.environ, PYTHONPATH=str(PRIVATE/'test-dependencies'))
    command = [sys.executable, '-X', 'utf8', '-B', '-m', 'unittest', '-v', *SUITE]
    result = subprocess.run(command, cwd=SOURCE, env=env, capture_output=True, timeout=120)
    output = result.stdout + result.stderr
    output.decode('utf-8')
    (TASK/'catalogue-identity-regression.log').write_bytes(output)
    report = dict(observedAt=now(), exitCode=result.returncode, testModules=SUITE,
                  sourcePins=before, sourceUnchanged=before == pins(),
                  outputSha256=hashlib.sha256(output).hexdigest(),
                  runtimeChanges=0, serverOperations=0)
    write(TASK/'catalogue-identity-regression.json', report)
    print(output.decode('utf-8'))
    assert result.returncode == 0 and report['sourceUnchanged']


if __name__ == '__main__':
    main()
