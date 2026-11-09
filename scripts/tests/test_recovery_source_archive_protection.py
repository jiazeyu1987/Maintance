"""Source-selected archive protection and original MAIN custody contracts.

The small factory/lifecycle cases use real private files and explicit mount
observation/command protocols. The producer cases retain the actual worker,
program/runtime/context/custody/epoch, SQL processes and historical validator.
Their external Docker/SQL/object/kernel semantics remain finite protocols:
actualBusinessRestore=False. Real kernel remount/stacked-mount behavior belongs
to the separate privileged Linux archive-view suite, not these observations.
"""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from test_recovery_program_generation import case
import test_recovery_program_restore as restore_fixture
from test_recovery_program_producer_contract import producer_case, invoke, receipt_and_native, validate as history
from recovery_engine import RecoveryError, digest, pin, pinned_json
from recovery_archive_view import ArchiveViewProtection
import recovery_main_target as main


pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'),
    reason='actual Linux private files/flock/context and MAIN producer protocols')


def archive_configuration(root, name, *, readonly=False):
    view = root/name; view.mkdir(mode=0o700)
    (view/'archives').mkdir(mode=0o700)
    programs = root/(name+'-programs'); programs.mkdir(mode=0o700)
    program = programs/'mount'; program.write_bytes(b'private source mount protocol\n'); program.chmod(0o700)
    mount = dict(mountId=10 if name == 'target-view' else 11, parentId=1, device='0:12', root='/',
        mountPoint=str(view), filesystem='cifs', source='//protocol/'+name,
        options=['ro' if readonly else 'rw','relatime'], superOptions=['rw'])
    return dict(schemaVersion='RegisteredArchiveViewProtection/v2' if readonly else
        'RegisteredArchiveViewProtection/v1', mountIdentity=mount, mountProgramPin=pin(program))


@pytest.fixture
def selection(tmp_path):
    target_view = archive_configuration(tmp_path,'target-view')
    source_view = archive_configuration(tmp_path,'source-view')
    state = tmp_path/'state'; state.mkdir(mode=0o700)
    data = tmp_path/'data'; data.mkdir(mode=0o700)
    commands = []
    target = dict(mainApplication=dict(archiveMountProtection=target_view), dataPaths=[str(data)],
        replacement=dict(stateRoot=str(state), storage=dict(preservedApplicationMounts=[])))
    source = dict(archiveRoots=[str(Path(target_view['mountIdentity']['mountPoint'])/'archives')])
    native = SimpleNamespace(config=target, source=source, original=dict(operationId='source-view-case'),
        command=lambda argv,**kwargs:commands.append((argv,kwargs)))
    return SimpleNamespace(native=native,target=target,source=source,target_view=target_view,
        source_view=source_view,commands=commands)


def test_explicit_source_selects_its_own_view_and_leaves_target_original_unchanged(selection):
    """BDD: old target A, explicit selected source B -> choose B without rewriting A."""
    h=selection; before=deepcopy(h.target)
    h.source.update(archiveMountProtection=h.source_view,
        archiveRoots=[str(Path(h.source_view['mountIdentity']['mountPoint'])/'archives')])
    protection=main.archive_view(h.native)
    assert protection.configuration == h.source_view
    assert protection.configuration != h.target_view
    assert h.target == before and not h.commands


@pytest.mark.parametrize('target_present',[True,False])
def test_explicit_null_source_protection_is_rejected_without_legacy_or_absent_fallback(selection,target_present):
    """BDD: an explicit invalid source selection never becomes a legacy/absent protection."""
    h=selection
    if not target_present: h.target['mainApplication'].pop('archiveMountProtection')
    h.source['archiveMountProtection']=None
    with pytest.raises(RecoveryError,match='ARCHIVE_VIEW_CONFIGURATION_INVALID'):
        main.archive_view(h.native)
    assert not h.commands


@pytest.mark.parametrize('scope',['uncovered-root','empty-roots','data-overlap','preserved-application-overlap'])
def test_explicit_source_must_cover_every_root_and_stay_disjoint_from_business_storage(selection,scope):
    h=selection; point=Path(h.source_view['mountIdentity']['mountPoint'])
    h.source.update(archiveMountProtection=h.source_view,archiveRoots=[str(point/'archives')])
    if scope=='uncovered-root': h.source['archiveRoots'].append(str(Path(h.target_view['mountIdentity']['mountPoint'])/'archives'))
    elif scope=='empty-roots': h.source['archiveRoots']=[]
    elif scope=='data-overlap': h.target['dataPaths']=[str(point/'database')]
    else: h.target['replacement']['storage']['preservedApplicationMounts']=[dict(mount=dict(Source=str(point/'application')))]
    with pytest.raises(RecoveryError,match='ARCHIVE_VIEW_SCOPE_INVALID'):
        main.archive_view(h.native)
    assert not h.commands


