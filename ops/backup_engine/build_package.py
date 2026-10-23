"""Build the backup engine from an explicit clean Git commit and file allowlist."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def build(output):
    root = Path(__file__).resolve().parents[2]
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args])
    if git('status', '--porcelain').strip():
        raise RuntimeError('PACKAGE_REQUIRES_CLEAN_WORKTREE')
    commit = git('rev-parse', 'HEAD').decode().strip()
    files = json.loads((root/'ops/backup_engine/files.json').read_bytes())
    payload = {}
    for source, target in files.items():
        raw = git('show', commit+':'+source)
        compile(raw, source, 'exec')
        payload[target] = raw
    entry=git('show',commit+':ops/backup_engine/entry.py')
    for role in ('repository','recovery','control'):
        payload[role+'_entry.py']=entry
    hashes = {p: hashlib.sha256(b).hexdigest() for p,b in sorted(payload.items())}
    version = dict(commit=commit, packageSha256=hashlib.sha256(canonical(hashes)).hexdigest(), files=hashes)
    payload['package.json'] = canonical(version)+b'\n'
    with tarfile.open(output, 'w:gz', format=tarfile.PAX_FORMAT) as archive:
        for name, raw in sorted(payload.items()):
            item=tarfile.TarInfo(name); item.size=len(raw); item.mode=0o600
            archive.addfile(item, io.BytesIO(raw))
    print(canonical(version | {'fileCount':len(hashes)}).decode())


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    build(parser.parse_args().output)
