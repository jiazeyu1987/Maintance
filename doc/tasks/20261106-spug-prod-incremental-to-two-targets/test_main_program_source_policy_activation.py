"""Real temporary native metadata; local protocol boundaries are not deployment.

The old planner is read from the explicitly pinned, retained 45 STANDARD package.
Its real READY and the current planner's real expired response share the same
files and owner limits. No backup, recovery or systemd command is dispatched.
"""
import ast
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import threading
from types import SimpleNamespace

import pytest

import main_program_control_activation as subject
from test_main_program_control_environment import remote_functions
from test_main_program_control_generation_activation import inputs
import test_main_program_control_activation as original_activation_tests
from test_main_program_control_generation import case, successor, load, save, repin, physical_pin

TASK = Path(__file__).resolve().parent
REPO = TASK.parents[2]
sys.path.insert(0, str(REPO / 'scripts/tests'))
from test_automatic_incremental_plan import MetadataFixture, LocalNative, Ledger, handler, ui_request
from recovery_control_smallapp import persist, Failure
from recovery_control_executor import pin


@pytest.fixture(scope='module')
def old_planner():
    delta = json.loads((TASK / 'archive-catalogue-package-delta-r3.json').read_bytes())
    row = next(r for r in delta['packages'] if r['variant'] == 'standard')
    raw = Path(row['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row['packageSha256']
    with tarfile.open(row['path'], 'r:gz') as archive:
        member = archive.getmember('control/recovery_control_incremental_plan.py')
        source = archive.extractfile(member).read()
    scope = {'__name__': 'retained_45_planner_protocol'}
    exec(compile(source, row['path'] + '!/' + member.name, 'exec'), scope)
    return scope['build_plan']


def make_chain(tmp_path, old_planner, age=timedelta(days=2)):
    # Explicit source-id protocol seam. Native, epoch, pins and chain validation
    # remain the real implementations; this does not claim the production source.
    f = MetadataFixture(tmp_path, policy=dict(maxChainPoints=16, maxChainAgeSeconds=86400))
    f.enable_epoch(); f.epoch_event()
    now = datetime.now(timezone.utc)
    for index, ref in enumerate(('full-root', 'increment-one', 'increment-two')):
        finished = (now - age + timedelta(minutes=index)).isoformat().replace('+00:00', 'Z')
        f.point(ref, tuple(f.points), finished=finished)
        config=f.native.configuration(); operation=tmp_path/'epoch-publications'/ref
        operation.mkdir(parents=True)
        persist(operation/'selection.json',dict(sourceEpoch=f.native.source_epoch(config,'source-A')))
        binding=f.native.document(f.points[ref]['controlPin'])
        parent=None if index==0 else ('full-root','increment-one')[index-1]
        f.native.publish_point_epoch(ui_request(ref,parent=parent),operation,binding['resultPin'],config)
    config = f.native.configuration(); owner = f.native.document(config['sourceConfigurations']['source-A'])
    epoch = f.native.source_epoch(config, 'source-A')
    baseline = dict(sourceConfigRef='source-A', operationId='increment-two', generationId='full-root',
        chain=[dict(operationId=ref, pointType='FULL' if index == 0 else 'INCREMENTAL',
            pointPin=row['pointPin'], epochBindingPin=pin(tmp_path / 'registry/point-epochs' / (ref + '.json')))
            for index, (ref, row) in enumerate(f.points.items())])
    value = inputs('57', 'source')
    coverage = dict(schemaVersion='MainProgramControlCoverage/v2', profile='incremental-chain-policy-admission/v1')
    expected = dict(baseFullRef='full-root', parentChainRef='increment-two', generationId='full-root')
    before = old_planner(f.native, 'source-A')
    after = f.native.incremental_plan('source-A')
    assert before['state'] == 'READY' and all(before[k] == v for k, v in expected.items())
    assert (after['state'], after['reasonCode']) == (('BASELINE_REQUIRED', 'INCREMENTAL_CHAIN_AGE_EXPIRED')
        if age >= timedelta(days=1) else ('READY',None))
    root = f.native.document(f.points['full-root']['pointPin'])
    root_audit=dict(schemaVersion='AutomaticBackupChainAudit/v1',status='PASS',sourceConfigRef='source-A',
        operationId='full-root',generationId='full-root',pointType='FULL',state='SUCCEEDED',actualExitCode=0,
        sourceRestored=True,pointPin=baseline['chain'][0]['pointPin'],epochBindingPin=baseline['chain'][0]['epochBindingPin'],
        manifestPin=root['manifestPin'],parentPointPins=[],chain=baseline['chain'][:1])
    raw=subject.canonical(root_audit);(tmp_path/'automatic-full-audit.json').write_bytes(raw)
    root_audit_pin=dict(file='automatic-full-audit.json',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    transition = dict(profile=coverage['profile'], coveragePin=value['coveragePin'],
        sourceBaselinePin=value['sourceBaselinePin'], sourceConfigRef='source-A',
        sourceExpected=expected, chain=baseline['chain'], policy={k:owner[k] for k in ('maxChainPoints','maxChainAgeSeconds')},
        rootAuditPin=root_audit_pin,rootManifestPin=root['manifestPin'])
    proof = dict(transition=transition, rootManifestPin=root['manifestPin'],
        rootCreatedAt=f.native.document(root['manifestPin'])['createdAt'], reasonCode=after['reasonCode'], plan=after)
    candidate = dict(sourceCaptureVerified=True, epoch=epoch, sourcePolicyAdmission=proof)
    observed = dict(physicalLockVerified=True, sourcePlanBefore=before, sourcePlanBeforeLocked=before,
        candidateBefore=candidate, candidateAfter=deepcopy(candidate), sourcePlanAfter=after)
    return SimpleNamespace(f=f, value=value, coverage=coverage, owner=owner, baseline=baseline,
        transition=transition, expected=expected, old=before, new=after, epoch=epoch, proof=proof,
        observed=observed,root_audit=root_audit,root_audit_pin=root_audit_pin)


@pytest.fixture(scope='module')
def base_chain(tmp_path_factory, old_planner):
    return make_chain(tmp_path_factory.mktemp('actual-source-policy'),old_planner)


@pytest.fixture
def chain(base_chain, monkeypatch):
    monkeypatch.setattr(subject,'SOURCES',('source-A',*subject.SOURCES[1:]))
    before={p:p.read_bytes() for p in base_chain.f.root.rglob('*') if p.is_file()}
    yield deepcopy(base_chain)
    for path in base_chain.f.root.rglob('*'):
        if path.is_file() and path not in before:path.unlink()
    for path,raw in before.items():
        if not path.exists() or path.read_bytes()!=raw:path.write_bytes(raw)


@contextmanager
def native_http(h):
    authorization = 'Bearer ' + 'p' * 48
    credential = h.f.root / 'transport.json'
    credential.write_bytes(subject.canonical(dict(headers={'Authorization': authorization})))
    credential.chmod(0o600)
    config = dict(authCredentialRef=dict(path=str(credential), uid=0, gid=0, mode=0o600),
        allowedClientAddresses=['127.0.0.1'])
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler(Ledger(h.f.root/'ledger', h.f.native), config))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    def request(configuration, path, process):
        assert process['pid'] == 23
        client = HTTPConnection('127.0.0.1', server.server_port, timeout=10)
        try:
            client.request('GET', path, headers={'Authorization': authorization})
            response = client.getresponse(); assert response.status == 200
            return json.loads(response.read())
        finally: client.close()
    try: yield request
    finally: server.shutdown(); server.server_close(); thread.join(timeout=5)


def after_source_branch(scope):
    # Execute the actual post-switch branch, not a copied implementation. This
    # first fails at its existing READY requirement and remains identical GREEN.
    tree = ast.parse(subject.REMOTE_SCRIPT)
    candidates = [node for node in ast.walk(tree) if isinstance(node, ast.If) and
        any(isinstance(sub, ast.Assign) and any(isinstance(target, ast.Subscript) and
            isinstance(target.slice, ast.Constant) and target.slice.value == 'sourcePlanAfter'
            for target in sub.targets) for sub in node.body)]
    assert len(candidates) == 1
    exec(compile(ast.Module(body=candidates, type_ignores=[]), '<actual-new-api-branch>', 'exec'), scope)


def test_actual_post_switch_branch_accepts_only_proven_expired_candidate_over_real_http(chain):
    h = chain; scope = remote_functions()
    scope.update(SPEC=dict(sourceExpected=h.expected, sourcePolicyTransition=h.transition),
        SOURCES=subject.SOURCES, selected=dict(role='source'), new=dict(pid=23), control={},
        first=h.observed['candidateBefore'], out=deepcopy(h.observed))
    with native_http(h) as http:
        scope['http'] = http
        after_source_branch(scope)
    assert scope['out']['sourcePlanAfter'] == h.new
    assert scope['out']['sourceBaselineVerified'] is True


def candidate_function():
    tree = ast.parse(subject.CANDIDATE_GATE)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    scope = dict(json=json, hashlib=hashlib, re=re, sys=sys, pathlib=__import__('pathlib'),
        need=subject.need,canonical=subject.canonical)
    if hasattr(subject, 'SOURCE_POLICY_PROGRAM'):
        exec(subject.SOURCE_POLICY_PROGRAM,scope)
    exec(compile(ast.Module(body=functions, type_ignores=[]), '<actual-candidate-functions>', 'exec'), scope)
    return scope['source_policy_admission']


def test_real_candidate_uses_root_manifest_shared_policy_actual_native_and_epoch(chain):
    h = chain
    proof = candidate_function()(h.f.native, h.owner, deepcopy(h.owner), h.transition, h.epoch, str(REPO))
    assert proof == h.proof
    assert proof['rootManifestPin'] != h.f.native.document(h.f.points['increment-two']['pointPin'])['manifestPin']


@pytest.mark.parametrize('change', ['legacy-v1','legacy-v2','legacy-v3','legacy-coverage','profile','host','target'])
def test_transition_scope_cannot_be_selected_by_wrong_version_profile_or_role(chain, change):
    h = chain; value=deepcopy(h.value); coverage=deepcopy(h.coverage)
    if change.startswith('legacy-v'): value['schemaVersion']='MainProgramControlActivationInputs/'+change[7:]
    elif change=='legacy-coverage': coverage['schemaVersion']='MainProgramControlCoverage/v1'
    elif change=='profile': coverage['profile']='unapproved-policy'
    elif change=='host': value['suffix']='58'
    else: value['role']='target'
    assert subject.make_source_policy_transition(value, coverage, h.baseline, h.owner, h.owner) is None


def test_scope_is_derived_from_original_owner_and_audit_without_changing_them(chain):
    h=chain; original=deepcopy((h.value,h.coverage,h.baseline,h.owner))
    assert subject.make_source_policy_transition(*original,h.owner,
        root_audit=h.root_audit,root_audit_pin=h.root_audit_pin) == h.transition
    assert (h.value,h.coverage,h.baseline,h.owner)==original


@pytest.mark.parametrize('change', ['owner-limit','root-bytes','epoch-bytes','epoch-id','root-time','source','prefix','point-type'])
def test_candidate_refuses_changed_originals_before_dispatch(chain, change):
    h=chain; owner=deepcopy(h.owner); transition=deepcopy(h.transition); epoch=deepcopy(h.epoch)
    if change=='owner-limit': owner['maxChainAgeSeconds']*=10
    elif change=='root-bytes': Path(transition['chain'][0]['pointPin']['path']).write_bytes(b'{}')
    elif change=='epoch-bytes': Path(transition['chain'][1]['epochBindingPin']['path']).write_bytes(b'{}')
    elif change=='epoch-id': epoch['epochId']='0'*64
    elif change=='root-time':
        ref=h.proof['rootManifestPin']; value=h.f.native.document(ref); value['createdAt']='2999-01-01T00:00:00Z'
        Path(ref['path']).write_bytes(subject.canonical(value))
    elif change=='source': transition['sourceConfigRef']='other-source'
    elif change=='prefix': transition['chain'][1],transition['chain'][2]=transition['chain'][2],transition['chain'][1]
    else: transition['chain'][0]['pointType']='INCREMENTAL'
    expected=Failure if change in ('root-bytes','epoch-bytes','root-time') else (ValueError,AssertionError)
    pattern='NATIVE_PIN_CHANGED' if expected is Failure else 'SOURCE_POLICY_'
    with pytest.raises(expected,match=pattern):
        candidate_function()(h.f.native,owner,h.owner,transition,epoch,str(REPO))


@pytest.mark.parametrize('change', ['no-lock','no-locked-plan','locked-parent','old-not-ready','candidate-final',
    'http-plan','missing-proof','wrong-manifest','another-valid-manifest','wrong-policy','other-reason','point-limit',
    'blocked','unexpected-field','nonnull-parent','bad-digest'])
def test_frozen_proof_rejects_unproven_or_changed_transition(chain, change):
    h=chain; observed=deepcopy(h.observed)
    if change=='no-lock': observed['physicalLockVerified']=False
    elif change=='no-locked-plan': del observed['sourcePlanBeforeLocked']
    elif change=='locked-parent': observed['sourcePlanBeforeLocked']['parentChainRef']='another-point'
    elif change=='old-not-ready': observed['sourcePlanBefore']['state']='BLOCKED'
    elif change=='candidate-final': observed['candidateAfter']['epoch']['epochId']='0'*64
    elif change=='http-plan': observed['sourcePlanAfter']['evidenceDigest']='0'*64
    elif change=='missing-proof': del observed['candidateBefore']['sourcePolicyAdmission']
    else:
        proof=observed['candidateBefore']['sourcePolicyAdmission']
        if change=='wrong-manifest': proof['rootManifestPin']['bytes']=0
        elif change=='another-valid-manifest': proof['rootManifestPin']=h.f.native.document(h.f.points['increment-two']['pointPin'])['manifestPin']
        elif change=='wrong-policy': proof['transition']['policy']['maxChainAgeSeconds']+=1
        else:
            plan=proof['plan']
            if change=='other-reason': plan['reasonCode']='BINLOG_PARENT_PURGED'
            elif change=='point-limit': plan['reasonCode']='INCREMENTAL_CHAIN_POINT_LIMIT_REACHED'
            elif change=='blocked': plan['state']='BLOCKED'
            elif change=='unexpected-field': plan['accepted']=True
            elif change=='nonnull-parent': plan['parentChainRef']='increment-two'
            else: plan['planDigest']='0'*64
        observed['candidateAfter']=deepcopy(observed['candidateBefore'])
        observed['sourcePlanAfter']=deepcopy(proof['plan'])
    with pytest.raises(ValueError,match='SOURCE_POLICY_'):
        subject.validate_source_policy_transition(h.transition,observed)


def test_historical_proof_uses_frozen_evidence_without_current_native_or_wall_clock(chain):
    h=chain; before={p:p.read_bytes() for p in h.f.root.rglob('*') if p.is_file()}
    # Delete no originals. A historical reader receives only frozen values and
    # has no Native, file callback or clock parameter with which to replan.
    assert subject.validate_source_policy_transition(h.transition,h.observed) is None
    assert all(p.read_bytes()==raw for p,raw in before.items())


def test_unbound_valid_manifest_cannot_issue_a_historical_pass(chain):
    h=chain;transition=deepcopy(h.transition);observed=deepcopy(h.observed)
    for key in ('rootAuditPin','rootManifestPin'):transition.pop(key)
    proof=observed['candidateBefore']['sourcePolicyAdmission'];proof['transition']=transition
    proof['rootManifestPin']=h.f.native.document(h.f.points['increment-two']['pointPin'])['manifestPin']
    observed['candidateAfter']=deepcopy(observed['candidateBefore'])
    with pytest.raises(ValueError,match='SOURCE_POLICY_'):
        subject.validate_source_policy_transition(transition,observed)


def test_unexpired_original_chain_remains_ready_without_broadening_admission(tmp_path,old_planner,monkeypatch):
    monkeypatch.setattr(subject,'SOURCES',('source-A',*subject.SOURCES[1:]))
    h=make_chain(tmp_path,old_planner,age=timedelta(hours=1))
    actual=candidate_function()(h.f.native,h.owner,h.owner,h.transition,h.epoch,str(REPO))
    assert actual==h.proof and actual['plan']['state']=='READY'
    assert subject.validate_source_policy_transition(h.transition,h.observed) is None


def test_actual_candidate_helper_runs_in_a_separate_python_process(chain):
    h=chain
    code="""
import ast,json,pathlib,sys
sys.path.insert(0,sys.argv[1]);sys.path.insert(0,sys.argv[2])
import main_program_control_activation as subject
from test_automatic_incremental_plan import LocalNative
value=json.loads(sys.argv[3]);scope=vars(subject).copy();scope.update(sys=sys,pathlib=pathlib)
exec(subject.SOURCE_POLICY_PROGRAM,scope)
tree=ast.parse(subject.CANDIDATE_GATE)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'<candidate-gate>','exec'),scope)
native=LocalNative(value['configurationPin'])
proof=scope['source_policy_admission'](native,value['owner'],value['owner'],value['transition'],value['epoch'],value['engine'])
print(json.dumps(proof))
"""
    value=dict(configurationPin=h.f.native.config_pin,owner=h.owner,transition=h.transition,epoch=h.epoch,engine=str(REPO))
    result=subprocess.run([sys.executable,'-B','-X','utf8','-c',code,str(TASK),str(REPO/'scripts/tests'),
        subject.canonical(value).decode('utf-8')],capture_output=True,timeout=30)
    assert result.returncode==0,result.stderr.decode('utf-8','replace')
    assert json.loads(result.stdout)==h.proof


@pytest.mark.parametrize('missing',[False,True])
def test_new_profile_core_projection_consumes_real_plan_proof_not_only_flags(chain,missing):
    h=chain; fixture=original_activation_tests.CoreProjectionTests();fixture.setUp()
    spec=fixture.spec;observed=fixture.observed
    spec['inputs']=h.value;spec['selected']['role']='source';spec['sourcePolicyTransition']=h.transition
    spec['activationInputsPin']=dict(file='inputs.json',bytes=1,sha256='c'*64)
    observed.update(h.observed,host='172.30.30.57',sourceCaptureVerified=True,sourceBaselineVerified=True,
        activationInputsPin=spec['activationInputsPin'],**{k:h.value[k] for k in ('coveragePin','previousControlGenerationPin','revisionId')})
    if missing:
        del observed['sourcePlanBeforeLocked']
        with pytest.raises(ValueError,match='SOURCE_POLICY_'):subject.project_core(spec,observed)
    else:assert subject.project_core(spec,observed)['activeReceiptPin'] is None


def test_new_profile_generation_rejects_success_flags_without_source_policy_proof(case,monkeypatch):
    import main_program_control_generation as generation
    updated,previous=successor(case,monkeypatch)
    (updated['task']/'automatic-full-audit.json').write_bytes((TASK/'automatic-full-audit.json').read_bytes())
    ref=updated['value']['activationEvidenceByHost']['57'][1]
    rich=json.loads(Path(ref['path']).read_bytes());value=json.loads((updated['task']/rich['activationInputsPin']['file']).read_bytes())
    coverage=dict(schemaVersion='MainProgramControlCoverage/v2',profile='incremental-chain-policy-admission/v1')
    newpin=save(updated['task'],value['coveragePin']['file'],coverage)
    for rows in updated['value']['activationEvidenceByHost'].values():
        for index,reference in enumerate(rows):
            path=Path(reference['path']);item=json.loads(path.read_bytes())
            inputs_path=updated['task']/item['activationInputsPin']['file'];iv=json.loads(inputs_path.read_bytes());iv['coveragePin']=newpin
            item['activationInputsPin']=save(inputs_path.parent,inputs_path.name,iv);item['coveragePin']=newpin
            save(path.parent,path.name,item);rows[index]=physical_pin(path)
    repin(updated)
    # Explicit coverage protocol seam: this test exercises the generation->rich
    # boundary, not actual package coverage. Every local pin is still read.
    def coverage_boundary(records,private,inputs,build,prior,public,private_plan):
        assert records.pinned(inputs['coveragePin'])==coverage
        assert prior['generationPin']==previous['generationPin']
        return []
    monkeypatch.setattr(generation,'_validate_upgrade_materials',coverage_boundary)
    with pytest.raises(ValueError,match='SOURCE_POLICY_'):load(updated)


@pytest.mark.parametrize('change',['missing','operation','point','epoch','state','exit','chain'])
def test_root_audit_must_be_the_exact_original_full_of_the_pinned_i2_chain(chain,change):
    h=chain;root=deepcopy(h.root_audit)
    if change=='missing':root=None
    elif change=='operation':root['operationId']='other-full'
    elif change=='point':root['pointPin']=h.baseline['chain'][1]['pointPin']
    elif change=='epoch':root['epochBindingPin']=h.baseline['chain'][1]['epochBindingPin']
    elif change=='state':root['state']='FAILED_RETAINED'
    elif change=='exit':root['actualExitCode']=True
    else:root['chain']=h.baseline['chain']
    with pytest.raises(ValueError,match='SOURCE_POLICY_'):
        subject.make_source_policy_transition(h.value,h.coverage,h.baseline,h.owner,h.owner,
            root_audit=root,root_audit_pin=h.root_audit_pin)


def test_legacy_remote_gate_still_rejects_expired_plan_even_with_true_flags(chain):
    h=chain; scope=remote_functions()
    scope.update(SPEC=dict(sourceExpected=h.expected),SOURCES=subject.SOURCES,http=lambda *args:deepcopy(h.new))
    with pytest.raises(ValueError,match='SOURCE_BASELINE_CHANGED'):
        scope['source_plan']({}, {})


def test_source_program_input_files_remain_outside_this_installer_change():
    # Installer-only wiring never dispatches a backup or synthesizes a new FULL.
    assert 'native.incremental_plan(' not in subject.SOURCE_IDLE
    compile(subject.CANDIDATE_GATE,'<candidate>','exec')
    compile(subject.REMOTE_SCRIPT,'<activation>','exec')
