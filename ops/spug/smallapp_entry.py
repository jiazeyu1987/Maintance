"""Spug's three existing manual templates: business choices and original history.

No backup engine or native registry lives here. W08 supplies display registration;
W01 supplies live validated choices and execution. Original Spug auth, dispatcher
and History are reused without changing its source or old publishing tasks.
"""
import datetime
import contextlib
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import smallapp_adapter as adapter

SETTINGS = Path('/var/lib/intruoyi-spug/smallapp-entry-settings.json')
ENTRIES = adapter.RECORDS / 'ui'
ACTIONS = ('FULL', 'INCREMENTAL', 'RESTORE')
PREFIX = 'python3 /opt/intruoyi-spug/smallapp_adapter.py --business-action '
CHOICE_FIELDS = frozenset(('applicationId', 'sourceConfigRef', 'engineSelectionRef',
                          'fullReady', 'fullErrorCode', 'parentChainRefs',
                          'recoveryPointRefs', 'freshTargetConfigRefs', 'historyErrorCode'))


def need(condition, code):
    if not condition:
        raise adapter.Refused(code)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def record_path(operation_id, root=ENTRIES):
    need(adapter.reference(operation_id), 'OPERATION_ID_INVALID')
    return Path(root) / (hashlib.sha256(operation_id.encode()).hexdigest() + '.json')


def prepared_request(operation_id, action, root=ENTRIES):
    record = adapter.read_json(record_path(operation_id, root))
    request = adapter.validate_request(record.get('request'))
    need(request['action'] == action and request['operationId'] == operation_id,
         'PREPARED_OPERATION_MISMATCH')
    need(record.get('dispatchReserved') is True, 'SPUG_DISPATCH_RESERVATION_REQUIRED')
    journal = adapter.RECORDS / (hashlib.sha256(operation_id.encode()).hexdigest() + '.json')
    need(record.get('dispatchState') == 'DISPATCHING' or
         ('dispatchState' not in record and journal.is_file()), 'SPUG_DISPATCH_CLAIM_REQUIRED')
    return request


def settings(path=SETTINGS):
    need(Path(path).is_file(), 'W08_DISPLAY_SETTINGS_REQUIRED')
    value = adapter.read_json(path)
    need(set(value) == {'applications', 'tasks', 'initialOperationIds', 'registrationVersions'}, 'ENTRY_SETTINGS_INVALID')
    need(isinstance(value['applications'], list) and value['applications'], 'W08_REGISTRATION_REQUIRED')
    seen = set()
    sources = set()
    for app in value['applications']:
        need(isinstance(app, dict) and set(app) == {'applicationId', 'displayName', 'sourceConfigRef',
             'targetConfigRefs', 'engineSelectionRef', 'registrationSha256'}, 'W08_DISPLAY_PROJECTION_INVALID')
        need(adapter.reference(app['applicationId']) and app['applicationId'] not in seen,
             'W08_APPLICATION_ID_INVALID')
        need(isinstance(app['displayName'], str) and 0 < len(app['displayName']) <= 160 and
             not any(ord(c) < 32 for c in app['displayName']), 'W08_DISPLAY_NAME_INVALID')
        need(app['sourceConfigRef'] is None or adapter.reference(app['sourceConfigRef']), 'W08_SOURCE_INVALID')
        if app['sourceConfigRef'] is not None:
            need(app['sourceConfigRef'] not in sources, 'W08_DUPLICATE_SOURCE')
            sources.add(app['sourceConfigRef'])
        need(app['engineSelectionRef'] is None or adapter.reference(app['engineSelectionRef']), 'W08_ENGINE_INVALID')
        refs = app['targetConfigRefs']
        need(isinstance(refs, list) and all(adapter.reference(r) for r in refs) and
             len(set(refs)) == len(refs) and app['sourceConfigRef'] not in refs, 'W08_TARGETS_INVALID')
        need(isinstance(app['registrationSha256'], str) and re.fullmatch('[0-9a-f]{64}',
             app['registrationSha256']), 'W08_REGISTRATION_PIN_REQUIRED')
        seen.add(app['applicationId'])
    versions = value['registrationVersions']
    need(isinstance(versions, dict) and set(versions) == seen and
         all(v is None or adapter.reference(v) for v in versions.values()), 'W08_VERSION_PROJECTION_INVALID')
    need(isinstance(value['tasks'], dict) and set(value['tasks']) == set(ACTIONS) and
         all(type(t) is int and t > 0 for t in value['tasks'].values()) and
         len(set(value['tasks'].values())) == 3, 'SPUG_TEMPLATE_MAPPING_REQUIRED')
    need(isinstance(value['initialOperationIds'], dict), 'INITIAL_OPERATION_MAPPING_INVALID')
    for app_id, operations in value['initialOperationIds'].items():
        need(app_id in seen and isinstance(operations, dict) and set(operations) == set(ACTIONS) and
             all(adapter.reference(v) and len(v) >= 8 for v in operations.values()) and
             len(set(operations.values())) == 3, 'INITIAL_OPERATION_MAPPING_INVALID')
    return value


