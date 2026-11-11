"""C2: real historical metadata files, with no payload or validator substitution."""
from copy import deepcopy
from contextlib import ExitStack
import hashlib
from pathlib import Path

import pytest

from test_recovery_preservation_inputs import (FLAGS, Inputs, derived, load, metadata, put, reference)
from repository_records import RepositoryError, canonical
from recovery_engine import RecoveryError, digest
from recovery_preservation_inputs import (derive_preservation_restore_owner,
    resolve_preservation_control_pins, verify_preservation_restore_inputs)


def point_ref(pin):
    return 'preservation-' + hashlib.sha256(canonical(pin)).hexdigest()


class History:
    def __init__(self, h):
        old = self.old = Inputs(h)
        self.repository = h['root']/'repository59'; self.repository.mkdir()
        cfg = h['root']/'config'
        self.identity = put(cfg/'identity59.json', {'databaseUuid':'independent-target59'})
        self.scope = put(cfg/'scope59.json', dict(schemaVersion='RecoverySourceScope/v1',
            sourceIdentityPin=self.identity))
        self.repo_pin = put(cfg/'repository59.json', dict(schemaVersion='MainTargetPreservationRepository/v1',
            repositoryId='preservation59', repositoryRoot=str(self.repository), sourceIdentityPin=self.identity,
            captureBinderPin=self.identity, readbackConfigPin=self.identity))
        self.target_policy = put(cfg/'target-preservation59.json', dict(schemaVersion='MainTargetPreservationPolicy/v1',
            targetConfigRef='target59', repositoryConfigurationPin=self.repo_pin))
        self.claims = h['root']/'claims59'
        old.owner['targetPreservationPolicies']['target59'] = self.target_policy
        old.owner['targets']['target59']['replacement'] = {'stateRoot':str(self.claims)}
        old.owner['targetProgramPolicies'] = {'target59':{'protocolOnly':'target59 program policy'}}
        old.base_pin = put(Path(old.base_pin['path']), old.owner)
        old.control['restoreConfigurations']['preserved58']['target59'] = old.base_pin
        old.control_pin = put(Path(old.control_pin['path']), old.control)
        old.controls = [old.control_pin]
        old.replace_binding(dict(old.binding, controlConfigurationPin=old.control_pin))
        old.inputs_pin = put(Path(old.inputs_pin['path']), dict(request=old.request, ownerConfigurationPin=old.base_pin))
        old.complete()
        self.publication(old.result)

        self.policy_pin = put(cfg/'policy59-v2.json', dict(schemaVersion='MainTargetPreservationSourcePolicy/v2',
            sourceConfigRef='preserved59', originTargetConfigRef='target59', repositoryConfigurationPin=self.repo_pin,
            publisherBindings=[dict(kind='REQUEST_DERIVED_OWNER', baseConfigurationPin=old.base_pin,
                preservationPolicyPin=self.target_policy, requestConfigurationsRoot=str(old.request_root),
                resolverContract='PreservationRestoreOwner/v1')],
            maxPoints=16, maxDocumentBytes=16*1024*1024, maxMetadataBytes=64*1024*1024))
        self.base = deepcopy(old.owner)
        self.base.update(operationsRoot=str(h['root']/'third-operations'),
            sources={'preserved59':dict(schemaVersion='MainTargetPreservationSource/v1', kind='TARGET_PRE_RESTORE',
                originTargetConfigRef='target59', repositoryConfigurationPin=self.repo_pin, sourceScopePin=self.scope,
                sourceIdentityPin=self.identity, policyRef='preservation-policy59')})
        self.base['targets']['target57'] = {'typeSensitive':1}
        self.base_pin = put(cfg/'base-third.json', self.base)
        self.request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='preservation-third-001',
            action='RESTORE', sourceConfigRef='preserved59', parentChainRef=None, targetConfigRef='target57',
            recoveryPointRef=point_ref(self.point_pin))
        self.request_pin = put(Path(self.base['operationsRoot'])/self.request['operationId']/'request.json', self.request)
        self.directory = old.request_root/self.request['operationId']
        self.inputs = put(self.directory/'restore-inputs.json', dict(request=self.request, ownerConfigurationPin=self.base_pin))
        self.control_path = cfg/'control-002.json'
        self.install_control(retain=True)

    def install_control(self, *, retain):
        self.control_pin = put(self.control_path, dict(schemaVersion='SmallAppExecutionServiceConfig/v2',
            taskRoot=str(self.old.task_root), preservationSourcePolicies={'preservation-policy59':self.policy_pin},
            restoreConfigurations={'preserved59':{'target57':self.base_pin}},
            retainedPreservationControlPins=[self.old.control_pin] if retain else []))
        self.control_pins = resolve_preservation_control_pins(self.control_pin, guard=lambda:None)['publisherControlPins']
        self.binding = put(self.directory/'preservation-point.json', dict(schemaVersion='SmallAppPreservationPointBinding/v1',
            reference=self.request['recoveryPointRef'], sourceConfigRef='preserved59', sourcePolicyPin=self.policy_pin,
            pointPin=self.point_pin, publicationOperationId=self.old.request['operationId'],
            controlConfigurationPin=self.control_pin))

    def publication(self, owner):
        """Write consistent metadata originals for the actually C1-derived D1."""
        old = self.old; h = old.h; op = old.request['operationId']
        op_dir = Path(old.owner['operationsRoot'])/op
        archive = self.repository/'preservations'/hashlib.sha256(op.encode()).hexdigest()
        sidecar = archive/'.repository'
        pub = op_dir/'target-preservation'/'publication'
        holds = self.repository/'.repository-control'/'preservation-holds'
        self.operation_copy = put(op_dir/'configuration.json', owner)
        binding = load(h['binding_pin']); binding.update(operationId=op, targetConfigRef='target59',
            policySha256=digest(owner['targetProgramPolicies']['target59']), configurationPin=self.operation_copy,
            requestPin=old.request_pin)
        self.execution = put(self.claims/op/'program-execution-binding.json', binding)
        intent = load(h['intent_pin']); intent.update(operationId=op, targetConfigRef='target59',
            policyPin=self.target_policy, repositoryConfigurationPin=self.repo_pin,
            configurationPin=self.operation_copy, requestPin=old.request_pin,
            executionBindingPin=self.execution, archivePath=str(archive))
        intent_pin = put(pub/'intent.json', intent)
        hold_intent = load(h['hold_intent']); hold_intent.update(repositoryId='preservation59', operationId=op,
            targetConfigRef='target59', archivePath=str(archive), pointPath=str(sidecar/'preservation-point.json'),
            preservationIntentPin=intent_pin)
        self.hold_intent = put(holds/(op+'-intent.json'), hold_intent)
        self.payload = archive/'payload'/'never-read.bin'; self.payload.parent.mkdir(parents=True, exist_ok=True)
        self.payload.write_bytes(b'new point payload; no restore proof')
        point = load(h['point_pin']); manifest = load(point['manifestPin'])
        manifest.update(backupId='captured-'+op, sourceIdentityPin=self.identity, payloadRefs=[reference(self.payload)])
        manifest_pin = put(sidecar/'manifest.json', manifest)
        terminal = load(point['captureTerminalEvidencePin']); terminal.update(operationId=op, targetConfigRef='target59')
        terminal_pin = put(sidecar/'capture-terminal.json', terminal)
        point.update(backupId=manifest['backupId'], payloadRefs=manifest['payloadRefs'],
            manifestPin=manifest_pin, captureTerminalEvidencePin=terminal_pin)
        self.point_pin = put(sidecar/'preservation-point.json', point)
        material = put(sidecar/'recovery-material.json', dict(schemaVersion='RecoveryMaterial/v1', pointType='FULL',
            recoveryPoint=point['commonRecoveryPoint'], manifestPin=manifest_pin, sourceScopePin=self.scope,
            payloadPins=point['payloadRefs'], protocolOnly=True))
        index = put(sidecar/'object-content-index.json', {'protocolOnly':'not a content proof'})
        self.repo_binding = put(sidecar/'recovery-repository-binding.json',
            dict(schemaVersion='RecoveryRepositoryBinding/v1', backupId=point['backupId'], generationId=point['generationId'],
                repositoryPointPin=self.point_pin, manifestPin=manifest_pin, sourceScopePin=self.scope,
                recoveryMaterialPin=material, objectContentIndexPin=index))
        proof = load(h['proof_pin']); proof.update(operationId=op, targetConfigRef='target59', intentPin=intent_pin,
            holdIntentPin=self.hold_intent, pointPin=self.point_pin, manifestPin=manifest_pin,
            repositoryBindingPin=self.repo_binding, recoveryMaterialPin=material, objectContentIndexPin=index,
            captureTerminalPin=terminal_pin)
        self.proof = put(pub/'archive-proof.json', proof)
        self.hold = put(holds/(op+'.json'), dict(schemaVersion='MainTargetPreservationHold/v1',
            repositoryId='preservation59', operationId=op, targetConfigRef='target59', role='TARGET_PRE_RESTORE',
            intentPin=self.hold_intent, pointPin=self.point_pin, archiveProofPin=self.proof, createdAt=intent['createdAt']))
        handoff = put(pub.parent/'session'/'handoff.json', dict(schemaVersion='MainTargetPreservationHandoff/v1',
            state='SUCCEEDED', operationId=op, targetConfigRef='target59', archiveProofPin=self.proof))
        self.final = put(pub/'preservation.json', dict(schemaVersion='MainTargetPreservation/v1', state='SUCCEEDED',
            operationId=op, targetConfigRef='target59', policyPin=self.target_policy, intentPin=intent_pin,
            archiveProofPin=self.proof, handoffPin=handoff, holdPin=self.hold, originalResultPins=[],
            finishedAt=intent['createdAt']))

    def derive(self):
        return derive_preservation_restore_owner(self.base_pin, self.request, self.binding,
            request_configurations_root=str(self.old.request_root), publisher_control_pins=self.control_pins,
            guard=lambda:None)

    def verify(self, owner):
        recovery = put(self.directory/'recovery.json', owner)
        return verify_preservation_restore_inputs(self.base_pin, self.request_pin,
            request_configurations_root=str(self.old.request_root), publisher_control_pins=self.control_pins,
            originals=dict(requestInputsPin=self.inputs, pointBindingPin=self.binding, recoveryConfigurationPin=recovery),
            guard=lambda:None)


