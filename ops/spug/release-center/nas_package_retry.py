"""Explicit same-package NAS republication after a sealed build failed."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile

from executor import digest, require, stamp
from nas_connection import connect_nas


def original_build(state, selected):
    root_id = selected.get('originalBuildJobId', selected['id'])
    root = next((j for j in state['jobs'] if j['id'] == root_id), None)
    require(root and root['action'] == 'build-release'
            and root.get('currentStep') == 'publish-original-package-to-nas',
            'Only a build sealed before NAS publication can be retried')
    require(all(j['status'] in ('failed', 'interrupted') and not j.get('resolution')
                and not j.get('effectsStarted') for j in (root, selected)),
            'Original unresolved build without deployment effects required')
    require(root['releaseTag'] == selected['releaseTag']
            and re.fullmatch(r'\d{4}(?:-\d{2}){5}', root['releaseTag']), 'Original release tag mismatch')
    if selected is not root:
        require(selected['action'] == 'resolve-task' and selected['payload']['decision'] == 'retry',
                'Linked NAS retry task required')
    return root


def verify_sealed_package(folder, application_id, original):
    """Read every archive member; never extract or rebuild package contents."""
    manifest_bytes = (folder / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    tag = original['releaseTag']
    require(manifest['applicationId'] == application_id
            and manifest['releaseTag'] == manifest['IMAGE_TAG'] == tag
            and manifest['gitCommit'] == original['payload']['commit'], 'Sealed build identity mismatch')
    expected = {'manifest.json': hashlib.sha256(manifest_bytes).hexdigest()}
    for item in manifest['files']:
        path = PurePosixPath(item['name'])
        require(not path.is_absolute() and '..' not in path.parts and '\\' not in item['name']
                and ':' not in item['name'] and item['name'] not in expected,
                'Unsafe or duplicate manifest member')
        expected[item['name']] = item['sha256']
        require(digest(folder / item['name']) == item['sha256'], 'Local sealed artifact checksum mismatch: ' + item['name'])
    seen = set()
    with tarfile.open(folder / 'release.tar', 'r:') as archive:
        for member in archive:
            require(member.isfile() and member.name in expected and member.name not in seen,
                    'Unexpected or duplicate sealed archive member')
            with archive.extractfile(member) as stream:
                require(hashlib.file_digest(stream, 'sha256').hexdigest() == expected[member.name],
                        'Archive member checksum mismatch: ' + member.name)
            seen.add(member.name)
    require(seen == set(expected), 'Incomplete sealed archive')
    package = dict(releaseTag=tag, gitCommit=manifest['gitCommit'], directory=str(folder),
                   manifestSha256=expected['manifest.json'], packageSha256=digest(folder / 'release.tar'),
                   stage='built', baseline=False)
    if original.get('sealedPackage'):
        require(original['sealedPackage'] == package, 'Original sealed package changed')
    return package, manifest


def republish(folder, manifest, nas_path):
    destination = Path(nas_path) / manifest['releaseTag']
    destination.mkdir(parents=True, exist_ok=True)
    require({p.name for p in destination.iterdir()} <= {'release.tar.partial', 'release.tar', 'manifest.json'},
            'Unexpected files in original NAS destination')
    local = folder / 'release.tar'
    complete, partial = destination / 'release.tar', destination / 'release.tar.partial'
    if (destination / 'manifest.json').exists():
        require(digest(destination / 'manifest.json') == digest(folder / 'manifest.json'), 'NAS manifest conflict')
    if complete.exists():
        require(digest(complete) == digest(local), 'NAS complete package conflict')
    else:
        if partial.exists():
            require(partial.stat().st_size <= local.stat().st_size, 'NAS partial is larger than original')
            with partial.open('rb') as remote, local.open('rb') as source:
                for block in iter(lambda: remote.read(1024 * 1024), b''):
                    require(source.read(len(block)) == block, 'NAS partial does not belong to original package')
        # Explicit user retry starts transfer again; no automatic retry or new archive.
        shutil.copyfile(local, partial)
        require(digest(partial) == digest(local), 'NAS original package checksum mismatch')
        partial.rename(complete)
    shutil.copyfile(folder / 'manifest.json', destination / 'manifest.json')
    require(digest(destination / 'manifest.json') == digest(folder / 'manifest.json'), 'NAS manifest checksum mismatch')
    return str(destination)


def resume(executor, job, selected):
    original = original_build(executor.state, selected)
    require(job['releaseTag'] == original['releaseTag'], 'Retry release tag mismatch')
    require(not any(p['releaseTag'] == original['releaseTag'] for p in executor.state['packages']),
            'Original package is already registered')
    job['originalBuildJobId'] = original['id']
    executor.step(job, 'verify-original-sealed-package')
    folder = executor.root / 'packages' / original['releaseTag']
    package, manifest = verify_sealed_package(folder, executor.c['applicationId'], original)
    # Older failed builds have no seal checkpoint. Establish it only after the
    # explicit retry fully verifies archive contents against the fixed build commit.
    original['sealedPackage'] = dict(package)
    executor.save()
    executor.step(job, 'republish-original-package-to-nas')
    connect_nas(executor.c['nasPath'], executor.c.get('nasCredentialsFile'))
    try:
        package['nasDirectory'] = republish(folder, manifest, executor.c['nasPath'])
    except OSError as error:
        raise RuntimeError('NAS original-package republication failed: ' + str(error)) from error
    executor.state['packages'].insert(0, package)
    for attempt in executor.state['jobs']:
        if (attempt is original or attempt.get('originalBuildJobId') == original['id']) \
                and attempt['status'] in ('failed', 'interrupted') and not attempt.get('resolution'):
            attempt['resolution'] = dict(decision='retry', note=job['payload']['note'], actor=job['actor'],
                                         time=stamp(), jobId=job['id'], originalBuildJobId=original['id'])
    job['result'] = dict(originalBuildJobId=original['id'], stage='built',
                        packageSha256=package['packageSha256'], nasDirectory=package['nasDirectory'])
    executor.save()
    executor.log(job, 'Original package verified and republished; no compilation or target deployment performed')
