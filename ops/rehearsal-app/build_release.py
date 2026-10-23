"""Build only from a clean dedicated checkout; produce one package for all hosts."""
import argparse
from datetime import datetime, timezone, timedelta
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
import hashlib
import tarfile

APP = Path(__file__).resolve().parent
REPO = APP.parents[1]


def run(args, cwd=APP):
    subprocess.run(args, cwd=cwd, check=True)


def output(args, cwd=APP):
    return subprocess.check_output(args, cwd=cwd, text=True, encoding='utf-8').strip()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if output(['git', 'status', '--porcelain'], REPO):
        raise SystemExit('BUILD_CHECKOUT_NOT_CLEAN')
    commit = output(['git', 'rev-parse', 'HEAD'], REPO)
    tag = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d-%H-%M-%S')
    dest = Path(args.output) / tag
    dest.mkdir(parents=True, exist_ok=False)
    run(['mvn.cmd', '-B', '-q', 'package'], APP / 'backend')
    run(['npm.cmd', 'ci', '--no-audit', '--no-fund'], APP / 'frontend')
    run(['npm.cmd', 'run', 'build'], APP / 'frontend')
    release = dict(releaseTag=tag, gitCommit=commit, application='rehearsal-smallapp')
    (APP / 'frontend/dist/release-info.json').write_text(json.dumps(release), encoding='utf-8')
    images = ['rehearsal-smallapp-backend:' + tag, 'rehearsal-smallapp-frontend:' + tag]
    for component, image in zip(('backend', 'frontend'), images):
        run(['docker', 'build', '--pull=false', '-t', image, str(APP / component)])
    name = 'rehearsal-release-check-' + uuid.uuid4().hex[:12]
    run(['docker', 'create', '--name', name, images[1]])
    try:
        run(['docker', 'cp', name + ':/usr/share/nginx/html/release-info.json', str(dest / 'release-info.json')])
        if json.loads((dest / 'release-info.json').read_text()) != release:
            raise RuntimeError('RELEASE_INFO_MISMATCH')
    finally:
        run(['docker', 'rm', name])
    images += ['mysql:8.0.39', 'redis:7-alpine', 'quay.io/minio/minio:RELEASE.2025-06-13T11-33-47Z']
    tar = dest / 'images.tar'
    run(['docker', 'save', '-o', str(tar), *images])
    # Docker's containerd image store exposes an index ID; classic engines expose
    # the config ID. Pin the exported config bytes, which identify the loaded image.
    with tarfile.open(tar) as bundle:
        descriptors=json.load(bundle.extractfile('manifest.json'))
        config_ids={name:'sha256:'+hashlib.sha256(bundle.extractfile(row['Config']).read()).hexdigest()
                    for row in descriptors for name in row['RepoTags']}
    manifest = dict(release, images=[dict(name=image,id=config_ids[image]) for image in images])
    archive = dest / 'images.tar.gz'
    with tar.open('rb') as src, gzip.open(archive, 'wb', compresslevel=1) as dst:
        shutil.copyfileobj(src, dst, length=1024*1024)
    tar.unlink()
    manifest.update(archiveBytes=archive.stat().st_size, archiveSha256=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest())
    (dest / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    shutil.copyfile(APP / 'deploy.py', dest / 'deploy.py')
    print(json.dumps(dict(releaseTag=tag, package=str(dest), archiveBytes=manifest['archiveBytes'])))
