"""Audit one completed UI backup and its exact preceding verified chain.

Example: --submission automatic-full-ui-submission.json --output automatic-full-audit.json
Then: --submission automatic-i1-ui-submission.json --parent automatic-full-audit.json
      --output automatic-i1-audit.json
No HTTP queries, SQL, mutations, service reloads or full-payload reads are issued.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

from common import TASK, PRIVATE, remote
from automatic_stage_deployment import load_stage_deployment
from prepare_automatic_ui_preflight import verify_submission_identity
from automatic_chain_audit import MAIN_SPEC_SCHEMA, canonical, need


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


def main_package_manifest(identity, task, private):
    """Explicit MAIN/v1 contract; old 130-file package reader stays unchanged."""
    commit = identity['sourceCommit']
    need(type(commit) is str and re.fullmatch('[0-9a-f]{40}', commit), 'AUDIT_MAIN_COMMIT_INVALID')
    build = json.loads((task / ('release-build-' + commit[:7] + '.json')).read_bytes())
    need(build['status'] == 'PASS' and build['targetCommit'] == commit and
         all(build[k] == identity[k] for k in ('packageSha256','fileManifestSha256','fileCount')) and
         type(build['fileCount']) is int and build['fileCount'] == 147, 'AUDIT_MAIN_BUILD_CHANGED')
    archive = private / ('package-' + commit[:7]) / 'backup-restore-standard.tgz'
    need(archive.stat().st_size <= 64*1024*1024, 'AUDIT_MAIN_ARCHIVE_LIMIT')
    raw = archive.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == build['packageSha256'], 'AUDIT_MAIN_PACKAGE_CHANGED')
    with tarfile.open(fileobj=io.BytesIO(raw)) as package:
        members = package.getmembers()
        need(len(members) == 148 and len({m.name for m in members}) == 148 and
             all(m.isfile() and 0 <= m.size <= 64*1024*1024 for m in members) and
             sum(m.size for m in members) <= 256*1024*1024, 'AUDIT_MAIN_MEMBER_SET_INVALID')
        try:
            manifest = json.load(package.extractfile('package.json'))
            files = manifest['files']
            need(type(files) is dict and len(files) == 147 and
                 manifest['variant'] == 'standard' and manifest['fileVerification'] is True and
                 manifest['payloadContentVerification'] is True and
                 manifest['packageSha256'] == build['fileManifestSha256'] ==
                 hashlib.sha256(canonical(files)).hexdigest(), 'AUDIT_MAIN_MANIFEST_CHANGED')
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise ValueError('AUDIT_MAIN_MANIFEST_INVALID') from error
        need({m.name for m in members} == {'package.json', *files}, 'AUDIT_MAIN_MEMBER_SET_INVALID')
        for name, digest in files.items():
            path = PurePosixPath(name)
            need(type(name) is str and str(path) == name and not path.is_absolute() and
                 '..' not in path.parts and '\\' not in name and ':' not in name and
                 type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest), 'AUDIT_MAIN_MEMBER_INVALID')
            need(hashlib.sha256(package.extractfile(name).read()).hexdigest() == digest,
                 'AUDIT_MAIN_MEMBER_CHANGED')
    return manifest


def _task_reference(path, reference, task):
    need(type(reference) is dict and set(reference) == {'file','bytes','sha256'} and
         type(reference['file']) is str and Path(reference['file']).name == reference['file'] and
         not any(c in reference['file'] for c in '/\\:') and path.resolve() == (task/reference['file']).resolve(),
         'AUDIT_MAIN_LOCAL_REFERENCE_INVALID')
    raw = path.read_bytes()
    need(len(raw) == reference['bytes'] and hashlib.sha256(raw).hexdigest() == reference['sha256'],
         'AUDIT_MAIN_LOCAL_REFERENCE_CHANGED')
    return json.loads(raw)


def _prepare_main(submission, submission_path, selection_path, installation_path, parent_path, seconds, task, private):
    need(selection_path is not None and installation_path is None, 'AUDIT_MAIN_EXPLICIT_SELECTION_REQUIRED')
    submission_raw = submission_path.read_bytes()
    need(json.loads(submission_raw) == submission, 'AUDIT_MAIN_SUBMISSION_CHANGED')
    initial_pins = [dict(path=submission_path.resolve().as_posix(), bytes=len(submission_raw),
                         sha256=hashlib.sha256(submission_raw).hexdigest())]
    selected = _task_reference(selection_path, submission['deploymentSelectionPin'], task)
    need(selected.get('schemaVersion') == 'TaskMainProgramInstallations/v4', 'AUDIT_MAIN_V4_REQUIRED')
    request = submission['request']; source = request['sourceConfigRef']; kind = submission['kind']
    need(type(submission.get('cycle')) is str and re.fullmatch('[a-z0-9][a-z0-9-]{0,47}', submission['cycle']) and
         kind in ('FULL','I1','I2') and request['action'] == ('FULL' if kind == 'FULL' else 'INCREMENTAL') and
         submission['implementationCommit'] == selected['sourceCommit'] and
         submission['applicationId'] == source and type(request['operationId']) is str and
         re.fullmatch('smallapp-[0-9a-f]{32}', request['operationId']) and
         submission['intent']['operationId'] == request['operationId'], 'AUDIT_MAIN_SUBMISSION_INVALID')
    need(all(submission.get(k) == selected[k] for k in ('controlGenerationPin','spugInstallationPin')),
         'AUDIT_MAIN_DEPLOYMENT_CHANGED')
    for key in ('sourceCaptureConfigurationPin','sourceOwnerConfigurationPin'):
        reference = submission.get(key)
        need(type(reference) is dict and set(reference) == {'path','bytes','sha256'} and
             type(reference['path']) is str and PurePosixPath(reference['path']).is_absolute() and
             type(reference['bytes']) is int and reference['bytes'] > 0 and
             type(reference['sha256']) is str and re.fullmatch('[0-9a-f]{64}', reference['sha256']),
             'AUDIT_MAIN_CONFIGURATION_PIN_INVALID')
    parent = None
    if parent_path is not None:
        parent_raw = parent_path.read_bytes(); parent = json.loads(parent_raw)
        initial_pins.append(dict(path=parent_path.resolve().as_posix(), bytes=len(parent_raw),
                                sha256=hashlib.sha256(parent_raw).hexdigest()))
    need((parent is None and kind == 'FULL' and request['parentChainRef'] is None) or
         (kind != 'FULL' and type(parent) is dict and parent.get('schemaVersion') == 'AutomaticBackupChainAudit/v1' and
          parent.get('status') == 'PASS' and parent.get('operationId') == request['parentChainRef'] and
          parent.get('sourceConfigRef') == source and parent.get('chain') and
          parent['chain'][-1]['operationId'] == request['parentChainRef']), 'AUDIT_MAIN_PARENT_CHANGED')
    baseline = _task_reference(task/submission['baselineEvidencePin']['file'], submission['baselineEvidencePin'], task)
    initial_pins.append(dict(path=(task/submission['baselineEvidencePin']['file']).resolve().as_posix(),
        **{k:submission['baselineEvidencePin'][k] for k in ('bytes','sha256')}))
    plan = submission['plan']; expected = {k:plan[k] for k in ('state','parentChainRef','baseFullRef','planDigest')}
    need(set(baseline) == {'schemaVersion','status','cycle','observedAt','applicationId','sourceConfigRef',
                          'deploymentSelectionPin','expectedPlan','operationId'} and
         baseline['schemaVersion'] == 'MainProgramAutomaticIncrementalUiBaseline/v1' and baseline['status'] == 'PASS' and
         baseline['cycle'] == submission['cycle'] and baseline['applicationId'] == baseline['sourceConfigRef'] == source and
         baseline['deploymentSelectionPin'] == submission['deploymentSelectionPin'] and baseline['operationId'] is None and
         baseline['expectedPlan'] == expected and plan['sourceConfigRef'] == source and
         expected['parentChainRef'] == request['parentChainRef'] and
         expected['state'] == ('BASELINE_REQUIRED' if kind == 'FULL' else 'READY') and
         submission['intent']['applicationId'] == source and submission['intent']['planDigest'] == expected['planDigest'] and
         type(expected['planDigest']) is str and re.fullmatch('[0-9a-f]{64}', expected['planDigest']) and
         (parent is None or expected['baseFullRef'] == parent['chain'][0]['operationId']), 'AUDIT_MAIN_BASELINE_CHANGED')
    # This is the exact v4 validator used by select_main_program_installation;
    # retain its full verified bundle instead of loading the same closure twice.
    from main_program_installation_selection import Records
    from main_program_spug_publication_verify_only import validate_publication_v4
    records = Records(task); records.pinned(submission['deploymentSelectionPin'])
    verified = validate_publication_v4(records, private, selected)
    bundle = verified['generation']; controllers = bundle['controllersByHost']['57']
    need(len(controllers) == 2 and controllers[0]['role'] == 'source' and controllers[1]['role'] == 'target' and
         controllers[0]['ownerConfigurationPin'] == submission['sourceOwnerConfigurationPin'], 'AUDIT_MAIN_SOURCE_CHANGED')
    bound = {str(Path(p['path']).resolve()):p for p in verified['inputPins']}
    def document(path):
        reference = bound.get(str(Path(path).resolve()))
        need(reference is not None, 'AUDIT_MAIN_UNBOUND_DEPLOYMENT_INPUT')
        raw = Path(path).read_bytes()
        need(hashlib.sha256(raw).hexdigest() == reference['sha256'] and len(raw) == reference['bytes'],
             'AUDIT_MAIN_UNBOUND_DEPLOYMENT_INPUT')
        return json.loads(raw)
    rich = document(private/(Path(selected['spugInstallationPin']['file']).stem+'.private.json'))
    transition = document(task/rich['resourceTransitionPin']['file'])
    if transition['schemaVersion'] == 'MainProgramSpugResourceTransitionReaderCustody/v1':
        transition = document(task/transition['transitionCorePin']['file'])
    resource_build = document(task/transition['resourceBuildPin']['file'])
    need(resource_build['sourceCommit'] == submission['spugCommit'], 'AUDIT_MAIN_SPUG_COMMIT_CHANGED')
    manifests = [main_package_manifest(row, task, private) for row in controllers]
    deployment = {k:submission[k] for k in ('cycle','spugCommit','deploymentSelectionPin','controlGenerationPin',
        'spugInstallationPin','sourceCaptureConfigurationPin','sourceOwnerConfigurationPin','baselineEvidencePin')}
    deployment.update(sourceCommit=selected['sourceCommit'], controllerGenerations=controllers)
    result = dict(schemaVersion=MAIN_SPEC_SCHEMA, request=request, parent=parent, engine=controllers[0]['engine'],
        seconds=seconds, controlConfigurationPin=controllers[0]['controlConfigurationPin'], files=manifests[0]['files'],
        controllerFiles=[m['files'] for m in manifests], fileCount=147,
        fileManifestSha256=controllers[0]['fileManifestSha256'], deployment=deployment)
    inputs = [submission_path, selection_path, task/submission['baselineEvidencePin']['file'],
              private/('package-'+selected['sourceCommit'][:7])/'backup-restore-standard.tgz']
    if parent_path is not None: inputs.append(parent_path)
    pins = {}
    for pin in [*verified['inputPins'], *initial_pins, *[local_pin(p) for p in inputs]]:
        path = Path(pin['path']).resolve().as_posix(); pin = dict(pin, path=path)
        need(path not in pins or pins[path] == pin, 'AUDIT_MAIN_INPUT_CONFLICT')
        pins[path] = pin
    result['localInputPins'] = list(pins.values())
    verify_local_inputs(result)
    return result


def prepare(submission_path, installation_path=None, parent_path=None, seconds=120, *, task=TASK, private=PRIVATE, selection_path=None):
    submission = json.loads(submission_path.read_text(encoding='utf-8'))
    request = submission['request']
    if request['action'] not in ('FULL', 'INCREMENTAL'): raise ValueError('AUDIT_BACKUP_ONLY')
    if submission['schemaVersion'] == 'AutomaticIncrementalUiSubmission/v3':
        return _prepare_main(submission, submission_path, selection_path, installation_path, parent_path, seconds, task, private)
    if selection_path is not None: raise ValueError('AUDIT_MAIN_V3_REQUIRED')
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
    parser.add_argument('--selection', help='Explicit current v4 selection required for MAIN/v3 submissions')
    parser.add_argument('--prepare-only', action='store_true', help='Validate local inputs without contacting a host')
    args = parser.parse_args()
    output = task_path(args.output)
    if output.exists(): raise FileExistsError('AUDIT_OUTPUT_ALREADY_EXISTS')
    spec = prepare(task_path(args.submission), None if args.installation is None else task_path(args.installation),
                   None if args.parent is None else task_path(args.parent),
                   selection_path=None if args.selection is None else task_path(args.selection))
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
