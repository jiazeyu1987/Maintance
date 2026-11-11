"""Read trusted preservation sources; never grant live target/clear authority.

Listing is bounded metadata only. Selection reuses the original strict historical
validator with its original owner/request, and binds those facts to a new request.
No point is rewritten or interpreted as an ordinary repository backup.
"""
from copy import deepcopy
from contextlib import nullcontext
import hashlib
import os
from pathlib import Path
import re
import stat

from recovery_backup_epoch import _path, _read_file, _signature
from repository_records import RepositoryError, canonical, document, require, validate_pin


ROLE = 'TARGET_PRE_RESTORE'
POLICY_FIELDS = ('schemaVersion sourceConfigRef originTargetConfigRef repositoryConfigurationPin '
    'publisherBindings maxPoints maxDocumentBytes maxMetadataBytes')
POINT_FIELDS = ('schemaVersion role backupId generationId pointType parentPointPins commonRecoveryPoint '
    'payloadRefs manifestPin readbackEvidencePin archiveCloseEvidencePin captureTerminalEvidencePin '
    'integrityState controlledRestoreEligible')
HOLD_INTENT_FIELDS = ('schemaVersion repositoryId operationId targetConfigRef role archivePath pointPath '
    'preservationIntentPin createdAt')
HOLD_FIELDS = 'schemaVersion repositoryId operationId targetConfigRef role intentPin pointPin archiveProofPin createdAt'
FINAL_FIELDS = ('schemaVersion state operationId targetConfigRef policyPin intentPin archiveProofPin '
    'handoffPin holdPin originalResultPins finishedAt')
INTENT_FIELDS = ('schemaVersion operationId targetConfigRef role policyPin repositoryConfigurationPin configurationPin '
    'requestPin originalTargetPin captureConfigurationPin executionBindingPin reservationPin contextPin readyEventPin '
    'replacingEventPin archivePath deadlineMonotonic createdAt')


def _need(value, suffix):
    require(value, 'PRESERVATION_SOURCE_'+suffix)


def _exact(value, fields, schema):
    _need(type(value) is dict and set(value)==set(fields.split()) and value.get('schemaVersion')==schema,
        'SCHEMA_INVALID')


def _text(value):
    return type(value) is str and 0 < len(value) <= 256 and not any(ord(c)<32 for c in value)


def _pin(reference):
    validate_pin(reference)
    return _path(reference['path'])


def _same_pin(left, right):
    return _pin(left)==_pin(right) and left['bytes']==right['bytes'] and left['sha256']==right['sha256']


def _same_content(left, right):
    _pin(left);_pin(right)
    return left['bytes']==right['bytes'] and left['sha256']==right['sha256']


class _PageMetadataLimit(RepositoryError):
    """Only exhaustion of a paged call's remaining aggregate byte budget."""


class _Reads:
    """Bounded original document reads using the existing guarded file reader."""
    def __init__(self, guard, *, paged=False):
        _need(callable(guard),'GUARD_INVALID')
        self.guard=guard
        self.maximum=4*1024*1024
        self.total_limit=64*1024*1024
        self.total=0
        self.records={}
        self.directories={}
        self.absent=set()
        self.paged=paged

    def budget(self, condition):
        if not condition and self.paged:raise _PageMetadataLimit('RESTORE_INPUTS_METADATA_LIMIT')
        _need(condition,'METADATA_LIMIT')

    def directory(self, path):
        self.guard();path=_path(str(path));info=path.stat()
        _need(stat.S_ISDIR(info.st_mode) and (os.name!='posix' or
            info.st_uid==os.geteuid() and not info.st_mode & 0o022),'DIRECTORY_INVALID')
        stamp=(_signature(info),info.st_mode)
        _need(path not in self.directories or self.directories[path][0]==stamp,'DIRECTORY_CHANGED')
        if path not in self.directories:self.directories[path]=(stamp,None)
        return path

    def listing(self, path, limit):
        path=self.directory(path);names=[]
        for child in path.iterdir():
            self.guard();names.append(child.name)
            _need(len(names)<=limit,'POINT_LIMIT')
        names=tuple(sorted(names))
        stamp,prior=self.directories[path]
        _need(prior is None or prior==names,'DIRECTORY_CHANGED')
        self.directories[path]=(stamp,names)
        return names

    def optional(self, path):
        path=_path(str(path));self.guard()
        if os.path.lexists(path):return True
        parent=path.parent
        while not parent.exists():parent=parent.parent
        self.directory(parent);self.absent.add(path)
        return False

    def read(self, reference, maximum=None):
        maximum=self.maximum if maximum is None else maximum
        _need(type(maximum) is int and maximum>0,'METADATA_LIMIT')
        maximum=min(maximum,self.maximum)
        path=_pin(reference)
        _need(reference['bytes']<=maximum,'METADATA_LIMIT')
        if self.paged:
            self.guard();_need(path.stat().st_size==reference['bytes'],'PIN_CHANGED')
        actual,value=self.fixed(path,maximum)
        _need(_same_pin(actual,reference),'PIN_CHANGED')
        return value

    def fixed(self, path, maximum=None):
        if maximum is None:maximum=self.maximum
        _need(type(maximum) is int and maximum>0,'METADATA_LIMIT')
        reference,value,_=self._fixed(path,min(maximum,self.maximum))
        return reference,value

    def raw(self, reference, maximum):
        """Share actual original bytes and this meter with the A1 verifier."""
        path=_pin(reference)
        _need(type(maximum) is int and maximum>0 and
            reference['bytes']<=min(maximum,self.maximum),'METADATA_LIMIT')
        if self.paged:
            self.guard();_need(path.stat().st_size==reference['bytes'],'PIN_CHANGED')
        actual,_,raw=self._fixed(path,min(maximum,self.maximum),want_raw=True)
        _need(_same_pin(actual,reference),'PIN_CHANGED')
        return raw

    def _fixed(self, path, maximum, *, want_raw=False):
        self.guard();path=_path(str(path));stamp=_signature(path.stat())
        if path in self.records:
            reference,value,observed=self.records[path]
            _need(stamp==observed,'METADATA_CHANGED')
            _need(reference['bytes']<=maximum,'METADATA_LIMIT')
            raw=None
            if want_raw:
                raw,actual=_read_file(path,maximum)
                _need(_same_pin(actual,reference) and _signature(path.stat())==observed,'METADATA_CHANGED')
            self.guard()
            return deepcopy(reference),deepcopy(value),raw
        remaining=self.total_limit-self.total
        _need(stamp[2]<=maximum,'METADATA_LIMIT')
        self.budget(stamp[2]<=remaining)
        raw,reference=_read_file(path,min(maximum,remaining))
        _need(_signature(path.stat())==stamp,'METADATA_CHANGED')
        self.total+=len(raw)
        self.budget(self.total<=self.total_limit)
        value=document(raw)
        self.records[path]=(reference,value,stamp)
        self.guard()
        return deepcopy(reference),deepcopy(value),raw if want_raw else None

    def pins(self):
        return [deepcopy(value[0]) for value in self.records.values()]

    def finish(self):
        self.guard()
        for path,(reference,_,stamp) in self.records.items():
            self.guard();_,observed=_read_file(path,self.maximum)
            _need(_same_pin(reference,observed) and _signature(path.stat())==stamp,'METADATA_CHANGED')
        for path,(stamp,names) in self.directories.items():
            self.guard();info=_path(str(path)).stat()
            _need((_signature(info),info.st_mode)==stamp and
                (names is None or tuple(sorted(child.name for child in path.iterdir()))==names),'DIRECTORY_CHANGED')
        for path in self.absent:
            self.guard();_need(not os.path.lexists(path),'METADATA_CHANGED')
        # Recheck identities after later reads/guards; no repeated payload hash.
        for path,(_,_,stamp) in self.records.items():
            _need(_signature(_path(str(path)).stat())==stamp,'METADATA_CHANGED')


