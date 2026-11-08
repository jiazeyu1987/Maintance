"""Derive private program documents inside one already-owned restore claim.

The caller supplies the independently verified active target and holds its real
source flock. This module neither selects an epoch nor changes containers or
registered originals. All proofs and proposed values are checked before the
first exclusive output publication; a partial publication remains blocked.
"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
import stat

from recovery_backup_epoch import _assert_lock, _parse, _path, _read_file
from recovery_engine import RecoveryError, canonical, require
from recovery_program_generation import (APPLICATIONS, _capture_transition,
    _mapped, _pin, _program_replacements, _services, _target_value, document,
    validate_policy)


OUTPUT_DIRECTORY = 'program-derived'
DOCUMENT_LIMIT = 4*1024*1024


def _private_directory(path):
    info = path.stat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and
            not info.st_mode & 0o077, 'PROGRAM_DERIVATION_CLAIM_INVALID')
    return info


def _same_directory(path, descriptor):
    observed, opened = _private_directory(_path(str(path))), os.fstat(descriptor)
    require((observed.st_dev, observed.st_ino) == (opened.st_dev, opened.st_ino),
            'PROGRAM_DERIVATION_CLAIM_CHANGED')


def _derive(policy, previous_target, switch_pin, operation_id, claim, lock_fd, reader, guard):
    def held():
        guard()
        _assert_lock(policy['backupEpochPolicy'], lock_fd)

    guard()
    validate_policy(policy)
    held()
    require(type(operation_id) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}', operation_id),
            'PROGRAM_DERIVATION_OPERATION_INVALID')
    epoch = policy['backupEpochPolicy']
    require(previous_target['replacement']['lockPath'] == epoch['sourceLockPath'] and
            previous_target['replacement']['databaseUuid'] == epoch['databaseUuid'],
            'PROGRAM_DERIVATION_TARGET_SCOPE_CHANGED')
    root = _path(previous_target['replacement']['stateRoot'])
    claim = _path(str(claim))
    require(claim == root/operation_id and claim.is_dir(), 'PROGRAM_DERIVATION_CLAIM_INVALID')
    _private_directory(root); _private_directory(claim)
    output_root = claim/OUTPUT_DIRECTORY
    require(not output_root.exists(), 'PROGRAM_DERIVATION_EXISTS')
    inputs = {}; staged = {}; evidence = []; seen = {}

    def register(reference, *, physical):
        guard(); _pin(reference)
        key = Path(reference['path']).as_posix()
        require(key not in seen or seen[key] == reference, 'PROGRAM_DOCUMENT_PIN_CONFLICT')
        if key not in seen:
            seen[key] = deepcopy(reference); evidence.append(deepcopy(reference))
        if physical:
            inputs[key] = deepcopy(reference)
        return key

    def raw(reference):
        register(reference, physical=True)
        value, observed = _read_file(reference['path'], DOCUMENT_LIMIT)
        require(observed == dict(reference, path=Path(reference['path']).as_posix()), 'PROGRAM_DOCUMENT_CHANGED')
        guard()
        return value

    def read(reference):
        key = register(reference, physical=False)
        if key in staged:
            require(staged[key]['pin'] == reference, 'PROGRAM_DOCUMENT_PIN_CONFLICT')
            return deepcopy(staged[key]['value'])
        # Even an injected custody reader cannot replace physical pin checks.
        raw(reference)
        value = reader(reference)
        guard()
        return value

    def stage(label, value):
        guard()
        encoded = canonical(value)
        require(0 < len(encoded) <= DOCUMENT_LIMIT, 'PROGRAM_DERIVATION_DOCUMENT_LIMIT')
        path = output_root/('%04d-%s.json' % (len(staged), label))
        pin = dict(path=path.as_posix(), bytes=len(encoded), sha256=hashlib.sha256(encoded).hexdigest())
        require(pin['path'] not in staged, 'PROGRAM_DERIVATION_EXISTS')
        staged[pin['path']] = dict(pin=pin, value=deepcopy(value), raw=encoded)
        return pin

    def material(reference, replacements, label, *, allow_raw):
        encoded = raw(reference)
        try:
            parsed = _parse(encoded)
        except ValueError:
            changes = {old:new for old,new in replacements.items() if old != new}
            try:
                text = encoded.decode('utf-8')
            except UnicodeError:
                require(allow_raw and not changes, 'PROGRAM_MATERIAL_FORMAT_UNSUPPORTED')
                return deepcopy(reference)
            # UTF-16 ASCII can also decode as UTF-8 containing NUL bytes. It
            # is not a proved UTF-8 environment; do not mistake that for an
            # absence of old program IDs or guess another configuration codec.
            require(not changes or '\0' not in text, 'PROGRAM_MATERIAL_FORMAT_UNSUPPORTED')
            needs_mapping = any(old in text for old in changes)
            require(allow_raw and not needs_mapping, 'PROGRAM_MATERIAL_FORMAT_UNSUPPORTED')
            return deepcopy(reference)
        actual = read(reference)
        require(actual == parsed, 'PROGRAM_DOCUMENT_CHANGED')
        mapped = _mapped(actual, replacements)
        return deepcopy(reference) if mapped == actual else stage(label, mapped)

    baseline = read(policy['baselineTargetPin'])
    require(baseline['replacement']['databaseUuid'] == epoch['databaseUuid'] and
            baseline['replacement']['lockPath'] == epoch['sourceLockPath'] and
            baseline['replacement']['stateRoot'] == previous_target['replacement']['stateRoot'],
            'PROGRAM_DERIVATION_TARGET_SCOPE_CHANGED')
    writer = previous_target['mainApplication']['writerAdmission']['evidencePin']
    if switch_pin is not None:
        switch = read(switch_pin)
        require(switch.get('schemaVersion') == 'MainProgramSwitchResult/v1' and
                switch.get('state') == 'CREATED_STOPPED' and switch.get('operationId') == operation_id and
                set(switch.get('applicationPins', {})) == APPLICATIONS, 'PROGRAM_SWITCH_PROOF_INVALID')
        before = _services(previous_target); after = deepcopy(before)
        for role in sorted(APPLICATIONS):
            proof = read(switch['applicationPins'][role])
            after[role].update(id=proof['created']['Id'],imageId=proof['created']['Image'])
        replacements = _program_replacements(before, after)
        writer_value = read(writer); mapped_writer = _mapped(writer_value, replacements)
        if mapped_writer != writer_value:
            writer = stage('writer-evidence', mapped_writer)
    target = _target_value(previous_target, switch_pin, operation_id, read, writer)
    replacements = _program_replacements(_services(baseline), _services(target))
    capture_bindings = {}
    for source_index,(source_ref,base_pin) in enumerate(policy['captureConfigurationPins'].items()):
        guard()
        base = read(base_pin); active = deepcopy(base)
        source = active['source']
        source['writerContainerIds'] = _mapped(source['writerContainerIds'], replacements)
        source['applicationImageIds'] = _mapped(source['applicationImageIds'], replacements)
        for field in ('configurationPins', 'materialPins'):
            for index,row in enumerate(source[field]):
                row['reference'] = material(row['reference'], replacements,
                    '%s-%d-%d' % (field,source_index,index), allow_raw=True)
        objects = read(source['objectSourcePin']); mapped_objects = deepcopy(objects)
        mapped_objects['versionPins'] = [material(reference,replacements,
            'version-%d-%d' % (source_index,index), allow_raw=False)
            for index,reference in enumerate(objects['versionPins'])]
        if mapped_objects != objects:
            source['objectSourcePin'] = stage('objects-%d' % source_index,mapped_objects)
        _capture_transition(base,active,baseline,target,source_ref,epoch,read)
        capture_pin = deepcopy(base_pin) if active == base else stage('capture-%d' % source_index,active)
        capture_bindings[source_ref] = dict(baseCapturePin=deepcopy(base_pin),capturePin=capture_pin)
    target_pin = stage('target', target)
    # Validate originals again after planning, and keep the same check through
    # publication. No JSON-format assumption is needed for unchanged raw pins.
    def original_inputs_unchanged():
        for reference in tuple(inputs.values()):
            raw(reference)

    original_inputs_unchanged(); held()
    parent_fd = os.open(claim,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    output_fd = None
    try:
        _same_directory(claim,parent_fd)
        try:
            os.mkdir(OUTPUT_DIRECTORY,0o700,dir_fd=parent_fd)
        except FileExistsError as error:
            raise RecoveryError('PROGRAM_DERIVATION_EXISTS') from error
        output_fd = os.open(OUTPUT_DIRECTORY,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent_fd)
        _same_directory(output_root,output_fd)
        os.fsync(parent_fd)
        for item in staged.values():
            held(); _same_directory(claim,parent_fd); _same_directory(output_root,output_fd)
            try:
                descriptor = os.open(Path(item['pin']['path']).name,
                    os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=output_fd)
            except FileExistsError as error:
                raise RecoveryError('PROGRAM_DERIVATION_EXISTS') from error
            with os.fdopen(descriptor,'wb') as stream:
                for offset in range(0,len(item['raw']),65536):
                    held(); stream.write(item['raw'][offset:offset+65536])
                stream.flush(); os.fsync(stream.fileno())
            _,actual = _read_file(item['pin']['path'],DOCUMENT_LIMIT)
            require(actual == item['pin'],'PROGRAM_DERIVATION_OUTPUT_CHANGED')
            register(item['pin'],physical=False)
        os.fsync(output_fd)
        original_inputs_unchanged(); held()
        for item in staged.values():
            held()
            _,actual = _read_file(item['pin']['path'],DOCUMENT_LIMIT)
            require(actual == item['pin'],'PROGRAM_DERIVATION_OUTPUT_CHANGED')
        _same_directory(claim,parent_fd); _same_directory(output_root,output_fd)
    finally:
        if output_fd is not None: os.close(output_fd)
        os.close(parent_fd)
    return dict(targetPin=target_pin,captureBindings=capture_bindings,evidencePins=evidence)


def derive(policy, previous_target, switch_pin, operation_id, claim, lock_fd, *, reader=document, guard=None):
    """Create exclusive private documents; ``previous_target`` must be verified.

    No retry/overwrite or rollback is attempted. On a post-publication failure,
    preserve the claim for the caller's normal retained-failure investigation.
    """
    try:
        return _derive(policy,previous_target,switch_pin,operation_id,claim,lock_fd,reader,
                       (lambda: None) if guard is None else guard)
    except (KeyError,TypeError,IndexError,AttributeError) as error:
        raise RecoveryError('PROGRAM_DERIVATION_FORMAT_INVALID') from error
