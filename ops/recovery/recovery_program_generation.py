"""Resolve immutable MAIN program configurations from completed restore epochs.

The installed baseline is used only at its explicitly pinned READY event.
Later successful restores must carry their own generation, even when images
did not change. Reading never creates or repairs an event or a configuration.
"""
from copy import deepcopy
from pathlib import Path
import re

from recovery_engine import RecoveryError, digest, require
from recovery_backup_epoch import _read_file, _parse, read_current, validate_policy as validate_epoch


POLICY_FIELDS = {'schemaVersion', 'targetConfigRef', 'baselineTargetPin', 'initialEpochPin',
                 'backupEpochPolicy', 'captureConfigurationPins'}
GENERATION_FIELDS = {'schemaVersion', 'operationId', 'epochId', 'policySha256', 'targetConfigRef',
    'baselineTargetPin', 'parentGenerationPin', 'targetPin', 'captureBindings', 'switchResultPin'}
APPLICATIONS = {'backend', 'frontend'}


def _pin(reference):
    require(type(reference) is dict and set(reference) == {'path', 'bytes', 'sha256'} and
            type(reference['path']) is str and Path(reference['path']).is_absolute() and
            type(reference['bytes']) is int and 0 < reference['bytes'] <= 4*1024*1024 and
            type(reference['sha256']) is str and re.fullmatch('[0-9a-f]{64}', reference['sha256']),
            'PROGRAM_DOCUMENT_PIN_INVALID')
    return reference


def document(reference):
    _pin(reference)
    raw, observed = _read_file(reference['path'], 4*1024*1024)
    require(observed == dict(reference, path=Path(reference['path']).as_posix()), 'PROGRAM_DOCUMENT_CHANGED')
    return _parse(raw)


def validate_policy(policy):
    require(type(policy) is dict and set(policy) == POLICY_FIELDS and
            policy['schemaVersion'] == 'RegisteredMainProgramPolicy/v1' and
            type(policy['targetConfigRef']) is str and 0 < len(policy['targetConfigRef']) <= 256 and
            type(policy['captureConfigurationPins']) is dict and len(policy['captureConfigurationPins']) <= 100 and
            all(type(k) is str and 0 < len(k) <= 256 for k in policy['captureConfigurationPins']),
            'PROGRAM_POLICY_INVALID')
    for reference in [policy['baselineTargetPin'], policy['initialEpochPin'], *policy['captureConfigurationPins'].values()]:
        _pin(reference)
    validate_epoch(policy['backupEpochPolicy'])
    return policy


def _mapped(value, replacements):
    if type(value) is str:
        return replacements.get(value, value)
    if type(value) is list:
        return [_mapped(item, replacements) for item in value]
    if type(value) is dict:
        return {_mapped(key, replacements): _mapped(item, replacements) for key, item in value.items()}
    return value


def _services(target):
    rows = target['services']
    require(type(rows) is list and len({row['role'] for row in rows}) == len(rows), 'PROGRAM_TARGET_SCOPE_CHANGED')
    return {row['role']: row for row in rows}


def _target_transition(previous, target, switch_pin, operation, read):
    if switch_pin is None:
        require(target == previous, 'PROGRAM_TARGET_SCOPE_CHANGED')
        return
    from recovery_program_containers import snapshot, verify_created
    from recovery_main_target import service_configuration_digest, network_attachments
    switch = read(switch_pin)
    require(switch.get('schemaVersion') == 'MainProgramSwitchResult/v1' and
            switch.get('state') == 'CREATED_STOPPED' and switch.get('operationId') == operation and
            set(switch.get('applicationPins', {})) == APPLICATIONS, 'PROGRAM_SWITCH_PROOF_INVALID')
    intent = read(switch['intentPin'])
    require(intent.get('schemaVersion') == 'MainProgramSwitchIntent/v1' and intent.get('operationId') == operation,
            'PROGRAM_SWITCH_PROOF_INVALID')
    services = _services(previous); expected = deepcopy(previous); changed = _services(expected)
    replacements = {}
    for role in sorted(APPLICATIONS):
        item = read(switch['applicationPins'][role])
        original, created = item['original'], item['created']
        require(original == intent['originals'][role] and original['Id'] == services[role]['id'] and
                original['Image'] == services[role]['imageId'] and
                service_configuration_digest(original) == previous['mainApplication']['serviceConfigurationDigests'][role],
                'PROGRAM_SWITCH_PROOF_INVALID')
        networks = {name: dict(Id=row['NetworkID'], Name=name) for name,row in original['NetworkSettings']['Networks'].items()}
        verify_created(original, intent['requests'][role], created, networks=networks,
                       engine_metadata=intent['engineMetadata'])
        retained = snapshot(original); retained['Name'] = item['retained']['Name']; retained['networks'] = {}
        require(snapshot(item['retained']) == retained, 'PROGRAM_SWITCH_PROOF_INVALID')
        replacements[original['Id']] = created['Id']
        replacements[original['Id'][:12]] = created['Id'][:12]
        replacements[original['Image']] = created['Image']
        changed[role].update(id=created['Id'], imageId=created['Image'])
        expected['replacement']['services'][role].update(id=created['Id'], imageId=created['Image'],
            labels=created['Config']['Labels'], mounts=sorted(created['Mounts'],key=lambda m:m['Destination']))
        expected['mainApplication']['serviceConfigurationDigests'][role] = service_configuration_digest(created)
        normalized = deepcopy(created)
        for name,endpoint in normalized['NetworkSettings']['Networks'].items():
            if not endpoint['NetworkID']:
                endpoint['NetworkID'] = original['NetworkSettings']['Networks'][name]['NetworkID']
        expected['mainApplication']['networkAttachments'][role] = network_attachments(normalized)
    main = expected['mainApplication']
    main['networks'] = _mapped(main['networks'], replacements)
    for network in main['networks']:
        network['memberContainerIds'].sort()
    for binding in main['archiveImageBindings']:
        if binding['role'] in APPLICATIONS:
            binding['imageId'] = changed[binding['role']]['imageId']
    writers = main['writerAdmission']
    writers['approvedWriterContainerIds'] = _mapped(writers['approvedWriterContainerIds'], replacements)
    new_proof = target['mainApplication']['writerAdmission']['evidencePin']
    require(read(new_proof) == _mapped(read(writers['evidencePin']), replacements), 'PROGRAM_TARGET_SCOPE_CHANGED')
    writers['evidencePin'] = new_proof
    require(target == expected, 'PROGRAM_TARGET_SCOPE_CHANGED')