def _policy(reads, reference, *, history=None):
    nested=history is not None and history.depth>0
    policy=reads.read(reference,min(4*1024*1024,reads.maximum)) if nested else reads.read(reference)
    _need(type(policy) is dict,'SCHEMA_INVALID')
    version=policy.get('schemaVersion')
    _need(version in ('MainTargetPreservationSourcePolicy/v1','MainTargetPreservationSourcePolicy/v2'),'SCHEMA_INVALID')
    _exact(policy,POLICY_FIELDS,version)
    tagged=version.endswith('/v2')
    _need(_text(policy['sourceConfigRef']) and _text(policy['originTargetConfigRef']),'POLICY_INVALID')
    for name,maximum in (('maxPoints',10000),('maxDocumentBytes',16*1024*1024),('maxMetadataBytes',64*1024*1024)):
        _need(type(policy[name]) is int and 0<policy[name]<=maximum,'POLICY_INVALID')
    _need(policy['maxDocumentBytes']<=policy['maxMetadataBytes'],'POLICY_INVALID')
    if nested:
        from recovery_preservation_inputs import _tighten_preservation_limits
        _tighten_preservation_limits(reads,policy['maxDocumentBytes'],policy['maxMetadataBytes'])
    else:
        reads.maximum=policy['maxDocumentBytes'];reads.total_limit=policy['maxMetadataBytes']
        reads.budget(reads.total<=reads.total_limit)
        if history is not None:
            reads.budget(all(pin['bytes']<=reads.maximum for pin,_,_ in reads.records.values()))
    _need(reference['bytes']<=reads.maximum,'METADATA_LIMIT')
    bindings=policy['publisherBindings']
    _need(type(bindings) is list and 1<=len(bindings)<=128,'POLICY_INVALID')
    seen=set()
    for binding in bindings:
        _need(type(binding) is dict,'POLICY_INVALID')
        if not tagged:
            _need(set(binding)=={'configurationPin','preservationPolicyPin'},'POLICY_INVALID')
            owner_pin=binding['configurationPin'];kind='UNCHANGED_OWNER'
        else:
            kind=binding.get('kind')
            fields={'kind','configurationPin','preservationPolicyPin'} if kind=='UNCHANGED_OWNER' else {
                'kind','baseConfigurationPin','preservationPolicyPin','requestConfigurationsRoot','resolverContract'}
            _need(kind in ('UNCHANGED_OWNER','REQUEST_DERIVED_OWNER') and set(binding)==fields,'POLICY_INVALID')
            owner_pin=_publisher_configuration(binding)
            if kind=='REQUEST_DERIVED_OWNER':
                _need(binding['resolverContract'] in ('ArchiveRestoreOwner/v1','PreservationRestoreOwner/v1'),
                    'RESOLVER_UNSUPPORTED')
                reads.directory(_path(binding['requestConfigurationsRoot']))
        _pin(owner_pin);_pin(binding['preservationPolicyPin'])
        key=(kind,owner_pin['bytes'],owner_pin['sha256'],binding['preservationPolicyPin']['path'])
        _need(key not in seen,'PUBLISHER_DUPLICATE');seen.add(key)
    repository=reads.read(policy['repositoryConfigurationPin'])
    _need(type(repository) is dict,'SCHEMA_INVALID')
    version=repository.get('schemaVersion')
    fields='schemaVersion repositoryId repositoryRoot sourceIdentityPin captureBinderPin '
    _need(version in ('MainTargetPreservationRepository/v1','MainTargetPreservationRepository/v2'),'SCHEMA_INVALID')
    fields+=('readbackConfigPin' if version.endswith('/v1') else 'readbackTemplatePin writeView')
    _exact(repository,fields,version)
    _need(_text(repository['repositoryId']),'POLICY_INVALID')
    reads.directory(_path(repository['repositoryRoot']))
    reads.read(repository['sourceIdentityPin'])
    for binding in bindings:
        owner=reads.read(_publisher_configuration(binding))
        _path(owner['operationsRoot'])
        _path(owner['targets'][policy['originTargetConfigRef']]['replacement']['stateRoot'])
        _need(owner['targetPreservationPolicies'][policy['originTargetConfigRef']]==binding['preservationPolicyPin'],
            'PUBLISHER_CHANGED')
        if tagged:
            old_policy=reads.read(binding['preservationPolicyPin'])
            _need(type(old_policy) is dict and old_policy.get('schemaVersion') in (
                'MainTargetPreservationPolicy/v1','MainTargetPreservationPolicy/v2') and
                old_policy.get('targetConfigRef')==policy['originTargetConfigRef'] and
                old_policy.get('repositoryConfigurationPin')==policy['repositoryConfigurationPin'],'PUBLISHER_CHANGED')
    return policy,repository


