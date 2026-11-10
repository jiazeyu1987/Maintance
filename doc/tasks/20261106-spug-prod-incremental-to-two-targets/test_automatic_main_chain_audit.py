"""Local package/metadata protocols; no host, backup, restore or payload replay."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

import pytest

TASK = Path(__file__).resolve().parent
sys.path.insert(0, str(TASK))
import automatic_chain_audit as audit
import verify_automatic_backup_chain as chain

PRIVATE = Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
COMMIT = '45dd7dc65409c87fe856584b85873ea96c0b830e'
MAIN = 'MainProgramAutomaticBackupChainAuditSpec/v1'
SELECTION = 'main-program-current-installations-45dd7dc-r6-v4.json'
SUBMISSION = 'automatic-main-20261110-r6-i1-ui-submission.json'


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audit.canonical(value))


def package_case(tmp_path, count=147):
    """Real files and tar; reviewed SAFE reader source, synthetic other members."""
    task, private, engine = tmp_path/'task', tmp_path/'private', tmp_path/'engine'
    engine.mkdir(); task.mkdir(); private.mkdir()
    with tarfile.open(PRIVATE/'package-45dd7dc/backup-restore-standard.tgz') as actual:
        contents = {name:actual.extractfile(name).read() for name in
                    ('common/repository_minimal.py', 'common/repository_native_readback.py')}
    contents.update({f'protocol/member-{i:03d}.py': f'VALUE = {i}\n'.encode()
                     for i in range(count-len(contents))})
    files = {name:hashlib.sha256(raw).hexdigest() for name, raw in contents.items()}
    digest = hashlib.sha256(audit.canonical(files)).hexdigest()
    manifest = dict(variant='standard', fileVerification=True,
                    payloadContentVerification=True, files=files, packageSha256=digest)
    for name, raw in contents.items():
        path = engine/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    put(engine/'package.json', manifest)
    archive = private/'package-45dd7dc/backup-restore-standard.tgz'
    archive.parent.mkdir()
    def write_archive(extra=None, changed=None):
        with tarfile.open(archive, 'w:gz') as stream:
            members = {'package.json':audit.canonical(manifest), **contents}
            if changed: members.update(changed)
            for name, raw in members.items():
                info = tarfile.TarInfo(name); info.size = len(raw)
                stream.addfile(info, io.BytesIO(raw))
            if extra is not None: stream.addfile(extra)
        raw = archive.read_bytes()
        build = dict(status='PASS', targetCommit=COMMIT, fileCount=count,
                     fileManifestSha256=digest, packageSha256=hashlib.sha256(raw).hexdigest())
        put(task/'release-build-45dd7dc.json', build)
        return dict(sourceCommit=COMMIT, **{k:build[k] for k in
                    ('fileCount','fileManifestSha256','packageSha256')})
    identity = write_archive()
    spec = dict(schemaVersion=MAIN, engine=engine.as_posix(), files=files,
                fileCount=count, fileManifestSha256=digest)
    return task, private, engine, identity, spec, write_archive


def test_main_package_reads_every_real_tar_member_and_installed_file(tmp_path):
    task, private, _, identity, spec, _ = package_case(tmp_path)
    assert chain.main_package_manifest(identity, task, private)['files'] == spec['files']
    reader = audit.AuditReader()
    result = audit.verify_package(reader, spec); reader.finish()
    assert result['fileCount'] == 147 and result['allInstalledFilesShaVerified'] is True


@pytest.mark.parametrize('mode', ['old', 'unknown'])
def test_147_requires_explicit_main_audit_schema(tmp_path, mode):
    _, _, _, _, spec, _ = package_case(tmp_path)
    if mode == 'old': spec.pop('schemaVersion')
    else: spec['schemaVersion'] = 'MainProgramAutomaticBackupChainAuditSpec/v99'
    with pytest.raises(ValueError, match='AUDIT_STANDARD_130_REQUIRED'):
        audit.verify_package(audit.AuditReader(), spec)


def test_main_contract_does_not_expand_old_local_package_manifest(tmp_path):
    task, private, _, identity, _, _ = package_case(tmp_path)
    with pytest.raises(ValueError, match='AUDIT_BUILD_INSTALLATION_CHANGED'):
        chain.package_manifest(identity, task, private)


@pytest.mark.parametrize('mode', ['wrong-count', 'changed-file', 'unsafe-name', 'extra', 'link', 'manifest'])
def test_main_tar_rejects_nonexact_or_changed_members(tmp_path, mode):
    task, private, _, identity, _, rewrite = package_case(tmp_path, 146 if mode == 'wrong-count' else 147)
    if mode == 'changed-file': identity = rewrite(changed={'protocol/member-000.py':b'changed'})
    elif mode == 'manifest': identity = rewrite(changed={'package.json':b'{}'})
    elif mode in ('unsafe-name','extra','link'):
        info = tarfile.TarInfo('../escape' if mode == 'unsafe-name' else 'unexpected')
        if mode == 'link': info.type = tarfile.SYMTYPE; info.linkname = 'package.json'
        identity = rewrite(extra=info)
    with pytest.raises(ValueError, match='AUDIT_MAIN_'):
        chain.main_package_manifest(identity, task, private)


@pytest.mark.parametrize('mode', ['file', 'manifest', 'missing', 'count'])
def test_main_installed_files_and_manifest_remain_strict(tmp_path, mode):
    _, _, engine, _, spec, _ = package_case(tmp_path)
    if mode == 'file': (engine/'protocol/member-000.py').write_bytes(b'changed')
    elif mode == 'missing': (engine/'protocol/member-000.py').unlink()
    elif mode == 'count': spec['fileCount'] = 146
    else:
        value = json.loads((engine/'package.json').read_bytes()); value['packageSha256']='0'*64
        put(engine/'package.json', value)
    with pytest.raises((ValueError, FileNotFoundError)):
        audit.verify_package(audit.AuditReader(), spec)


def test_verified_historical_bundle_chain_boundary_preserves_v3_parent_and_all_147_files(monkeypatch):
    # Formal historical validation supplies real original evidence at the
    # dispatcher-output unit boundary. This is not current r6 acceptance.
    import main_program_current_installation as current
    import main_program_installation_selection as contract
    import main_program_spug_publication as publication
    import main_program_spug_publication_verify_only as verify
    import main_program_spug_historical_custody as history
    custody=publication.file_pin(PRIVATE/'main-program-spug-historical-read-custody-20261110-r1.private.json')
    context=history.load_context(TASK,PRIVATE,custody)
    records=contract.Records(TASK);selected=records.read(SELECTION)
    verified=verify.validate_publication_v4(records,PRIVATE,selected,historical=context)
    reader=current.BoundDocuments(TASK,verified['inputPins']+records.path_pins()+context.finish())
    runtime=current.project_runtime(reader,PRIVATE,selected,reader.read(selected['verificationInputsPin']),
                                    'PUBLICATION_VERIFICATION')
    def historical_boundary(task,private,*,selection_file):
        assert task==TASK and private==PRIVATE and selection_file==SELECTION
        return dict(selection=selected,selectionPin=records.references[SELECTION],
                    generation=verified['generation'],inputPins=reader.finish(),spugRuntime=runtime)
    monkeypatch.setattr(current,'load_current_installation',historical_boundary)
    def forbidden(*args, **kwargs):
        pytest.fail('remote dispatch is forbidden in local preparation')
    monkeypatch.setattr(chain, 'remote', forbidden)
    spec = chain.prepare(TASK/SUBMISSION, parent_path=TASK/'automatic-i2-audit.json',
                         selection_path=TASK/SELECTION)
    original = json.loads((TASK/SUBMISSION).read_bytes())
    assert spec['schemaVersion'] == MAIN and spec['fileCount'] == len(spec['files']) == 147
    assert spec['request'] == original['request'] and spec['parent']['operationId'] == original['request']['parentChainRef']
    assert spec['deployment']['cycle'] == original['cycle']
    for name in ('deploymentSelectionPin','controlGenerationPin','spugInstallationPin',
                 'sourceCaptureConfigurationPin','sourceOwnerConfigurationPin','baselineEvidencePin'):
        assert spec['deployment'][name] == original[name]
    assert spec['deployment']['spugCommit'] == original['spugCommit']
    assert len(spec['localInputPins']) > 1000
    chain.verify_local_inputs(spec)


@pytest.mark.parametrize('mode', ['missing', 'pin', 'schema', 'generation', 'owner', 'cycle', 'parent'])
def test_v3_rejects_invalid_explicit_binding_before_any_remote(tmp_path, mode):
    submission = json.loads((TASK/SUBMISSION).read_bytes())
    selected = json.loads((TASK/SELECTION).read_bytes())
    if mode == 'schema': selected['schemaVersion'] = 'TaskMainProgramInstallations/v3'
    put(tmp_path/SELECTION, selected)
    actual = chain.local_pin(tmp_path/SELECTION)
    submission['deploymentSelectionPin'] = dict(file=SELECTION, **{k:actual[k] for k in ('bytes','sha256')})
    if mode == 'pin': submission['deploymentSelectionPin']['sha256'] = '0'*64
    if mode == 'generation': submission['controlGenerationPin']['sha256'] = '0'*64
    if mode == 'owner': submission['sourceOwnerConfigurationPin'] = None
    if mode == 'cycle': submission['cycle'] = '../other'
    parent = json.loads((TASK/'automatic-i2-audit.json').read_bytes())
    if mode == 'parent': parent['operationId']='smallapp-'+'0'*32
    put(tmp_path/'submission.json', submission); put(tmp_path/'parent.json', parent)
    with pytest.raises(ValueError, match='AUDIT_MAIN_'):
        chain.prepare(tmp_path/'submission.json', parent_path=tmp_path/'parent.json', task=tmp_path,
                      selection_path=None if mode == 'missing' else tmp_path/SELECTION)


def test_main_runtime_configuration_binding_rejects_original_pin_drift(tmp_path):
    owner_path, capture_path = tmp_path/'owner.json', tmp_path/'capture.json'
    put(capture_path, {'source':{'identity':'protocol only'}})
    put(owner_path, {'sources':{'source-A':{'configurationPath':capture_path.as_posix()}}})
    owner_pin, capture_pin = chain.local_pin(owner_path), chain.local_pin(capture_path)
    config = {'taskRoot':tmp_path.as_posix(), 'sourceConfigurations':{'source-A':owner_pin}}
    request = {'sourceConfigRef':'source-A', 'operationId':'operation-A'}
    put(tmp_path/'request-configurations/operation-A/request-inputs.json',
        {'ownerConfigurationPin':owner_pin, 'captureConfigurationPin':capture_pin})
    spec = {'schemaVersion':MAIN, 'deployment':{'sourceOwnerConfigurationPin':owner_pin,
            'sourceCaptureConfigurationPin':capture_pin}}
    reader = audit.AuditReader()
    audit.verify_main_configuration(reader, spec, config, request); reader.finish()
    spec['deployment']['sourceCaptureConfigurationPin'] = dict(capture_pin, sha256='0'*64)
    with pytest.raises(ValueError, match='AUDIT_MAIN_CAPTURE_CHANGED'):
        audit.verify_main_configuration(audit.AuditReader(), spec, config, request)


def test_main_actual_request_capture_must_equal_submitted_original_pin(tmp_path):
    capture_path, other_path, owner_path = [tmp_path/name for name in ('capture.json','other.json','owner.json')]
    put(capture_path, {'source':{'identity':'original protocol'}})
    put(other_path, {'source':{'identity':'other protocol'}})
    put(owner_path, {'sources':{'source-A':{'configurationPath':capture_path.as_posix()}}})
    owner, capture = chain.local_pin(owner_path), chain.local_pin(capture_path)
    request = {'operationId':'operation-A', 'sourceConfigRef':'source-A'}
    config = {'taskRoot':tmp_path.as_posix(), 'sourceConfigurations':{'source-A':owner}}
    inputs_path = tmp_path/'request-configurations/operation-A/request-inputs.json'
    inputs = {'ownerConfigurationPin':owner, 'captureConfigurationPin':capture}
    put(inputs_path, inputs)
    spec = {'schemaVersion':MAIN, 'deployment':{'sourceOwnerConfigurationPin':owner,
            'sourceCaptureConfigurationPin':capture}}
    audit.verify_main_configuration(audit.AuditReader(), spec, config, request)
    put(inputs_path, dict(inputs, captureConfigurationPin=chain.local_pin(other_path)))
    with pytest.raises(ValueError, match='AUDIT_MAIN_REQUEST_CONFIGURATION_CHANGED'):
        audit.verify_main_configuration(audit.AuditReader(), spec, config, request)
