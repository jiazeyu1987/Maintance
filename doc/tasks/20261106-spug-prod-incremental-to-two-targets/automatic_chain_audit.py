"""Read-only FULL/incremental audit of pinned native metadata, never payload replay.

The installed package supplies its original chain/epoch validators. No function
dispatches a backup, opens a database, reconciles a ledger, or writes remote files.
"""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import time


def need(condition, code):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


class AuditReader:
    """One bounded metadata read per pin; final checks detect concurrent changes."""
    def __init__(self, seconds=120):
        self.deadline = time.monotonic() + seconds
        self.cache, self.identities, self.pins_by_path = {}, {}, {}
        self.total_bytes = 0

    def guard(self):
        need(time.monotonic() < self.deadline, 'AUDIT_METADATA_TIMEOUT')

    @staticmethod
    def identity(path):
        path = Path(path)
        need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(),
             'AUDIT_PATH_ALIAS_REJECTED')
        info = path.stat()
        need(stat.S_ISREG(info.st_mode), 'AUDIT_REGULAR_FILE_REQUIRED')
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_mode

    def raw(self, pin):
        self.guard()
        need(type(pin) is dict and set(pin) == {'path', 'bytes', 'sha256'} and
             type(pin['path']) is str and type(pin['bytes']) is int and pin['bytes'] >= 0 and
             type(pin['sha256']) is str and re.fullmatch('[0-9a-f]{64}', pin['sha256']), 'AUDIT_PIN_INVALID')
        key = canonical(pin)
        if key not in self.cache:
            need(pin['bytes'] <= 64 * 1024 * 1024, 'AUDIT_METADATA_LIMIT')
            before = self.identity(pin['path'])
            need(before == self.identities.get(Path(pin['path']), before), 'AUDIT_INPUT_CHANGED')
            need(before[2] == pin['bytes'], 'AUDIT_PIN_CHANGED')
            need(self.total_bytes + pin['bytes'] <= 256 * 1024 * 1024, 'AUDIT_TOTAL_METADATA_LIMIT')
            raw = Path(pin['path']).read_bytes()
            need(before == self.identity(pin['path']), 'AUDIT_INPUT_CHANGED')
            need(len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256'], 'AUDIT_PIN_CHANGED')
            self.total_bytes += len(raw)
            self.identities[Path(pin['path'])] = before
            self.pins_by_path[Path(pin['path'])] = pin
            self.cache[key] = raw
        return self.cache[key]

    def local_pin(self, path):
        self.guard()
        path = Path(path)
        before = self.identity(path)
        need(before == self.identities.get(path, before), 'AUDIT_INPUT_CHANGED')
        if path in self.pins_by_path:
            return self.pins_by_path[path]
        need(before[2] <= 64 * 1024 * 1024, 'AUDIT_METADATA_LIMIT')
        raw = path.read_bytes()
        need(before == self.identity(path), 'AUDIT_INPUT_CHANGED')
        pin = dict(path=path.as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        key = canonical(pin)
        if key not in self.cache:
            need(self.total_bytes + len(raw) <= 256 * 1024 * 1024, 'AUDIT_TOTAL_METADATA_LIMIT')
            self.total_bytes += len(raw); self.cache[key] = raw
        self.identities[path] = before
        self.pins_by_path[path] = pin
        return pin

    def document(self, pin):
        return json.loads(self.raw(pin))

    def local(self, path):
        return self.document(self.local_pin(path))

    def require(self, pin):
        self.raw(pin)

    def finish(self):
        for path, original in self.identities.items():
            self.guard()
            need(self.identity(path) == original, 'AUDIT_INPUT_CHANGED')


def check_reader_contract(caller_raw, reader_raw):
    """Check the reviewed STANDARD calling convention, plus its full reader body."""
    caller, reader = ast.parse(caller_raw), ast.parse(reader_raw)
    publish = next(node for node in caller.body if isinstance(node, ast.FunctionDef) and node.name == 'publish')
    calls = [node for node in ast.walk(publish) if isinstance(node, ast.Call) and
             isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and
             node.func.value.id == 'reader' and node.func.attr == 'verify']
    need(len(calls) == 1 and len(calls[0].args) == 3 and not calls[0].keywords,
         'AUDIT_FULL_SAFE_READER_REQUIRED')
    constructors = [node for node in ast.walk(publish) if isinstance(node, ast.Call) and
                    isinstance(node.func, ast.Name) and node.func.id == 'SmbReadback']
    need(constructors and all(not node.keywords for node in constructors), 'AUDIT_FULL_SAFE_READER_REQUIRED')
    cls = next(node for node in reader.body if isinstance(node, ast.ClassDef) and node.name == 'SmbReadback')
    methods = {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}
    verify = methods['verify']
    need(not verify.args.kwonlyargs and not verify.args.kw_defaults, 'AUDIT_FULL_SAFE_READER_REQUIRED')
    trees = [node for node in ast.walk(verify) if isinstance(node, ast.Call) and
             isinstance(node.func, ast.Attribute) and node.func.attr == 'tree']
    expected_check = any(isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and
        node.left.id == 'reference' and any(isinstance(right, ast.Name) and right.id == 'expected'
        for right in node.comparators) for node in ast.walk(methods['read']))
    need(len(trees) == 2 and expected_check, 'AUDIT_FULL_SAFE_READER_REQUIRED')
    return True


def verify_package(reader, spec):
    engine = Path(spec['engine'])
    version = reader.local(engine / 'package.json')
    need(version['variant'] == 'standard' and version['fileVerification'] is True and
         version['payloadContentVerification'] is True and len(version['files']) == spec['fileCount'] == 130,
         'AUDIT_STANDARD_130_REQUIRED')
    need(version['files'] == spec['files'] and version['packageSha256'] == spec['fileManifestSha256'] ==
         hashlib.sha256(canonical(version['files'])).hexdigest(), 'AUDIT_PACKAGE_MANIFEST_CHANGED')
    for name, digest in version['files'].items():
        path = PurePosixPath(name)
        need(not path.is_absolute() and '..' not in path.parts, 'AUDIT_PACKAGE_PATH_INVALID')
        pin = reader.local_pin(engine / name)
        need(pin['sha256'] == digest, 'AUDIT_PACKAGE_FILE_CHANGED')
    caller = reader.raw(reader.local_pin(engine / 'common/repository_minimal.py'))
    full_reader = reader.raw(reader.local_pin(engine / 'common/repository_native_readback.py'))
    check_reader_contract(caller, full_reader)
    return dict(engine=engine.as_posix(), variant='standard', fileCount=130,
        fileManifestSha256=version['packageSha256'], allInstalledFilesShaVerified=True,
        repositoryProgramPin=reader.local_pin(engine / 'common/repository_minimal.py'),
        fullReaderPin=reader.local_pin(engine / 'common/repository_native_readback.py'))


def read_chain(reader, config, source, references):
    from recovery_backup_epoch import read_current
    from recovery_control_incremental_plan import read_declared, read_point, validate_chain, validate_epoch
    need(references and len(references) == len(set(references)) and all(
         type(ref) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,120}', ref) for ref in references),
         'AUDIT_CHAIN_REFERENCES_INVALID')
    epoch = read_current(config['sourceEpochPolicies'][source])
    need(epoch['state'] == 'READY', 'AUDIT_EPOCH_NOT_READY')
    rows = {}
    for reference in references:
        binding_pin = reader.local(Path(config['registryRoot']) / 'points' / (reference + '.pin.json'))
        binding = reader.document(binding_pin)
        need(binding['schemaVersion'] == 'SmallAppPointBinding/v2' and binding['reference'] == reference and
             binding['sourceConfigRef'] == source, 'AUDIT_POINT_SOURCE_MISMATCH')
        row = read_point(reader, read_declared(reader, reference, binding_pin, binding),
                         complete=reference == references[-1])
        bound_pin = reader.local_pin(Path(config['registryRoot']) / 'point-epochs' / (reference + '.json'))
        bound = reader.document(bound_pin)
        need(validate_epoch(epoch, bound, source_ref=source, reference=reference,
            point_pin=row['pointPin'], result_pin=row['resultPin'], reader=reader) is None, 'AUDIT_POINT_EPOCH_MISMATCH')
        rows[reference] = dict(row, epochBindingPin=bound_pin, epochBinding=bound)
    validate_chain(rows)
    need(rows[references[-1]]['point']['parentPointPins'] == [rows[ref]['pointPin'] for ref in references[:-1]],
         'AUDIT_PARENT_PREFIX_MISMATCH')
    return rows, epoch


def verify_readback(reader, point, manifest):
    native = reader.document(point['readbackEvidencePin'])
    need(native['schemaVersion'] == 'RepositoryMinimumReadback/v1' and native['operationId'] == point['backupId'] and
         native['manifestPin'] == point['manifestPin'] and native['payloadRefs'] == point['payloadRefs'] == manifest['payloadRefs'] and
         native['independentConnectionId'] and native['serverDurabilityVerified'] is False and
         'payloadContentVerified' not in native, 'AUDIT_NATIVE_SAFE_READBACK_INVALID')
    originals = reader.document(native['originalRecordsPin'])
    need(originals['schemaVersion'] == 'RepositoryReadbackOriginals/v1' and
         originals['manifestPin'] == point['manifestPin'], 'AUDIT_READBACK_ORIGINALS_INVALID')
    expected = sorted(manifest['payloadRefs'], key=lambda pin: pin['path'])
    need(len({pin['path'] for pin in expected}) == len(expected) and
         sorted(originals['archivedFilePins'].values(), key=lambda pin: pin['path']) == expected,
         'AUDIT_FULL_PAYLOAD_READBACK_MISMATCH')
    archive = Path(point['manifestPin']['path']).parent.parent
    tree = reader.document(manifest['payloadTreePin']); generated = []
    for name, marker in tree.items():
        need(not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts,
             'AUDIT_PAYLOAD_TREE_PATH_INVALID')
        if marker == 'directory': continue
        need(type(marker) is str and re.fullmatch(r'file\|(0|[1-9][0-9]*)\|[0-9a-f]{64}', marker),
             'AUDIT_PAYLOAD_TREE_INVALID')
        _, size, digest = marker.split('|')
        generated.append(dict(path=(archive / name).as_posix(), bytes=int(size), sha256=digest))
    need(sorted(generated, key=lambda pin: pin['path']) == expected, 'AUDIT_PAYLOAD_TREE_MISMATCH')
    need(originals['readbackOriginalPins'], 'AUDIT_READBACK_COPIES_MISSING')
    for pin in originals['readbackOriginalPins'].values(): reader.require(pin)
    return dict(verificationMode='NATIVE_FULL_READBACK_EVIDENCE_AUDIT', payloadContentVerified=True,
        payloadFiles=len(expected), payloadBytes=sum(pin['bytes'] for pin in expected),
        independentConnectionId=native['independentConnectionId'], originalRecordsPin=native['originalRecordsPin'],
        retainedOriginalCopiesVerified=len(originals['readbackOriginalPins']), extraFullPayloadReadDispatched=False,
        serverDurabilityVerified=False)


def verify_request(reader, config, request, rows):
    """Re-derive immutable request configs with the pure production binder."""
    from recovery_control_capture_config import bind_documents
    operation, source = request['operationId'], request['sourceConfigRef']
    ledger = Path(config['ledgerRoot']) / operation
    need(reader.local(ledger / 'request.json') == request, 'AUDIT_UI_REQUEST_CHANGED')
    selected = reader.local(ledger / 'selection.json'); dispatch = reader.local(ledger / 'intent.json')
    need(dispatch['operationId'] == operation and dispatch['requestSha256'] == hashlib.sha256(canonical(request)).hexdigest()
         and dispatch['selection'] == selected, 'AUDIT_DISPATCH_BINDING_INVALID')
    root = Path(config['taskRoot']) / 'request-configurations' / operation
    inputs = reader.local(root / 'request-inputs.json')
    need(inputs['request'] == request and inputs['ownerConfigurationPin'] == config['sourceConfigurations'][source],
         'AUDIT_CAPTURE_INPUTS_CHANGED')
    need(selected['pointBindingPin'] == inputs['pointBindingPin'], 'AUDIT_SELECTED_PARENT_CHANGED')
    parent = None
    if request['action'] == 'INCREMENTAL':
        old = rows[request['parentChainRef']]
        binding = reader.document(old['output']['data']['repositoryBindingPin'])
        parent = dict(reference=old['reference'], sourceConfigRef=source, pointPin=old['pointPin'], point=old['point'],
            binding=binding, material=reader.document(binding['recoveryMaterialPin']), capturePoint=old['captured'])
        need(inputs['pointBindingPin'] == old['bindingPin'], 'AUDIT_PARENT_REQUEST_CHANGED')
    else: need(inputs['pointBindingPin'] is None, 'AUDIT_FULL_PARENT_FORBIDDEN')
    owner, capture, objects = bind_documents(request, reader.document(inputs['ownerConfigurationPin']),
        reader.document(inputs['captureConfigurationPin']), reader.document(inputs['objectSourcePin']), parent)
    need(reader.local(root / 'objects.json') == objects, 'AUDIT_OBJECT_REQUEST_CHANGED')
    capture['source']['objectSourcePin'] = reader.local_pin(root / 'objects.json')
    need(reader.local(root / 'capture.json') == capture, 'AUDIT_CAPTURE_REQUEST_CHANGED')
    owner['sources'][source]['configurationPath'] = (root / 'capture.json').as_posix()
    need(reader.local(root / 'repository.json') == owner and
         selected['ownerConfigurationPin'] == reader.local_pin(root / 'repository.json') and
         selected['ownerProgramPin'] == config['programPins']['repository'], 'AUDIT_OWNER_REQUEST_CHANGED')
    return ledger, selected, owner, capture


def verify_database(reader, current, material, rows, request):
    database, captured = material['database'], current['captured']
    need(database['endPosition'] == captured['databaseEnd'], 'AUDIT_DATABASE_END_CHANGED')
    report = dict(method=database['method'], startPosition=database['startPosition'], endPosition=database['endPosition'],
                  sqlPin=database['sqlPin'], rawSqlPin=database.get('rawSqlPin'), expectedDataPin=database['expectedDataPin'])
    if request['action'] == 'FULL':
        need(database['method'] == 'FORMAL_SQL_FULL' and database['startPosition'] is None and
             captured['databaseDelta'] == dict(kind='SQL_FULL', segments=[]), 'AUDIT_FULL_DATABASE_METHOD_INVALID')
        return report
    need(database['method'] == 'BINLOG_SQL' and database['startPosition'] ==
         rows[request['parentChainRef']]['captured']['databaseEnd'], 'AUDIT_INCREMENTAL_START_CHANGED')
    scopes = [pin for pin in current['point']['payloadRefs']
              if pin['path'].endswith('/payload/database.sql.incremental-scope.json')]
    need(len(scopes) == 1, 'AUDIT_INCREMENTAL_SCOPE_REQUIRED')
    scope = reader.document(scopes[0]); expected = reader.document(database['expectedDataPin'])
    from formal_data_evidence import incremental_observation_tables
    changed = incremental_observation_tables(expected, scope, captured, expected['schema']['database'])
    report.update(scopePin=scopes[0], scopePolicy=scope['policy'], affectedTables=expected['affectedTables'],
        affectedScope=changed, logMode=captured['databaseDelta']['logMode'], segments=[row['segment'] for row in scope['segments']],
        eventCount=sum(row['eventCount'] for row in scope['segments']),
        rowEventCount=sum(row['rowEventCount'] for row in scope['segments']),
        ddlEventCount=sum(row['ddlEventCount'] for row in scope['segments']))
    return report


def verify_dispatch_contract(*, request, selection, python_pin, request_pin, intent_pin,
                             reply_pin, owner_root, owner_result, launched, process, exited, reply):
    """Bind a launcher response to the one original, successfully completed owner.

    The repository CLI returns 2 for its specific asynchronous query response.
    That response alone proves no successful backup. The caller independently
    verifies the original owner's result pin, published point, and exit state.
    """
    operation = request['operationId']
    output_path = (PurePosixPath(request_pin['path']).parent / 'execute/result.json').as_posix()
    expected_argv = [python_pin['path'], selection['ownerProgramPin']['path'], '--configuration',
        selection['ownerConfigurationPin']['path'], '--request', request_pin['path'], '--output', output_path]
    need(all(row['operationId'] == row['requestId'] == operation for row in (launched, process, exited)) and
         launched['requestPin'] == exited['requestPin'] == request_pin and
         process['intentPin'] == exited['intentPin'] == intent_pin and
         type(process['pid']) is int and process['pid'] > 0 and process['pid'] == exited['pid'] and
         exited['timedOut'] is False and exited['resultPin'] == reply_pin and
         reply_pin['path'] == output_path and launched['restoreTargetPin'] is None and
         launched['pythonPin'] == python_pin and launched['programPin'] == selection['ownerProgramPin'] and
         launched['configurationPin'] == selection['ownerConfigurationPin'] and
         launched['argv'] == expected_argv, 'AUDIT_ORIGINAL_DISPATCH_INVALID')
    need(owner_result['operationId'] == owner_result['requestId'] == operation and
         owner_result['state'] == 'SUCCEEDED' and type(owner_result['actualExitCode']) is int and
         owner_result['actualExitCode'] == 0 and owner_result['failureCode'] is None,
         'AUDIT_ORIGINAL_OWNER_NOT_SUCCESSFUL')
    need(reply['schemaVersion'] == 'backup-restore-operation-result/v1' and
         reply['operationId'] == reply['requestId'] == operation and reply['action'] == request['action'] and
         type(exited['actualExitCode']) is int, 'AUDIT_ORIGINAL_REPLY_INVALID')
    if exited['actualExitCode'] == 0:
        need(reply == owner_result, 'AUDIT_SYNCHRONOUS_OWNER_RESULT_CHANGED')
        resolution = 'OWNER_TERMINAL_RETURNED_SYNCHRONOUSLY'
    elif exited['actualExitCode'] == 2:
        need(reply['state'] == 'TERMINAL_UNKNOWN' and reply['actualExitCode'] is None and
             reply['failureCode'] == 'REPOSITORY_QUERY_ORIGINAL_OPERATION' and
             reply['data'] == dict(operationDirectory=owner_root,
                 resultRef=(PurePosixPath(owner_root) / 'result.json').as_posix()),
             'AUDIT_ASYNCHRONOUS_OWNER_BINDING_INVALID')
        resolution = 'ORIGINAL_OWNER_TERMINAL_AFTER_ASYNC_REPLY'
    else:
        raise ValueError('AUDIT_ORIGINAL_LAUNCHER_EXIT_UNSUPPORTED')
    return dict(launcherActualExitCode=exited['actualExitCode'], launcherState=reply['state'],
        ownerActualExitCode=owner_result['actualExitCode'], ownerState=owner_result['state'],
        originalReplyPin=reply_pin, resolution=resolution)


def audit(spec):
    """Entry point executed read-only on the source host after native completion."""
    reader = AuditReader(seconds=spec.get('seconds', 120))
    package = verify_package(reader, spec)
    config = reader.document(spec['controlConfigurationPin'])
    need(config['programPins']['repository'] == reader.local_pin(Path(spec['engine']) / 'repository_entry.py'),
         'AUDIT_OWNER_PROGRAM_NOT_PACKAGED')
    sys.path[:0] = config['environment']['PYTHONPATH'].split(os.pathsep)
    request = spec['request']; operation, source = request['operationId'], request['sourceConfigRef']
    parent = spec.get('parent')
    if parent is None:
        need(request['action'] == 'FULL' and request['parentChainRef'] is None, 'AUDIT_FULL_REQUIRED')
        references = [operation]
    else:
        need(parent['schemaVersion'] == 'AutomaticBackupChainAudit/v1' and parent['status'] == 'PASS' and
             parent['sourceConfigRef'] == source and request['action'] == 'INCREMENTAL' and
             request['parentChainRef'] == parent['operationId'], 'AUDIT_PARENT_REPORT_INVALID')
        references = [row['operationId'] for row in parent['chain']] + [operation]
    rows, epoch = read_chain(reader, config, source, references)
    current = rows[operation]; point, output = current['point'], current['output']
    need(point['pointType'] == request['action'], 'AUDIT_ACTION_CHANGED')
    if parent is not None:
        need([rows[ref]['pointPin'] for ref in references[:-1]] == [row['pointPin'] for row in parent['chain']] and
             parent['sourceEpoch'] == epoch, 'AUDIT_PARENT_REPORT_CHANGED')
    ledger, selected, owner, capture_config = verify_request(reader, config, request, rows)
    need(selected['configurationPin'] == spec['controlConfigurationPin'] and selected['sourceEpoch'] == epoch,
         'AUDIT_SELECTED_GENERATION_CHANGED')
    owner_root = Path(owner['operationRoot']) / hashlib.sha256(operation.encode()).hexdigest()
    need(reader.local(owner_root / 'request.json') == request and
         reader.local_pin(owner_root / 'result.json') == current['resultPin'], 'AUDIT_UNIQUE_OWNER_RESULT_INVALID')
    start = reader.local(owner_root / 'start.json')
    need(start['configurationPin'] == selected['ownerConfigurationPin'] and start['readbackOnly'] is False and
         start['requestSha256'] == hashlib.sha256(canonical(request)).hexdigest(), 'AUDIT_OWNER_ADMISSION_CHANGED')
    launched = reader.local(ledger / 'execute/native-intent.json')
    process = reader.local(ledger / 'execute/native-process.json')
    exited = reader.local(ledger / 'execute/native-original-exit.json')
    reply_pin = reader.local_pin(ledger / 'execute/result.json')
    dispatch = verify_dispatch_contract(request=request, selection=selected, python_pin=config['pythonPin'],
        request_pin=reader.local_pin(ledger / 'request.json'),
        intent_pin=reader.local_pin(ledger / 'execute/native-intent.json'), reply_pin=reply_pin,
        owner_root=owner_root.as_posix(), owner_result=output, launched=launched, process=process,
        exited=exited, reply=reader.document(reply_pin))
    owner_process = reader.local(owner_root / 'worker-process.json')
    proc = Path('/proc') / str(owner_process['pid']) / 'cmdline'
    need(owner_process['operationId'] == operation and
         (not proc.exists() or str(owner_root).encode() not in proc.read_bytes()), 'AUDIT_OWNER_STILL_RUNNING')
    data = output['data']; manifest = reader.document(point['manifestPin'])
    need(data['manifestPin'] == point['manifestPin'] and data['readbackPin'] == point['readbackEvidencePin'] and
         point['rehearsalEligible'] is True and point['controlledRestoreEligible'] is False and
         point['blockedReason'] == 'REPOSITORY_RECOVERY_NOT_RUN', 'AUDIT_POINT_PUBLICATION_INVALID')
    readback = verify_readback(reader, point, manifest)
    close = reader.document(point['ownerCloseEvidencePin'])
    need(close['operationId'] == operation and close['archiveReaderClosed'] is True and
         close['closeResponse']['state'] == 'ARCHIVE_READER_CLOSED_NOT_NAS_PROOF', 'AUDIT_ARCHIVE_NOT_CLOSED')
    capture_result = reader.document(data['captureResultPin'])
    need(capture_result['operationId'] == capture_result['requestId'] == operation and
         capture_result['action'] == request['action'] and capture_result['state'] == 'SUCCEEDED' and
         capture_result['actualExitCode'] == 0 and capture_result['failureCode'] is None,
         'AUDIT_CAPTURE_NOT_SUCCESSFUL')
    restoration_pin = capture_result['data']['sourceRestorationPin']
    restoration = reader.document(restoration_pin)
    need(restoration['schemaVersion'] == 'minimal-capture-source-restoration/v1' and restoration['restored'] is True and
         restoration['errors'] == [] and restoration['sourceIdentity'] == current['captured']['sourceIdentity'],
         'AUDIT_SOURCE_NOT_RESTORED')
    repository = reader.document(data['repositoryBindingPin'])
    material = reader.document(repository['recoveryMaterialPin']); database = material['database']
    database_report = verify_database(reader, current, material, rows, request)
    objects = reader.document(repository['objectContentIndexPin'])
    expected_objects_parent = None if parent is None else reader.document(
        rows[request['parentChainRef']]['output']['data']['repositoryBindingPin'])['objectContentIndexPin']
    need(objects['repositoryBound'] is True and objects['parentExportIndexPin'] == expected_objects_parent,
         'AUDIT_OBJECT_PARENT_CHANGED')
    from recovery_backup_epoch import read_current
    policy = config['sourceEpochPolicies'][source]
    need(policy['sourceIdentity'] == current['captured']['sourceIdentity'] == capture_config['source']['sourceIdentity'] and
         policy['databaseUuid'] == database['endPosition']['databaseUuid'] == capture_config['source']['databaseUuid'] and
         policy['sourceLockPath'] == capture_config['sourceLockPath'] and read_current(policy) == epoch,
         'AUDIT_EPOCH_SOURCE_CHANGED')
    reader.finish()
    return dict(schemaVersion='AutomaticBackupChainAudit/v1', status='PASS', observedAt=datetime.now(timezone.utc).isoformat(),
        operationId=operation, sourceConfigRef=source, pointType=request['action'], state='SUCCEEDED', actualExitCode=0,
        finishedAt=output['finishedAt'], resultPin=current['resultPin'], pointPin=current['pointPin'],
        manifestPin=point['manifestPin'], generationId=point['generationId'], parentPointPins=point['parentPointPins'],
        sourceEpoch=epoch, epochBindingPin=current['epochBindingPin'], nativeLauncherExitCode=exited['actualExitCode'],
        nativeDispatch=dispatch,
        uniqueOwnerOperationVerified=True, sourceRestorationPin=restoration_pin, sourceRestored=True,
        sourceIndependentHealthCheckRequired=True, restoreExecuted=False, registeredTargetAdmissionRequired=True,
        chain=[dict(operationId=ref, pointPin=rows[ref]['pointPin'], pointType=rows[ref]['point']['pointType'],
                    epochBindingPin=rows[ref]['epochBindingPin']) for ref in references], package=package, readback=readback,
        database=database_report,
        objectDelta=dict(changedContentCount=len(objects['changedContentSha256']), parentExportIndexPin=expected_objects_parent),
        verifiedMetadataPins=len(reader.cache), metadataBytesRead=reader.total_bytes, **spec.get('deployment', {}))