def validated_selections(payload, config):
    """Only W01's current authenticated choices matched to valid W08 metadata."""
    need(isinstance(payload, dict) and set(payload) == {'observedAt', 'applications'},
         'W01_SELECTION_FIELDS_INVALID')
    try:
        stamp = datetime.datetime.fromisoformat(payload['observedAt'].replace('Z', '+00:00'))
        age = (datetime.datetime.now(datetime.timezone.utc) - stamp).total_seconds()
    except (AttributeError, TypeError, ValueError):
        raise adapter.Refused('W01_SELECTION_TIMESTAMP_INVALID') from None
    need(-5 <= age <= 60, 'W01_SELECTION_OBSERVATION_STALE')
    need(isinstance(payload['applications'], list), 'W01_SELECTION_APPLICATIONS_INVALID')
    known = {a['applicationId']: a for a in config['applications']}
    rows = {}
    for item in payload['applications']:
        need(isinstance(item, dict) and set(item) == CHOICE_FIELDS, 'W01_SELECTION_ITEM_INVALID')
        app_id = item['applicationId']
        need(adapter.reference(app_id) and app_id in known and app_id not in rows, 'W01_APPLICATION_NOT_REGISTERED')
        app = known[app_id]
        need(adapter.reference(item['sourceConfigRef']) and item['sourceConfigRef'] == app['sourceConfigRef'],
             'W01_SOURCE_REGISTRATION_MISMATCH')
        need(type(item['fullReady']) is bool and
             ((item['fullReady'] and item['fullErrorCode'] is None and adapter.reference(item['engineSelectionRef'])) or
              (not item['fullReady'] and adapter.symbolic_error(item['fullErrorCode']) and
               (item['engineSelectionRef'] is None or adapter.reference(item['engineSelectionRef'])))),
             'W01_SOURCE_READINESS_INVALID')
        need(item['historyErrorCode'] is None or adapter.symbolic_error(item['historyErrorCode']),
             'W01_HISTORY_ERROR_INVALID')
        need(item['historyErrorCode'] is None or not item['parentChainRefs'] and not item['recoveryPointRefs'],
             'W01_HISTORY_REFERENCES_UNVERIFIED')
        for field in ('parentChainRefs', 'recoveryPointRefs', 'freshTargetConfigRefs'):
            refs = item[field]
            need(isinstance(refs, list) and len(refs) <= 1000 and all(adapter.reference(r) for r in refs) and
                 len(set(refs)) == len(refs), 'W01_SELECTION_REFERENCES_INVALID')
        need(set(item['freshTargetConfigRefs']).issubset(set(app['targetConfigRefs'])), 'W01_TARGET_NOT_REGISTERED')
        rows[app_id] = item
    return rows


def catalogue(config, bridge):
    rows = validated_selections(bridge.selections(), config)
    return [dict(app, validated=rows.get(app['applicationId']),
                 readinessError=None if app['applicationId'] in rows else 'SOURCE_NOT_VERIFIED_BY_W01')
            for app in config['applications']]