def _capture_transition(base, active, baseline, target, source_ref, epoch_policy, read):
    code = 'PROGRAM_CAPTURE_SCOPE_CHANGED'
    old_services, services = _services(baseline), _services(target)
    require(set(old_services) == set(services) and base.get('sourceConfigRef') == source_ref and
            base.get('sourceLockPath') == epoch_policy['sourceLockPath'] and
            base['source']['sourceIdentity'] == epoch_policy['sourceIdentity'] and
            base['source']['databaseUuid'] == epoch_policy['databaseUuid'] and
            base['source']['database'] == baseline['database'] and
            base['source']['mysqlContainerId'] == old_services['mysql']['id'] and
            base['source']['minioContainerId'] == old_services['minio']['id'], code)
    replacements = {old_services[r][field]: services[r][field] for r in APPLICATIONS for field in ('id','imageId')}
    expected = deepcopy(base)
    expected['source']['writerContainerIds'] = _mapped(base['source']['writerContainerIds'], replacements)
    expected['source']['applicationImageIds'] = _mapped(base['source']['applicationImageIds'], replacements)
    require(set(base['source']['writerContainerIds']) <= {old_services[r]['id'] for r in APPLICATIONS}, code)
    # Configuration/material documents may carry exact program IDs. A new pin
    # is allowed only for the same document with those IDs replaced recursively.
    for field in ('configurationPins', 'materialPins'):
        before, after = base['source'][field], active['source'][field]
        require(len(before) == len(after), code)
        for old, new in zip(before, after):
            require({k:v for k,v in old.items() if k != 'reference'} ==
                    {k:v for k,v in new.items() if k != 'reference'}, code)
            if old['reference'] != new['reference']:
                require(read(new['reference']) == _mapped(read(old['reference']), replacements), code)
        expected['source'][field] = deepcopy(after)
    old_objects = read(base['source']['objectSourcePin']); objects = read(active['source']['objectSourcePin'])
    expected_objects = deepcopy(old_objects)
    require(len(old_objects['versionPins']) == len(objects['versionPins']), code)
    for old,new in zip(old_objects['versionPins'],objects['versionPins']):
        require(read(new) == _mapped(read(old), replacements), code)
    expected_objects['versionPins'] = objects['versionPins']
    require(objects == expected_objects, code)
    expected['source']['objectSourcePin'] = active['source']['objectSourcePin']
    require(active == expected, code)


