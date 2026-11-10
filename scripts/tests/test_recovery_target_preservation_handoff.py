"""Phase2b: real files/flock/ctx/custody/exporters, finite SQL/SMB protocols.

No server is contacted and actualBusinessRestore is False. The source SAFE
semantic candidate is the same independently verified entry as phase2a.
"""
from copy import deepcopy
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_recovery_target_preservation import (publication_case, capture_protocol as original_capture_protocol,
    case, restore_case, claim, locked, started, context, construct, quiesce)
from recovery_engine import Budget, RecoveryError, canonical, pin, pinned_json
from repository_records import RepositoryError


def module():
    return importlib.import_module('recovery_target_preservation')


@pytest.fixture
def capture_protocol(original_capture_protocol):
    # New 2b fixture only: bounded, explicit inputs before publication_case
    # pins the full owner and independent reservation. Product and old FULL
    # fixture defaults are unchanged. The original ten-second query window
    # proved insufficient during the full finite guard in r2.
    h=original_capture_protocol
    h.capture_config['limits'].update(querySeconds=30,dataSeconds=60)
    return h


def test_actual_prepare_exporter_intent_keeps_native_canonical_contract(publication_case):
    from recovery_engine import canonical,digest
    from recovery_target_preservation import TargetPreservation
    h=publication_case;claim(h.case)
    with locked(h.case) as fd:
        _,binding,_=started(h,fd)
        with context(h,binding,fd,budget=__import__('recovery_engine').Budget(240000)) as ctx:
            native=construct(h,ctx)
            TargetPreservation.prepare(native,policy_pin=h.preservation_policy,reservation_pin=h.reservation)
            rows=[r for r in ctx.snapshot()['invocations'] if '/session/stream-' in r['intentPinAtDispatch']['path']]
            assert rows and all(r['terminalObservation']['state']=='SUCCEEDED' for r in rows)
            for row in rows:
                value=row['intentObservation'];reference=row['intentPinAtDispatch']
                assert reference['bytes']==len(canonical(value))
                assert reference['sha256']==digest(value)


@pytest.fixture
def handoff_case(publication_case):
    h=publication_case
    original=h.transport.query
    def query(native,sql,*,mutation=False):
        if sql=='SET GLOBAL super_read_only=OFF; SET GLOBAL read_only=OFF;':
            assert mutation and native.native_context.phase=='PREPARATION'
            state=json.loads(h.state_path.read_bytes())
            assert state['flags']==['1','1']
            state['flags']=['0','0'];h.state_path.write_bytes(canonical(state))
            h.handoff_dispatches+=1
            return b''
        return original(native,sql,mutation=mutation)
    h.transport.query=query;h.handoff_dispatches=0
    return h


def test_archive_then_unique_typed_handoff_holds_barriers_without_payload_reread(handoff_case,monkeypatch):
    h=handoff_case;claim(h.case)
    with locked(h.case) as fd:
        _,binding,_=started(h,fd)
        with context(h,binding,fd,budget=Budget(240000)) as ctx:
            native=construct(h,ctx)
            publication=module().TargetPreservation.prepare(native,policy_pin=h.preservation_policy,
                reservation_pin=h.reservation)
            quiesce(h,native)
            archive=publication.capture_and_publish()
            payloads={p['path'] for p in pinned_json(pinned_json(archive)['pointPin'])['payloadRefs']}
            original=module().actual_pin
            def bounded(path,*args,**kwargs):
                assert str(path) not in payloads,'PAYLOAD_REHASHED_AFTER_COMPLETE_READBACK'
                return original(path,*args,**kwargs)
            monkeypatch.setattr(module(),'actual_pin',bounded)
            verified=publication.handoff()
            assert type(verified) is module().VerifiedTargetPreservation
            final=pinned_json(verified.reference)
            assert final['schemaVersion']=='MainTargetPreservation/v1' and final['state']=='SUCCEEDED'
            assert final['archiveProofPin']==archive
            handoff=pinned_json(final['handoffPin'])
            assert handoff['state']=='SUCCEEDED' and handoff['archiveProofPin']==archive
            assert h.handoff_dispatches==1 and json.loads(h.state_path.read_bytes())['flags']==['0','0']
            assert h.transport.scheduler=='OFF' and not h.transport.releases
            assert not native.storage_running and not native.running_applications
            assert publication.session.handed_off and publication.session._lease.handed_off
            assert module().require_preservation(ctx,native=native) is verified
            # A caller cannot redirect even the genuine typed object's pin to
            # another same-content file. The operation's fixed original owns
            # authorization, independently of schema/content equivalence.
            original_final=deepcopy(verified.reference)
            copied=ctx._root/'copied-preservation-final.json'
            copied.write_bytes(Path(original_final['path']).read_bytes());copied.chmod(0o600)
            verified.reference=pin(copied)
            with pytest.raises(RecoveryError,match='PRESERVATION_FINAL_CHANGED'):
                module().require_preservation(ctx,native=native)
            verified.reference=original_final
            with pytest.raises(RecoveryError,match='PROGRAM_NATIVE_STAGE_REQUIRED'):ctx.stage(None)
            with pytest.raises((RecoveryError,RepositoryError),match='PRESERVATION_HANDOFF_ALREADY_USED'):
                publication.handoff()
            assert h.handoff_dispatches==1
            # Same-content inode replacement is rejected by the continuous
            # actual archive lease, without rereading the large payload bytes.
            path=Path(next(iter(payloads)));raw=path.read_bytes()
            path.rename(publication.root/'retained-first-payload');path.write_bytes(raw)
            with pytest.raises(RecoveryError,match='ARCHIVED_PAYLOAD_CHANGED|ARCHIVE_WATCH_CHANGED|PATH_ALIAS_REJECTED'):
                module().require_preservation(ctx,native=native)
        assert publication._closed and publication._repository_lock.stream.closed
        assert Path(final['holdPin']['path']).exists()