def _publisher_configuration(binding):
    return binding['baseConfigurationPin'] if binding.get('kind')=='REQUEST_DERIVED_OWNER' else binding['configurationPin']


def _publisher_owner(reads,policy,intent,operation,*,publisher_control_pins=(),history=None,
        source_policy_pin=None,point_pin=None):
    """Select explicit deployment trust, then verify its one owner contract."""
    tagged=policy['schemaVersion'].endswith('/v2')
    trusted=[]
    for row in policy['publisherBindings']:
        declared=reads.read(_publisher_configuration(row))
        root=_path(declared['operationsRoot'])/operation
        if (_pin(intent['configurationPin'])!=root/'configuration.json' or
                row['preservationPolicyPin']!=intent['policyPin']):continue
        if row.get('kind')=='REQUEST_DERIVED_OWNER' or _same_content(
                _publisher_configuration(row),intent['configurationPin']):trusted.append(row)
    if tagged and len(trusted)>1:
        # Explicit original base pins distinguish retained deployment generations.
        # Missing other-generation originals are observed absences, not a caught
        # verifier failure or permission to try an alternative derivation.
        matched=[]
        for row in trusted:
            if row.get('kind')!='REQUEST_DERIVED_OWNER':
                matched.append(row);continue
            path=_path(row['requestConfigurationsRoot'])/operation/'restore-inputs.json'
            if reads.optional(path):
                _,inputs=reads.fixed(path)
                _need(type(inputs) is dict and 'ownerConfigurationPin' in inputs,'PUBLISHER_CHANGED')
                if _same_pin(inputs['ownerConfigurationPin'],row['baseConfigurationPin']):matched.append(row)
        trusted=matched
    _need(len(trusted)==1,'PUBLISHER_AMBIGUOUS' if tagged and len(trusted)>1 else 'PUBLISHER_UNTRUSTED')
    selected=trusted[0];declared=reads.read(_publisher_configuration(selected))
    operation_root=_path(declared['operationsRoot'])/operation
    _need(_pin(intent['configurationPin'])==operation_root/'configuration.json' and
        _pin(intent['requestPin'])==operation_root/'request.json','HISTORICAL_PATH_CHANGED')
    owner=reads.read(intent['configurationPin']);request=reads.read(intent['requestPin'])
    originals={};resolver=None
    if tagged and selected['kind']=='REQUEST_DERIVED_OWNER':
        resolver=selected['resolverContract']
        _need(resolver=='ArchiveRestoreOwner/v1' or
            resolver=='PreservationRestoreOwner/v1' and history is not None,'RESOLVER_UNSUPPORTED')
        directory=_path(selected['requestConfigurationsRoot'])/operation
        if resolver=='PreservationRestoreOwner/v1':
            originals={key:reads.fixed(directory/name,maximum)[0] for key,name,maximum in (
                ('requestInputsPin','restore-inputs.json',65536),('pointBindingPin','preservation-point.json',65536),
                ('recoveryConfigurationPin','recovery.json',16*1024*1024))}
        else:
            originals={key:reads.fixed(directory/name)[0] for key,name in (
                ('requestInputsPin','restore-inputs.json'),('pointBindingPin','archive-point.json'),
                ('recoveryConfigurationPin','recovery.json'))}
    context=nullcontext()
    if history is not None:
        pins=dict(sourcePolicyPin=source_policy_pin,pointPin=point_pin,configurationPin=intent['configurationPin'],
            requestPin=intent['requestPin'],executionBindingPin=intent['executionBindingPin'],originals=originals,
            intentPin=reads.fixed(operation_root/'target-preservation'/'publication'/'intent.json')[0])
        context=history.publication(_path(declared['operationsRoot']),operation,policy['originTargetConfigRef'],pins,
            derived=resolver=='PreservationRestoreOwner/v1')
    with context:
        if resolver=='PreservationRestoreOwner/v1':
            from recovery_preservation_inputs import _verify_preservation_originals
            rebuilt,_=_verify_preservation_originals(reads,selected['baseConfigurationPin'],intent['requestPin'],
                request_configurations_root=selected['requestConfigurationsRoot'],originals=originals,
                publisher_control_pins=publisher_control_pins,history=history)
            _need(canonical(owner)==canonical(rebuilt),'PUBLISHER_CHANGED')
        elif resolver=='ArchiveRestoreOwner/v1':
            from recovery_restore_inputs import verify_archive_restore_inputs
            verification=verify_archive_restore_inputs(selected['baseConfigurationPin'],intent['requestPin'],
                request_configurations_root=selected['requestConfigurationsRoot'],originals=originals,
                guard=reads.guard,reader=reads.raw)
            _need(canonical(owner)==canonical(verification['derivedOwner']),'PUBLISHER_CHANGED')
        else:
            _need(canonical(owner)==canonical(declared) if tagged else owner==declared,'PUBLISHER_CHANGED')
    return owner,request,operation_root