@pytest.fixture
def history(derived):
    return History(derived)


def test_preservation_publisher_rebuilds_ancestor_from_real_originals(history, monkeypatch):
    f = history; old = f.old; a1 = old.h['a1']
    payloads = {f.payload, old.h['payload'], *a1.root.rglob('payload.bin')}
    original_open = Path.open
    def checked(path, *args, **kwargs):
        assert path not in payloads, 'C2_METADATA_OPENED_PAYLOAD'
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', checked)
    expected = deepcopy(f.base)
    expected['sources']['preserved59'].update(schemaVersion='MainTargetPreservationBoundSource/v1',
        sourcePolicyPin=f.policy_pin, pointBindingPin=dict(f.binding, path=Path(f.binding['path']).as_posix()),
        publisherControlPins=f.control_pins,
        recoveryPoints={f.request['recoveryPointRef']:f.point_pin}, archiveRoots=[str(f.repository)],
        repositoryBindingPinsByManifestSha256={load(f.point_pin)['manifestPin']['sha256']:f.repo_binding})
    owner = f.derive()
    assert canonical(owner) == canonical(expected)
    result = f.verify(owner)
    assert canonical(result['derivedOwner']) == canonical(expected)
    assert all(result[flag] is False for flag in FLAGS)
    originals = result['originalResultPins']
    for pin in [old.request_pin, old.control_pin, *old.originals.values(), old.h['point_pin'], old.h['binding_pin'],
            f.operation_copy, f.execution, f.hold_intent, f.hold, f.final, *a1.originals.values()]:
        assert any(Path(actual['path']) == Path(pin['path']) and actual['bytes'] == pin['bytes'] and
            actual['sha256'] == pin['sha256'] for actual in originals)
    assert len({Path(pin['path']) for pin in originals}) == len(originals)