def test_explicit_source_allows_exact_view_root_but_legacy_target_keeps_strict_descendant_rule(selection):
    """BDD: source's explicit root may be its mount; old target-only scope is unchanged."""
    h=selection
    h.source.update(archiveMountProtection=h.source_view,
        archiveRoots=[h.source_view['mountIdentity']['mountPoint']])
    assert main.archive_view(h.native).configuration == h.source_view
    h.source.pop('archiveMountProtection')
    h.source['archiveRoots']=[h.target_view['mountIdentity']['mountPoint']]
    with pytest.raises(RecoveryError,match='ARCHIVE_VIEW_SCOPE_INVALID'):
        main.archive_view(h.native)


def test_missing_source_field_preserves_legacy_target_selection_and_absence(selection):
    h=selection
    assert main.archive_view(h.native).configuration == h.target_view
    h.target['mainApplication'].pop('archiveMountProtection')
    assert main.archive_view(h.native) is None
    assert not h.commands


def test_permanent_readonly_lifecycle_records_original_identity_without_any_remount(tmp_path,monkeypatch):
    """BDD: explicit permanent RO identity -> complete install/verify/release, zero transport."""
    config=archive_configuration(tmp_path,'source-view',readonly=True)
    original=deepcopy(config); observed=deepcopy(config['mountIdentity']); commands=[]
    monkeypatch.setattr(ArchiveViewProtection,'_observed',lambda _:deepcopy(observed))
    protection=ArchiveViewProtection(config,'permanent-ro',tmp_path/'journal',
        lambda argv,**kwargs:commands.append((argv,kwargs)))
    protection.preflight(); protection.install(); protection.verify()
    released=protection.release()
    intent=pinned_json(pin(protection.journal/'intent.json'))
    active=pinned_json(pin(protection.journal/'active.json'))
    terminal=pinned_json(released)
    assert intent['schemaVersion']=='ArchiveViewProtectionIntent/v1'
    assert active['schemaVersion']=='ArchiveViewProtectionActive/v1'
    assert terminal['schemaVersion']=='ArchiveViewProtectionRelease/v1'
    assert intent['operationId']==active['operationId']==terminal['operationId']=='permanent-ro'
    assert intent['configurationDigest']==active['configurationDigest']==digest(original)
    assert active['observedMountDigest']==digest(original['mountIdentity'])
    assert terminal['originalMountRestored'] is True
    assert config==original and observed==original['mountIdentity'] and not commands


@pytest.mark.parametrize('drift',['became-writable','different-mount','different-source'])
def test_permanent_readonly_drift_never_remounts_or_publishes_release(tmp_path,monkeypatch,drift):
    config=archive_configuration(tmp_path,'source-view',readonly=True)
    observed=deepcopy(config['mountIdentity']); commands=[]
    monkeypatch.setattr(ArchiveViewProtection,'_observed',lambda _:deepcopy(observed))
    protection=ArchiveViewProtection(config,'permanent-ro-drift',tmp_path/'journal',
        lambda argv,**kwargs:commands.append((argv,kwargs)))
    protection.install()
    if drift=='became-writable': observed['options']=['rw','relatime']
    elif drift=='different-mount': observed['mountId']+=1
    else: observed['source']='//protocol/changed'
    with pytest.raises(RecoveryError,match='ARCHIVE_VIEW_CHANGED'): protection.verify()
    with pytest.raises(RecoveryError,match='ARCHIVE_VIEW_CHANGED'): protection.release()
    assert not commands and not (protection.journal/'released.json').exists()


@pytest.mark.parametrize('version,readonly',[('v1',True),('v2',False)])
def test_archive_view_version_never_relaxes_original_rw_or_permanent_ro_mode(tmp_path,version,readonly):
    config=archive_configuration(tmp_path,'source-view',readonly=readonly)
    config['schemaVersion']='RegisteredArchiveViewProtection/'+version
    with pytest.raises(RecoveryError,match='ARCHIVE_VIEW_CONFIGURATION_INVALID'):
        ArchiveViewProtection(config,'bad-mode',tmp_path/'journal',lambda *_args,**_kwargs:None)


