"""Read-only selection of an incremental parent from immutable native originals.

The latest successful FULL starts a generation. Every point in that generation
must form one complete parent prefix; branch ambiguity is never resolved by a
filename, UI history, or an arbitrary timestamp tie-breaker.
"""
from datetime import datetime, timezone
from pathlib import Path
import re
import time

import recovery_control_executor as executor
from recovery_control_smallapp import (Failure, Ledger, exact, fingerprint, local_read,
    need, opaque, public_error)

MAX_SECONDS = 30


class PlanReader:
    """One pinned read per original, with a bounded lifetime and final identity check."""
    def __init__(self, native):
        self.native = native
        self.deadline = time.monotonic() + MAX_SECONDS
        self.documents, self.identities, self.required = {}, {}, {}

    def guard(self):
        need(time.monotonic() < self.deadline, 'INCREMENTAL_PLAN_TIMEOUT')

    @staticmethod
    def identity(path):
        path = Path(path)
        need(path.resolve() == path and not path.is_symlink(), 'INCREMENTAL_PLAN_INPUT_CHANGED')
        info = path.stat()
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_mode

    def read(self, path, action):
        self.guard()
        path = Path(path)
        before = self.identity(path)
        value = action()
        need(before == self.identity(path), 'INCREMENTAL_PLAN_INPUT_CHANGED')
        self.identities[path] = before
        self.guard()
        return value

    def document(self, pin):
        self.guard()
        executor.pin_reference(pin)
        key = fingerprint(pin)
        if key not in self.documents:
            self.documents[key] = self.read(pin['path'], lambda: self.native.document(pin))
        return self.documents[key]

    def local(self, path):
        return self.read(path, lambda: local_read(path))

    def require(self, pin):
        executor.pin_reference(pin)
        self.required[fingerprint(pin)] = pin

    def finish(self):
        for key, pin in self.required.items():
            self.guard()
            if key not in self.documents:
                self.read(pin['path'], lambda pin=pin: executor.verify(pin))
        for path, identity in self.identities.items():
            self.guard()
            need(self.identity(path) == identity, 'INCREMENTAL_PLAN_INPUT_CHANGED')
        self.guard()


def timestamp(value):
    need(type(value) is str and re.fullmatch(
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)', value),
        'INCREMENTAL_NATIVE_COMPLETION_TIME_INVALID')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise Failure('INCREMENTAL_NATIVE_COMPLETION_TIME_INVALID') from None
    need(parsed.utcoffset().total_seconds() == 0 and parsed <= datetime.now(timezone.utc),
         'INCREMENTAL_NATIVE_COMPLETION_TIME_INVALID')
    return parsed


def response(source_ref, state, reason=None, *, selected=None, base=None, evidence=None):
    value = dict(schemaVersion='AutomaticIncrementalPlan/v1', sourceConfigRef=source_ref,
        state=state, reasonCode=reason, parentChainRef=None, baseFullRef=None, generationId=None,
        chainDepth=0, pointType=None, finishedAt=None, baseFinishedAt=None,
        basePointType=None, parentPointType=None)
    if selected is not None:
        point = selected['point']
        value.update(parentChainRef=point['backupId'], baseFullRef=base['point']['backupId'],
            generationId=point['generationId'], chainDepth=len(point['parentPointPins']) + 1,
            pointType=point['pointType'], parentPointType=point['pointType'], basePointType='FULL',
            finishedAt=selected['output']['finishedAt'], baseFinishedAt=base['output']['finishedAt'])
    # Only the digest is public. It binds the actual source configuration and
    # pinned originals without returning private filesystem paths or credentials.
    value['evidenceDigest'] = fingerprint(evidence)
    value['planDigest'] = fingerprint(value)
    return value


