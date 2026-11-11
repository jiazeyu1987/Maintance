"""Explicit real-CIFS facility test, invoked only by the parent on its fixture.

The filesystem, SMB session, real ctx, physical lock and reservation are never
substituted. Only the existing external business-service protocols are finite
local fixtures. This performs prepare plus an independent SMB metadata read;
it does not quiesce/export/restore real or protocol business data, or set READY.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys

from test_recovery_target_capture_configuration import (
    main_configuration_case,capture_protocol,case,restore_case,construct,claim,locked,context,freeze_inputs)
from recovery_engine import Budget,pin,pinned_json,write
from recovery_program_activation import snapshot_restore
from recovery_program_execution import bind_execution
from test_recovery_program_activation import start
from recovery_program_evidence import _Reader
import recovery_resource_admission as admission
import recovery_target_preservation as preservation


def test_actual_cifs_prepare_uses_kernel_view_and_independent_signed_smb(main_configuration_case,monkeypatch):
    assert sys.platform.startswith('linux'),'REAL_CIFS_FACILITY_REQUIRED'
    assert 'MAIN_PRESERVATION_CIFS_INPUT' in os.environ,'EXPLICIT_CIFS_INPUT_REQUIRED'
    input_path=Path(os.environ['MAIN_PRESERVATION_CIFS_INPUT'])
    inputs=json.loads(input_path.read_bytes())
    assert set(inputs)=={'privateRoot','repositoryId','repositoryRoot','uncRoot','repositoryRelativePath',
        'credentialPin','libraryPins','port','authProtocol','operationId','evidencePath'}
    private=Path(inputs['privateRoot']);repository=Path(inputs['repositoryRoot'])
    output=Path(inputs['evidencePath'])
    assert private.is_absolute() and private.is_dir() and output.parent==private and not output.exists()
    assert repository.is_absolute() and repository.is_dir()
    import smbclient,smbprotocol
    for module in (smbclient,smbprotocol):
        assert pin(module.__file__) in inputs['libraryPins'],'REAL_PINNED_SMB_MODULE_REQUIRED'
    h=main_configuration_case
    # A separate real owner/reservation protects all previous fixture originals.
    operations=h.case['root']/'cifs-prepare-operations';operations.mkdir(mode=0o700)
    h.root=operations/inputs['operationId'];h.root.mkdir(mode=0o700)
    host=h.case['root']/'cifs-prepare-host';host.mkdir(mode=0o700)
    monkeypatch.setattr(admission,'HOST_ROOT',host)
    h.request['operationId']=inputs['operationId'];h.owner['operationsRoot']=str(operations)
    h.owner['targets']['target57']['replacement']['storage']['protectedRoots'].append(str(operations))
    h.case['policy']['baselineTargetPin']=write(h.case['root']/'cifs-prepare-target.json',h.owner['targets']['target57'])
    h.owner['targetProgramPolicies']['target57']=deepcopy(h.case['policy'])
    metadata=h.case['root']/'cifs-inputs';metadata.mkdir(mode=0o700)
    template=write(metadata/'readback-template.json',dict(
        schemaVersion='MainTargetPreservationReadbackTemplate/v1',
        **{k:inputs[k] for k in ('repositoryRoot','uncRoot','repositoryRelativePath','credentialPin','libraryPins','port','authProtocol')},
        maximumRecordBytes=1024*1024,maximumTotalRecordBytes=4*1024*1024,
        recordRootPolicy='CURRENT_OPERATION_TARGET_PRESERVATION_PUBLICATION'))
    scope=pinned_json(pinned_json(h.main_configuration['source']['objectSourcePin'])['sourceScopePin'])
    import formal_capture_recovery_inputs as binder
    repository_pin=write(metadata/'repository.json',dict(
        schemaVersion='MainTargetPreservationRepository/v2',repositoryId=inputs['repositoryId'],
        repositoryRoot=str(repository),sourceIdentityPin=scope['sourceIdentityPin'],
        captureBinderPin=pin(binder.__file__),readbackTemplatePin=template,
        writeView=dict(mountPoint=str(repository),filesystem='cifs',
            mountSource='//'+inputs['uncRoot'][2:].replace('\\','/'),
            mountRoot='/'+inputs['repositoryRelativePath'])))
    policy_pin=write(metadata/'policy.json',dict(schemaVersion='MainTargetPreservationPolicy/v2',
        targetConfigRef='target57',captureRef='source57',captureConfigurationPin=h.case['base_pin'],
        repositoryConfigurationPin=repository_pin,backupEpochPolicy=deepcopy(h.case['epoch']),
        maxArchiveBytes=8*1024*1024,maxReadbackRecordBytes=4*1024*1024,maxPreservationSeconds=180,minimumFreeBytes=1))
    h.owner['targetPreservationPolicies']={'target57':policy_pin};freeze_inputs(h)
    h.claim=claim(h.case,inputs['operationId'])
    with locked(h.case) as fd:
        saved=snapshot_restore(h.case['policy'],inputs['operationId'],fd)
        binding=bind_execution(h.owner,h.request,h.root,saved,fd)
        start(h.case,h.claim,fd,operation=inputs['operationId'])
        with context(h,binding,fd,budget=Budget(240000)) as ctx:
            native=construct(h,ctx)
            publication=preservation.TargetPreservation.prepare(native,policy_pin=policy_pin,reservation_pin=h.reservation)
            intent=pinned_json(publication.intent_pin)
            assert intent['schemaVersion']=='MainTargetPreservationIntent/v2'
            view=pinned_json(intent['writeViewObservationPin'])
            assert view['mountIdentity']['filesystem']=='cifs'
            assert view['mountIdentity']['mountPoint']==str(repository)
            reader=_Reader(lambda:None,(ctx._root,ctx._claim))
            preservation._read_v2_admission(reader,policy_pin=policy_pin,policy=pinned_json(policy_pin),
                repository=pinned_json(repository_pin),request=h.request,root=ctx._root,binding_pin=binding,
                derivation_pin=intent['readbackDerivationPin'],view_pin=intent['writeViewObservationPin'])
            reader.unchanged()
            from repository_native_readback import PreservationReadback
            with PreservationReadback(publication.readback,publication.deadline) as smb:
                observed,retained=smb.read(publication.hold_intent['path'],publication.hold_intent,retain=True)
                assert observed==publication.hold_intent and retained is not None
                assert Path(retained['path']).read_bytes()==Path(publication.hold_intent['path']).read_bytes()
            state=json.loads(h.state_path.read_bytes())
            assert state['actions']==[] and state['flags']==['0','0'] and not h.transport.releases
            assert ctx.snapshot()['mutationDispatched'] is False
            publication.check()
            evidence=dict(status='PREPARED_NOT_CAPTURED',inputPin=pin(input_path),
                configurationPin=h.owner_pin,requestPin=h.request_pin,reservationPin=h.reservation,
                executionBindingPin=binding,policyPin=policy_pin,intentPin=publication.intent_pin,
                writeViewObservationPin=intent['writeViewObservationPin'],
                readbackDerivationPin=intent['readbackDerivationPin'],holdIntentPin=publication.hold_intent,
                independentSmbOriginalPin=retained,actualCifs=True,actualSignedEncryptedSmb=True,
                actualBusinessRestore=False,businessQuiesced=False,epochReadyFabricated=False,
                originalResultPins=deepcopy(native.original_pins))
        # Closing local custody does not remove pending holds or invent READY.
        assert Path(publication.hold_intent['path']).is_file()
    raw=json.dumps(evidence,sort_keys=True,ensure_ascii=False,indent=2).encode('utf-8')
    descriptor=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(descriptor,'wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    descriptor=os.open(output.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)