def _historical(reads,policy,repository,operation,hold_intent,*,publisher_control_pins=(),history=None,
        source_policy_pin=None,point_pin=None):
    intent_pin=hold_intent['preservationIntentPin']
    # Allowed historical paths come from deployment trust, never from an
    # arbitrary pointer in an untrusted hold or a guessed operation directory.
    _need(any(_pin(intent_pin)==_path(reads.read(_publisher_configuration(row))['operationsRoot'])/
        operation/'target-preservation'/'publication'/'intent.json' for row in policy['publisherBindings']),
        'HISTORICAL_PATH_CHANGED')
    intent=reads.read(intent_pin)
    _need(type(intent) is dict,'SCHEMA_INVALID')
    version=intent.get('schemaVersion')
    _need(version in ('MainTargetPreservationIntent/v1','MainTargetPreservationIntent/v2'),'SCHEMA_INVALID')
    _exact(intent,INTENT_FIELDS+(' readbackDerivationPin writeViewObservationPin' if version.endswith('/v2') else ''),version)
    origin=policy['originTargetConfigRef']
    _need(intent['operationId']==operation and intent['targetConfigRef']==origin and intent['role']==ROLE and
        intent['repositoryConfigurationPin']==policy['repositoryConfigurationPin'] and
        intent['archivePath']==hold_intent['archivePath'],'ORIGIN_CHANGED')
    owner,request,operation_root=_publisher_owner(reads,policy,intent,operation,
        publisher_control_pins=publisher_control_pins,history=history,source_policy_pin=source_policy_pin,
        point_pin=point_pin)
    publication=operation_root/'target-preservation'/'publication'
    old_policy=reads.read(intent['policyPin'])
    _need(type(old_policy) is dict and old_policy.get('schemaVersion') in ('MainTargetPreservationPolicy/v1','MainTargetPreservationPolicy/v2') and
        old_policy.get('targetConfigRef')==origin and old_policy.get('repositoryConfigurationPin')==policy['repositoryConfigurationPin'] and
        owner['targetPreservationPolicies'][origin]==intent['policyPin'],'PUBLISHER_CHANGED')
    _need(_pin(intent_pin)==publication/'intent.json' and
        _pin(intent['configurationPin'])==operation_root/'configuration.json' and
        _pin(intent['requestPin'])==operation_root/'request.json','HISTORICAL_PATH_CHANGED')
    _need(request.get('schemaVersion')=='SmallAppBackupUiRequest/v1' and request.get('action')=='RESTORE' and
        request.get('operationId')==operation and request.get('targetConfigRef')==origin,'HISTORICAL_REQUEST_CHANGED')
    binding_pin=intent['executionBindingPin']
    claim=_path(owner['targets'][origin]['replacement']['stateRoot'])/operation
    _need(_pin(binding_pin)==claim/'program-execution-binding.json','HISTORICAL_PATH_CHANGED')
    binding=reads.read(binding_pin)
    _exact(binding,'schemaVersion operationId targetConfigRef policySha256 configurationPin requestPin reservationPin contextPin',
        'MainProgramExecutionBinding/v1')
    _need(binding['operationId']==operation and binding['targetConfigRef']==origin and
        binding['configurationPin']==intent['configurationPin'] and binding['requestPin']==intent['requestPin'] and
        binding['contextPin']==intent['contextPin'] and binding['reservationPin']==intent['reservationPin'],'BINDING_CHANGED')
    if policy['schemaVersion'].endswith('/v2'):
        from recovery_engine import digest
        _need(binding['policySha256']==digest(owner['targetProgramPolicies'][origin]),'BINDING_CHANGED')
    return dict(owner=owner,request=request,intent=intent,bindingPin=binding_pin,
        finalPath=publication/'preservation.json',publication=publication)


def _row(reads,policy,repository,operation,intent_pin,hold_intent,final,*,publisher_control_pins=(),history=None,
        source_policy_pin=None,point_pin=None):
    archive=_path(repository['repositoryRoot'])/'preservations'/hashlib.sha256(operation.encode()).hexdigest()
    point_path=archive/'.repository'/'preservation-point.json'
    _need(hold_intent['role']==ROLE and hold_intent['repositoryId']==repository['repositoryId'] and
        hold_intent['targetConfigRef']==policy['originTargetConfigRef'] and
        _path(hold_intent['archivePath'])==archive and _path(hold_intent['pointPath'])==point_path,'HOLD_SCOPE_CHANGED')
    history=_historical(reads,policy,repository,operation,hold_intent,publisher_control_pins=publisher_control_pins,
        history=history,source_policy_pin=source_policy_pin,point_pin=point_pin)
    row=dict(operationId=operation,role=ROLE,originTargetConfigRef=policy['originTargetConfigRef'],
        sourceConfigRef=policy['sourceConfigRef'],pointType='FULL',reference=None,pointPin=None,
        status='PRESERVATION_PENDING',blockedReason='PRESERVATION_SOURCE_PUBLICATION_PENDING',
        controlledRestoreEligible=None,sourceRestored=None,writersRemainQuiesced=None,
        restoreVerified=False,incrementalParentEligible=False,sourceAdmissionAvailable=False)
    if final is None:return row,history
    final_pin,hold=final
    _need(hold['role']==ROLE and hold['repositoryId']==repository['repositoryId'] and
        hold['targetConfigRef']==policy['originTargetConfigRef'] and _same_pin(hold['intentPin'],intent_pin) and
        _pin(hold['pointPin'])==point_path,'HOLD_BINDING_CHANGED')
    _need(_pin(hold['archiveProofPin'])==history['publication']/'archive-proof.json','HISTORICAL_PATH_CHANGED')
    row.update(pointPin=hold['pointPin'],reference='preservation-'+hashlib.sha256(canonical(hold['pointPin'])).hexdigest(),
        status='PRESERVATION_BLOCKED')
    for reference,reason in ((hold['archiveProofPin'],'PRESERVATION_SOURCE_ARCHIVE_PROOF_MISSING'),
            (hold['pointPin'],'PRESERVATION_SOURCE_POINT_MISSING')):
        if not reads.optional(_pin(reference)):
            row['blockedReason']=reason;return row,history
    proof=reads.read(hold['archiveProofPin']);point=reads.read(hold['pointPin'])
    _need(type(proof) is dict and proof.get('schemaVersion')=='MainTargetPreservationArchive/v1' and
        proof.get('state')=='ARCHIVED_VERIFIED' and proof.get('role')==ROLE and
        proof.get('operationId')==operation and proof.get('targetConfigRef')==policy['originTargetConfigRef'] and
        proof.get('pointPin')==hold['pointPin'] and _same_pin(proof['holdIntentPin'],intent_pin) and
        proof.get('intentPin')==hold_intent['preservationIntentPin'] and
        _pin(hold['archiveProofPin'])==history['publication']/'archive-proof.json','PROOF_CHANGED')
    _exact(point,POINT_FIELDS,'MainTargetPreservationPoint/v1')
    _need(point['role']==ROLE and point['controlledRestoreEligible'] is False and point['pointType']=='FULL' and
        point['parentPointPins']==[] and point['integrityState']=='COMPLETE' and
        _text(point['backupId']) and _text(point['generationId']),'POINT_CHANGED')
    row.update(backupId=point['backupId'],generationId=point['generationId'],controlledRestoreEligible=False)
    _need(_pin(point['manifestPin'])==archive/'.repository'/'manifest.json','HISTORICAL_PATH_CHANGED')
    if not reads.optional(_pin(point['manifestPin'])):
        row['blockedReason']='PRESERVATION_SOURCE_MANIFEST_MISSING';return row,history
    manifest=reads.read(point['manifestPin'])
    _need(type(manifest) is dict and manifest.get('schemaVersion')=='RepositoryManifest/v1' and manifest.get('sourceIdentityPin')==repository['sourceIdentityPin'] and
        all(manifest.get(k)==point[k] for k in ('backupId','generationId','pointType','parentPointPins','commonRecoveryPoint','payloadRefs')) and
        proof.get('manifestPin')==point['manifestPin'],'IDENTITY_CHANGED')
    _need(type(point['payloadRefs']) is list and bool(point['payloadRefs']),'POINT_CHANGED')
    for payload in point['payloadRefs']:
        path=_pin(payload)
        _need(archive in path.parents and '.repository' not in path.relative_to(archive).parts,'PAYLOAD_PATH_CHANGED')
    _need(_pin(point['captureTerminalEvidencePin'])==archive/'.repository'/'capture-terminal.json','HISTORICAL_PATH_CHANGED')
    if not reads.optional(_pin(point['captureTerminalEvidencePin'])):
        row['blockedReason']='PRESERVATION_SOURCE_CAPTURE_TERMINAL_MISSING';return row,history
    terminal=reads.read(point['captureTerminalEvidencePin'])
    _need(type(terminal) is dict and terminal.get('schemaVersion')=='MainTargetCaptureTerminal/v1' and terminal.get('operationId')==operation and
        terminal.get('targetConfigRef')==policy['originTargetConfigRef'] and terminal.get('sourceRestored') is False and
        terminal.get('writersRemainQuiesced') is True,'CAPTURE_TERMINAL_CHANGED')
    row.update(pointPin=hold['pointPin'],reference='preservation-'+hashlib.sha256(canonical(hold['pointPin'])).hexdigest(),
        backupId=point['backupId'],generationId=point['generationId'],manifestPin=point['manifestPin'],createdAt=manifest.get('createdAt'),
        controlledRestoreEligible=False,sourceRestored=False,writersRemainQuiesced=True,
        status='PRESERVATION_BLOCKED',blockedReason='PRESERVATION_SOURCE_FINAL_MISSING')
    history.update(point=point,pointPin=hold['pointPin'],proof=proof)
    if not reads.optional(history['finalPath']):return row,history
    preservation_pin,preservation=reads.fixed(history['finalPath'])
    _exact(preservation,FINAL_FIELDS,'MainTargetPreservation/v1')
    _need(preservation['state']=='SUCCEEDED' and preservation['operationId']==operation and
        preservation['targetConfigRef']==policy['originTargetConfigRef'] and
        preservation['policyPin']==history['intent']['policyPin'] and
        preservation['intentPin']==hold_intent['preservationIntentPin'] and
        preservation['archiveProofPin']==hold['archiveProofPin'] and _same_pin(preservation['holdPin'],final_pin),'FINAL_CHANGED')
    _need(_pin(preservation['handoffPin'])==history['publication'].parent/'session'/'handoff.json','HISTORICAL_PATH_CHANGED')
    if not reads.optional(_pin(preservation['handoffPin'])):
        row['blockedReason']='PRESERVATION_SOURCE_HANDOFF_MISSING';return row,history
    handoff=reads.read(preservation['handoffPin'])
    _need(type(handoff) is dict and handoff.get('schemaVersion')=='MainTargetPreservationHandoff/v1' and handoff.get('state')=='SUCCEEDED' and
        handoff.get('operationId')==operation and handoff.get('targetConfigRef')==policy['originTargetConfigRef'] and
        handoff.get('archiveProofPin')==hold['archiveProofPin'],'HANDOFF_CHANGED')
    row.update(status='PRESERVATION_PUBLISHED',blockedReason=None,sourceAdmissionAvailable=True)
    history['preservationPin']=preservation_pin
    return row,history


