"""Build only the exact committed input in a new task-owned release worktree."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
TASK=Path(__file__).resolve().parent
PRIVATE=Path("C:/Spug/runtime/private/full-to-prod-20261105")

ROOT=TASK.parents[2]
def git(*args,cwd=ROOT):
    return subprocess.check_output(['git',*args],cwd=cwd).decode('utf-8').strip()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True);args=parser.parse_args()
    commit=git('rev-parse',args.commit)
    assert len(commit)==40 and commit==args.commit
    previous=TASK/'release-build-verification.json'
    if previous.exists():
        old=json.loads(previous.read_text(encoding='utf-8'))
        (TASK/('release-build-'+old['targetCommit'][:7]+'.json')).write_bytes(previous.read_bytes())
    worktree=PRIVATE/('release-'+commit[:7]);package=PRIVATE/('package-'+commit[:7])
    assert not worktree.exists() and not package.exists()
    git('worktree','add','--detach',str(worktree),commit)
    assert git('rev-parse','HEAD',cwd=worktree)==commit and not git('status','--porcelain',cwd=worktree)
    command=[sys.executable,'-B','ops/backup_engine/build_variants.py','--output-directory',str(package)]
    result=subprocess.run(command,cwd=worktree,capture_output=True)
    (TASK/('release-build-'+commit[:7]+'.log')).write_bytes(result.stdout+result.stderr)
    assert result.returncode==0,'BUILD_FAILED_SEE_NETWORK_RELEASE_BUILD_LOG'
    assert git('rev-parse','HEAD',cwd=worktree)==commit and not git('status','--porcelain',cwd=worktree)
    artifact=package/'backup-restore-standard.tgz'
    with tarfile.open(artifact) as archive:
        version=json.load(archive.extractfile('package.json'))
        assert version['variant']=='standard' and version['fileVerification'] and version['payloadContentVerification']
        assert set(archive.getnames())==set(version['files'])|{'package.json'}
        for name,sha in version['files'].items():
            data=archive.extractfile(name).read()
            assert hashlib.sha256(data).hexdigest()==sha
            compile(data,name,'exec')
        assert hashlib.sha256(json.dumps(version['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==version['packageSha256']
    report=dict(status='PASS',worktree=str(worktree),targetCommit=commit,buildCommand=command,
        validationCommand='all archive members SHA256 + Python compile; exact HEAD and clean git status before/after',
        packageSha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),fileManifestSha256=version['packageSha256'],
        fileCount=len(version['files']),allFilesShaAndCompileVerified=True,newCommits=False,mergeRequired=False,deleted=False)
    (TASK/'release-build-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (TASK/('release-build-'+commit[:7]+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
