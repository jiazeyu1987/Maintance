"""Typed MAIN material publication; archive proof grants no clear permission.

Ordinary repository points and their original-process exit contract are not
interpreted here. Dedicated preservation points retain the current target while
its real capture context and original writer protections remain held.
"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
import shutil
import time
from types import SimpleNamespace

from recovery_engine import RecoveryError
from recovery_archive_guard import ArchivePathGuard
from recovery_backup_epoch import _path, _read_file
from recovery_program_native import _NativeView
from recovery_target_capture import MainTargetCapture
from minimal_capture_support import actual_pin, exclusive_json
from repository_records import (RepositoryError, canonical, document, exact,
    require, utc, validate_pin)

ROLE = 'TARGET_PRE_RESTORE'
POLICY = ('schemaVersion targetConfigRef captureRef captureConfigurationPin '
    'repositoryConfigurationPin backupEpochPolicy maxArchiveBytes '
    'maxReadbackRecordBytes maxPreservationSeconds minimumFreeBytes')
REPOSITORY = ('schemaVersion repositoryId repositoryRoot sourceIdentityPin '
    'captureBinderPin readbackConfigPin')
HOLD_INTENT = ('schemaVersion repositoryId operationId targetConfigRef role '
    'archivePath pointPath preservationIntentPin createdAt')
HOLD = ('schemaVersion repositoryId operationId targetConfigRef role intentPin '
    'pointPin archiveProofPin createdAt')
PROOF = ('schemaVersion state operationId targetConfigRef role intentPin '
    'materialsPin holdIntentPin pointPin manifestPin payloadTreePin '
    'repositoryBindingPin recoveryMaterialPin objectContentIndexPin readbackPin '
    'sidecarReadbackPin archiveClosePin captureTerminalPin payloadContentVerified '
    'serverDurabilityVerified independentFailureDomain originalResultPins finishedAt')
POINT = ('schemaVersion role backupId generationId pointType parentPointPins '
    'commonRecoveryPoint payloadRefs manifestPin readbackEvidencePin '
    'archiveCloseEvidencePin captureTerminalEvidencePin integrityState controlledRestoreEligible')


def _read(reference, limit=4*1024*1024):
    validate_pin(reference)
    raw, observed = _read_file(reference['path'], limit)
    require(observed == reference, 'PRESERVATION_INPUT_CHANGED')
    return raw


def _json(reference, limit=4*1024*1024):
    return document(_read(reference, limit))


def _new(path, value):
    # Repository manifests use the existing repository canonical format; the
    # capture journal's canonical format intentionally has a different newline.
    path = _path(str(path)); raw = canonical(value)
    require(0 < len(raw) <= 64*1024*1024, 'PRESERVATION_DOCUMENT_LIMIT')
    fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(directory)
    finally:os.close(directory)
    return actual_pin(path)


def _directory(path):
    path = _path(str(path))
    value = path.lstat()
    require(path.is_dir() and value.st_uid == os.geteuid() and not value.st_mode & 0o022,
        'PRESERVATION_DIRECTORY_INVALID')
    return value.st_dev, value.st_ino


def _operation(value):
    require(type(value) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,120}', value),
        'PRESERVATION_OPERATION_INVALID')
    return value


def _location(root, operation):
    return root/'preservations'/hashlib.sha256(_operation(operation).encode()).hexdigest()


def preservation_holds(configuration, *, guard):
    """Pending intent holds too; unknown, partial or malformed records fail closed."""
    root = _path(str(configuration.root))
    directory = root/'.repository-control'/'preservation-holds'
    guard()
    if not os.path.lexists(directory):
        return set()
    _directory(directory)
    names = sorted(directory.iterdir())
    require(len(names) <= 10000, 'PRESERVATION_HOLD_LIMIT')
    intents, finals, paths = {}, {}, set()
    try:
        for path in names:
            guard()
            require(path.name.endswith('.json'), 'PRESERVATION_HOLD_NAME_INVALID')
            require(not path.is_symlink() and path.is_file(), 'PRESERVATION_HOLD_FILE_INVALID')
            reference = actual_pin(path, guard)
            value = _json(reference)
            if value.get('schemaVersion') == 'MainTargetPreservationHoldIntent/v1':
                exact(value, HOLD_INTENT, 'MainTargetPreservationHoldIntent/v1')
                operation = _operation(value['operationId'])
                archive = _location(root, operation)
                require(path.name == operation+'-intent.json' and value['role'] == ROLE and
                    value['repositoryId'] == configuration.value['repositoryId'] and
                    value['archivePath'] == str(archive) and
                    value['pointPath'] == str(archive/'.repository'/'preservation-point.json') and
                    operation not in intents, 'PRESERVATION_HOLD_SCOPE_INVALID')
                _json(value['preservationIntentPin'])
                intents[operation] = (reference, value)
                paths.add(value['pointPath'])
            else:
                exact(value, HOLD, 'MainTargetPreservationHold/v1')
                operation = _operation(value['operationId'])
                require(path.name == operation+'.json' and value['role'] == ROLE and
                    value['repositoryId'] == configuration.value['repositoryId'] and
                    operation not in finals, 'PRESERVATION_HOLD_SCOPE_INVALID')
                finals[operation] = value
        for operation, value in finals.items():
            require(operation in intents, 'PRESERVATION_HOLD_INTENT_REQUIRED')
            reference, intent = intents[operation]
            require(value['intentPin'] == reference and
                value['targetConfigRef'] == intent['targetConfigRef'] and
                value['pointPin']['path'] == intent['pointPath'], 'PRESERVATION_HOLD_BINDING_CHANGED')
            point, proof = _json(value['pointPin']), _json(value['archiveProofPin'])
            require(point['schemaVersion'] == 'MainTargetPreservationPoint/v1' and
                proof['schemaVersion'] == 'MainTargetPreservationArchive/v1' and
                proof['state'] == 'ARCHIVED_VERIFIED' and proof['operationId'] == operation and
                proof['holdIntentPin'] == reference and proof['pointPin'] == value['pointPin'],
                'PRESERVATION_HOLD_PROOF_CHANGED')
        guard()
        require(sorted(directory.iterdir()) == names, 'PRESERVATION_HOLD_SET_CHANGED')
        return paths
    except (ValueError, KeyError, TypeError, OSError, RepositoryError) as error:
        if isinstance(error, RepositoryError) and error.code.startswith('PRESERVATION_'):
            raise
        raise RepositoryError('PRESERVATION_HOLD_INVALID') from error


class _Deadline:
    def __init__(self, publication):
        self.publication = publication
        self.end = min(publication.session.budget.deadline,
            time.monotonic()+publication.policy['maxPreservationSeconds'])

    def check(self):
        self.publication.check()

    def remaining(self):
        self.check()
        return max(.001, self.end-time.monotonic())


class VerifiedPreservationArchive:
    """Internal evidence value; deliberately has no stage/handoff authority."""
    def __init__(self, publication, reference):
        self._publication = publication
        self.archive_pin = deepcopy(reference)


class TargetPreservation:
    @classmethod
    def prepare(cls, native, *, policy_pin, reservation_pin):
        view = getattr(native, 'native_context', None)
        require(type(view) is _NativeView and view.phase == 'PREPARATION',
            'PRESERVATION_PREPARATION_REQUIRED')
        view.guard_native(native)
        context = view._context
        target = context._request['targetConfigRef']
        require(context._owner.get('targetPreservationPolicies', {}).get(target) == policy_pin,
            'PRESERVATION_POLICY_UNREGISTERED')
        policy = _json(policy_pin)
        exact(policy, POLICY, 'MainTargetPreservationPolicy/v1')
        program = context._policy
        require(policy['targetConfigRef'] == target and
            program['captureConfigurationPins'].get(policy['captureRef']) == policy['captureConfigurationPin'] and
            policy['backupEpochPolicy'] == program['backupEpochPolicy'], 'PRESERVATION_POLICY_SCOPE_CHANGED')
        require(all(type(policy[k]) is int and policy[k] > 0 for k in
            ('maxArchiveBytes','maxReadbackRecordBytes','maxPreservationSeconds','minimumFreeBytes')),
            'PRESERVATION_BUDGET_INVALID')
        repository = _json(policy['repositoryConfigurationPin'])
        exact(repository, REPOSITORY, 'MainTargetPreservationRepository/v1')
        require(type(repository['repositoryId']) is str and repository['repositoryId'],
            'PRESERVATION_REPOSITORY_INVALID')
        root = _path(repository['repositoryRoot']); _directory(root)
        from recovery_replacement_storage import overlaps
        forbidden = [str(context._root), *native.config['dataPaths'], native.config['dataRoot'],
            native.config['replacement']['stateRoot'], program['backupEpochPolicy']['root']]
        require(all(not overlaps(str(root), p) for p in forbidden), 'PRESERVATION_REPOSITORY_OVERLAP')
        readback = _json(repository['readbackConfigPin'])
        require(readback['repositoryRoot'] == str(root) and
            readback['recordRoot'] == str(context._root/'target-preservation'/'publication') and
            readback['maximumTotalRecordBytes'] <= policy['maxReadbackRecordBytes'],
            'PRESERVATION_READBACK_SCOPE_CHANGED')
        # No callback substitutes for the pinned, installed formal binder.
        import formal_capture_recovery_inputs as binder
        require(repository['captureBinderPin']['path'] == str(Path(binder.__file__).resolve()),
            'PRESERVATION_BINDER_CHANGED')
        _read(repository['captureBinderPin'])
        require(getattr(context, '_target_preservation', None) is None, 'PRESERVATION_ALREADY_USED')
        from repository_retention import RepositoryLock
        def preparation_guard():
            view.guard_native(native); context.budget.remaining()
        configuration = SimpleNamespace(root=root, archives=root/'preservations', value=repository,
            identity_pin=repository['sourceIdentityPin'], current=preparation_guard)
        # The target's real lock is already proved above. This is the existing
        # shared repository byte lock, not a second target lock implementation.
        owner = RepositoryLock(configuration, context._request)
        result = None
        try:
            session = MainTargetCapture.prepare(native, capture_ref=policy['captureRef'], reservation_pin=reservation_pin)
            source_scope = _json(_json(session.source['objectSourcePin'])['sourceScopePin'])
            require(source_scope['sourceIdentityPin'] == repository['sourceIdentityPin'],
                'PRESERVATION_SOURCE_IDENTITY_CHANGED')
            result = cls.__new__(cls)
            result._closed = result._used = False
            result._pins, result._leases, result._directories = {}, [], {}
            result._repository_lock = owner
            result.native, result.context, result.session = native, context, session
            result.policy, result.readback = deepcopy(policy), deepcopy(readback)
            result.policy_pin, result.repository_pin = deepcopy(policy_pin), deepcopy(policy['repositoryConfigurationPin'])
            result.root = context._root/'target-preservation'/'publication'
            result.root.mkdir(mode=0o700)
            result.configuration, result._repository_lock = configuration, owner
            configuration.current = result._check_base
            result.deadline = _Deadline(result)
            result._proof = None
            context._target_preservation = result
            for path in (root, result.root, owner.control): result._directories[path] = _directory(path)
            for reference in (policy_pin, result.repository_pin, repository['sourceIdentityPin'],
                    repository['readbackConfigPin'], repository['captureBinderPin']):
                result._remember(reference)
            from repository_native_readback import PreservationReadback
            with PreservationReadback(readback, result.deadline) as reader:
                reader.check()
            for reference in (readback['credentialPin'], *readback['libraryPins']): result._remember(reference)
            result._admit_archive_resources()
            execution = _json(context._binding)
            snapshot = _json(execution['contextPin'])
            operation = context._request['operationId']
            result.archive = _location(root, operation)
            result.intent_pin = result._write(result.root/'intent.json', dict(
                schemaVersion='MainTargetPreservationIntent/v1', operationId=operation, targetConfigRef=target,
                role=ROLE, policyPin=policy_pin, repositoryConfigurationPin=result.repository_pin,
                configurationPin=execution['configurationPin'], requestPin=execution['requestPin'],
                originalTargetPin=view.evidence['targetPin'], captureConfigurationPin=session._capture_pin,
                executionBindingPin=context._binding, reservationPin=reservation_pin, contextPin=execution['contextPin'],
                readyEventPin=snapshot['readyEpoch']['eventPin'], replacingEventPin=context._epoch['eventPin'],
                archivePath=str(result.archive), deadlineMonotonic=result.deadline.end, createdAt=utc()))
            result._hold_before_capture()
            return result
        except BaseException as error:
            try:
                if result is None: owner.close()
                else: result.close()
            except BaseException as cleanup:
                error.cleanupError = cleanup
                error.unknown = True
            raise

    def _admit_archive_resources(self):
        from recovery_resource_admission import observe_resources
        budget = self.native.config['resourceBudget']
        observed = observe_resources(self.context._owner,self.context._request,budget)
        devices = {}
        def add(path, amount, free=None):
            self.check()
            info = Path(path).stat(); available = shutil.disk_usage(path).free
            if free is not None: available = min(available,free)
            row = devices.setdefault(info.st_dev,dict(device=info.st_dev,requiredBytes=0,freeBytes=available))
            row['requiredBytes'] += amount; row['freeBytes'] = min(row['freeBytes'],available)
        add(self.configuration.root,self.policy['maxArchiveBytes'])
        add(self.root,self.policy['maxReadbackRecordBytes'])
        add(self.session.root,self.session.budget.maximum+self.session.budget.reserve)
        for row in observed['disks']:
            add(row['path'],budget['diskBytesByPath'][row['path']],row['freeBytes'])
        for row in devices.values():
            row['requiredBytes'] += self.policy['minimumFreeBytes']
            require(row['freeBytes'] >= row['requiredBytes'],'PRESERVATION_ARCHIVE_CAPACITY_INSUFFICIENT')
        self._write(self.root/'resource-admission.json',dict(schemaVersion='MainTargetPreservationResourceAdmission/v1',
            operationId=self.context._request['operationId'],devices=list(devices.values()),admitted=True,observedAt=utc()))

    def _hold_before_capture(self):
        self.check()
        for path in (self.configuration.archives,
                self.configuration.root/'.repository-control'/'preservation-holds'):
            if not os.path.lexists(path): path.mkdir(mode=0o700)
            self._directories[path] = _directory(path)
        preservation_holds(self.configuration,guard=self.check)
        operation = self.context._request['operationId']
        self.hold_intent = self._write(self.configuration.root/'.repository-control'/'preservation-holds'/
            (operation+'-intent.json'),dict(schemaVersion='MainTargetPreservationHoldIntent/v1',
                repositoryId=self.configuration.value['repositoryId'],operationId=operation,
                targetConfigRef=self.context._request['targetConfigRef'],role=ROLE,archivePath=str(self.archive),
                pointPath=str(self.archive/'.repository'/'preservation-point.json'),
                preservationIntentPin=self.intent_pin,createdAt=utc()))

    def _remember(self, reference):
        validate_pin(reference)
        path = reference['path']
        if path in self._pins:
            require(self._pins[path] == reference, 'PRESERVATION_PIN_CONFLICT')
            return reference
        require(actual_pin(path) == reference, 'PRESERVATION_INPUT_CHANGED')
        lease = ArchivePathGuard.capture([path])
        require(actual_pin(path) == reference, 'PRESERVATION_INPUT_CHANGED')
        self._leases.append(lease); self._pins[path] = deepcopy(reference)
        return reference

    def _write(self, path, value):
        self.check()
        reference = _new(path, value)
        self._remember(reference)
        self.native.original_pins.append(deepcopy(reference))
        return reference

    def _check_base(self):
        require(not self._closed, 'PRESERVATION_CLOSED')
        require(self.context._target_preservation is self and self.session._context is self.context,
            'PRESERVATION_OWNER_CHANGED')
        self.session.guard()
        require(time.monotonic() < self.deadline.end, 'PRESERVATION_DEADLINE')
        for path, expected in self._directories.items():
            require(_directory(path) == expected, 'PRESERVATION_DIRECTORY_CHANGED')
        for lease in self._leases: lease.check()

    def check(self):
        # RepositoryLock.check calls configuration.current (_check_base) once.
        self._repository_lock.check()
        require(not os.path.lexists(self._repository_lock.unknown_path),
            'REPOSITORY_PREVIOUS_WRITE_TERMINAL_UNKNOWN')

    def capture_and_publish(self):
        require(not self._used, 'PRESERVATION_ALREADY_USED')
        self._used = True
        try:
            self.check()
            materials = self.session.capture()
            from repository_minimal import publish_materials
            return publish_materials(self.configuration, materials, publication=self, deadline=self.deadline)
        except BaseException as error:
            if not (self.root/'failure.json').exists():
                snapshot = self.context.snapshot()
                reference = _new(self.root/'failure.json', dict(
                    schemaVersion='MainTargetPreservationFailure/v1', operationId=self.context._request['operationId'],
                    targetConfigRef=self.context._request['targetConfigRef'], phase=self.session.phase,
                    failureCode=getattr(error,'code',type(error).__name__),
                    mutationDispatched=snapshot['mutationDispatched'],
                    terminalUnknown=bool(getattr(error,'unknown',False) or
                        getattr(error,'clientCleanupUncertain',False) or
                        self.session.snapshot()['terminalUnknown'] or snapshot['terminalUnknown']),
                    originalResultPins=deepcopy(list(self._pins.values())), finishedAt=utc()))
                self.native.original_pins.append(reference)
            raise

    def _publish(self, materials):
        from repository_minimal import CapturedPublisher, capture_tree
        from repository_native_readback import PreservationReadback
        from repository_binding import assemble_readback_bindings, repository_binding
        import formal_capture_recovery_inputs as binder
        data = materials.result; root = self.session.root
        inputs = _json(data['captureInputsPin'], 64*1024*1024)
        tree = capture_tree(root, data['captureInputsPin'], inputs)
        require(_json(data['archiveEntriesPin'],64*1024*1024) == tree and
            inputs['pointType'] == 'FULL' and _json(inputs['capturePointPin'])['sourceRestored'] is False,
            'PRESERVATION_MATERIALS_CHANGED')
        total = sum(int(v.split('|')[1]) for v in tree.values() if v != 'directory')
        require(total <= self.policy['maxArchiveBytes'], 'PRESERVATION_ARCHIVE_BUDGET_EXCEEDED')
        from recovery_resource_admission import observe_resources
        budget = self.native.config['resourceBudget']
        observed = observe_resources(self.context._owner,self.context._request,budget)
        device = self.configuration.root.stat().st_dev
        required = total+self.policy['minimumFreeBytes']
        required += sum(budget['diskBytesByPath'][r['path']] for r in observed['disks'] if r['device']==device)
        if self.session.root.stat().st_dev == device:
            required += self.session.budget.maximum+self.session.budget.reserve
        require(shutil.disk_usage(self.configuration.root).free >= required,
            'PRESERVATION_ARCHIVE_CAPACITY_INSUFFICIENT')
        source_files = [root/name for name, spec in tree.items() if spec != 'directory']
        source_dirs = [root, *(root/name for name,spec in tree.items() if spec == 'directory')]
        self._leases.append(ArchivePathGuard.capture(source_files, closed_directories=source_dirs))
        for name, reference in inputs['archiveFilePins'].items():
            require(actual_pin(root/name,self.check) == reference, 'PRESERVATION_MATERIALS_CHANGED')
        require(actual_pin(data['captureInputsPin']['path'],self.check) == data['captureInputsPin'],
            'PRESERVATION_MATERIALS_CHANGED')
        preservation_holds(self.configuration,guard=self.check)
        operation = self.context._request['operationId']; target = self.context._request['targetConfigRef']
        hold_root = self.configuration.root/'.repository-control'/'preservation-holds'
        publisher = CapturedPublisher(self.configuration,root,tree,self.context._request,self.deadline)
        published = publisher.stream(self.archive,tree,verify_content=True)
        close = publisher.archive_request('close')
        require(close['state']=='ARCHIVE_READER_CLOSED_NOT_NAS_PROOF','PRESERVATION_ARCHIVE_CLOSE_FAILED')
        sidecar=self.archive/'.repository';sidecar.mkdir(mode=0o700)
        # Hold the copied payload identities and closed directory membership
        # through full readback, proof validation and eventual typed handoff.
        # The dedicated sidecar exists before closing the archive root; its own
        # membership closes only after all formal sidecars have been written.
        self._leases.append(ArchivePathGuard.capture(
            [self.archive/name for name,spec in tree.items() if spec!='directory'],
            closed_directories=[self.archive,*(self.archive/name for name,spec in tree.items() if spec=='directory')]))
        tree_pin=self._write(sidecar/'payload-tree.json',tree)
        payloads=[published[n] for n in sorted(tree) if tree[n]!='directory']
        manifest=dict(schemaVersion='RepositoryManifest/v1',backupId=inputs['backupId'],generationId=inputs['generationId'],
            pointType='FULL',parentPointPins=[],commonRecoveryPoint=inputs['recoveryPoint'],
            sourceIdentityPin=self.configuration.identity_pin,createdAt=utc(),
            versionPins=inputs['semanticSupplement']['versionPins'],
            toolPins=[actual_pin(p,self.check) for p in self.session.config['tools'].values()],
            payloadRefs=payloads,payloadTreePin=tree_pin,copyProtectionPin=None)
        manifest_pin=self._write(sidecar/'manifest.json',manifest)
        material=dict(manifestPin=manifest_pin,payloadTreePin=tree_pin,payloadRefs=payloads)
        with PreservationReadback(self.readback,self.deadline) as reader:
            connection,originals=reader.verify(str(self.archive),tree,material,payload_content=True)
            self._remember(originals)
            # The retained record closure is checked strictly before invoking
            # the existing binder, whose LIGHT helpers alone are insufficient.
            records=_json(originals,96*1024*1024)
            for reference in records['readbackOriginalPins'].values():self._remember(reference)
            outputs=assemble_readback_bindings(manifest_pin,{'originalRecordsPin':originals},self.deadline,
                binder.assemble_repository_capture_records,verify_content=True)
            recovery=self._write(sidecar/'recovery-material.json',outputs['recoveryMaterial'])
            index=self._write(sidecar/'object-content-index.json',outputs['objectContentIndex'])
            readback=self._write(sidecar/'readback-original.json',dict(schemaVersion='RepositoryMinimumReadback/v1',
                operationId=operation,manifestPin=manifest_pin,independentConnectionId=connection,
                payloadRefs=payloads,originalRecordsPin=originals,payloadContentVerified=True,
                serverDurabilityVerified=False,recoveryMaterialPin=recovery,objectContentIndexPin=index,
                sourceScopePin=outputs['recoveryMaterial']['sourceScopePin']))
            close_pin=self._write(sidecar/'archive-close.json',dict(schemaVersion='RepositoryMinimumArchiveClose/v1',
                operationId=operation,archiveReaderClosed=True,closeResponse=close))
            self.session.guard(force=True)
            snapshot=self.context.snapshot()
            require(not snapshot['terminalUnknown'] and all(row['terminalPin'] is not None and
                row['terminalObservation']['state']=='SUCCEEDED' for row in snapshot['invocations']),
                'PRESERVATION_CAPTURE_TERMINAL_UNPROVEN')
            native_pin=self._write(self.root/'capture-native-evidence.json',snapshot)
            materials_pin=self.session._pins[str(self.session._journal/'materials.json')]
            terminal=self._write(sidecar/'capture-terminal.json',dict(schemaVersion='MainTargetCaptureTerminal/v1',
                operationId=operation,targetConfigRef=target,materialsPin=materials_pin,nativeEvidencePin=native_pin,
                sourceRestored=False,writersRemainQuiesced=True,finishedAt=utc()))
            point={k:manifest[k] for k in ('backupId','generationId','pointType','parentPointPins','commonRecoveryPoint','payloadRefs')}
            point.update(schemaVersion='MainTargetPreservationPoint/v1',role=ROLE,manifestPin=manifest_pin,
                readbackEvidencePin=readback,archiveCloseEvidencePin=close_pin,captureTerminalEvidencePin=terminal,
                integrityState='COMPLETE',controlledRestoreEligible=False)
            point_pin=self._write(sidecar/'preservation-point.json',point)
            binding=self._write(sidecar/'recovery-repository-binding.json',repository_binding(
                SimpleNamespace(policy={'sourceIdentityPin':self.configuration.identity_pin}),
                point_pin,point,recovery,index,verify_metadata=True))
            sidecars=[tree_pin,manifest_pin,recovery,index,readback,close_pin,terminal,point_pin,binding]
            self._leases.append(ArchivePathGuard.capture([p['path'] for p in sidecars],closed_directories=[sidecar]))
            verified=[]
            for reference in sidecars:
                actual,_=reader.read(reference['path'],reference)
                verified.append(actual)
            sidecar_readback=self._write(self.root/'sidecar-readback.json',dict(
                schemaVersion='MainTargetPreservationSidecarReadback/v1',operationId=operation,
                pointPin=point_pin,independentConnectionId=connection,verifiedPins=verified,
                payloadContentVerified=True,serverDurabilityVerified=False,finishedAt=utc()))
        self.session.guard(force=True)
        for reference in list(self._pins.values()):
            require(actual_pin(reference['path'],self.check)==reference,'PRESERVATION_INPUT_CHANGED')
        proof=self._write(self.root/'archive-proof.json',dict(schemaVersion='MainTargetPreservationArchive/v1',
            state='ARCHIVED_VERIFIED',operationId=operation,targetConfigRef=target,role=ROLE,
            intentPin=self.intent_pin,materialsPin=materials_pin,holdIntentPin=self.hold_intent,pointPin=point_pin,
            manifestPin=manifest_pin,payloadTreePin=tree_pin,repositoryBindingPin=binding,recoveryMaterialPin=recovery,
            objectContentIndexPin=index,readbackPin=readback,sidecarReadbackPin=sidecar_readback,
            archiveClosePin=close_pin,captureTerminalPin=terminal,payloadContentVerified=True,
            serverDurabilityVerified=False,independentFailureDomain=False,
            originalResultPins=deepcopy(list(self._pins.values())),finishedAt=utc()))
        self._write(hold_root/(operation+'.json'),dict(schemaVersion='MainTargetPreservationHold/v1',
            repositoryId=self.configuration.value['repositoryId'],operationId=operation,targetConfigRef=target,
            role=ROLE,intentPin=self.hold_intent,pointPin=point_pin,archiveProofPin=proof,createdAt=utc()))
        self._proof=proof
        validate_archive(self.native,proof)
        return proof

    def close(self):
        if self._closed:return
        self._closed=True
        try:
            for lease in reversed(self._leases):lease.close()
        finally:
            self._leases=[]
            self._repository_lock.close()


def validate_archive(native, archive_proof_pin):
    view=getattr(native,'native_context',None)
    require(type(view) is _NativeView,'PRESERVATION_CONTEXT_REQUIRED')
    publication=getattr(view._context,'_target_preservation',None)
    require(type(publication) is TargetPreservation and publication.native is native and
        publication._proof==archive_proof_pin,'PRESERVATION_PROOF_OWNER_CHANGED')
    publication.check()
    proof=_json(archive_proof_pin)
    exact(proof,PROOF,'MainTargetPreservationArchive/v1')
    require(proof['state']=='ARCHIVED_VERIFIED' and proof['role']==ROLE and
        proof['payloadContentVerified'] is True and proof['serverDurabilityVerified'] is False and
        proof['independentFailureDomain'] is False and proof['intentPin']==publication.intent_pin and
        proof['operationId']==publication.context._request['operationId'] and
        proof['targetConfigRef']==publication.context._request['targetConfigRef'], 'PRESERVATION_PROOF_INVALID')
    point=_json(proof['pointPin']);exact(point,POINT,'MainTargetPreservationPoint/v1')
    require(point['role']==ROLE and point['pointType']=='FULL' and point['parentPointPins']==[] and
        point['integrityState']=='COMPLETE' and point['controlledRestoreEligible'] is False,
        'PRESERVATION_POINT_INVALID')
    for reference in proof['originalResultPins']:
        require(actual_pin(reference['path'],publication.check)==reference,'PRESERVATION_INPUT_CHANGED')
    for reference in point['payloadRefs']:
        require(actual_pin(reference['path'],publication.check)==reference,'PRESERVATION_PAYLOAD_CHANGED')
    require(proof['pointPin']['path'] in preservation_holds(publication.configuration,guard=publication.check),
        'PRESERVATION_HOLD_REQUIRED')
    publication.check()
    return VerifiedPreservationArchive(publication,archive_proof_pin)