def _hold_records(reads,policy,repository,*,small=False):
    directory=_path(repository['repositoryRoot'])/'.repository-control'/'preservation-holds'
    if not reads.optional(directory):return {},{},directory,False
    intents,finals={},{}
    for name in reads.listing(directory,2*policy['maxPoints']):
        if small:
            reads.guard();_need((directory/name).stat().st_size<=65536,'INDEX_LIMIT')
            reference,value,_=reads._fixed(directory/name,min(65536,reads.maximum))
        else:reference,value=reads.fixed(directory/name)
        _need(type(value) is dict,'SCHEMA_INVALID')
        version=value.get('schemaVersion')
        _exact(value,HOLD_INTENT_FIELDS if version=='MainTargetPreservationHoldIntent/v1' else HOLD_FIELDS,
            'MainTargetPreservationHoldIntent/v1' if version=='MainTargetPreservationHoldIntent/v1' else 'MainTargetPreservationHold/v1')
        operation=value['operationId']
        _need(type(operation) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,120}',operation),'HOLD_NAME_INVALID')
        pending=version=='MainTargetPreservationHoldIntent/v1';index=intents if pending else finals
        _need(name==operation+('-intent.json' if pending else '.json') and operation not in index,'HOLD_NAME_INVALID')
        index[operation]=(reference,value)
    _need(len(intents)<=policy['maxPoints'] and set(finals)<=set(intents),'HOLD_SET_INVALID')
    return intents,finals,directory,True


def _catalogue(reads,policy,repository):
    intents,finals,_,_=_hold_records(reads,policy,repository)
    rows=[];histories={};identities=set()
    for operation,(reference,intent) in sorted(intents.items()):
        row,history=_row(reads,policy,repository,operation,reference,intent,finals.get(operation))
        if 'backupId' in row:
            identity=(row['backupId'],row['generationId'])
            _need(identity not in identities,'POINT_DUPLICATE');identities.add(identity)
        rows.append(row)
        if row['reference'] is not None:
            _need(row['reference'] not in histories,'POINT_DUPLICATE')
            histories[row['reference']]=(row,history)
    return rows,histories