@pytest.fixture
def source_archive_producer(case,monkeypatch,request):
    """Seal source protection before initial owner/reservation, never repin live originals."""
    version=request.param
    original_freeze=restore_fixture.freeze_inputs
    def freeze_with_explicit_source(h):
        assert not (h.root/'configuration.json').exists()
        target_before=deepcopy(h.owner['targets'])
        source_protection=deepcopy(h.owner['targets']['target57']['mainApplication']['archiveMountProtection'])
        programs=h.case['root']/'source-protection-programs'; programs.mkdir(mode=0o700)
        program=programs/'mount'; program.write_bytes(b'original source-only mount program\n'); program.chmod(0o700)
        source_protection['mountProgramPin']=pin(program)
        source_protection['schemaVersion']='RegisteredArchiveViewProtection/'+version
        if version=='v2':
            source_protection['mountIdentity']['options']=['ro','relatime']
            h.transport.mount=deepcopy(source_protection['mountIdentity'])
        h.source['archiveMountProtection']=source_protection
        h.source_protection=deepcopy(source_protection)
        original_freeze(h)
        assert h.owner['targets']==target_before
    monkeypatch.setattr(restore_fixture,'freeze_inputs',freeze_with_explicit_source)
    h=restore_fixture.restore_case.__wrapped__(case,monkeypatch)
    return producer_case.__wrapped__(h,monkeypatch)


@pytest.mark.parametrize('source_archive_producer',['v1','v2'],indirect=True,ids=['source-rw','source-permanent-ro'])
@pytest.mark.parametrize('outcome',['success','restore-failure'])
def test_real_main_producer_keeps_selected_source_custody_across_stage_and_history(source_archive_producer,outcome):
    """BDD: real MAIN stage/result -> original selected-source protection/pins survive success or failure."""
    h=source_archive_producer
    target=h.owner['targets']['target57']; original_target=deepcopy(target)
    if outcome=='restore-failure': h.fail='objects'
    actual_exit,result=invoke(h)
    assert actual_exit==(0 if outcome=='success' else 1)
    assert result['state']==('SUCCEEDED' if outcome=='success' else 'FAILED_RETAINED')
    receipt,native=receipt_and_native(h,result)
    custody=pinned_json(result['data']['programProtectionCustodyPin'])
    assert native['phase']=='RESTORE' and len(h.natives)==2
    assert h.natives[0].protection_custody is h.natives[1].protection_custody
    assert h.natives[0].source['archiveMountProtection']==h.natives[1].source['archiveMountProtection']==h.source_protection
    assert custody['protections']['archive']['state']==('RELEASED' if outcome=='success' else 'INSTALLED')
    assert h.source_protection['mountProgramPin'] in custody['originalResultPins']
    assert target['mainApplication']['archiveMountProtection']['mountProgramPin'] not in custody['originalResultPins']
    intent=pinned_json(pin(h.claim/'archive-view/intent.json'))
    active=pinned_json(pin(h.claim/'archive-view/active.json'))
    assert intent['configurationDigest']==active['configurationDigest']==digest(h.source_protection)
    mounts=[row for row in h.transport.calls if row[0]=='command' and Path(row[2][0]).name=='mount']
    if h.source_protection['schemaVersion'].endswith('/v2'):
        assert not mounts and h.transport.mount==h.source_protection['mountIdentity']
    else:
        assert [row[2][4] for row in mounts]==(['remount,bind,ro','remount,bind,rw'] if outcome=='success' else ['remount,bind,ro'])
        assert all(row[2][0]==h.source_protection['mountProgramPin']['path'] for row in mounts)
    proof=history(h)
    assert proof['resultState']==result['state'] and proof['replacementState']==receipt['state']
    assert proof['protectionStates']['archive']['state']==custody['protections']['archive']['state']
    assert h.owner['targets']['target57']==original_target and h.actualBusinessRestore is False
    # Read the real successful/retained history, then corrupt only the selected
    # source program original. No envelope or replacement original is rewritten.
    selected=Path(h.source_protection['mountProgramPin']['path'])
    selected.write_bytes(selected.read_bytes()+b'changed source program\n')
    with pytest.raises(RecoveryError): history(h)
