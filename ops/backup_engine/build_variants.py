"""Build separate standard (frozen 2026-10-21) and lightweight source packages.

These are local source snapshots, not a server deployment or an application release.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from standard_fixes import apply as safe_fixes


ROOT = Path(__file__).resolve().parents[2]
BASELINE = Path(__file__).with_name('baselines') / 'backup-restore-standard-20261021.tgz'
BASELINE_PACKAGE = 'eb8b63dd5813085228c9d16f06087049810f1e226ef878c3c1d04bdc98bdfd19'
VARIANTS = ('standard', 'lightweight')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def standard_sources():
    with tarfile.open(BASELINE, 'r:gz') as archive:
        version = json.load(archive.extractfile('package.json'))
        if (version['packageSha256'] != BASELINE_PACKAGE or
                hashlib.sha256(canonical(version['files'])).hexdigest() != BASELINE_PACKAGE):
            raise RuntimeError('STANDARD_BASELINE_MANIFEST_CHANGED')
        payload = {}
        for name, expected in version['files'].items():
            raw = archive.extractfile(name).read()
            if hashlib.sha256(raw).hexdigest() != expected:
                raise RuntimeError('STANDARD_BASELINE_FILE_CHANGED ' + name)
            payload[name] = raw
    return payload, dict(commit=version['commit'], source='frozen-20261021',
                         originalPackageSha256=BASELINE_PACKAGE)


def lightweight_sources():
    mapping = json.loads((ROOT/'ops/backup_engine/files.json').read_bytes())
    payload = {target: (ROOT/source).read_bytes() for source, target in mapping.items()}
    entry = (ROOT/'ops/backup_engine/entry_lightweight.py').read_bytes()
    for role in ('repository', 'recovery', 'control'):
        payload[role+'_entry.py'] = entry
    commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).decode().strip()
    return payload, dict(commit=commit, source='explicit-working-tree-snapshot')


def archive_prefix(variant):
    if variant not in VARIANTS:
        raise ValueError('UNKNOWN_BACKUP_VARIANT')
    return 'prod-' + variant + '-'


def write_package(destination, variant, payload, origin):
    payload = dict(payload)
    name = 'common/repository_minimal.py'
    raw = payload[name]
    # ponytail: name both publication and cancellation paths identically; no new wire schema.
    if raw.count(b"'prod-'") != 2:
        raise RuntimeError('ARCHIVE_NAMING_SITES_CHANGED')
    payload[name] = raw.replace(b"'prod-'", repr(archive_prefix(variant)).encode())
    for name, raw in payload.items():
        compile(raw, name, 'exec')
    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(payload.items())}
    version = dict(origin, variant=variant, archivePrefix=archive_prefix(variant),
                   payloadContentVerification=variant == 'standard', fileVerification=variant == 'standard', files=hashes,
                   packageSha256=hashlib.sha256(canonical(hashes)).hexdigest())
    payload['package.json'] = canonical(version) + b'\n'
    # Exclusive creation keeps existing packages untouched.
    with destination.open('xb') as output:
        with tarfile.open(fileobj=output, mode='w:gz', format=tarfile.PAX_FORMAT) as archive:
            for name, raw in sorted(payload.items()):
                item = tarfile.TarInfo(name); item.size = len(raw); item.mode = 0o600
                archive.addfile(item, io.BytesIO(raw))
    return {key: version[key] for key in ('variant', 'archivePrefix', 'packageSha256',
                                        'source', 'payloadContentVerification')}


def build(output):
    output = Path(output)
    if output.exists():
        raise FileExistsError('VARIANT_OUTPUT_ALREADY_EXISTS')
    standard, standard_origin = standard_sources()
    standard = safe_fixes(standard)
    standard_origin.update(source='frozen-20261021-with-reviewed-fixes',
        authenticationFix='redis-pinned-password-20261022', requestParentBinding=True,
        businessLogicFix='scoped-startup-ddl-20261023-r1', backupStepTimings=True,
        stepTiming='restore-stage-boundaries-20261023-r2')
    lightweight, lightweight_origin = lightweight_sources()
    output.mkdir(parents=True)
    results = []
    for variant, payload, origin in (('standard', standard, standard_origin),
                                     ('lightweight', lightweight, lightweight_origin)):
        destination = output / ('backup-restore-' + variant + '.tgz')
        results.append(write_package(destination, variant, payload, origin) | {'package': str(destination)})
    (output/'variants.json').write_bytes(canonical(results) + b'\n')
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', required=True)
    print(json.dumps(build(parser.parse_args().output_directory), indent=2))