@pytest.mark.parametrize('change, expected', [
    ('missing-binding','PRESERVATION_(SOURCE_INVALID|RESTORE_ORIGINAL_BINDING_INVALID)'),
    ('copy-type','PRESERVATION_SOURCE_PUBLISHER_CHANGED'),
    ('unretained','PRESERVATION_RESTORE_CONTROL_UNTRUSTED'),
])
def test_preservation_publisher_rejects_incomplete_historical_closure(history, change, expected):
    f = history
    if change == 'missing-binding':
        Path(f.old.binding_pin['path']).unlink()
    elif change == 'copy-type':
        changed = deepcopy(f.old.result); changed['targets']['target59']['typeSensitive'] = True
        f.publication(changed)
    else:
        f.install_control(retain=False)
    with pytest.raises((RecoveryError, RepositoryError), match=expected):
        f.derive()


@pytest.mark.parametrize('violation', ['cycle','depth','operations','conflict'])
def test_real_pin_history_state_rejects_bounded_traversal(tmp_path, violation):
    import recovery_preservation_inputs as module
    reads = module._Reads(lambda:None)
    state = module._History()
    def entry(index, *, changed=False, posix=False):
        path = tmp_path/('pin-'+str(index)+('-changed' if changed else '')+'.json')
        pin = reference(path) if path.exists() else put(path, {'operation':index})
        reads.read(pin)
        if posix: pin = dict(pin, path=Path(pin['path']).as_posix())
        pins = dict(sourcePolicyPin=pin, pointPin=pin, configurationPin=pin, requestPin=pin,
            intentPin=pin, executionBindingPin=pin, originals={})
        return state.publication(tmp_path/'operations', 'operation-'+str(index), 'target59', pins, derived=True)
    expected = {'cycle':'HISTORY_CYCLE','depth':'HISTORY_LIMIT',
        'operations':'HISTORY_LIMIT','conflict':'OPERATION_CONFLICT'}[violation]
    if violation == 'cycle':
        with entry(0):
            with pytest.raises(RecoveryError, match=expected):
                with entry(0): pass
    elif violation == 'depth':
        with ExitStack() as stack:
            for i in range(32): stack.enter_context(entry(i))
            with pytest.raises(RecoveryError, match=expected):
                stack.enter_context(entry(32))
    elif violation == 'operations':
        for i in range(128):
            with entry(i): pass
        with pytest.raises(RecoveryError, match=expected):
            with entry(128): pass
    else:
        with entry(0): pass
        with entry(0, posix=True): pass
        with pytest.raises(RecoveryError, match=expected):
            with entry(0, changed=True): pass
    reads.finish()


