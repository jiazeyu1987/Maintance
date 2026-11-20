"""Deployment metadata tail. Caller holds the runtime operation lock.

Called only after normal-mode health succeeds; no network, restart or SQL here.
An explicit environment path is required, including on targets without backups.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile


def require(ok, message):
    if not ok:
        raise ValueError(message)


def environment_path(profile):
    explicit = profile.get('runtimeEnvironmentFile')
    bound = (profile.get('backupSourceBinding') or {}).get('environmentFile')
    require(not (explicit and bound) or explicit == bound, 'Runtime environment paths disagree')
    value = explicit or bound  # Both are explicit registered contracts, never inferred paths.
    require(isinstance(value, str) and value and Path(value).is_absolute()
            and '..' not in Path(value).parts, 'Explicit runtimeEnvironmentFile required')
    return Path(value)


def read_environment(profile):
    path = environment_path(profile)
    require(path.is_file() and not path.is_symlink(), 'Runtime environment must be a regular file')
    raw = path.read_bytes()
    matches = re.findall(rb'(?m)^IMAGE_TAG=([^\r\n]*)', raw)
    require(len(matches) == 1 and re.fullmatch(rb'[A-Za-z0-9_.-]+', matches[0]),
            'Exactly one valid IMAGE_TAG required')
    return path, raw


def write_json(path, value):
    data = (json.dumps(value, sort_keys=True) + '\n').encode()
    require(not path.exists() and not path.is_symlink(), 'Metadata receipt already exists')
    descriptor, name = tempfile.mkstemp(prefix='.'+path.name+'-', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        require(not path.exists() and not path.is_symlink(), 'Metadata receipt appeared concurrently')
        os.replace(temporary, path)
    finally:
        if temporary.exists(): temporary.unlink()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def align(profile, candidate, evidence, *, inspect, run):
    tag = candidate['releaseTag']
    require(re.fullmatch(r'20\d{2}(-\d{2}){5}', tag), 'Invalid release tag')
    identities = {}
    for role in ('backend', 'frontend'):
        expected = candidate['images'][role]
        require(expected['name'].endswith(':' + tag), 'Manifest image tag differs')
        container = inspect(profile[role])
        rows = json.loads(run(['docker', 'image', 'inspect', expected['name']]))
        require(len(rows) == 1 and container['State']['Running'] is True
                and container['Image'] == rows[0]['Id'] == expected['id']
                and expected['name'] in rows[0].get('RepoTags', []), 'Running image or tag differs')
        identities[role] = container['Id']
    path, current = read_environment(profile)
    evidence = Path(evidence)
    binding = dict(releaseTag=tag, containers=identities, images=candidate['images'], path=str(path))
    if evidence.exists():
        require(evidence.is_dir() and not evidence.is_symlink(), 'Invalid metadata evidence directory')
        intent = json.loads((evidence / 'intent.json').read_text(encoding='utf-8'))
        require(intent['binding'] == binding, 'Metadata attempt identity changed')
        before = (evidence / 'runtime.env.before').read_bytes()
        require(digest(before) == intent['beforeSha256'], 'Original environment evidence changed')
    else:
        before = current
        after = re.sub(rb'(?m)^IMAGE_TAG=[^\r\n]*', ('IMAGE_TAG='+tag).encode(), before)
        intent = dict(binding=binding, beforeSha256=digest(before), afterSha256=digest(after))
        evidence.mkdir(mode=0o700)
        descriptor = os.open(evidence/'runtime.env.before', os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as output:
            output.write(before); output.flush(); os.fsync(output.fileno())
        write_json(evidence/'intent.json', intent)
    after = re.sub(rb'(?m)^IMAGE_TAG=[^\r\n]*', ('IMAGE_TAG='+tag).encode(), before)
    require(digest(after) == intent['afterSha256'] and current in (before, after),
            'Runtime environment changed since metadata attempt')
    if current != after:
        original_stat = path.stat()
        descriptor, name = tempfile.mkstemp(prefix='.release-env-', dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(after); output.flush(); os.fsync(output.fileno())
                os.chmod(temporary, stat.S_IMODE(original_stat.st_mode))
                if hasattr(os, 'fchown'):
                    os.fchown(output.fileno(), original_stat.st_uid, original_stat.st_gid)
            require(not path.is_symlink() and path.stat().st_ino == original_stat.st_ino
                    and path.read_bytes() == before, 'Runtime environment changed concurrently')
            os.replace(temporary, path)
        finally:
            if temporary.exists(): temporary.unlink()
    require(path.read_bytes() == after, 'Runtime environment readback differs')
    result = dict(status='ALIGNED', releaseTag=tag, beforeSha256=intent['beforeSha256'],
                  afterSha256=intent['afterSha256'], containers=identities)
    receipt = evidence/'result.json'
    if receipt.exists():
        require(json.loads(receipt.read_text(encoding='utf-8')) == result, 'Metadata receipt changed')
    else:
        write_json(receipt, result)
    return result