def _resolve(policy, reader, guard=None):
    guard = (lambda: None) if guard is None else guard
    guard()
    validate_policy(policy)
    evidence = []; seen = {}
    def read(reference):
        guard()
        _pin(reference)
        key = reference['path']
        require(key not in seen or seen[key] == reference, 'PROGRAM_DOCUMENT_PIN_CONFLICT')
        if key not in seen:
            seen[key] = deepcopy(reference); evidence.append(deepcopy(reference))
        result = reader(reference)
        guard()
        return result
    epoch_policy = policy['backupEpochPolicy']; current = read_current(epoch_policy, guard=guard)
    require(current['state'] == 'READY', 'PROGRAM_EPOCH_NOT_READY')
    initial = read(policy['initialEpochPin'])
    require(initial['state'] == 'READY' and initial['policySha256'] == digest(epoch_policy) and
            Path(policy['initialEpochPin']['path']).parent == Path(epoch_policy['root']), 'PROGRAM_INITIAL_EPOCH_INVALID')
    baseline = read(policy['baselineTargetPin'])
    require(baseline['replacement']['databaseUuid'] == epoch_policy['databaseUuid'] and
            baseline['replacement']['lockPath'] == epoch_policy['sourceLockPath'], 'PROGRAM_BASELINE_SCOPE_CHANGED')
    event = read(current['eventPin'])
    require(event['sequence'] >= initial['sequence'], 'PROGRAM_INITIAL_EPOCH_INVALID')
    # Validate the installed cutover really is in this journal, not a copied
    # READY event from another location or a future sequence.
    initial_path = Path(epoch_policy['root'])/('%020d.json' % initial['sequence'])
    require(Path(policy['initialEpochPin']['path']) == initial_path, 'PROGRAM_INITIAL_EPOCH_INVALID')
    generations = []; previous_pin = None; previous_target = baseline
    target_pin = policy['baselineTargetPin']; captures = policy['captureConfigurationPins']
    for sequence in range(initial['sequence']+1, event['sequence']+1):
        guard()
        path = Path(epoch_policy['root'])/('%020d.json' % sequence)
        _,reference = _read_file(path)
        record = read(reference)
        if record['kind'] != 'RESTORE_FINISHED':
            continue
        receipt = read(record['evidencePin'])
        if record['state'] == 'FAILED_RETAINED':
            continue
        generation_pin = receipt.get('programGenerationPin')
        require(generation_pin is not None, 'PROGRAM_GENERATION_REQUIRED')
        generation = read(generation_pin)
        require(type(generation) is dict and set(generation) == GENERATION_FIELDS and
                generation['schemaVersion'] == 'MainProgramGeneration/v1' and
                generation['operationId'] == record['operationId'] and generation['epochId'] == record['epochId'] and
                generation['policySha256'] == digest(policy) and generation['targetConfigRef'] == policy['targetConfigRef'] and
                generation['baselineTargetPin'] == policy['baselineTargetPin'] and
                generation['parentGenerationPin'] == previous_pin and
                receipt.get('targetConfigRef') == policy['targetConfigRef'] and
                receipt.get('databaseUuid') == epoch_policy['databaseUuid'], 'PROGRAM_GENERATION_BINDING_INVALID')
        claim = Path(baseline['replacement']['stateRoot'])/record['operationId']
        require(Path(record['evidencePin']['path']) == claim/'replacement-result.json' and
                Path(generation_pin['path']).parent == claim, 'PROGRAM_GENERATION_LOCATION_INVALID')
        target_pin = generation['targetPin']; target = read(target_pin)
        _target_transition(previous_target, target, generation['switchResultPin'], record['operationId'], read)
        require(type(generation['captureBindings']) is dict and
                set(generation['captureBindings']) == set(policy['captureConfigurationPins']), 'PROGRAM_CAPTURE_BINDINGS_INVALID')
        captures = {}
        for source_ref, binding in generation['captureBindings'].items():
            require(type(binding) is dict and set(binding) == {'baseCapturePin','capturePin'} and
                    binding['baseCapturePin'] == policy['captureConfigurationPins'][source_ref], 'PROGRAM_CAPTURE_BASE_CHANGED')
            _capture_transition(read(binding['baseCapturePin']), read(binding['capturePin']),
                baseline, target, source_ref, epoch_policy, read)
            captures[source_ref] = binding['capturePin']
        previous_pin, previous_target = generation_pin, target
        generations.append(generation_pin)
    for source_ref, base_pin in policy['captureConfigurationPins'].items():
        if not generations:
            base = read(base_pin)
            _capture_transition(base,base,baseline,baseline,source_ref,epoch_policy,read)
    require(read_current(epoch_policy, guard=guard) == current, 'PROGRAM_EPOCH_CHANGED')
    return dict(target=previous_target,targetPin=target_pin,captures=captures,
                generationPin=previous_pin,epoch=current,evidence=evidence)


def resolve_capture(policy, source_ref, base_pin, *, reader=document, guard=None):
    try:
        validate_policy(policy)
        require(source_ref in policy['captureConfigurationPins'], 'PROGRAM_CAPTURE_SOURCE_UNREGISTERED')
        require(base_pin == policy['captureConfigurationPins'][source_ref], 'PROGRAM_CAPTURE_BASE_CHANGED')
        result = _resolve(policy,reader,guard)
        return result['captures'][source_ref], result['evidence']
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise RecoveryError('PROGRAM_GENERATION_FORMAT_INVALID') from error


def resolve_target(policy, *, reader=document, guard=None):
    try:
        result = _resolve(policy,reader,guard)
        return result['target'],result['targetPin'],result['evidence']
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise RecoveryError('PROGRAM_GENERATION_FORMAT_INVALID') from error