@pytest.mark.parametrize('dimension', ['document','aggregate'])
def test_nested_policy_limits_recheck_all_actual_prior_bytes(tmp_path, dimension):
    import recovery_preservation_inputs as module
    reads = module._Reads(lambda:None)
    first = put(tmp_path/'first.json', {'actual':'original metadata'})
    second = put(tmp_path/'second.json', {'actual':'second original'})
    reads.read(first); reads.read(second)
    document = first['bytes']-1 if dimension == 'document' else max(first['bytes'],second['bytes'])
    aggregate = reads.total-1 if dimension == 'aggregate' else module.METADATA_LIMIT
    with pytest.raises(RecoveryError, match='METADATA_LIMIT'):
        module._tighten_preservation_limits(reads, document, aggregate)
    module._tighten_preservation_limits(reads, 1024, 2048)
    module._tighten_preservation_limits(reads, module.DOCUMENT_LIMIT, module.METADATA_LIMIT)
    assert (reads.maximum,reads.total_limit) == (1024,2048)
    reads.finish()


def test_nested_raw_limit_checks_actual_size_before_opening_a_bad_pin(tmp_path, monkeypatch):
    import recovery_preservation_inputs as module
    reads = module._Reads(lambda:None)
    reads.read(put(tmp_path/'prior.json', {}))
    path = tmp_path/'bad-pin.json'; path.write_bytes(b'{}' + b' '*30)
    actual = reference(path)
    module._tighten_preservation_limits(reads, 32, 33)
    false_size = dict(actual, bytes=2)
    def forbidden(path, maximum):
        raise AssertionError('C2_KNOWN_PIN_OPENED_BEFORE_ACTUAL_REMAINING_CHECK')
    monkeypatch.setattr(module, '_read_file', forbidden)
    import recovery_restore_inputs as archive
    monkeypatch.setattr(archive, '_read_file', forbidden)
    with pytest.raises(RecoveryError, match='METADATA_LIMIT'):
        reads.read(false_size, 32)