def _hold_index(reads,policy,repository):
    """Observe the complete small index without opening point/manifest bodies."""
    reads.paged=True
    intents,finals,directory,exists=_hold_records(reads,policy,repository,small=True)
    observed=directory
    if not exists:
        while not observed.exists():observed=observed.parent
    reads.directory(observed);reads.guard();info=observed.stat()
    _need((_signature(info),info.st_mode)==reads.directories[observed][0],'DIRECTORY_CHANGED')
    directory_identity=dict(path=str(observed),exists=exists,device=info.st_dev,inode=info.st_ino,
        mode=info.st_mode,size=info.st_size,modifiedNanoseconds=info.st_mtime_ns,
        changedNanoseconds=info.st_birthtime_ns if os.name=='nt' else info.st_ctime_ns)
    entries=[];points=set();references=set()
    origin=policy['originTargetConfigRef'];root=_path(repository['repositoryRoot'])
    for operation,(intent_pin,intent) in sorted(intents.items()):
        archive=root/'preservations'/hashlib.sha256(operation.encode()).hexdigest()
        point_path=archive/'.repository'/'preservation-point.json'
        _need(intent['role']==ROLE and intent['repositoryId']==repository['repositoryId'] and
            intent['targetConfigRef']==origin and _path(intent['archivePath'])==archive and
            _path(intent['pointPath'])==point_path,'HOLD_SCOPE_CHANGED')
        historical_path=_pin(intent['preservationIntentPin'])
        _need(any(historical_path==_path(reads.read(_publisher_configuration(row))['operationsRoot'])/
            operation/'target-preservation'/'publication'/'intent.json' for row in policy['publisherBindings']),
            'HISTORICAL_PATH_CHANGED')
        entry=dict(operationId=operation,holdIntentPin=intent_pin,holdPin=None,pointPin=None,reference=None)
        if operation in finals:
            hold_pin,hold=finals[operation]
            point_pin=hold['pointPin'];point=_pin(point_pin)
            reference='preservation-'+hashlib.sha256(canonical(point_pin)).hexdigest()
            _need(point not in points and reference not in references,'POINT_DUPLICATE')
            points.add(point);references.add(reference)
            _need(hold['role']==ROLE and hold['repositoryId']==repository['repositoryId'] and
                hold['targetConfigRef']==origin and _same_pin(hold['intentPin'],intent_pin) and
                point==point_path and _pin(hold['archiveProofPin'])==historical_path.parent/'archive-proof.json',
                'HOLD_BINDING_CHANGED')
            entry.update(holdPin=hold_pin,pointPin=point_pin,reference=reference)
        entries.append(entry)
    return entries,intents,finals,directory_identity


def _paged_catalogue(reads,source_policy_pin):
    policy,repository=_policy(reads,source_policy_pin)
    _need(policy['schemaVersion']=='MainTargetPreservationSourcePolicy/v2','POLICY_INVALID')
    entries,intents,finals,identity=_hold_index(reads,policy,repository)
    snapshot=hashlib.sha256(canonical(dict(sourcePolicyPin=source_policy_pin,
        repositoryConfigurationPin=policy['repositoryConfigurationPin'],holdDirectoryIdentity=identity,
        entries=entries))).hexdigest()
    return policy,repository,entries,intents,finals,snapshot


def _snapshot(value):
    _need(type(value) is str and re.fullmatch('[0-9a-f]{64}',value),'CURSOR_INVALID')


def _cursor_after(cursor,source_policy_pin,repository_pin,snapshot,entries):
    if cursor is None:return 0
    fields={'schemaVersion','sourcePolicyPin','repositoryConfigurationPin','snapshotDigest','afterOperationId'}
    _need(type(cursor) is dict and set(cursor)==fields and
        cursor['schemaVersion']=='MainTargetPreservationCursor/v1','CURSOR_INVALID')
    try:
        _need(len(canonical(cursor))<=4096,'CURSOR_INVALID')
        _pin(cursor['sourcePolicyPin']);_pin(cursor['repositoryConfigurationPin'])
    except (ValueError,TypeError,RepositoryError) as error:
        raise RepositoryError('PRESERVATION_SOURCE_CURSOR_INVALID') from error
    _snapshot(cursor['snapshotDigest'])
    after=cursor['afterOperationId']
    _need(type(after) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,120}',after),'CURSOR_INVALID')
    operations=[entry['operationId'] for entry in entries]
    require(canonical(cursor['sourcePolicyPin'])==canonical(source_policy_pin) and
        canonical(cursor['repositoryConfigurationPin'])==canonical(repository_pin) and
        cursor['snapshotDigest']==snapshot and after in operations,'PRESERVATION_CATALOGUE_CHANGED_RESTART')
    return operations.index(after)+1


def _page_preservation(reads,source_policy_pin,*,cursor,limit):
    policy,repository,entries,intents,finals,snapshot=_paged_catalogue(reads,source_policy_pin)
    position=_cursor_after(cursor,source_policy_pin,policy['repositoryConfigurationPin'],snapshot,entries)
    rows=[];identities=set()
    while position<len(entries) and len(rows)<limit:
        operation=entries[position]['operationId'];intent_pin,intent=intents[operation]
        try:row,_=_row(reads,policy,repository,operation,intent_pin,intent,finals.get(operation))
        except _PageMetadataLimit:
            if not rows:raise
            break
        if 'backupId' in row:
            identity=(row['backupId'],row['generationId'])
            _need(identity not in identities,'POINT_DUPLICATE');identities.add(identity)
        rows.append(row);position+=1
    next_cursor=None
    if position<len(entries):
        next_cursor=dict(schemaVersion='MainTargetPreservationCursor/v1',sourcePolicyPin=deepcopy(source_policy_pin),
            repositoryConfigurationPin=deepcopy(policy['repositoryConfigurationPin']),snapshotDigest=snapshot,
            afterOperationId=rows[-1]['operationId'])
        _cursor_after(next_cursor,source_policy_pin,policy['repositoryConfigurationPin'],snapshot,entries)
    return dict(schemaVersion='MainTargetPreservationPage/v1',sourceConfigRef=policy['sourceConfigRef'],
        sourcePolicyPin=deepcopy(source_policy_pin),repositoryConfigurationPin=deepcopy(policy['repositoryConfigurationPin']),
        role=ROLE,snapshotDigest=snapshot,discoveredCount=len(entries),pageCount=len(rows),metadataBytes=reads.total,
        points=rows,nextCursor=next_cursor,complete=next_cursor is None,payloadContentVerified=False,
        clearAuthorized=False,originalResultPins=reads.pins())