def application_catalogue(config, application_id):
    matches = [app for app in config['applications'] if app['applicationId'] == application_id]
    need(len(matches) == 1 and matches[0]['sourceConfigRef'] is not None, 'SOURCE_NOT_REGISTERED_BY_W08')
    return catalogue(config, adapter.HttpBridge(source_ref=matches[0]['sourceConfigRef']))


def admit_selection(request, config, bridge):
    adapter.validate_request(request)
    bridge.validate_binding(request)
    matches = [a for a in config['applications'] if a['sourceConfigRef'] == request['sourceConfigRef']]
    need(len(matches) == 1, 'SOURCE_NOT_REGISTERED_BY_W08')
    app = matches[0]
    rows = validated_selections(bridge.selections(), config)
    choice = rows.get(app['applicationId'])
    need(choice is not None, 'SOURCE_NOT_VERIFIED_BY_W01')
    if request['action'] != 'RESTORE':
        need(choice['fullReady'], choice['fullErrorCode'])
    if request['action'] != 'FULL':
        need(choice['historyErrorCode'] is None, choice['historyErrorCode'])
    if request['action'] == 'INCREMENTAL':
        need(request['parentChainRef'] in choice['parentChainRefs'], 'PARENT_CHAIN_NOT_ACCEPTED')
    elif request['action'] == 'RESTORE':
        need(request['recoveryPointRef'] in choice['recoveryPointRefs'], 'RECOVERY_POINT_NOT_ACCEPTED')
        need(request['targetConfigRef'] in choice['freshTargetConfigRefs'], 'TARGET_NOT_CURRENTLY_FRESH')
    return app


def validate_prepared_binding(operation_id, bridge, config=None, root=ENTRIES):
    record = adapter.read_json(record_path(operation_id, root))
    config = settings() if config is None else config
    apps = [a for a in config['applications'] if a['applicationId'] == record.get('applicationId')]
    need(len(apps) == 1 and apps[0]['sourceConfigRef'] == record['request']['sourceConfigRef'],
         'PREPARED_SOURCE_CHANGED')
    need(record.get('bridgeFingerprint') == bridge.fingerprint, 'ORIGINAL_BRIDGE_BINDING_CHANGED')


@contextlib.contextmanager
def source_reservation_lock(source_ref, root):
    """The OS releases ownership on exit, including abrupt process termination.

    Keep the file inode permanently. A legacy mkdir lock at the same path is an
    explicit migration blocker; never remove it or guess whether its owner died.
    Old entry processes also refuse this file, so mixed versions cannot bypass it.
    """
    Path(root).mkdir(parents=True, exist_ok=True)
    lock = Path(root) / (hashlib.sha256(source_ref.encode()).hexdigest() + '.reserve-lock')
    need(not lock.is_dir(), 'SOURCE_SUBMISSION_LEGACY_LOCK_PRESENT')
    try:
        stream = lock.open('a+b')
    except OSError:
        need(not lock.is_dir(), 'SOURCE_SUBMISSION_LEGACY_LOCK_PRESENT')
        raise
    with stream:
        if os.name == 'posix':
            import fcntl
            acquire = lambda: fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            release = lambda: fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        elif os.name == 'nt':
            import msvcrt
            if os.fstat(stream.fileno()).st_size == 0:
                stream.write(b'\0')
                stream.flush()
            stream.seek(0)
            acquire = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            release = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            raise adapter.Refused('SOURCE_SUBMISSION_LOCK_PLATFORM_UNSUPPORTED')
        try:
            acquire()
        except OSError as error:
            if error.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise adapter.Refused('SOURCE_SUBMISSION_RESERVATION_BUSY') from None
            raise
        try:
            yield
        finally:
            release()


def reserve(request, config, bridge, user_id, root=ENTRIES):
    """Once-only Spug dispatch. Lost reply/server restart never invents a rerun."""
    adapter.validate_request(request)
    with source_reservation_lock(request['sourceConfigRef'], root):
        return reserve_locked(request, config, bridge, user_id, root)