def validate_epoch(current_epoch, point_epoch, *, source_ref, reference, point_pin, result_pin, reader=None):
    """Validate explicit restoration epochs; an unchanged DB UUID proves nothing."""
    need(type(current_epoch) is dict and current_epoch.get('state') == 'READY',
         'BACKUP_EPOCH_NOT_READY')
    if point_epoch is None:
        return 'BACKUP_POINT_EPOCH_REQUIRED'
    exact(point_epoch, 'schemaVersion reference sourceConfigRef pointPin resultPin policySha256 epochId epochEventPin',
          'BACKUP_POINT_EPOCH_BINDING_INVALID')
    need(point_epoch['schemaVersion'] == 'SmallAppPointEpochBinding/v1' and
         point_epoch['reference'] == reference and point_epoch['sourceConfigRef'] == source_ref and
         point_epoch['pointPin'] == point_pin and point_epoch['resultPin'] == result_pin,
         'BACKUP_POINT_EPOCH_BINDING_INVALID')
    event = (executor.document if reader is None else reader.document)(point_epoch['epochEventPin'])
    need(event.get('schemaVersion') == 'SourceBackupEpochEvent/v1' and event.get('state') == 'READY' and
         event.get('policySha256') == point_epoch['policySha256'] and
         event.get('epochId') == point_epoch['epochId'], 'BACKUP_POINT_EPOCH_EVENT_INVALID')
    if (point_epoch['policySha256'], point_epoch['epochId']) != (
            current_epoch['policySha256'], current_epoch['epochId']):
        return 'BACKUP_POINT_EPOCH_CHANGED'
    return None


def read_declared(reader, reference, binding_pin, binding):
    output = reader.document(binding['resultPin'])
    need(output.get('operationId') == output.get('requestId') == reference and
         output.get('action') in ('FULL', 'INCREMENTAL') and output.get('state') == 'SUCCEEDED' and
         type(output.get('actualExitCode')) is int and output['actualExitCode'] == 0,
         'POINT_ORIGINAL_RESULT_INVALID')
    need(output.get('schemaVersion') == 'backup-restore-operation-result/v1' and
         output.get('failureCode') is None and type(output.get('originalResultPins')) is list and
         output['originalResultPins'],
         'INCREMENTAL_ORIGINAL_SUCCESS_INCOMPLETE')
    finished = timestamp(output['finishedAt'])
    need(timestamp(output['startedAt']) <= finished, 'INCREMENTAL_NATIVE_COMPLETION_TIME_INVALID')
    point_pin = output['data']['pointPin']
    point = reader.document(point_pin)
    need(point.get('schemaVersion') == 'RepositoryPoint/v1' and point['backupId'] == reference and
         point['pointType'] == output['action'] and point.get('integrityState') == 'COMPLETE' and
         type(point['parentPointPins']) is list, 'INCREMENTAL_REPOSITORY_POINT_INVALID')
    return dict(reference=reference, bindingPin=binding_pin, resultPin=binding['resultPin'],
        pointPin=point_pin, point=point, output=output, finished=finished)


def validate_source_restoration(reader, row, captured, capture_pin):
    """Frozen capture content precedes restoration; its success receipt follows it."""
    need(type(captured.get('sourceRestored')) is bool, 'INCREMENTAL_CAPTURE_BINDING_INVALID')
    if captured['sourceRestored']:
        return
    code = 'INCREMENTAL_SOURCE_RESTORATION_INVALID'
    result_pin = row['output']['data'].get('captureResultPin')
    need(type(result_pin) is dict, code)
    result = reader.document(result_pin)
    need(result.get('schemaVersion') == 'backup-restore-operation-result/v1' and
         result.get('operationId') == result.get('requestId') == row['reference'] and
         result.get('action') == captured['pointType'] and result.get('state') == 'SUCCEEDED' and
         type(result.get('actualExitCode')) is int and result['actualExitCode'] == 0 and
         result.get('failureCode') is None and type(result.get('data')) is dict, code)
    data = result['data']
    original = data.get('capturePointPin')
    restoration_pin = data.get('sourceRestorationPin')
    need(type(original) is dict and type(restoration_pin) is dict and
         type(data.get('captureRoot')) is str and
         data.get('sourceIdentity') == captured['sourceIdentity'] and
         data.get('recoveryPoint') == captured['commonRecoveryPoint'], code)
    executor.pin_reference(original)
    executor.pin_reference(restoration_pin)
    root = Path(data['captureRoot'])
    # Repository publication changes the path, preserving the captured bytes.
    need(root.is_absolute() and root.resolve() == root and
         Path(original['path']) == root / 'payload' / 'capture-content-point.json' and
         Path(restoration_pin['path']) == root / 'source-restoration.json' and
         all(original[key] == capture_pin[key] for key in ('bytes', 'sha256')), code)
    restoration = reader.document(restoration_pin)
    need(restoration.get('schemaVersion') == 'minimal-capture-source-restoration/v1' and
         restoration.get('sourceIdentity') == captured['sourceIdentity'] and
         restoration.get('restored') is True and restoration.get('errors') == [], code)
    need(timestamp(result['startedAt']) <= timestamp(restoration['at']) <=
         timestamp(result['finishedAt']) <= row['finished'], code)