def list_preservation_page(source_policy_pin, *, cursor=None, limit=1, guard):
    """Return bounded metadata for this page; never grant source/clear authority."""
    try:
        _need(type(limit) is int and 1<=limit<=32,'CURSOR_INVALID')
        reads=_Reads(guard,paged=True)
        value=_page_preservation(reads,source_policy_pin,cursor=cursor,limit=limit)
        reads.finish()
        return value
    except RepositoryError:raise
    except (ValueError,KeyError,TypeError,OSError) as error:
        raise RepositoryError('PRESERVATION_SOURCE_INVALID') from error


_CURRENT_SNAPSHOT=object()


def _select_preservation(reads,source_policy_pin,reference,*,snapshot_digest):
    policy,repository,entries,intents,finals,snapshot=_paged_catalogue(reads,source_policy_pin)
    if snapshot_digest is not _CURRENT_SNAPSHOT:
        require(snapshot==snapshot_digest,'PRESERVATION_CATALOGUE_CHANGED_RESTART')
    selected=[entry for entry in entries if entry['reference'] is not None and entry['reference']==reference]
    _need(bool(selected),'POINT_UNKNOWN');_need(len(selected)==1,'POINT_DUPLICATE')
    entry=selected[0];operation=entry['operationId'];intent_pin,intent=intents[operation]
    row,_=_row(reads,policy,repository,operation,intent_pin,intent,finals.get(operation))
    _need(row['reference']==reference and row['pointPin']==entry['pointPin'],'POINT_CHANGED')
    return dict(schemaVersion='MainTargetPreservationSelection/v1',sourceConfigRef=policy['sourceConfigRef'],
        sourcePolicyPin=deepcopy(source_policy_pin),repositoryConfigurationPin=deepcopy(policy['repositoryConfigurationPin']),
        role=ROLE,snapshotDigest=snapshot,reference=reference,pointPin=deepcopy(entry['pointPin']),point=row,
        metadataBytes=reads.total,originalResultPins=reads.pins(),payloadContentVerified=False,
        sourceAdmissionGranted=False,targetAdmitted=False,clearAuthorized=False)


def select_preservation_point(source_policy_pin, reference, *, snapshot_digest, guard):
    """Read one indexed point's metadata; full admission remains independent."""
    try:
        _snapshot(snapshot_digest)
        reads=_Reads(guard,paged=True)
        value=_select_preservation(reads,source_policy_pin,reference,snapshot_digest=snapshot_digest)
        reads.finish()
        return value
    except RepositoryError:raise
    except (ValueError,KeyError,TypeError,OSError) as error:
        raise RepositoryError('PRESERVATION_SOURCE_INVALID') from error


class PreservationCatalogueRead:
    """One trusted control, one metadata budget, and one final read barrier."""

    def __init__(self,current_control_pin,*,guard):
        from recovery_preservation_inputs import resolve_preservation_control_pins

        self._reads=_Reads(guard,paged=True)
        self._resolution=resolve_preservation_control_pins(current_control_pin,guard=guard,reader=self._reads.raw)
        current=self._reads.read(self._resolution['currentControlPin'])
        self._policies=current.get('preservationSourcePolicies')
        self._policy_ref=None
        self._finished=False

    @property
    def control_resolution(self):
        return deepcopy(self._resolution)

    def _require_open(self):
        _need(not self._finished,'SESSION_FINISHED')

    def _policy_pin(self,policy_ref):
        _need(self._policy_ref is None or policy_ref==self._policy_ref,'SESSION_POLICY_CHANGED')
        _need(_text(policy_ref) and type(self._policies) is dict and policy_ref in self._policies,
            'SESSION_POLICY_UNREGISTERED')
        self._policy_ref=policy_ref
        reference=self._policies[policy_ref]
        _pin(reference)
        return reference

    def page(self,policy_ref,*,cursor=None,limit=1):
        self._require_open()
        try:
            _need(type(limit) is int and 1<=limit<=32,'CURSOR_INVALID')
            return _page_preservation(self._reads,self._policy_pin(policy_ref),cursor=cursor,limit=limit)
        except RepositoryError:raise
        except (ValueError,KeyError,TypeError,OSError) as error:
            raise RepositoryError('PRESERVATION_SOURCE_INVALID') from error

    def _select(self,policy_ref,reference,snapshot_digest):
        try:
            return _select_preservation(self._reads,self._policy_pin(policy_ref),reference,
                snapshot_digest=snapshot_digest)
        except RepositoryError:raise
        except (ValueError,KeyError,TypeError,OSError) as error:
            raise RepositoryError('PRESERVATION_SOURCE_INVALID') from error

    def select(self,policy_ref,reference,*,snapshot_digest):
        self._require_open()
        _snapshot(snapshot_digest)
        return self._select(policy_ref,reference,snapshot_digest)

    def select_current(self,policy_ref,reference):
        self._require_open()
        return self._select(policy_ref,reference,_CURRENT_SNAPSHOT)

    def raw(self,reference,maximum):
        self._require_open()
        return self._reads.raw(reference,maximum)

    def fixed(self,path,maximum):
        self._require_open()
        return self._reads.fixed(path,maximum)

    def listing(self,path,limit):
        self._require_open()
        _need(type(limit) is int and limit>0,'POINT_LIMIT')
        return self._reads.listing(path,limit)

    def finish(self):
        self._require_open()
        self._finished=True
        self._reads.finish()
        return dict(schemaVersion='PreservationCatalogueReadSummary/v1',controlResolution=self.control_resolution,
            metadataBytes=self._reads.total,originalResultPins=self._reads.pins())


