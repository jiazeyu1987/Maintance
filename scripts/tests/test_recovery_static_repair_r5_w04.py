"""W04 R5 isolated engineering protocols; never real recovery acceptance."""
import base64
import copy
import os
from pathlib import Path
import sys

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops/recovery'))
import recovery_cli as cli
import recovery_engine as engine
from recovery_engine import Budget, RecoveryError, canonical, digest, load, pin, pinned_json, write
from recovery_engine_state import Journal
from recovery_plan import resolve_chain
from test_recovery_residual_r3 import local_cli_protocol


@pytest.mark.parametrize('name', ['intent.json', 'request.json', 'exit.json', 'streams.json', 'result.json'])
@pytest.mark.parametrize('fault', ['missing', 'changed'])
def test_success_cache_original_fault_refuses_without_child_or_original_replacement(local_cli_protocol, name, fault):
    _, request_pin, evidence, output, operations = local_cli_protocol
    assert cli.main(['--request',request_pin['path'],'--output',str(output)]) == 0
    original = load(output)
    path = next(evidence.glob('operation-*/invocation-*/'+name))
    if fault == 'missing': path.unlink()
    else: path.write_bytes(path.read_bytes()+b' ')
    retained = None if fault == 'missing' else path.read_bytes()
    journal = next(evidence.glob('request-*.json')); before = journal.read_bytes()
    for destination in (output,evidence.parent/('cache-'+fault+'-'+name)):
        assert cli.main(['--request',request_pin['path'],'--output',str(destination)]) == 2
        failed = load(destination)
        assert failed['state'] == 'TERMINAL_UNKNOWN'
        assert failed['failureCode'] == 'TERMINAL_PUBLICATION_RECONCILIATION_REQUIRED'
        assert failed['originalResultPins'] == original['originalResultPins']
        assert failed['actualExitCode'] == 0 and len(operations) == 1
        assert journal.read_bytes() == before
        assert (None if not path.exists() else path.read_bytes()) == retained


def test_cache_rehash_uses_one_budget_inside_large_file_loop(local_cli_protocol, monkeypatch):
    request, request_pin, evidence, output, operations = local_cli_protocol
    assert cli.main(['--request',request_pin['path'],'--output',str(output)]) == 0
    journal_path = next(evidence.glob('request-*.json')); journal = load(journal_path)
    result = pinned_json(journal['resultPin'])
    large = evidence.parent/'large-original'; large.write_bytes(b'x'*(3*1024*1024))
    result['originalResultPins'].append(pin(large))
    journal['resultPin'] = write(journal['resultPin']['path'],result)
    journal['cacheEvidencePins'] = [journal['resultPin'],write(output,result)]
    write(journal_path,journal)
    actual = engine.check_pin; seen = []
    budget = Budget(5000)
    def inspected(ref, *, content=True, budget=None):
        assert budget is shared
        if ref['path'] == str(large):
            original_remaining = budget.remaining
            def expire():
                seen.append('budget')
                if len(seen) == 3: raise RecoveryError('DEADLINE_EXCEEDED')
                return original_remaining()
            monkeypatch.setattr(budget,'remaining',expire)
        return actual(ref,content=content,budget=budget)
    shared = budget
    monkeypatch.setattr(engine,'check_pin',inspected)
    with pytest.raises(RecoveryError,match='TERMINAL_PUBLICATION_RECONCILIATION_REQUIRED'):
        Journal(evidence,request).begin(budget=budget)
    assert len(seen) == 3 and len(operations) == 1


@pytest.mark.parametrize('destination', ['request','input','policy','config','trust','identity','journal','target','lock',
                                        'guard','repo-lock','intent','child-request','exit','streams','child-result'])
