"""Program derivation: injected mapping units and separate Linux physical-file tests."""
from copy import deepcopy
import hashlib
import importlib
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops/recovery'))
from recovery_program_generation import document, _capture_transition, _target_transition
from recovery_engine import RecoveryError
from test_recovery_program_generation import case, switched, write


def module():
    return importlib.import_module('recovery_program_derivation')


def test_mapping_unit_exact_full_short_image_and_original_unchanged():
    from recovery_program_generation import _mapped, _program_replacements
    before = {'backend': {'id':'a'*64, 'imageId':'sha256:'+'1'*64},
              'frontend': {'id':'b'*64, 'imageId':'sha256:'+'2'*64}}
    after = {'backend': {'id':'c'*64, 'imageId':'sha256:'+'3'*64},
             'frontend': {'id':'d'*64, 'imageId':'sha256:'+'4'*64}}
    original = {'a'*12:['a'*64, 'sha256:'+'1'*64, 'prefix-'+'a'*64]}
    result = _mapped(original, _program_replacements(before, after))
    assert result == {'c'*12:['c'*64, 'sha256:'+'3'*64, 'prefix-'+'a'*64]}
    assert original == {'a'*12:['a'*64, 'sha256:'+'1'*64, 'prefix-'+'a'*64]}


def test_mapping_unit_ambiguous_short_id_and_image_mappings_are_rejected():
    from recovery_program_generation import _program_replacements
    before = {'backend': {'id':'a'*64, 'imageId':'sha256:'+'1'*64},
              'frontend': {'id':'a'*12+'b'*52, 'imageId':'sha256:'+'2'*64}}
    after = {'backend': {'id':'c'*64, 'imageId':'sha256:'+'3'*64},
             'frontend': {'id':'d'*64, 'imageId':'sha256:'+'4'*64}}
    with pytest.raises(Exception, match='PROGRAM_MAPPING_CONFLICT'):
        _program_replacements(before, after)
    before['frontend']['id'] = 'b'*64
    before['frontend']['imageId'] = before['backend']['imageId']
    with pytest.raises(Exception, match='PROGRAM_MAPPING_CONFLICT'):
        _program_replacements(before, after)


def test_mapping_unit_cannot_silently_drop_colliding_json_keys():
    from recovery_program_generation import _mapped
    with pytest.raises(RecoveryError,match='PROGRAM_MAPPING_CONFLICT'):
        _mapped({'old':'one','new':'two'},{'old':'new'})


