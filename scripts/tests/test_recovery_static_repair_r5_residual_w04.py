"""R5 residual: actual offline CLI/trust/authority/Ed25519 preflight, no services."""
import base64
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops/recovery'))
import recovery_cli as cli
import recovery_engine as engine
from recovery_engine import RecoveryError, canonical, load, pin, pinned_json, write
from recovery_plan import signed_evidence
from test_recovery_static_repair_r5_w04 import full_noop_later_chain


@pytest.fixture
def signed_cli(tmp_path, monkeypatch):
    # Short owned paths avoid masking the intended publication fault on Windows.
    root = tmp_path.parent/('r'+hashlib.sha256(tmp_path.name.encode()).hexdigest()[:8])
    root.mkdir(mode=0o700)
    repository = root/'repo'; repository.mkdir(mode=0o700)
    points, policy = full_noop_later_chain(repository)
    external = root/'private-originals'; external.mkdir(mode=0o700)
    source = root/'source-material'; source.mkdir(mode=0o700)
    evidence = root/'evidence'; evidence.mkdir(mode=0o700)
    scope_value = pinned_json(policy['sourceScopePin'])
    scope = write(policy['sourceScopePin']['path'], dict(scope_value, materialPaths=[str(source)]))
    point = pinned_json(points[0]); metadata = Path(points[0]['path']).parent
    binding_ref = policy['repositoryBindingPinsByManifestSha256'][point['manifestPin']['sha256']]
    binding = pinned_json(binding_ref)
    material = pinned_json(binding['recoveryMaterialPin'])
    material_ref = write(binding['recoveryMaterialPin']['path'], dict(material, sourceScopePin=scope))
    binding.update(sourceScopePin=scope, recoveryMaterialPin=material_ref)
    policy.update(repositoryId='isolated-r5-residual-engineering', sourceScopePin=scope,
                  repositoryPointPins=[points[0]], evidenceRoot=str(evidence), toolPins=[])
    key = Ed25519PrivateKey.generate()
    key_path = external/'authority.pem'
    key_path.write_bytes(key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
    policy['repositoryEvidenceKeyPins'] = [pin(key_path)]
    identity = write(root/'target-identity.json', dict(targetId='engineering-target', sourceIdentityPin=scope_value['sourceIdentityPin']))
    python = pin(Path(sys.executable))
    data_target = write(root/'data-target.json', dict(targetIdentityPin=identity, database={},
        restoreMode='REBUILD_EMPTY', versionedDataLocation=str(root/'new-target'), existingDataLocation=str(root/'old-target'), preserveExisting=True))
    config_ref = write(root/'config.json', dict(schemaVersion='RecoveryEnvironmentConfig/v1',
        targetId='engineering-target', targetIdentityPin=identity, database={}, pythonPin=python,
        imagePins=policy['supportedVersionPins']))
    environment_policy = write(root/'environment-policy.json', {'engineeringOnly':True})
    own_root = Path(cli.__file__).absolute().parent
    modules = {own_root/'recovery_cli.py'}
    for pattern in ('recovery_engine*.py','recovery_plan*.py','recovery_data*.py','recovery_cutover*.py'):
        modules.update(own_root.glob(pattern))
    policy.update(schemaVersion='RecoveryDataPolicy/v1', pythonPin=python, dataTargetPin=data_target,
        environmentPolicyPin=environment_policy, moduleSourcePins=[pin(path) for path in sorted(modules)],
        dataWorkerPin=pin(own_root/'recovery_data.py'), environmentCliPin=pin(own_root/'recovery_cli.py'))
    window = dict(notBefore='1970-01-01T00:00:00Z', expiresAt='9999-01-01T00:00:00Z')
    grant = write(root/'grant.json', dict(schemaVersion='RecoveryEnvironmentAuthorization/v1', approved=True,
        operationId='engineering-operation', targetId='engineering-target', mode='REHEARSAL',
        executorId='engineering-executor', actions=['RESTORE_EXECUTE'], **window))
    lease = write(root/'lease.json', dict(schemaVersion='RecoveryEnvironmentLease/v1', state='HELD',
        operationId='engineering-operation', targetId='engineering-target', executorId='engineering-executor', fenceToken=1, **window))
    request = dict(schemaVersion='backup-restore-operation/v1', operationId='engineering-operation',
        requestId='engineering-request', action='RESTORE_PREFLIGHT', mode='REHEARSAL', selectedPointPin=points[0],
        sourceOrTargetRef=config_ref, policyPin=environment_policy, authorizationRefs=[grant], leaseRef=lease,
        inputPins={'repositoryPoint':points[0]}, deadlineMilliseconds=30000)
    invocations = []
    def no_child(*args, **kwargs):
        invocations.append((args, kwargs))
        raise AssertionError('READ_ONLY_PREFLIGHT_MUST_NOT_DISPATCH_CHILD')
    monkeypatch.setattr(engine.InvocationRunner, 'run', no_child)
    def configure_original(path, provenance=None):
        original = write(path, {'engineeringOnly':True, 'originalTerminalBytes':'retained'})
        for field in ('ownerCloseEvidencePin','readbackEvidencePin','originalExitEvidencePin'):
            payload = dict(pinned_json(point[field])['payload'], originalProcessPin=original)
            payload.update((provenance or {}).get(field, {}))
            point[field] = write(point[field]['path'], dict(schemaVersion='RepositorySignedRecord/v1',
                keySha256=policy['repositoryEvidenceKeyPins'][0]['sha256'], payload=payload,
                signature=base64.b64encode(key.sign(canonical(payload))).decode()))
            assert signed_evidence(point[field], policy)['originalProcessPin'] == original
        selected = write(metadata/'point.json', point)
        policy['repositoryPointPins'] = [selected]
        binding['repositoryPointPin'] = selected
        policy['repositoryBindingPinsByManifestSha256'] = {
            point['manifestPin']['sha256']:write(binding_ref['path'], binding)}
        policy_ref = write(root/'data-policy.json', policy)
        trust_ref = write(root/'trust.json', dict(schemaVersion='RecoveryDataTrust/v1',
            policySha256=environment_policy['sha256'], targetConfigSha256=config_ref['sha256'],
            dataPolicyPin=policy_ref, recordSchemasPin=policy['recordSchemasPin'], executorId='engineering-executor',
            leaseSha256s=[lease['sha256']], authorizationSha256s=[grant['sha256']]))
        monkeypatch.setenv('RECOVERY_DATA_TRUST_FILE', trust_ref['path'])
        monkeypatch.setenv('RECOVERY_DATA_TRUST_SHA256', trust_ref['sha256'])
        request.update(selectedPointPin=selected, inputPins={'repositoryPoint':selected})
        request_ref = write(root/'request.json', request)
        return SimpleNamespace(root=root, external=external, source=source, evidence=evidence, policy=policy,
            request=request, request_pin=request_ref, original=original, invocations=invocations)
    return configure_original, external


@pytest.mark.parametrize('state', ['missing','intact'])
@pytest.mark.parametrize('destination', ['primary','secondary'])
def test_cli_signed_external_original_collision_preserves_absence_or_bytes(signed_cli, state, destination, capsys):
    configure, external = signed_cli
    output = external/'result.json'
    original = output if destination == 'primary' else output.with_name(output.name+'.recording-failure.json')
    fixture = configure(original)
    retained = original.read_bytes()
    if state == 'missing': original.unlink(); retained = None
    assert cli.main(['--request',fixture.request_pin['path'],'--output',str(output)]) == 1
    assert (original.read_bytes() if original.exists() else None) == retained
    assert not fixture.invocations and not list(fixture.evidence.iterdir())
    if destination == 'secondary': assert not output.exists()
    else: assert not output.with_name(output.name+'.recording-failure.json').exists()
    assert 'PUBLIC_OUTPUT_PROTECTED_PATH' in capsys.readouterr().out


@pytest.mark.parametrize('state', ['missing','intact'])
@pytest.mark.parametrize('destination', ['primary','secondary'])
def test_cli_transitive_source_material_root_rejects_primary_and_derived_receipt(signed_cli, state, destination, capsys):
    configure, external = signed_cli
    fixture = configure(external/'original.json')
    output = fixture.source/'result.json'
    protected = output if destination == 'primary' else output.with_name(output.name+'.recording-failure.json')
    retained = None
    if state == 'intact':
        write(protected, {'engineeringSourceMaterial':True}); retained = protected.read_bytes()
    assert cli.main(['--request',fixture.request_pin['path'],'--output',str(output)]) == 1
    assert (protected.read_bytes() if protected.exists() else None) == retained
    assert not fixture.invocations and not list(fixture.evidence.iterdir())
    other = output.with_name(output.name+'.recording-failure.json') if destination == 'primary' else output
    assert not other.exists()
    assert 'PUBLIC_OUTPUT_PROTECTED_PATH' in capsys.readouterr().out


def test_cli_missing_external_original_fails_actual_signed_preflight_and_publishes_only_safe_path(signed_cli):
    configure, external = signed_cli
    fixture = configure(external/'original.json')
    original = Path(fixture.original['path']); original.unlink()
    output = fixture.root/'safe-result.json'
    assert cli.main(['--request',fixture.request_pin['path'],'--output',str(output)]) == 1
    result = load(output)
    assert result['state'] == 'FAILED_RETAINED' and result['failureCode'] == 'RECOVERY_FILENOTFOUNDERROR'
    assert not original.exists() and not fixture.invocations
    journal = load(next(fixture.evidence.glob('request-*.json')))
    assert journal['state'] == 'FAILED_RETAINED'
    assert not list(fixture.evidence.glob('operation-*/restore-plan.json'))


def test_cli_safe_actual_signed_preflight_same_new_and_evidence_root_cache(signed_cli):
    configure, external = signed_cli
    fixture = configure(external/'original.json')
    original_bytes = Path(fixture.original['path']).read_bytes()
    output = fixture.root/'safe-result.json'
    assert cli.main(['--request',fixture.request_pin['path'],'--output',str(output)]) == 0
    result = load(output)
    assert result['state'] == 'SUCCEEDED' and result['data']['orderedChainPins'] == [fixture.request['selectedPointPin']]
    journal_path = next(fixture.evidence.glob('request-*.json')); before = journal_path.read_bytes()
    for destination in (output, fixture.root/'new-result.json', fixture.evidence/'public.json'):
        assert cli.main(['--request',fixture.request_pin['path'],'--output',str(destination)]) == 0
        assert load(destination) == result and journal_path.read_bytes() == before
    assert Path(fixture.original['path']).read_bytes() == original_bytes and not fixture.invocations
    assert not list(fixture.evidence.glob('operation-*/invocation-*'))


@pytest.mark.parametrize('fault', ['missing','changed','invalid-json','node-limit','document-limit','byte-limit','deadline'])
def test_cli_incomplete_transitive_scope_stops_all_publication_without_budget_reset(signed_cli, monkeypatch, capsys, fault):
    configure, external = signed_cli
    fixture = configure(external/'original.json')
    scope = fixture.policy['sourceScopePin']; scope_path = Path(scope['path'])
    retained = Path(fixture.original['path']).read_bytes()
    if fault == 'missing': scope_path.unlink()
    elif fault == 'changed': scope_path.write_bytes(scope_path.read_bytes()+b' ')
    elif fault == 'invalid-json':
        # Exact Pin still valid: the referenced bytes cannot define an input scope.
        grant = fixture.request['authorizationRefs'][0]; grant_path = Path(grant['path'])
        grant_path.write_bytes(b'not-json'); fixture.request['authorizationRefs'] = [pin(grant_path)]
        fixture.request_pin = write(fixture.request_pin['path'],fixture.request)
    elif fault == 'node-limit': monkeypatch.setattr(cli.PublicOutput,'MAX_NODES',5)
    elif fault == 'document-limit': monkeypatch.setattr(cli.PublicOutput,'MAX_DOCUMENTS',1)
    elif fault == 'byte-limit': monkeypatch.setattr(cli.PublicOutput,'MAX_JSON_BYTES',1)
    else:
        instances = []
        actual_init, actual_read = engine.Budget.__init__, cli.pinned_json
        def budget_init(budget, milliseconds):
            instances.append(budget); actual_init(budget,milliseconds)
        def expire_in_document(ref, **kwargs):
            value = actual_read(ref,**kwargs)
            if ref == scope: kwargs['budget'].deadline = 0
            return value
        monkeypatch.setattr(engine.Budget,'__init__',budget_init)
        monkeypatch.setattr(cli,'pinned_json',expire_in_document)
    publishers = []
    actual_collect = cli.PublicOutput.collect
    def observe(publisher, *args, **kwargs):
        if publisher not in publishers: publishers.append(publisher)
        return actual_collect(publisher,*args,**kwargs)
    monkeypatch.setattr(cli.PublicOutput,'collect',observe)
    output = fixture.root/'safe-result.json'
    assert cli.main(['--request',fixture.request_pin['path'],'--output',str(output)]) == 1
    assert not output.exists() and not output.with_name(output.name+'.recording-failure.json').exists()
    assert not fixture.invocations and not list(fixture.evidence.iterdir())
    assert len(publishers) == 1 and not publishers[0].complete
    assert Path(fixture.original['path']).read_bytes() == retained
    message = capsys.readouterr().out
    assert 'PUBLIC_OUTPUT_SCOPE_INCOMPLETE' in message
    if fault in ('missing','changed'): assert scope_path in publishers[0].protected
    if fault == 'deadline': assert len(instances) == 1 and publishers[0].budget is instances[0]


def test_cli_expired_budget_at_error_publication_never_restarts_scope_or_writes(signed_cli, monkeypatch, capsys):
    configure, external = signed_cli
    fixture = configure(external/'original.json')
    publishers = []
    actual_bind = cli.PublicOutput.bind
    def expire_after_admission(publisher, *args):
        actual_bind(publisher,*args)
        publishers.append(publisher); publisher.budget.deadline = 0
        raise RecoveryError('ENGINEERING_AFTER_ADMISSION_FAILURE')
    monkeypatch.setattr(cli.PublicOutput,'bind',expire_after_admission)
    output = fixture.root/'safe-result.json'
    assert cli.main(['--request',fixture.request_pin['path'],'--output',str(output)]) == 1
    assert len(publishers) == 1 and publishers[0].complete
    assert not output.exists() and not output.with_name(output.name+'.recording-failure.json').exists()
    assert not fixture.invocations and not list(fixture.evidence.iterdir())
    assert 'DEADLINE_EXCEEDED' in capsys.readouterr().out