def test_registered_preservation_requires_session_before_stage(handoff_case):
    h=handoff_case;claim(h.case)
    with locked(h.case) as fd:
        _,binding,_=started(h,fd)
        with context(h,binding,fd,budget=Budget(240000)) as ctx:
            with pytest.raises(RecoveryError,match='PROGRAM_TARGET_PRESERVATION_REQUIRED'):ctx.stage(None)
            assert h.handoff_dispatches==0


def test_context_owns_publication_lock_and_leases_even_before_capture(handoff_case):
    h=handoff_case;claim(h.case)
    with locked(h.case) as fd:
        _,binding,_=started(h,fd)
        with context(h,binding,fd,budget=Budget(240000)) as ctx:
            native=construct(h,ctx)
            publication=module().TargetPreservation.prepare(native,policy_pin=h.preservation_policy,
                reservation_pin=h.reservation)
        assert publication._closed and publication._repository_lock.stream.closed
        assert Path(publication.hold_intent['path']).exists()


@pytest.mark.parametrize('problem',['malformed','link'])
def test_real_retention_planner_checks_dynamic_holds_before_inventory(tmp_path,problem):
    import repository_retention as retention
    root=tmp_path/'repository';root.mkdir(mode=0o700)
    directory=root/'.repository-control'/'preservation-holds';directory.mkdir(parents=True,mode=0o700)
    path=directory/'restore-1.intent.json'
    if problem=='malformed':path.write_bytes(b'{}')
    else:path.symlink_to(root/'missing')
    configuration=SimpleNamespace(root=root,value={'repositoryId':'finite'},current=lambda:None)
    class Catalog:
        config=configuration
        deadline=SimpleNamespace(check=lambda:None)
        def list(self):
            pytest.fail('ORDINARY_INVENTORY_REACHED_BEFORE_HOLD_GUARD')
    with pytest.raises((RepositoryError,RecoveryError),match='PRESERVATION_'):
        retention.plan_retention(Catalog(),{'operationId':'retention-1'})


def test_real_retention_delete_rechecks_late_malformed_hold_before_removal(tmp_path,monkeypatch):
    # Real pinned inventory files, the original server byte lock and actual
    # execute_retention path. Catalog is a finite file-inventory protocol seam;
    # this does not claim a complete business archive/readback validation.
    import repository_retention as retention
    from repository_records import pin_file,write_new
    root=tmp_path/'repository';root.mkdir(mode=0o700)
    archives=root/'archives';archives.mkdir(mode=0o700)
    evidence=tmp_path/'evidence';evidence.mkdir(mode=0o700)
    policy=dict(retainNewestPoints=1,minValidFullPoints=1,retentionSeconds=1,legalHoldPointPins=[])
    policy_pin=write_new(tmp_path/'retention-policy.json',policy)
    points=[]
    for name,year in [('old',2000),('new',2001)]:
        sidecar=archives/name/'.repository';sidecar.mkdir(parents=True,mode=0o700)
        manifest=write_new(sidecar/'manifest.json',dict(createdAt=f'{year}-01-01T00:00:00Z'))
        points.append(write_new(sidecar/'point.json',dict(integrityState='COMPLETE',rehearsalEligible=True,
            pointType='FULL',payloadRefs=[],manifestPin=manifest)))
    configuration=SimpleNamespace(root=root,value={'repositoryId':'finite'},policy=policy,current=lambda:None)
    def authorization(request,reference):
        assert request['policyPin']==policy_pin and pin_file(reference['path'])==reference
    configuration.authorization=authorization
    class Catalog:
        config=configuration
        deadline=SimpleNamespace(check=lambda:None)
        def list(self):
            return [(reference,pinned_json(reference)) for reference in points]
        def chain(self,reference):
            point=pinned_json(reference)
            return [(reference,point,pinned_json(point['manifestPin']))]
        def load(self,reference):
            point=pinned_json(reference)
            return point,pinned_json(point['manifestPin'])
    catalog=Catalog();catalog.archives=archives
    request=dict(operationId='retention-1',policyPin=policy_pin)
    planned=retention.plan_retention(catalog,request)
    assert planned['deletePointPins']==points[:1]
    planned_pin=write_new(tmp_path/'retention-plan.json',planned)
    original=retention.write_new;late=[]
    def recorded(path,value):
        reference=original(path,value)
        if value.get('state')=='DELETE_INTENT':
            holds=root/'.repository-control'/'preservation-holds';holds.mkdir(mode=0o700)
            late.append(original(holds/'late-intent.json',{}))
        return reference
    monkeypatch.setattr(retention,'write_new',recorded)
    with pytest.raises((RepositoryError,RecoveryError),match='PRESERVATION_'):
        retention.execute_retention(catalog,request,planned_pin,evidence)
    assert late and (archives/'old').is_dir() and (archives/'new').is_dir()
    assert list(evidence.glob('*-intent.json')) and not list(evidence.glob('*-complete.json'))