def raw_pin(path, data):
    path.write_bytes(data)
    path.chmod(0o600)
    return dict(path=path.as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


@pytest.fixture
def physical(case, tmp_path):
    if not sys.platform.startswith('linux'):
        pytest.skip('Physical derivation contract requires actual Linux flock and dir_fd')
    import fcntl
    expected_target, _, switch = switched(case, tmp_path)
    contents = {'d'*12: ['d'*64, case['target']['services'][3]['imageId'],
                         'literal-prefix-'+'d'*64], 'frontend':'e'*12}
    config = write(tmp_path/'configuration.json', contents)
    material = write(tmp_path/'material.json', dict(program='e'*64, alias='e'*12))
    raw = raw_pin(tmp_path/'unchanged.env', b'PORT=48081\nMODE=production\n')
    case['capture']['source']['configurationPins'] = [dict(kind='configuration',reference=config),
                                                    dict(kind='environment',reference=raw)]
    case['capture']['source']['materialPins'] = [dict(kind='material',reference=material)]
    versions = write(tmp_path/'versions.json', dict(images={s['role']:s['imageId'] for s in case['target']['services']},
                                                  aliases=['d'*12, 'e'*12]))
    objects = write(tmp_path/'objects.json', dict(sourceIdentity=case['epoch']['sourceIdentity'],versionPins=[versions]))
    case['capture']['source']['objectSourcePin'] = objects
    case['base_pin'] = write(tmp_path/'capture.json', case['capture'])
    case['policy']['captureConfigurationPins']['source57'] = case['base_pin']
    lock_path = Path(case['epoch']['sourceLockPath'])
    lock_path.touch(mode=0o600)
    lock_path.chmod(0o600)
    fd = os.open(lock_path, os.O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    claim = Path(case['target']['replacement']['stateRoot'])/'restore-1'
    claim.mkdir(mode=0o700)
    original_files = {p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    case.update(expected_target=expected_target,switch=switch,fd=fd,claim=claim,
                original_files=original_files,raw_pin=raw)
    try:
        yield case
    finally:
        os.close(fd)


def derive(real, **changes):
    arguments = dict(policy=real['policy'], previous_target=real['target'],switch_pin=real['switch'],
                     operation_id='restore-1',claim=real['claim'],lock_fd=real['fd'])
    arguments.update(changes)
    return module().derive(**arguments)


def assert_originals(real):
    assert all(path.read_bytes() == data for path,data in real['original_files'].items())


def test_linux_derives_strict_target_capture_and_only_exact_recursive_materials(physical):
    result = derive(physical)
    target = document(result['targetPin'])
    expected = deepcopy(physical['expected_target'])
    expected['mainApplication']['writerAdmission']['evidencePin'] = target['mainApplication']['writerAdmission']['evidencePin']
    assert target == expected
    binding = result['captureBindings']['source57']
    assert binding['baseCapturePin'] == physical['base_pin']
    capture = document(binding['capturePin'])
    source = capture['source']
    mapped = document(source['configurationPins'][0]['reference'])
    assert mapped['6'*12] == ['6'*64, target['services'][3]['imageId'],'literal-prefix-'+'d'*64]
    assert mapped['frontend'] == '7'*12
    assert source['configurationPins'][1]['reference'] == physical['raw_pin']
    assert document(source['materialPins'][0]['reference']) == dict(program='7'*64,alias='7'*12)
    objects = document(source['objectSourcePin'])
    assert document(objects['versionPins'][0])['aliases'] == ['6'*12,'7'*12]
    _target_transition(physical['target'],target,physical['switch'],'restore-1',document)
    _capture_transition(physical['capture'],capture,physical['target'],target,'source57',physical['epoch'],document)
    assert physical['switch'] in result['evidencePins']
    assert physical['base_pin'] in result['evidencePins']
    for reference in [result['targetPin'], binding['capturePin']]:
        path = Path(reference['path'])
        assert path.is_relative_to(physical['claim']) and path.stat().st_mode & 0o777 == 0o600
    assert_originals(physical)


def test_linux_short_id_cannot_remain_stale_or_map_to_another_role(physical):
    result = derive(physical)
    target = document(result['targetPin'])
    active = document(result['captureBindings']['source57']['capturePin'])
    version = document(document(active['source']['objectSourcePin'])['versionPins'][0])
    assert version['aliases'] == ['6'*12, '7'*12]
    for invalid in ('d'*12, '7'*12):
        changed = deepcopy(active)
        version['aliases'][0] = invalid
        version_pin = write(physical['root']/('bad-version-'+invalid+'.json'), version)
        objects = document(active['source']['objectSourcePin'])
        objects['versionPins'] = [version_pin]
        changed['source']['objectSourcePin'] = write(physical['root']/('bad-object-'+invalid+'.json'), objects)
        with pytest.raises(Exception, match='PROGRAM_CAPTURE_SCOPE_CHANGED'):
            _capture_transition(physical['capture'],changed,physical['target'],target,'source57',physical['epoch'],document)
    assert_originals(physical)


def test_linux_no_switch_retains_target_and_unmodified_capture_pins(physical):
    result = derive(physical,switch_pin=None)
    assert document(result['targetPin']) == physical['target']
    binding = result['captureBindings']['source57']
    assert binding['capturePin'] == physical['base_pin']
    assert_originals(physical)


def test_linux_later_generation_always_maps_original_capture_to_current_program(physical):
    first = derive(physical)
    active = document(first['targetPin'])
    second_claim = physical['claim'].parent/'restore-2';second_claim.mkdir(mode=0o700)
    second = derive(physical,previous_target=active,switch_pin=None,
                    operation_id='restore-2',claim=second_claim)
    assert document(second['targetPin']) == active
    capture = document(second['captureBindings']['source57']['capturePin'])
    assert capture['source']['writerContainerIds'] == ['6'*64,'7'*64]
    assert '6'*12 in document(capture['source']['configurationPins'][0]['reference'])
    assert_originals(physical)


@pytest.mark.parametrize('bad', ['unlocked','wrong-lock'])
def test_linux_requires_actual_exclusive_source_lock(physical,bad):
    import fcntl
    if bad == 'unlocked':
        fcntl.flock(physical['fd'],fcntl.LOCK_UN)
        fd = physical['fd']
    else:
        path = physical['root']/'other.lock'; path.touch(mode=0o600)
        fd = os.open(path,os.O_RDWR)
        fcntl.flock(fd,fcntl.LOCK_EX)
    try:
        with pytest.raises(Exception, match='BACKUP_EPOCH_(EXCLUSIVE_LOCK_REQUIRED|SOURCE_LOCK_MISMATCH)'):
            derive(physical,lock_fd=fd)
        assert list(physical['claim'].iterdir()) == []
    finally:
        if fd != physical['fd']: os.close(fd)


@pytest.mark.parametrize('bad', ['outside','missing','alias'])
def test_linux_claim_must_be_exact_private_operation_directory(physical,bad):
    if bad == 'outside':
        claim = physical['root']/'wrong';claim.mkdir(mode=0o700)
    elif bad == 'missing':
        claim = physical['claim'];claim.rmdir()
    else:
        claim = physical['root']/'alias';claim.symlink_to(physical['claim'],target_is_directory=True)
    with pytest.raises(Exception, match='PROGRAM_DERIVATION_CLAIM_INVALID|BACKUP_EPOCH_PATH_ALIAS_REJECTED'):
        derive(physical,claim=claim)
    assert_originals(physical)


def test_linux_duplicate_derivation_never_replaces_published_documents(physical):
    result = derive(physical)
    before = {p:p.read_bytes() for p in physical['claim'].rglob('*') if p.is_file()}
    with pytest.raises(Exception, match='PROGRAM_DERIVATION_EXISTS'):
        derive(physical)
    assert all(path.read_bytes() == raw for path,raw in before.items())
    assert document(result['targetPin'])
    assert_originals(physical)


@pytest.mark.parametrize('field', ['operation','original','mount','port','retained'])
def test_linux_switch_proof_cannot_bypass_strict_container_contract(physical,field):
    switch = document(physical['switch'])
    if field == 'operation':
        switch['operationId'] = 'other'
    else:
        item = document(switch['applicationPins']['backend'])
        if field == 'original': item['original']['Id'] = '8'*64
        elif field == 'mount': item['created']['Mounts'] = []
        elif field == 'port': item['created']['HostConfig']['PortBindings'] = {}
        else: item['retained']['Config']['Env'].append('UNAPPROVED=value')
        switch['applicationPins']['backend'] = write(physical['root']/('invalid-application-'+field+'.json'),item)
    switch_pin = write(physical['root']/('invalid-switch-'+field+'.json'),switch)
    with pytest.raises((RecoveryError,ValueError),match='PROGRAM_'):
        derive(physical,switch_pin=switch_pin)
    assert list(physical['claim'].iterdir()) == []
    assert_originals(physical)


@pytest.mark.parametrize('field', ['source','database','lock','mysql','credential'])
def test_linux_baseline_capture_cannot_reassign_source_scope(physical,field):
    base = deepcopy(physical['capture'])
    if field == 'source':base['source']['sourceIdentity'] = 'other'
    elif field == 'database':base['source']['database'] = 'other'
    elif field == 'lock':base['sourceLockPath'] = '/other.lock'
    elif field == 'mysql':base['source']['mysqlContainerId'] = '8'*64
    else:base['extraCredential'] = 'unregistered'
    base_pin = write(physical['root']/'invalid-capture.json',base)
    policy = deepcopy(physical['policy']);policy['captureConfigurationPins']['source57'] = base_pin
    # Extra baseline data is preserved exactly; only physical-scope changes fail.
    if field == 'credential':
        result = derive(physical,policy=policy)
        assert document(result['captureBindings']['source57']['capturePin'])['extraCredential'] == 'unregistered'
    else:
        with pytest.raises(Exception, match='PROGRAM_CAPTURE_SCOPE_CHANGED'):
            derive(physical,policy=policy)
        assert list(physical['claim'].iterdir()) == []
    assert_originals(physical)


def test_linux_unknown_raw_format_requiring_id_replacement_fails_before_writes(physical):
    base = deepcopy(physical['capture'])
    raw = raw_pin(physical['root']/'requires-map.env', ('CONTAINER='+'d'*64+'\n').encode('ascii'))
    base['source']['materialPins'].append(dict(kind='environment',reference=raw))
    policy = deepcopy(physical['policy'])
    policy['captureConfigurationPins']['source57'] = write(physical['root']/'raw-capture.json',base)
    with pytest.raises(Exception, match='PROGRAM_MATERIAL_FORMAT_UNSUPPORTED'):
        derive(physical,policy=policy)
    assert list(physical['claim'].iterdir()) == []
    assert_originals(physical)


def test_linux_pin_drift_is_rejected_before_publishing(physical):
    reference = physical['capture']['source']['configurationPins'][0]['reference']
    Path(reference['path']).write_bytes(b'{}')
    with pytest.raises(Exception,match='PROGRAM_DOCUMENT_CHANGED'):
        derive(physical)
    assert list(physical['claim'].iterdir()) == []


def test_linux_shared_guard_can_abort_before_any_output(physical):
    def guard(): raise TimeoutError('derivation shared budget expired')
    with pytest.raises(TimeoutError,match='derivation shared budget expired'):
        derive(physical,guard=guard)
    assert list(physical['claim'].iterdir()) == []
    assert_originals(physical)


def test_linux_original_target_and_capture_objects_are_not_mutated(physical):
    before = deepcopy((physical['target'],physical['capture'],physical['policy']))
    derive(physical)
    assert (physical['target'],physical['capture'],physical['policy']) == before
    assert_originals(physical)


def test_linux_output_integrity_boundary_rechecks_earlier_files_before_return(physical):
    changed = []
    def guard():
        files = sorted((physical['claim']/'program-derived').glob('*.json'))
        if len(files) >= 2 and files[0].stat().st_size and not changed:
            files[0].write_bytes(b'{}')
            changed.append(files[0])
    with pytest.raises(RecoveryError,match='PROGRAM_DERIVATION_OUTPUT_CHANGED'):
        derive(physical,guard=guard)
    assert changed
    assert changed[0].read_bytes() == b'{}'
    assert_originals(physical)


def test_linux_raw_integrity_boundary_refuses_unknown_non_utf8_identity_encoding(physical):
    base = deepcopy(physical['capture'])
    raw = raw_pin(physical['root']/'utf16.env', ('CONTAINER='+'d'*64+'\n').encode('utf-16-le'))
    base['source']['materialPins'].append(dict(kind='environment',reference=raw))
    policy = deepcopy(physical['policy'])
    policy['captureConfigurationPins']['source57'] = write(physical['root']/'utf16-capture.json',base)
    with pytest.raises(RecoveryError,match='PROGRAM_MATERIAL_FORMAT_UNSUPPORTED'):
        derive(physical,policy=policy)
    assert list(physical['claim'].iterdir()) == []
    assert_originals(physical)