def _describe_bound_preservation(reads, source_policy_pin, request, point_binding,*,publisher_control_pins=(),history=None):
    """Borrow one caller ledger for fixed metadata; never grant admission."""
    try:
        fields={'schemaVersion','reference','sourceConfigRef','sourcePolicyPin','pointPin',
            'publicationOperationId','controlConfigurationPin'}
        request_fields={'schemaVersion','operationId','action','sourceConfigRef','parentChainRef',
            'recoveryPointRef','targetConfigRef'}
        _need(type(point_binding) is dict and set(point_binding)==fields and
            point_binding['schemaVersion']=='SmallAppPreservationPointBinding/v1' and
            type(request) is dict and set(request)==request_fields and
            request['schemaVersion']=='SmallAppBackupUiRequest/v1' and request['action']=='RESTORE' and
            request['parentChainRef'] is None,'BOUND_INPUT_INVALID')
        old=point_binding['publicationOperationId'];new=request['operationId']
        _need(all(type(value) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,120}',value)
            for value in (old,new)) and old!=new and _text(request['targetConfigRef']) and
            _text(point_binding['sourceConfigRef']) and
            point_binding['sourceConfigRef']==request['sourceConfigRef'] and
            type(point_binding['reference']) is str and
            re.fullmatch('preservation-[0-9a-f]{64}',point_binding['reference']) and
            point_binding['reference']==request['recoveryPointRef'],'BOUND_INPUT_INVALID')
        try:
            for reference in (source_policy_pin,point_binding['sourcePolicyPin'],
                    point_binding['pointPin'],point_binding['controlConfigurationPin']):_pin(reference)
        except (RepositoryError,ValueError,TypeError) as error:
            raise RepositoryError('PRESERVATION_SOURCE_BOUND_INPUT_INVALID') from error
        _need(canonical(source_policy_pin)==canonical(point_binding['sourcePolicyPin']),'BOUND_INPUT_INVALID')
        # The caller verifies control/base trust; its self-reported control pin
        # is shape-checked above, never read or promoted into authority here.
        policy,repository=_policy(reads,source_policy_pin,history=history)
        _need(policy['sourceConfigRef']==request['sourceConfigRef'],'BOUND_INPUT_INVALID')
        directory=_path(repository['repositoryRoot'])/'.repository-control'/'preservation-holds'
        intent_path=directory/(old+'-intent.json');hold_path=directory/(old+'.json')
        _need(reads.optional(intent_path) and reads.optional(hold_path),'BOUND_HOLD_MISSING')
        intent_pin,intent=reads.fixed(intent_path);hold_pin,hold=reads.fixed(hold_path)
        _exact(intent,HOLD_INTENT_FIELDS,'MainTargetPreservationHoldIntent/v1')
        _exact(hold,HOLD_FIELDS,'MainTargetPreservationHold/v1')
        _need(intent['operationId']==old and hold['operationId']==old,'BOUND_POINT_CHANGED')
        row,history=_row(reads,policy,repository,old,intent_pin,intent,(hold_pin,hold),
            publisher_control_pins=publisher_control_pins,history=history,source_policy_pin=source_policy_pin,
            point_pin=point_binding['pointPin'])
        _need(row['reference']==point_binding['reference'] and
            canonical(row['pointPin'])==canonical(point_binding['pointPin']),'BOUND_POINT_CHANGED')
        require(row['status']=='PRESERVATION_PUBLISHED' and row['blockedReason'] is None,
            row['blockedReason'] or 'PRESERVATION_SOURCE_BOUND_POINT_CHANGED')
        return policy,repository,row,history
    except RepositoryError:raise
    except (ValueError,KeyError,TypeError,OSError) as error:
        raise RepositoryError('PRESERVATION_SOURCE_INVALID') from error


def list_preservation_points(source_policy_pin, *, guard):
    """Project trusted metadata, never hash payloads or grant restore authority."""
    try:
        reads=_Reads(guard);policy,repository=_policy(reads,source_policy_pin)
        points,_=_catalogue(reads,policy,repository);reads.finish()
        return dict(schemaVersion='MainTargetPreservationCatalogue/v1',sourceConfigRef=policy['sourceConfigRef'],
            sourcePolicyPin=deepcopy(source_policy_pin),role=ROLE,points=points,payloadContentVerified=False,
            clearAuthorized=False,originalResultPins=reads.pins())
    except RepositoryError:raise
    except (ValueError,KeyError,TypeError,OSError) as error:
        raise RepositoryError('PRESERVATION_SOURCE_INVALID') from error


def resolve_preservation_source(source_policy_pin, request_pin, *, guard):
    """Verify one original closure for a new request; target gates remain separate."""
    try:
        reads=_Reads(guard);policy,repository=_policy(reads,source_policy_pin)
        request=reads.read(request_pin)
        from recovery_minimal_plan import request_contract
        request_contract(request)
        _need(request['action']=='RESTORE' and request['sourceConfigRef']==policy['sourceConfigRef'] and
            request['parentChainRef'] is None and request['targetConfigRef'] is not None,'REQUEST_INVALID')
        _,histories=_catalogue(reads,policy,repository)
        _need(request['recoveryPointRef'] in histories,'POINT_UNKNOWN')
        row,history=histories[request['recoveryPointRef']]
        _need(row['sourceAdmissionAvailable'],row['blockedReason'].removeprefix('PRESERVATION_SOURCE_') if row['blockedReason'] else 'INCOMPLETE')
        _need(request['operationId']!=row['operationId'] and _pin(request_pin)!=_pin(history['intent']['requestPin']),
            'NEW_REQUEST_REQUIRED')
        from recovery_target_preservation import validate_preservation_evidence
        # This is intentionally the real historical validator, not an injectable
        # success callback. It owns payload/binder/native/hold/handoff admission.
        validation=validate_preservation_evidence(history['owner'],history['request'],history['preservationPin'],
            binding_pin=history['bindingPin'],guard=guard)
        _need(validation.get('schemaVersion')=='MainTargetPreservationEvidenceValidation/v1' and
            validation.get('targetPreservationPin')==history['preservationPin'] and
            validation.get('payloadContentVerified') is True and validation.get('clearAuthorized') is False,
            'VALIDATION_CHANGED')
        reads.finish()
        return deepcopy(dict(schemaVersion='MainTargetPreservationRestoreAdmission/v1',sourcePolicyPin=source_policy_pin,
            requestPin=request_pin,sourceConfigRef=policy['sourceConfigRef'],reference=row['reference'],pointPin=row['pointPin'],
            manifestPin=row['manifestPin'],recoveryMaterialPin=history['proof']['recoveryMaterialPin'],
            repositoryBindingPin=history['proof']['repositoryBindingPin'],targetPreservationPin=history['preservationPin'],
            historicalConfigurationPin=history['intent']['configurationPin'],historicalRequestPin=history['intent']['requestPin'],
            executionBindingPin=history['bindingPin'],preservationValidation=validation,payloadContentVerified=True,
            controlledRestoreEligible=False,sourceRestored=False,incrementalParentEligible=False,
            clearAuthorized=False,targetAdmitted=False,programArchiveVerified=False,originalResultPins=reads.pins()))
    except RepositoryError:raise
    except (ValueError,KeyError,TypeError,OSError) as error:
        raise RepositoryError('PRESERVATION_SOURCE_INVALID') from error
