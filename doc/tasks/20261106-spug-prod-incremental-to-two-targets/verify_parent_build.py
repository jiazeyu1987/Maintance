"""Bind fresh committed checkout bytes to the tested Python program semantics."""
import ast
import hashlib
import json
import subprocess
import sys
import tarfile

from common import TASK, now, write


if __name__ == '__main__':
    root = TASK.parents[2]
    build = json.loads((TASK / 'release-build-verification.json').read_text(encoding='utf-8'))
    tested = json.loads((TASK / 'parent-guard-implementation-commit.json').read_text(encoding='utf-8'))
    assert build['status'] == tested['status'] == 'PASS'
    assert build['targetCommit'] == tested['implementationCommit']
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip() == build['targetCommit']
    for name, sha in tested['testedInputSha256'].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == sha, 'TESTED_SOURCE_CHANGED'
    sys.path.insert(0, str(root / 'ops/backup_engine'))
    from build_variants import standard_sources, safe_fixes
    payload, _ = standard_sources()
    payload = safe_fixes(payload)
    payload['common/repository_minimal.py'] = payload['common/repository_minimal.py'].replace(b"'prod-'", b"'prod-standard-'")
    from pathlib import Path
    package = Path(build['worktree']).parent / ('package-' + build['targetCommit'][:7]) / 'backup-restore-standard.tgz'
    differences = []
    with tarfile.open(package) as archive:
        version = json.load(archive.extractfile('package.json'))
        assert set(version['files']) == set(payload) and len(payload) == 127
        for name, expected in payload.items():
            actual = archive.extractfile(name).read()
            assert hashlib.sha256(actual).hexdigest() == version['files'][name]
            assert actual.replace(b'\r\n', b'\n') == expected.replace(b'\r\n', b'\n'), 'UNTESTED_PACKAGE_BYTES'
            assert ast.dump(ast.parse(actual)) == ast.dump(ast.parse(expected)), 'UNTESTED_PACKAGE_PROGRAM'
            if actual != expected:
                differences.append(name)
    report = dict(status='PASS', observedAt=now(), sourceCommit=build['targetCommit'],
                  packageSha256=build['packageSha256'], fileManifestSha256=version['packageSha256'],
                  pythonProgramsVerified=127, allTestedInputsUnchanged=True,
                  allProgramASTsEqual=True, onlyGitCheckoutLineEndingDifferences=differences,
                  rawBytesAllEqual=not differences)
    write(TASK / 'parent-guard-build-program-verification.json', report)
    print(json.dumps(report))