def test_success_cache_protected_output_is_never_written(local_cli_protocol, monkeypatch, destination):
    request, request_pin, evidence, output, operations = local_cli_protocol
    assert cli.main(['--request',request_pin['path'],'--output',str(output)]) == 0
    policy = cli.trusted_configuration(request)[1]
    extra = {key:write(evidence.parent/(key+'.json'),{'engineeringInput':key}) for key in ('policy','config','trust')}
    request['policyPin'] = extra['policy']; request['sourceOrTargetRef'] = extra['config']
    # Rebind the engineering request and journal to exact additional input Pins.
    request_pin = write(request_pin['path'],request)
    journal_path = next(evidence.glob('request-*.json')); journal = load(journal_path)
    journal['requestSha256'] = digest(request); write(journal_path,journal)
    monkeypatch.setenv('RECOVERY_DATA_TRUST_FILE',extra['trust']['path'])
    control = evidence.parent/'repo/.repository-control'
    names = {'request':Path(request_pin['path']),'input':Path(request['inputPins']['restorePlan']['path']),
        'policy':Path(extra['policy']['path']),'config':Path(extra['config']['path']),'trust':Path(extra['trust']['path']),
        'identity':Path(pinned_json(policy['dataTargetPin'])['targetIdentityPin']['path']),
        'journal':journal_path,'target':next(evidence.glob('target-*.state.json')),
        'lock':next(evidence.glob('target-*.lock')),'guard':control/'recovery-read-guard.json','repo-lock':control/'write.lock'}
    invocation = next(evidence.glob('operation-*/invocation-*'))
    names.update({key:invocation/name for key,name in [('intent','intent.json'),('child-request','request.json'),
                 ('exit','exit.json'),('streams','streams.json'),('child-result','result.json')]})
    path = names[destination]
    before = path.read_bytes() if path.exists() else None
    public_before = output.read_bytes()
    assert cli.main(['--request',request_pin['path'],'--output',str(path)]) == 1
    assert (path.read_bytes() if path.exists() else None) == before
    assert not path.with_name(path.name+'.recording-failure.json').exists()
    assert output.read_bytes() == public_before and len(operations) == 1


@pytest.mark.parametrize('destination', ['request','input','journal','target','lock','guard','child-result'])
def test_fresh_execution_rejects_protected_output_before_admission(local_cli_protocol, destination):
    request, request_pin, evidence, _, operations = local_cli_protocol
    identity = pinned_json(cli.trusted_configuration(request)[1]['dataTargetPin'])['targetIdentityPin']
    operation = evidence/('operation-'+digest({'operation':request['operationId'],'request':request['requestId']}))
    paths = {'request':Path(request_pin['path']),'input':Path(request['inputPins']['restorePlan']['path']),
        'journal':evidence/('request-'+digest(request['requestId'])+'.json'),
        'target':evidence/('target-'+digest(identity)+'.state.json'),
        'lock':evidence/('target-'+digest(identity)+'.lock'),
        'guard':evidence.parent/'repo/.repository-control/recovery-read-guard.json',
        'child-result':operation/'invocation-001/result.json'}
    path=paths[destination];before=path.read_bytes() if path.exists() else None
    assert cli.main(['--request',request_pin['path'],'--output',str(path)]) == 1
    assert not operations and (path.read_bytes() if path.exists() else None) == before
    assert not list(evidence.iterdir())


def test_normal_public_same_new_and_private_evidence_root_file_cache(local_cli_protocol):
    _, request_pin, evidence, output, operations = local_cli_protocol
    assert cli.main(['--request',request_pin['path'],'--output',str(output)]) == 0
    original = load(output)
    for path in (output,evidence.parent/'new.json',evidence/'public.json',evidence/'public.json'):
        assert cli.main(['--request',request_pin['path'],'--output',str(path)]) == 0
        assert load(path) == original and len(operations) == 1