def reserve_locked(request, config, bridge, user_id, root):
    path = record_path(request['operationId'], root)
    if path.exists():
        record = adapter.read_json(path)
        need(record.get('request') == request, 'OPERATION_ID_REQUEST_REUSE_REJECTED')
        return record, False
    # An unknown original cannot be bypassed by generating another operation ID.
    for prior_path in Path(root).glob('*.json'):
        prior = adapter.read_json(prior_path)
        original = adapter.validate_request(prior.get('request'))
        if original['sourceConfigRef'] != request['sourceConfigRef']:
            continue
        if prior.get('dispatchState') == 'CANCELLED_UNACCEPTED':
            validate_cancellation(prior)
            continue
        journal_path = adapter.RECORDS / (hashlib.sha256(original['operationId'].encode()).hexdigest() + '.json')
        need(journal_path.exists(), 'ORIGINAL_OPERATION_STILL_UNRESOLVED')
        original_bridge = bridge.for_request(original)
        need(prior.get('bridgeFingerprint') == original_bridge.fingerprint,
             'ORIGINAL_BRIDGE_BINDING_CHANGED')
        # execute validates the full journal identity and reuses durable terminal
        # evidence. Only unresolved originals need another authenticated GET.
        current = adapter.execute(original, original_bridge, root=adapter.RECORDS, query_only=True)
        need(current['state'] in ('SUCCEEDED', 'FAILED'), 'ORIGINAL_OPERATION_STILL_UNRESOLVED')
    app = admit_selection(request, config, bridge)
    record = dict(request=request, applicationId=app['applicationId'], registrationSha256=app['registrationSha256'],
                  spugTaskId=config['tasks'][request['action']], ownerUserId=user_id, createdAt=now(),
                  bridgeFingerprint=bridge.fingerprint, dispatchReserved=True, spugHistoryId=None,
                  dispatchErrorCode=None, dispatchState='RESERVED', dispatchToken=uuid.uuid4().hex,
                  dispatchAudit=[dict(state='RESERVED', at=now(), userId=user_id)])
    try:
        adapter.write_json(path, record, exclusive=True)
        return record, True
    except FileExistsError:
        original = adapter.read_json(path)
        need(original.get('request') == request, 'OPERATION_ID_REQUEST_REUSE_REJECTED')
        return original, False


def public_record(record):
    # Whitelist only public request/result references. Never include credentials/native originals.
    return dict({key: record[key] for key in ('request', 'applicationId', 'spugTaskId', 'createdAt',
            'spugHistoryId', 'dispatchErrorCode')}, dispatchState=record.get('dispatchState'),
            cancelledUnaccepted=record.get('dispatchState') == 'CANCELLED_UNACCEPTED')


def validate_cancellation(record):
    audit = record.get('dispatchAudit')
    need(record.get('dispatchReserved') is False and record.get('spugHistoryId') is None and
         record.get('dispatchErrorCode') is None and isinstance(audit, list) and len(audit) == 1 and
         audit[0].get('state') == 'CANCELLED_UNACCEPTED' and
         audit[0].get('evidence') == 'OPERATION_NOT_FOUND', 'CANCELLATION_EVIDENCE_INVALID')


def unaccepted_retry_result(request, application_id, entry_exists, journal_exists,
                            history_exists, native_error):
    """Read-only absence evidence bound to the complete unchanged UI request."""
    adapter.validate_request(request)
    need(not entry_exists and not journal_exists and not history_exists,
         'ORIGINAL_OPERATION_ALREADY_RECORDED')
    need(native_error == 'OPERATION_NOT_FOUND', 'ORIGINAL_OPERATION_NOT_PROVEN_UNACCEPTED')
    return dict(request=request, applicationId=application_id, retryAllowed=True)


def operation_history_exists(operation_id, config):
    from apps.schedule.models import History
    return History.objects.filter(task_id__in=config['tasks'].values(), output__contains=operation_id).exists()