def read_point(reader, row, *, complete=True):
    point, output, reference = row['point'], row['output'], row['reference']
    point_pin = row['pointPin']
    if complete:
        for pin in output['originalResultPins']:
            reader.require(pin)
    repository = reader.document(output['data']['repositoryBindingPin'])
    need(repository.get('schemaVersion') == 'RecoveryRepositoryBinding/v1' and
         repository['backupId'] == reference and repository['generationId'] == point['generationId'] and
         repository['repositoryPointPin'] == point_pin and repository['manifestPin'] == point['manifestPin'],
         'INCREMENTAL_REPOSITORY_BINDING_INVALID')
    manifest = reader.document(point['manifestPin'])
    need(manifest.get('schemaVersion') == 'RepositoryManifest/v1' and all(
         manifest[key] == point[key] for key in ('backupId', 'generationId', 'pointType', 'parentPointPins',
                                               'commonRecoveryPoint')), 'INCREMENTAL_MANIFEST_BINDING_INVALID')
    terminal = reader.document(point['originalExitEvidencePin'])
    need(terminal.get('state') == 'EXITED' and terminal.get('processTerminated') is True and
         type(terminal.get('actualExitCode')) is int and terminal['actualExitCode'] == 0,
         'INCREMENTAL_ORIGINAL_EXIT_INVALID')
    material = reader.document(repository['recoveryMaterialPin'])
    capture_pin = material['database']['capturePointPin']
    captured = reader.document(capture_pin)
    need(material.get('schemaVersion') == 'RecoveryMaterial/v1' and
         material['manifestPin'] == point['manifestPin'] and material['pointType'] == point['pointType'] and
         captured.get('schemaVersion') == 'backup-capture-point/v1' and captured['backupId'] == reference and
         captured['generationId'] == point['generationId'] and captured['pointType'] == point['pointType'] and
         material['sourceDatabaseUuid'] == captured['databaseEnd']['databaseUuid'] and
         material['recoveryPoint'] == captured['commonRecoveryPoint'] == point['commonRecoveryPoint'],
         'INCREMENTAL_CAPTURE_BINDING_INVALID')
    validate_source_restoration(reader, row, captured, capture_pin)
    end = captured['databaseEnd']
    need(type(end) is dict and type(end.get('position')) is int and end['position'] >= 4 and
         type(end.get('file')) is str and re.fullmatch(r'.+\.\d+', end['file']) and
         type(end.get('executedGtidSet')) is str, 'INCREMENTAL_CAPTURE_POSITION_INVALID')
    return dict(row, captured=captured, capturePin=capture_pin)