def test_unowned_existing_public_file_and_fault_receipt_cannot_be_overwritten(local_cli_protocol):
    _, request_pin, evidence, output, operations = local_cli_protocol
    unknown = evidence.parent/'unowned.json';write(unknown,{'configuration':True})
    before=unknown.read_bytes()
    assert cli.main(['--request',request_pin['path'],'--output',str(unknown)]) == 1
    assert unknown.read_bytes()==before and not operations
    fault=output.with_name(output.name+'.recording-failure.json');write(fault,{'configuration':True})
    before=fault.read_bytes()
    assert cli.main(['--request',request_pin['path'],'--output',str(output)]) == 1
    assert fault.read_bytes()==before and not output.exists() and not operations


def full_noop_later_chain(root, *, mutation=None):
    """Actual local JSON/Pins/tree/Ed25519 engineering evidence, no services."""
    from recovery_data_files import tree_delta
    key=Ed25519PrivateKey.generate(); key_path=root/'authority.pem'
    key_path.write_bytes(key.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo))
    identity=write(root/'source.json',dict(sourceFingerprint='engineering-source',databaseUuid='engineering-db'))
    scope=write(root/'scope.json',dict(sourceIdentityPin=identity))
    version=write(root/'version.json',{'engineeringVersion':'8'})
    schema=pin(Path(__file__).resolve().parents[2]/'doc/tasks/20261010-backup-restore-modular-development/record-schemas.json')
    policy=dict(repositoryPointPins=[],sourceScopePin=scope,repositoryEvidenceKeyPins=[pin(key_path)],recordSchemasPin=schema,
        supportedVersionPins=[version],maxChainLength=10,readbackRule={'requiredValues':{}},originalExitRule={'requiredValues':{}},
        repositoryBindingPinsByManifestSha256={})
    points=[];materials=[];parent_index=None;prior_files={}; prior_position=None
    for number in range(3):
        archive=root/'archives'/str(number);meta=archive/'.repository';meta.mkdir(parents=True)
        kind='FULL' if number==0 else 'INCREMENTAL'; backup=str(number)
        if mutation=='duplicate-identity' and number==2: backup='0'
        position=dict(file='mysql-bin.000001',position=100 if number<2 else 140,gtidSet='',databaseUuid='engineering-db',serverVersion='8')
        asset=b'unchanged' if number<2 else b'changed'
        spec=dict(kind='file',bytes=len(asset),sha256=engine.hashlib.sha256(asset).hexdigest());files={'asset':spec}
        changed,deleted=tree_delta(prior_files,files)
        marker=digest(dict(databaseEnd=position,fileInventory=files))
        start=prior_position
        if mutation=='log-gap' and number==2: start=dict(start,position=120)
        if mutation=='prefix' and number==2: parents=points[-1:]
        else: parents=list(points)
        segments=[] if number<2 else [dict(file=position['file'],startPosition=100,stopPosition=140)]
        capture=write(archive/'capture.json',dict(schemaVersion='backup-capture-point/v1',sourceIdentity='engineering-source',
            backupId=backup,generationId='generation',pointType=kind,commonRecoveryPoint=marker,databaseEnd=position,
            databaseDelta=None if number==0 else dict(kind='BINLOG_SQL',parentPosition=start,segments=segments),
            fileInventory=files,fileDelta=dict(changedPaths=changed,deletedPaths=deleted)))
        sql=archive/'sql';sql.write_bytes(b'-- IntRuoyi binlog incremental; engineering\n' if number else b'-- engineering full\n')
        sql_pin=pin(sql); payloads=[capture,sql_pin];file_payloads={}
        if changed:
            file_path=archive/'asset';file_path.write_bytes(asset);file_ref=pin(file_path)
            file_payloads={'asset':file_ref};payloads.append(file_ref)
        inventory=write(archive/'files.json',files);payloads.append(inventory)
        objects=archive/'objects.jsonl';objects.write_bytes(b'');objects_pin=pin(objects);payloads.append(objects_pin)
        observation=dict(bucket='bucket',state='NO_MULTIPART_UPLOAD_OBSERVED',httpStatus=200,rawSha256='a'*64,rawBytes=2,
                         maxUploads=1,uploadCount=0,isTruncated=False,scope='WHOLE_BUCKET_FROM_START')
        multi=write(archive/'multipart-observations.json',dict(state='MULTIPART_EMPTY_POINT_OBSERVATIONS',before=[observation],after=[observation]));payloads.append(multi)
        receipt=write(archive/'export.json',dict(buckets=['bucket'],state='S3_EXPORTED_PENDING_RESTORE_PROOF',inventoryBytes=0,
            inventorySha256=objects_pin['sha256'],versionCount=0,deleteMarkerCount=0,totalVersionBytes=0,uniqueContentCount=0,
            multipartObservationsSha256=multi['sha256']));payloads.append(receipt)
        payloads.sort(key=lambda ref:Path(ref['path']).name)
        tree=write(meta/'tree.json',{Path(ref['path']).relative_to(archive).as_posix():'file|'+str(ref['bytes'])+'|'+ref['sha256'] for ref in payloads})
        protection=write(meta/'protection.json',{'engineeringCopyProtected':True})
        manifest=write(meta/'manifest.json',dict(schemaVersion='RepositoryManifest/v1',backupId=backup,generationId='generation',pointType=kind,
            parentPointPins=parents,commonRecoveryPoint=marker,payloadRefs=payloads,payloadTreePin=tree,copyProtectionPin=protection,
            sourceIdentityPin=identity,toolPins=[],versionPins=[version]))
        process=write(meta/'original-process.json',{'engineeringOnly':True})
        def signed(name,value):
            return write(meta/name,dict(schemaVersion='RepositorySignedRecord/v1',keySha256=policy['repositoryEvidenceKeyPins'][0]['sha256'],
                payload=value,signature=base64.b64encode(key.sign(canonical(value))).decode()))
        common=dict(backupId=backup,manifestPin=manifest,originalProcessPin=process,operationId='engineering-'+str(number))
        close=signed('close.json',dict(common,schemaVersion='RepositoryOwnerClose/v1',exactReaderCloseVerified=True,sourceFinalGuardVerified=True))
        readback=signed('readback.json',dict(common,schemaVersion='RepositoryReadback/v1',independentConnection=True,payloadRefs=payloads))
        exit_ref=signed('exit.json',dict(common,schemaVersion='RepositoryOriginalExit/v1',actualExitCode=0,rawTerminalVerified=True,processTerminated=True))
        point=dict(schemaVersion='RepositoryPoint/v1',backupId=backup,generationId='generation',pointType=kind,parentPointPins=parents,
            commonRecoveryPoint=marker,manifestPin=manifest,payloadRefs=payloads,readbackEvidencePin=readback,ownerCloseEvidencePin=close,
            originalExitEvidencePin=exit_ref,integrityState='COMPLETE',blockedReason='REPOSITORY_CURRENT_RECOVERY_PASSED_REQUIRED',
            rehearsalEligible=True,controlledRestoreEligible=False)
        point_pin=write(meta/'point.json',point)
        expected=write(meta/'expected.json',{'engineeringData':True})
        references=write(meta/'references.json',dict(schemaVersion='RecoveryReferenceInventory/v1',complete=True,recoveryPoint=marker))
        derived=write(meta/'derived.json',dict(schemaVersion='RecoveryDerivedInventory/v1',complete=True,recoveryPoint=marker,classes={'redis':{},'queue':{}}))
        material=dict(schemaVersion='RecoveryMaterial/v1',manifestPin=manifest,pointType=kind,recoveryPoint=marker,sourceScopePin=scope,
            sourceFingerprint='wrong' if mutation=='source' and number==2 else 'engineering-source',sourceDatabaseUuid='engineering-db',
            payloadPins=payloads,versionPins=[version],referenceInventoryPin=references,derivedInventoryPin=derived,
            database=dict(method='FORMAL_SQL_FULL' if number==0 else 'BINLOG_SQL',startPosition=start,endPosition=position,
                          expectedDataPin=expected,sqlPin=sql_pin,rawSqlPin=sql_pin,capturePointPin=capture),
            objects=dict(method='PHYSICAL_FILES',capturePointPin=capture,fileInventoryPin=inventory,filePayloadPins=file_payloads,
                         inventoryPin=objects_pin,exportReceiptPin=receipt))
        if mutation=='version' and number==2: material['versionPins']=[]
        material_pin=write(meta/'material.json',material)
        index=write(meta/'index.json',dict(schemaVersion='backup-capture-object-index/v1',backupId=backup,generationId='generation',
            sourceIdentity='engineering-source',recoveryPoint=marker,pointType=kind,parentExportIndexPin=parent_index,
            inventoryPin=objects_pin,exportReceiptPin=receipt,contentPins={},changedContentSha256=[],repositoryBound=True,manifestPin=manifest))
        binding=write(meta/'binding.json',dict(schemaVersion='RecoveryRepositoryBinding/v1',backupId=backup,generationId='generation',
            repositoryPointPin=point_pin,manifestPin=manifest,sourceScopePin=scope,recoveryMaterialPin=material_pin,objectContentIndexPin=index))
        policy['repositoryBindingPinsByManifestSha256'][manifest['sha256']]=binding
        policy['repositoryPointPins'].append(point_pin);points.append(point_pin);materials.append(material)
        parent_index=index;prior_files=files;prior_position=position
    if mutation=='payload': Path(materials[0]['database']['sqlPin']['path']).write_bytes(b'altered engineering payload')
    if mutation=='duplicate-pin': policy['repositoryPointPins'].append(points[0])
    return points,policy