def native_absence(request, config, bridge, root=ENTRIES, allow_reserved=False):
    adapter.validate_request(request)
    bridge.validate_binding(request)
    apps = [a for a in config['applications'] if a['sourceConfigRef'] == request['sourceConfigRef']]
    need(len(apps) == 1, 'SOURCE_NOT_REGISTERED_BY_W08')
    operation_id = request['operationId']
    journal = adapter.RECORDS / (hashlib.sha256(operation_id.encode()).hexdigest() + '.json')

    def recorded():
        return (record_path(operation_id, root).exists(), journal.exists(),
                operation_history_exists(operation_id, config))

    def require_absence():
        local, journal_exists, history_exists = recorded()
        need(not journal_exists and not history_exists and (allow_reserved or not local),
             'ORIGINAL_OPERATION_ALREADY_RECORDED')

    require_absence()
    try:
        adapter.validate_result(bridge.query(operation_id), request)
    except adapter.Refused as error:
        if str(error) != 'OPERATION_NOT_FOUND':
            raise
    else:
        raise adapter.Refused('ORIGINAL_OPERATION_ALREADY_ACCEPTED')
    # Recheck local acceptance after the GET. The eventual POST still uses the
    # original exclusive reservation and same-source nonterminal guard.
    require_absence()
    return apps[0]


def unaccepted_original(request, config, bridge):
    app = native_absence(request, config, bridge)
    return unaccepted_retry_result(request, app['applicationId'], False, False, False, 'OPERATION_NOT_FOUND')


def cancel_unaccepted(request, config, bridge, user_id, root=ENTRIES):
    """Fence a late original POST before allowing the browser to edit its draft."""
    adapter.validate_request(request)
    with source_reservation_lock(request['sourceConfigRef'], root):
        path = record_path(request['operationId'], root)
        if path.exists():
            record = adapter.read_json(path)
            need(record.get('request') == request, 'OPERATION_ID_REQUEST_REUSE_REJECTED')
            need(record.get('dispatchState') == 'CANCELLED_UNACCEPTED', 'ORIGINAL_OPERATION_ALREADY_RECORDED')
            validate_cancellation(record)
            return record
        app = native_absence(request, config, bridge, root)
        record = dict(request=request, applicationId=app['applicationId'],
                      registrationSha256=app['registrationSha256'], bridgeFingerprint=bridge.fingerprint,
                      spugTaskId=config['tasks'][request['action']], ownerUserId=user_id,
                      createdAt=now(), spugHistoryId=None, dispatchErrorCode=None, dispatchReserved=False,
                      dispatchState='CANCELLED_UNACCEPTED',
                      dispatchAudit=[dict(state='CANCELLED_UNACCEPTED', at=now(), userId=user_id,
                                          evidence='OPERATION_NOT_FOUND')])
        adapter.write_json(path, record, exclusive=True)
        return record


def recover_reserved(request, config, bridge, user_id, root=ENTRIES):
    """Explicit recovery of the pre-dispatch window only; never replay unknown work."""
    adapter.validate_request(request)
    with source_reservation_lock(request['sourceConfigRef'], root):
        path = record_path(request['operationId'], root)
        record = adapter.read_json(path)
        need(record.get('request') == request, 'OPERATION_ID_REQUEST_REUSE_REJECTED')
        need(record.get('dispatchState') == 'RESERVED' and bool(record.get('dispatchToken')),
             'ORIGINAL_DISPATCH_NOT_RECOVERABLE')
        need(not record.get('spugHistoryId') and not record.get('dispatchErrorCode'),
             'ORIGINAL_DISPATCH_NOT_RECOVERABLE')
        need(record.get('bridgeFingerprint') == bridge.fingerprint, 'ORIGINAL_BRIDGE_BINDING_CHANGED')
        native_absence(request, config, bridge, root, allow_reserved=True)
        app = admit_selection(request, config, bridge)
        need(record['applicationId'] == app['applicationId'] and
             record['registrationSha256'] == app['registrationSha256'] and
             record['spugTaskId'] == config['tasks'][request['action']], 'PREPARED_SOURCE_CHANGED')
        # Revoke the old queued dispatch capability while holding the same lock
        # used by dispatch. A stale thread can no longer enter dispatch_job.
        previous = record['dispatchToken']
        record['dispatchToken'] = uuid.uuid4().hex
        record['dispatchAudit'].append(dict(state='RESERVED', at=now(), userId=user_id,
            evidence='OPERATION_NOT_FOUND', revokedToken=previous, token=record['dispatchToken']))
        adapter.write_json(path, record)
        return record