def validate_chain(points):
    by_pin = {fingerprint(row['pointPin']): row for row in points.values()}
    need(len(by_pin) == len(points), 'INCREMENTAL_POINT_ALIAS_INVALID')
    for row in points.values():
        point, captured = row['point'], row['captured']
        parents = point['parentPointPins']
        if point['pointType'] == 'FULL':
            need(not parents and point['generationId'] == point['backupId'] and
                 captured['parentPointPin'] is None and captured['parentRepositoryPointPin'] is None,
                 'INCREMENTAL_FULL_ROOT_INVALID')
            continue
        need(point['pointType'] == 'INCREMENTAL' and parents, 'INCREMENTAL_PARENT_PREFIX_INVALID')
        seen = set()
        for index, parent_pin in enumerate(parents):
            parent = by_pin.get(fingerprint(parent_pin))
            need(parent is not None and parent['reference'] != row['reference'] and
                 parent['reference'] not in seen, 'INCREMENTAL_PARENT_PREFIX_INVALID')
            seen.add(parent['reference'])
            need(parent['point']['parentPointPins'] == parents[:index] and
                 parent['point']['generationId'] == point['generationId'] and
                 parent['point']['pointType'] == ('FULL' if index == 0 else 'INCREMENTAL'),
                 'INCREMENTAL_PARENT_PREFIX_INVALID')
            need(parent['captured']['sourceIdentity'] == captured['sourceIdentity'] and
                 parent['captured']['databaseEnd']['databaseUuid'] == captured['databaseEnd']['databaseUuid'],
                 'INCREMENTAL_CHAIN_SOURCE_CHANGED')
        parent = by_pin[fingerprint(parents[-1])]
        need(captured['parentRepositoryPointPin'] == parent['pointPin'] and
             captured['parentPointPin'] == parent['capturePin'], 'INCREMENTAL_CAPTURE_PARENT_INVALID')
        need(captured['databaseDelta'].get('parentPosition') == parent['captured']['databaseEnd'],
             'INCREMENTAL_CAPTURE_START_CHANGED')
        need(row['finished'] >= parent['finished'], 'INCREMENTAL_COMPLETION_ORDER_INVALID')


def continuity_reason(previous, observation):
    """Classify proven lost continuity separately from a failed source observation."""
    from formal_capture_incremental import binlog_ranges, validate_position
    exact(observation, 'position logs', 'INCREMENTAL_SOURCE_OBSERVATION_INVALID')
    current, logs = observation['position'], observation['logs']
    validate_position(previous)
    validate_position(current)
    need(type(logs) is list and logs and all(type(row) is dict and set(row) == {'file', 'bytes'} and
         type(row['file']) is str and re.fullmatch(r'[A-Za-z0-9_-]+\.[0-9]{6}', row['file']) and
         type(row['bytes']) is int and row['bytes'] >= 4 for row in logs),
         'INCREMENTAL_SOURCE_LOGS_INVALID')
    names = [row['file'] for row in logs]
    need(len(names) == len(set(names)) and current['file'] in names, 'INCREMENTAL_SOURCE_OBSERVATION_CHANGED')
    if previous['file'] not in names:
        return 'INCREMENTAL_PARENT_BINLOG_PURGED'
    try:
        binlog_ranges(logs, previous, current)
    except Exception as error:
        mapping = {'FORMAL_CAPTURE_BINLOG_GAP': 'INCREMENTAL_BINLOG_CHAIN_GAP',
            'FORMAL_CAPTURE_BINLOG_LINEAGE_CHANGED': 'INCREMENTAL_SOURCE_LINEAGE_CHANGED',
            'FORMAL_CAPTURE_GTID_REGRESSED': 'INCREMENTAL_SOURCE_POSITION_REGRESSED',
            'FORMAL_CAPTURE_BINLOG_POSITION_INVALID': 'INCREMENTAL_SOURCE_POSITION_REGRESSED'}
        code = public_error(error)
        if code in mapping:
            return mapping[code]
        raise
    return None