def test_actual_resolve_chain_accepts_noop_and_later_increment_with_same_real_marker(tmp_path):
    points,policy=full_noop_later_chain(tmp_path)
    chain=resolve_chain(points[1],policy)
    assert len(chain)==2 and chain[0][2]['recoveryPoint']==chain[1][2]['recoveryPoint']
    capture=pinned_json(chain[1][2]['objects']['capturePointPin'])
    assert capture['databaseDelta']['segments']==[] and capture['fileDelta']=={'changedPaths':[],'deletedPaths':[]}
    chain=resolve_chain(points[2],policy)
    assert [step[0] for step in chain]==points
    assert chain[2][2]['recoveryPoint']!=chain[1][2]['recoveryPoint']


@pytest.mark.parametrize('mutation,code', [('duplicate-identity','POINT_IDENTITY_DUPLICATE'),('log-gap','DATABASE_LOG_GAP'),
    ('prefix','COMPLETE_PARENT_PREFIX_REQUIRED'),('source','SOURCE_BINDING_MISMATCH'),('version','VERSION_COMBINATION_REQUIRED'),
    ('payload','PIN_CHANGED'),('duplicate-pin','POINT_CATALOG_DUPLICATE')])
def test_actual_noop_chain_still_rejects_invalid_ancestry_and_originals(tmp_path,mutation,code):
    points,policy=full_noop_later_chain(tmp_path,mutation=mutation)
    with pytest.raises(RecoveryError,match=code): resolve_chain(points[2],policy)


def test_cycle_refused_before_reentering_original(tmp_path,monkeypatch):
    # A cryptographic immutable cycle cannot be constructed without hash fixed
    # points. This explicit reader substitute checks only the recursive gate.
    points,policy=full_noop_later_chain(tmp_path)
    import recovery_plan as plan
    actual=plan.pinned_json
    def cyclic(ref):
        value=actual(ref)
        if ref==points[2]: value['parentPointPins']=[points[2]]
        return value
    monkeypatch.setattr(plan,'pinned_json',cyclic)
    monkeypatch.setattr(plan,'legacy_completion',lambda point,policy:dict(actual(point['manifestPin']),parentPointPins=point['parentPointPins']))
    with pytest.raises(RecoveryError,match='CHAIN_CYCLE'):resolve_chain(points[2],policy)