def claim_dispatch(record, root=ENTRIES):
    request = adapter.validate_request(record['request'])
    with source_reservation_lock(request['sourceConfigRef'], root):
        path = record_path(request['operationId'], root)
        current = adapter.read_json(path)
        need(current.get('request') == request, 'OPERATION_ID_REQUEST_REUSE_REJECTED')
        if current.get('dispatchState') != 'RESERVED' or current.get('dispatchToken') != record.get('dispatchToken'):
            return None  # This queued capability was explicitly revoked or claimed.
        current['dispatchState'] = 'DISPATCHING'
        current['dispatchAudit'].append(dict(state='DISPATCHING', at=now(), token=current['dispatchToken']))
        adapter.write_json(path, current)
        return current


def original_result(operation_id, root=ENTRIES, journal=adapter.RECORDS):
    path = record_path(operation_id, root)
    need(path.exists(), 'ORIGINAL_OPERATION_NOT_LOCALLY_RECORDED')
    record = adapter.read_json(path)
    request = adapter.validate_request(record.get('request'))
    need(request['operationId'] == operation_id, 'PREPARED_OPERATION_MISMATCH')
    if record.get('dispatchState') == 'CANCELLED_UNACCEPTED':
        validate_cancellation(record)
        return dict(public_record(record), result=None, repeatSubmissionAllowed=False)
    result = adapter.running(request, 'ORIGINAL_EXECUTION_NOT_YET_OBSERVED')
    journal_path = Path(journal) / (hashlib.sha256(operation_id.encode()).hexdigest() + '.json')
    if journal_path.exists():
        try:
            result = adapter.execute(request, adapter.request_bridge(request), root=journal, query_only=True)
        except adapter.Refused as error:
            result = adapter.running(request, str(error))
    elif record.get('dispatchErrorCode'):
        result = adapter.running(request, record['dispatchErrorCode'])
    return dict(public_record(record), result=result, repeatSubmissionAllowed=False)


def installed_task(config, action):
    from apps.schedule.models import Task
    task = Task.objects.filter(pk=config['tasks'][action]).first()
    need(task is not None and not task.is_active and task.command == PREFIX + action and
         task.interpreter == 'sh' and json.loads(task.targets) == ['local'], 'SPUG_MANUAL_TEMPLATE_CHANGED')
    return task


def dispatch(record, config):
    """Original local Spug dispatcher + native task history; immutable per-run args."""
    try:
        record = claim_dispatch(record)
    except (adapter.Refused, OSError):
        print(json.dumps({'errorCode': 'SPUG_DISPATCH_CLAIM_FAILED',
                          'operationId': record['request']['operationId'], 'retryAllowed': False}), flush=True)
        return
    if record is None:
        return
    from apps.schedule.executors import dispatch_job
    from apps.schedule.models import History
    from libs import human_datetime
    from django.db import close_old_connections
    path = record_path(record['request']['operationId'])
    try:
        task = installed_task(config, record['request']['action'])
        command = task.command + ' --prepared-operation ' + shlex.quote(record['request']['operationId'])
        code, duration, output = dispatch_job('local', task.interpreter, command)
        history = History.objects.create(task_id=task.id, status=1 if code == 0 else 2,
                         run_time=human_datetime(), output=json.dumps({'local': [code, duration, output]}))
        record['spugHistoryId'] = history.id
    except adapter.Refused as error:
        record['dispatchErrorCode'] = str(error)
    except Exception:
        # Explicit failed/unknown boundary; no raw upstream data and no retry.
        record['dispatchErrorCode'] = 'SPUG_DISPATCH_OR_HISTORY_FAILED'
    finally:
        try:
            adapter.write_json(path, record)
        except (OSError, adapter.Refused):
            print(json.dumps({'errorCode': 'SPUG_DISPATCH_JOURNAL_UPDATE_FAILED',
                              'operationId': record['request']['operationId'], 'retryAllowed': False}), flush=True)
        close_old_connections()