def build_plan(native, source_ref, *, exclude_operation=None):
    opaque(source_ref)
    evidence = []
    reader = PlanReader(native)
    def finish(*args, **kwargs):
        reader.finish()
        return response(*args, **kwargs)
    try:
        config = native.configuration()
        native.registration(source_ref)
        need(source_ref in config['sourceConfigurations'], 'SOURCE_CONFIGURATION_REQUIRED')
        # Incomplete durable operations remain busy after a service restart.
        reader.guard()
        Ledger(config['ledgerRoot'], native).require_source_idle(source_ref,
            exclude_operation=exclude_operation, guard=reader.guard)
        owner_pin = config['sourceConfigurations'][source_ref]
        owner = reader.document(owner_pin)
        capture_pin = executor.pin(owner['sources'][source_ref]['configurationPath'])
        capture = reader.document(capture_pin)
        need(capture['sourceConfigRef'] == source_ref, 'CAPTURE_REQUEST_SOURCE_MISMATCH')
        evidence.extend([owner_pin, capture_pin])
        epoch = native.source_epoch(config, source_ref)
        evidence.append(epoch)
        points = {}
        from recovery_control_point_quarantine import quarantined
        for path in sorted((Path(config['registryRoot']) / 'points').glob('*.pin.json')):
            reader.guard()
            reference = opaque(path.name[:-9])
            binding_pin = reader.local(path)
            binding = reader.document(binding_pin)
            exact(binding, 'schemaVersion reference sourceConfigRef resultPin', 'POINT_BINDING_FIELDS_INVALID')
            need(binding['schemaVersion'] == 'SmallAppPointBinding/v2' and binding['reference'] == reference,
                 'POINT_SOURCE_MISMATCH')
            if binding['sourceConfigRef'] != source_ref:
                continue
            if quarantined(reader, config, reference, source_ref, binding_pin):
                continue
            points[reference] = read_declared(reader, reference, binding_pin, binding)
            evidence.append(binding_pin)
        roots = [row for row in points.values() if row['point']['pointType'] == 'FULL']
        if not roots:
            need(not points, 'INCREMENTAL_PARENT_PREFIX_INVALID')
            return finish(source_ref, 'BASELINE_REQUIRED', 'NO_SUCCESSFUL_FULL_BASELINE', evidence=evidence)
        # Retired generations retain verified binding/result/root metadata. Their
        # payload readback and incremental internals are not scheduling inputs.
        roots = [read_point(reader, row, complete=False) for row in roots]
        for root in roots:
            reader.guard()
            validate_chain({root['reference']: root})
        latest_time = max(row['finished'] for row in roots)
        roots = [row for row in roots if row['finished'] == latest_time]
        need(len(roots) == 1, 'AMBIGUOUS_LATEST_FULL')
        base = roots[0]
        if (base['captured']['sourceIdentity'], base['captured']['databaseEnd']['databaseUuid']) != (
                capture['source']['sourceIdentity'], capture['source']['databaseUuid']):
            return finish(source_ref, 'BASELINE_REQUIRED', 'SOURCE_BACKUP_IDENTITY_CHANGED', evidence=evidence)
        generation = [read_point(reader, row) for row in points.values()
                      if row['point']['generationId'] == base['reference']]
        validate_chain({row['reference']: row for row in generation})
        deepest = max(len(row['point']['parentPointPins']) for row in generation)
        leaves = [row for row in generation if len(row['point']['parentPointPins']) == deepest]
        need(len(leaves) == 1, 'INCREMENTAL_CHAIN_BRANCHED')
        selected = leaves[0]
        selected_pins = selected['point']['parentPointPins'] + [selected['pointPin']]
        need(len(generation) == len(selected_pins) and all(row['pointPin'] in selected_pins for row in generation),
             'INCREMENTAL_CHAIN_BRANCHED')
        if epoch is not None:
            for row in generation:
                path = Path(config['registryRoot']) / 'point-epochs' / (row['reference'] + '.json')
                bound = reader.local(path) if path.exists() or path.is_symlink() else None
                reason = validate_epoch(epoch, bound, source_ref=source_ref, reference=row['reference'],
                    point_pin=row['pointPin'], result_pin=row['resultPin'], reader=reader)
                if reason is not None:
                    return finish(source_ref, 'BASELINE_REQUIRED', reason, evidence=evidence)
                evidence.append(bound)
        reader.guard()
        observed = native.incremental_source_observation(capture, deadline=reader.deadline)
        need(observed['position']['databaseUuid'] == capture['source']['databaseUuid'],
             'INCREMENTAL_LIVE_SOURCE_IDENTITY_CHANGED')
        reason = continuity_reason(selected['captured']['databaseEnd'], observed)
        need(native.source_epoch(config, source_ref) == epoch, 'BACKUP_EPOCH_CHANGED_DURING_PLAN')
        if reason is not None:
            return finish(source_ref, 'BASELINE_REQUIRED', reason, evidence=evidence)
        # A live master normally advances between preview and submit. Only the
        # stable readiness conclusion affects the public digest, not its moving
        # position or the currently retained log sizes.
        return finish(source_ref, 'READY', selected=selected, base=base, evidence=evidence)
    except Exception as error:
        code = 'INCREMENTAL_PLAN_TIMEOUT' if time.monotonic() >= reader.deadline else public_error(error)
        return response(source_ref, 'BLOCKED', code, evidence=evidence)
