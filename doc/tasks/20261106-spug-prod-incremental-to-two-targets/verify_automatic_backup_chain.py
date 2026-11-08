"""Audit one completed UI backup and its exact preceding verified chain.

Example: --submission automatic-full-ui-submission.json --output automatic-full-audit.json
Then: --submission automatic-i1-ui-submission.json --parent automatic-full-audit.json
      --output automatic-i1-audit.json
No HTTP queries, SQL, mutations, service reloads or full-payload reads are issued.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

from common import TASK, PRIVATE, remote
from automatic_stage_deployment import load_stage_deployment
from prepare_automatic_ui_preflight import verify_submission_identity


def task_path(value):
    path = Path(value)
    if not path.is_absolute(): path = TASK / path
    path = path.resolve()
    if not path.is_relative_to(TASK.resolve()): raise ValueError('AUDIT_TASK_PATH_REQUIRED')
    return path


def local_pin(path):
    raw = path.read_bytes()
    return dict(path=path.resolve().as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def verify_local_inputs(spec):
    for expected in spec['localInputPins']:
        if local_pin(Path(expected['path'])) != expected:
            raise ValueError('AUDIT_LOCAL_INPUT_CHANGED')


def package_manifest(identity, task, private):
    """Read the exact local build/package for one controller's installed generation."""
    commit = identity['sourceCommit']
    if not re.fullmatch('[0-9a-f]{40}', commit): raise ValueError('AUDIT_COMMIT_INVALID')
    build = json.loads((task / ('release-build-' + commit[:7] + '.json')).read_text(encoding='utf-8'))
    if not (build['status'] == 'PASS' and build['targetCommit'] == commit and
            build['packageSha256'] == identity['packageSha256'] and
            build['fileManifestSha256'] == identity['fileManifestSha256'] and
            build['fileCount'] == identity['fileCount'] == 130):
        raise ValueError('AUDIT_BUILD_INSTALLATION_CHANGED')
    archive = private / ('package-' + commit[:7]) / 'backup-restore-standard.tgz'
    if hashlib.sha256(archive.read_bytes()).hexdigest() != build['packageSha256']:
        raise ValueError('AUDIT_PACKAGE_CHANGED')
    with tarfile.open(archive) as package:
        manifest = json.load(package.extractfile('package.json'))
        actual = hashlib.sha256(json.dumps(manifest['files'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        if not (manifest['packageSha256'] == build['fileManifestSha256'] == actual and len(manifest['files']) == 130):
            raise ValueError('AUDIT_MANIFEST_CHANGED')
    return manifest


def prepare(submission_path, installation_path=None, parent_path=None, seconds=120, *, task=TASK, private=PRIVATE):
    submission = json.loads(submission_path.read_text(encoding='utf-8'))
    request = submission['request']
    if request['action'] not in ('FULL', 'INCREMENTAL'): raise ValueError('AUDIT_BACKUP_ONLY')
    kind = submission['kind']
    deployment = None
    if kind != 'FULL' or submission['schemaVersion'] != 'AutomaticIncrementalUiSubmission/v1':
        deployment = load_stage_deployment(task, private, kind)
        selected_path = task / deployment['selection']['sourceInstallationPin']['file']
        if installation_path is not None and installation_path.resolve() != selected_path.resolve():
            raise ValueError('AUDIT_STAGE_INSTALLATION_MISMATCH')
        installation = deployment['sourceInstallation']
        installation_path = selected_path
        verify_submission_identity(submission, kind, deployment['sourceCommit'], deployment)
        generations = deployment['controllerGenerations']
    else:
        installation_path = task / 'automatic-control-installation-57.json' if installation_path is None else installation_path
        installation = json.loads(installation_path.read_text(encoding='utf-8'))
        verify_submission_identity(submission, kind, installation['sourceCommit'])
        generations = [installation, installation]
    if installation['status'] != 'PASS': raise ValueError('AUDIT_INSTALLATION_NOT_VERIFIED')
    controller_files = [package_manifest(generation, task, private)['files'] for generation in generations]
    controller = installation['controllers'][0]
    parent = None if parent_path is None else json.loads(parent_path.read_text(encoding='utf-8'))
    result = dict(request=request, parent=parent, engine=controller['engine'], seconds=seconds,
        controlConfigurationPin=controller['controlConfigurationPin'], files=controller_files[0], controllerFiles=controller_files,
        fileCount=130, fileManifestSha256=installation['fileManifestSha256'])
    inputs = [submission_path, installation_path]
    if parent_path is not None: inputs.append(parent_path)
    if deployment is not None:
        result['deployment'] = dict(sourceCommit=deployment['sourceCommit'], spugCommit=deployment['spugCommit'],
            deploymentSelectionPin=deployment['selectionPin'], sourceInstallationPin=deployment['selection']['sourceInstallationPin'],
            controllerGenerations=deployment['controllerGenerations'])
        inputs += [task / deployment['selectionPin']['file'],
                   private / deployment['selection']['sourcePrivateInstallationPin']['file'],
                   task / deployment['selection']['sourceBuildPin']['file'],
                   task / deployment['selection']['spugInstallationPin']['file']]
    result['localInputPins'] = [local_pin(path) for path in inputs]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--submission', required=True)
    parser.add_argument('--parent')
    parser.add_argument('--output', required=True)
    parser.add_argument('--installation', help='Must match the immutable stage selection for I1/I2')
    parser.add_argument('--prepare-only', action='store_true', help='Validate local inputs without contacting a host')
    args = parser.parse_args()
    output = task_path(args.output)
    if output.exists(): raise FileExistsError('AUDIT_OUTPUT_ALREADY_EXISTS')
    spec = prepare(task_path(args.submission), None if args.installation is None else task_path(args.installation),
                   None if args.parent is None else task_path(args.parent))
    if args.prepare_only:
        print(json.dumps(dict(status='PREPARED', operationId=spec['request']['operationId'],
                             action=spec['request']['action'], remoteReadDispatched=False)))
        return
    core = (TASK / 'automatic_chain_audit.py').read_text(encoding='utf-8')
    # Only the audited source and public spec are sent; no local secret is included.
    script = core + '\nSPEC=' + repr(spec) + '\nprint(json.dumps(audit(SPEC)))\n'
    report = remote('172.30.30.57', script, timeout=150)
    if report['status'] != 'PASS' or report['operationId'] != spec['request']['operationId']:
        raise ValueError('AUDIT_RESULT_BINDING_INVALID')
    verify_local_inputs(spec)
    raw = json.dumps(report, ensure_ascii=False, indent=2).encode('utf-8')
    with output.open('xb') as stream: stream.write(raw)
    if output.read_bytes() != raw: raise ValueError('AUDIT_REPORT_WRITE_CHANGED')
    print(json.dumps(dict(status='PASS', operationId=report['operationId'], pointType=report['pointType'],
        chainDepth=len(report['chain']), payloadBytes=report['readback']['payloadBytes'], report=output.name)))


if __name__ == '__main__':
    main()