def initialize_spug():
    sys.dont_write_bytecode = True
    sys.path.insert(0, '/data/spug/spug_api')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'spug.settings'
    import django
    django.setup()


def handler():
    from django.test import RequestFactory
    from django.db import close_old_connections
    from libs.middleware import AuthenticationMiddleware
    auth = AuthenticationMiddleware(lambda request: None)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'SpugManualBackupEntry'
        sys_version = ''

        def log_message(self, fmt, *args):
            return  # Never log token-bearing headers or parameter bodies.

        def reply(self, status, value):
            raw = json.dumps(value, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(raw)

        def authorize(self, edit=False):
            need(self.client_address[0] == '127.0.0.1', 'ENTRY_LOOPBACK_ONLY')
            token = self.headers.get_all('X-Token', [])
            need(len(token) == 1 and re.fullmatch('[0-9a-f]{32}', token[0]), 'SPUG_LOGIN_REQUIRED')
            request = RequestFactory().get('/smallapp-entry/', HTTP_X_TOKEN=token[0],
                          HTTP_X_FORWARDED_FOR=self.headers.get('X-Forwarded-For', ''))
            need(auth.process_request(request) is None and not request.user.is_deleted, 'SPUG_LOGIN_REQUIRED')
            need(bool(request.user.has_perms(['schedule.schedule.view'])), 'SPUG_VIEW_PERMISSION_REQUIRED')
            if edit:
                need(bool(request.user.has_perms(['schedule.schedule.edit'])), 'SPUG_EXECUTE_PERMISSION_REQUIRED')
                need(self.headers.get('Origin') == 'http://127.0.0.1:18080', 'ENTRY_REQUEST_ORIGIN_REFUSED')
            return request.user.id

        def do_GET(self):
            try:
                self.authorize()
                if self.path == '/simple-config':
                    import smallapp_simple
                    self.reply(200, smallapp_simple.public_configuration())
                elif self.path.startswith('/progress/') and self.path.count('/') == 2:
                    import smallapp_simple
                    operation = self.path[len('/progress/'):]
                    record = adapter.read_json(record_path(operation))
                    self.reply(200, smallapp_simple.progress(record))
                elif urlsplit(self.path).path == '/selections':
                    config = settings()
                    try:
                        query = urlsplit(self.path).query
                        parameters = parse_qs(query, strict_parsing=True) if query else {}
                        if parameters:
                            need(set(parameters) == {'applicationId'} and len(parameters['applicationId']) == 1, 'ENTRY_ROUTE_UNKNOWN')
                            apps = application_catalogue(config, parameters['applicationId'][0])
                        else:
                            apps = [dict(a, validated=None, readinessError='SOURCE_NOT_VERIFIED_BY_W01') for a in config['applications']]
                        code = None
                    except adapter.Refused as error:
                        code = str(error)
                        apps = [dict(a, validated=None, readinessError=code) for a in config['applications']]
                    self.reply(200, dict(applications=apps, errorCode=code, tasks=config['tasks'],
                                        initialOperationIds=config['initialOperationIds'],
                                        registrationVersions=config['registrationVersions']))
                elif self.path == '/history':
                    entries = []
                    for path in ENTRIES.glob('*.json'):
                        entries.append(public_record(adapter.read_json(path)))
                    self.reply(200, sorted(entries, key=lambda r: r['createdAt'], reverse=True))
                elif self.path.startswith('/unaccepted-original?'):
                    need(len(self.path) <= 4096, 'ENTRY_BODY_INVALID')
                    values = parse_qs(urlsplit(self.path).query, strict_parsing=True)
                    need(set(values) == {'request'} and len(values['request']) == 1, 'ENTRY_BODY_INVALID')
                    try:
                        request = json.loads(values['request'][0])
                    except (UnicodeError, ValueError):
                        raise adapter.Refused('ENTRY_BODY_INVALID') from None
                    self.reply(200, unaccepted_original(request, settings(), adapter.request_bridge(request)))
                elif self.path.startswith('/operations/') and self.path.count('/') == 2:
                    self.reply(200, original_result(self.path[len('/operations/'):]))
                else:
                    raise adapter.Refused('ENTRY_ROUTE_UNKNOWN')
            except adapter.Refused as error:
                self.reply(401 if str(error) == 'SPUG_LOGIN_REQUIRED' else 409, {'errorCode': str(error)})
            except Exception:
                self.reply(500, {'errorCode': 'ENTRY_READ_FAILED'})
            finally:
                close_old_connections()

        def do_POST(self):
            try:
                user_id = self.authorize(edit=True)
                need(self.path in ('/operations', '/cancel-unaccepted', '/recover-reserved'), 'ENTRY_ROUTE_UNKNOWN')
                need(not self.headers.get_all('Transfer-Encoding', []), 'ENTRY_BODY_INVALID')
                sizes = self.headers.get_all('Content-Length', [])
                need(len(sizes) == 1 and re.fullmatch('[0-9]+', sizes[0]), 'ENTRY_BODY_INVALID')
                size = int(sizes[0])
                need(0 < size <= 4096 and self.headers.get_content_type() == 'application/json', 'ENTRY_BODY_INVALID')
                raw = self.rfile.read(size)
                need(len(raw) == size, 'ENTRY_BODY_TRUNCATED')
                try:
                    value = json.loads(raw.decode('utf-8'))
                except (UnicodeError, ValueError):
                    raise adapter.Refused('ENTRY_BODY_INVALID') from None
                adapter.validate_request(value)
                if self.path == '/cancel-unaccepted':
                    record = cancel_unaccepted(value, settings(),
                        adapter.request_bridge(value), user_id)
                    self.reply(200, dict(public_record(record), result=None, repeatSubmissionAllowed=False))
                    return
                if self.path == '/recover-reserved':
                    config = settings()
                    installed_task(config, value['action'])
                    record = recover_reserved(value, config,
                        adapter.request_bridge(value), user_id)
                    threading.Thread(target=dispatch, args=(record, config), daemon=False).start()
                    self.reply(202, dict(public_record(record),
                        result=adapter.running(value, 'SPUG_DISPATCH_RESERVED'), repeatSubmissionAllowed=False))
                    return
                # Check immutable original first; a repeated request only queries.
                path = record_path(value['operationId'])
                if path.exists():
                    need(adapter.read_json(path).get('request') == value, 'OPERATION_ID_REQUEST_REUSE_REJECTED')
                    self.reply(200, original_result(value['operationId']))
                    return
                config = settings()
                installed_task(config, value['action'])
                record, first = reserve(value, config, adapter.request_bridge(value), user_id)
                if not first:
                    self.reply(200, original_result(value['operationId']))
                    return
                threading.Thread(target=dispatch, args=(record, config), daemon=False).start()
                self.reply(202, dict(public_record(record),
                    result=adapter.running(value, 'SPUG_DISPATCH_RESERVED'), repeatSubmissionAllowed=False))
            except adapter.Refused as error:
                self.reply(401 if str(error) == 'SPUG_LOGIN_REQUIRED' else 409, {'errorCode': str(error)})
            except Exception:
                self.reply(500, {'errorCode': 'ENTRY_SUBMISSION_OUTCOME_UNKNOWN', 'retryAllowed': False})
            finally:
                close_old_connections()
    return Handler


if __name__ == '__main__':
    initialize_spug()
    # The page can report missing actual settings; missing input never enables execution.
    with ThreadingHTTPServer(('127.0.0.1', 18081), handler()) as server:
        server.daemon_threads = False
        server.serve_forever(poll_interval=0.5)
