"""Manual Spug entries for the existing W01 small-app execution bridge.

No capture/restore implementation lives here. A request is durably reserved before
one submission; repeated clicks and uncertain replies only query the original ID.
Private transport bindings must be supplied from W01's actual delivery.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

REQUEST_FIELDS = frozenset(('schemaVersion', 'operationId', 'action', 'sourceConfigRef',
                            'parentChainRef', 'recoveryPointRef', 'targetConfigRef'))
RESULT_FIELDS = frozenset(('schemaVersion', 'operationId', 'action', 'state',
                           'errorCode', 'logRefs', 'resultRef'))
STATES = frozenset(('RUNNING', 'SUCCEEDED', 'FAILED'))
PRIVATE = Path('/run/intruoyi-spug')
RECORDS = Path('/var/lib/intruoyi-spug/smallapp')


class Refused(Exception):
    """A safe symbolic error; never attach raw credentials or upstream text."""


def reference(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}', value) is not None


def symbolic_error(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Z][A-Z0-9_]{0,95}', value) is not None


def validate_request(value):
    if not isinstance(value, dict) or set(value) != REQUEST_FIELDS:
        raise Refused('REQUEST_FIELDS_INVALID')
    if value['schemaVersion'] != 'SmallAppBackupUiRequest/v1':
        raise Refused('REQUEST_SCHEMA_INVALID')
    if not reference(value['operationId']) or len(value['operationId']) < 8:
        raise Refused('OPERATION_ID_INVALID')
    if not reference(value['sourceConfigRef']):
        raise Refused('SOURCE_CONFIG_REF_INVALID')
    action = value['action']
    if not isinstance(action, str) or action not in ('FULL', 'INCREMENTAL', 'RESTORE'):
        raise Refused('ACTION_INVALID')
    if action == 'FULL':
        if any(value[k] is not None for k in ('parentChainRef', 'recoveryPointRef', 'targetConfigRef')):
            raise Refused('FULL_REFERENCE_CONFLICT')
    elif action == 'INCREMENTAL':
        if not reference(value['parentChainRef']):
            raise Refused('AUTHENTIC_PARENT_CHAIN_REF_REQUIRED')
        if value['recoveryPointRef'] is not None or value['targetConfigRef'] is not None:
            raise Refused('INCREMENTAL_REFERENCE_CONFLICT')
    else:
        if not reference(value['recoveryPointRef']):
            raise Refused('AUTHENTIC_RECOVERY_POINT_REF_REQUIRED')
        if not reference(value['targetConfigRef']) or value['parentChainRef'] is not None:
            raise Refused('FRESH_TASK_TARGET_REQUIRED')
    return value


def validate_result(value, request):
    if not isinstance(value, dict) or set(value) != RESULT_FIELDS:
        raise Refused('BRIDGE_RESULT_FIELDS_INVALID')
    if value['schemaVersion'] != 'SmallAppBackupUiResult/v1':
        raise Refused('BRIDGE_RESULT_SCHEMA_INVALID')
    if value['operationId'] != request['operationId'] or value['action'] != request['action']:
        raise Refused('BRIDGE_ORIGINAL_OPERATION_MISMATCH')
    if not isinstance(value['state'], str) or value['state'] not in STATES:
        raise Refused('BRIDGE_STATE_INVALID')
    code = value['errorCode']
    if code is not None and not symbolic_error(code):
        raise Refused('BRIDGE_ERROR_CODE_UNSAFE')
    if not isinstance(value['logRefs'], list) or len(value['logRefs']) > 100 or any(not reference(r) for r in value['logRefs']):
        raise Refused('BRIDGE_LOG_REFERENCES_UNSAFE')
    if value['resultRef'] is not None and not reference(value['resultRef']):
        raise Refused('BRIDGE_RESULT_REFERENCE_UNSAFE')
    if value['state'] == 'SUCCEEDED' and (not value['resultRef'] or code is not None):
        raise Refused('BRIDGE_SUCCESS_EVIDENCE_MISSING')
    return value


def running(request, code=None):
    return dict(schemaVersion='SmallAppBackupUiResult/v1', operationId=request['operationId'],
                action=request['action'], state='RUNNING', errorCode=code, logRefs=[], resultRef=None)


def read_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        raise Refused('LOCAL_INPUT_MISSING_OR_INVALID') from None
    if not isinstance(value, dict):
        raise Refused('LOCAL_INPUT_MISSING_OR_INVALID')
    return value


def sync_directory(path):
    if os.name != 'nt':
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def write_json(path, value, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path if exclusive else path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    if not exclusive:
        os.replace(temporary, path)
    sync_directory(path.parent)
    if read_json(path) != value:
        raise Refused('JOURNAL_READBACK_FAILED')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Refused('BRIDGE_REDIRECT_REFUSED')


class HttpBridge:
    """Explicit private endpoints, never an IntRuoyi release admin-api route."""
    def __init__(self, path=PRIVATE / 'smallapp-bridge.private.json'):
        if not Path(path).is_file():
            raise Refused('W01_TRANSPORT_BINDING_REQUIRED')
        config = read_json(path)
        self.source_refs = config.get('sourceConfigRefs')
        self.target_refs = config.get('targetConfigRefs')
        for refs in (self.source_refs, self.target_refs):
            if not isinstance(refs, list) or any(not reference(r) for r in refs) or len(set(refs)) != len(refs):
                raise Refused('W01_REGISTERED_CONFIG_BINDING_REQUIRED')
        if not self.source_refs:
            raise Refused('W01_REGISTERED_CONFIG_BINDING_REQUIRED')
        self.submit_url = config.get('submitUrl')
        self.query_template = config.get('queryUrlTemplate')
        if not isinstance(self.query_template, str) or self.query_template.count('{operationId}') != 1:
            raise Refused('W01_QUERY_ENDPOINT_REQUIRED')
        urls = [self.submit_url, self.query_template.replace('{operationId}', 'operation-check')]
        origins = []
        for value in urls:
            if not isinstance(value, str):
                raise Refused('W01_ENDPOINT_REQUIRED')
            parsed = urllib.parse.urlsplit(value)
            if (parsed.scheme not in ('http', 'https') or parsed.hostname not in
                    ('host.docker.internal', '127.0.0.1', 'localhost', '172.30.30.59')
                    or parsed.username or parsed.password or parsed.fragment or parsed.query
                    or not parsed.path or '/admin-api' in parsed.path):
                raise Refused('W01_ENDPOINT_OUTSIDE_BATCH')
            origins.append((parsed.scheme, parsed.hostname, parsed.port))
        if origins[0] != origins[1]:
            raise Refused('W01_ENDPOINT_ORIGIN_MISMATCH')
        self.origin = origins[0]
        self.selection_url = config.get('selectionUrl')
        credential = config.get('credentialRef')
        if not isinstance(credential, str) or re.fullmatch(r'[A-Za-z0-9_.-]+\.json', credential) is None:
            raise Refused('W01_PRIVATE_CREDENTIAL_REF_REQUIRED')
        self.headers = read_json(Path(path).parent / credential).get('headers')
        if not isinstance(self.headers, dict) or any(
                not isinstance(k, str) or re.fullmatch(r'[A-Za-z0-9-]+', k) is None
                or not isinstance(v, str) or '\r' in v or '\n' in v for k, v in self.headers.items()):
            raise Refused('W01_PRIVATE_AUTH_INVALID')
        if any(k.lower() in ('host', 'content-length', 'content-type') for k in self.headers):
            raise Refused('W01_PRIVATE_AUTH_HEADER_REFUSED')
        self.fingerprint = hashlib.sha256(json.dumps(urls, separators=(',', ':')).encode()).hexdigest()
        self.opener = urllib.request.build_opener(NoRedirect())
        self.requests = []

    def validate_binding(self, request):
        # Logical refs are explicit inputs, not application-specific code branches.
        # W01 remains responsible for authoritative registry and fresh-target proof.
        if request['sourceConfigRef'] not in self.source_refs:
            raise Refused('SOURCE_NOT_IN_CURRENT_BINDING')
        if request['action'] == 'RESTORE' and request['targetConfigRef'] not in self.target_refs:
            raise Refused('TARGET_NOT_IN_CURRENT_BINDING')

    def call(self, url, request=None):
        self.requests.append('GET' if request is None else 'POST')
        data = None if request is None else json.dumps(request, separators=(',', ':')).encode('utf-8')
        headers = {**self.headers, 'Content-Type': 'application/json'}
        try:
            with self.opener.open(urllib.request.Request(url, data=data, headers=headers), timeout=10) as response:
                body = response.read(65537)
                if len(body) > 65536:
                    raise Refused('BRIDGE_RESPONSE_TOO_LARGE')
                return json.loads(body.decode('utf-8'))
        except urllib.error.HTTPError as error:
            body = error.read(65537)
            try:
                value = json.loads(body.decode('utf-8')) if len(body) <= 65536 else None
            except (UnicodeError, ValueError):
                raise Refused('BRIDGE_HTTP_' + str(error.code)) from None
            if isinstance(value, dict) and set(value) == {'errorCode'} and symbolic_error(value['errorCode']):
                raise Refused(value['errorCode']) from None
            raise Refused('BRIDGE_HTTP_' + str(error.code)) from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise Refused('BRIDGE_UNAVAILABLE_OR_RESPONSE_INVALID') from None

    def submit(self, request):
        return self.call(self.submit_url, request)

    def query(self, operation_id):
        return self.call(self.query_template.replace('{operationId}', urllib.parse.quote(operation_id, safe='')))

    def selections(self):
        if not isinstance(self.selection_url, str):
            raise Refused('W01_SELECTION_ENDPOINT_REQUIRED')
        parsed = urllib.parse.urlsplit(self.selection_url)
        if ((parsed.scheme, parsed.hostname, parsed.port) != self.origin or parsed.username or
                parsed.password or parsed.query or parsed.fragment or parsed.path != '/selections'):
            raise Refused('W01_SELECTION_ENDPOINT_OUTSIDE_BINDING')
        return self.call(self.selection_url)


def execute(request, bridge, root=RECORDS, query_only=False):
    validate_request(request)
    path = Path(root) / (hashlib.sha256(request['operationId'].encode()).hexdigest() + '.json')
    reserved = False
    if not query_only:
        # Read/query an existing original even after its source or target is retired.
        # New submissions alone need current explicit source/target admission.
        if not path.exists():
            bridge.validate_binding(request)
        receipt = dict(request=request, bridgeFingerprint=bridge.fingerprint,
                       reservedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       disposition='SUBMISSION_RESERVED', lastResult=None)
        try:
            write_json(path, receipt, exclusive=True)
            reserved = True
        except FileExistsError:
            receipt = read_json(path)
    else:
        receipt = read_json(path)
    if receipt.get('request') != request:
        raise Refused('OPERATION_ID_REQUEST_REUSE_REJECTED')
    if receipt.get('bridgeFingerprint') != bridge.fingerprint:
        raise Refused('ORIGINAL_BRIDGE_BINDING_CHANGED')
    try:
        result = bridge.submit(request) if reserved else bridge.query(request['operationId'])
        result = validate_result(result, request)
    except Refused as error:
        # A lost submission response never becomes another POST. Query the
        # original ID immediately, then retain it for later user queries.
        if reserved:
            try:
                result = validate_result(bridge.query(request['operationId']), request)
            except Refused as query_error:
                result = running(request, str(query_error))
        else:
            result = running(request, str(error))
    receipt.update(disposition='ORIGINAL_QUERY_ONLY', lastResult=result,
                   observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat())
    # One writer owns updates. Concurrent repeat queries do not overwrite its receipt.
    if reserved:
        write_json(path, receipt)
    write_json(Path(root) / 'observations' / (uuid.uuid4().hex + '.json'),
               dict(bridgeFingerprint=bridge.fingerprint, result=result,
                    observedAt=receipt['observedAt'], submissionIssuedThisRun=reserved), exclusive=True)
    return result


class Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's normal error can echo a credential mistakenly entered as a parameter.
        raise Refused('CLI_ARGUMENTS_INVALID')


def main():
    parser = Parser(description='Manual small-app bridge entry; original operation only.')
    parser.add_argument('--action')
    parser.add_argument('--operation-id')
    parser.add_argument('--source-config-ref')
    parser.add_argument('--business-action')
    parser.add_argument('--prepared-operation')
    parser.add_argument('--parent-chain-ref')
    parser.add_argument('--recovery-point-ref')
    parser.add_argument('--target-config-ref')
    parser.add_argument('--query', action='store_true')
    args = None
    try:
        args = parser.parse_args()
        if args.business_action is not None or args.prepared_operation is not None:
            if any((args.action, args.operation_id, args.source_config_ref, args.parent_chain_ref,
                    args.recovery_point_ref, args.target_config_ref, args.query)):
                raise Refused('UI_AND_CLI_INPUT_CONFLICT')
            if args.business_action not in ('FULL', 'INCREMENTAL', 'RESTORE') or not reference(args.prepared_operation):
                raise Refused('BUSINESS_PAGE_SELECTION_REQUIRED')
            from smallapp_entry import prepared_request
            request = prepared_request(args.prepared_operation, args.business_action)
        else:
            # Retained old task commands are history, not an alternate execution entry.
            # An independently activated old FULL task must never submit when a bridge arrives.
            if not args.query:
                raise Refused('BUSINESS_PAGE_SELECTION_REQUIRED')
            request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId=args.operation_id,
                           action=args.action, sourceConfigRef=args.source_config_ref,
                           parentChainRef=args.parent_chain_ref, recoveryPointRef=args.recovery_point_ref,
                           targetConfigRef=args.target_config_ref)
        validate_request(request)
        bridge = HttpBridge()
        if args.prepared_operation:
            from smallapp_entry import validate_prepared_binding
            journal = RECORDS / (hashlib.sha256(request['operationId'].encode()).hexdigest() + '.json')
            if not journal.exists():
                validate_prepared_binding(args.prepared_operation, bridge)
        result = execute(request, bridge, query_only=args.query)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        print({'RUNNING': '原任务执行或核对中，只查询原编号', 'SUCCEEDED': '执行完成',
               'FAILED': '原任务失败，保留真实错误与日志'}[result['state']], flush=True)
        return 0 if result['state'] == 'SUCCEEDED' else 2 if result['state'] == 'FAILED' else 3
    except Refused as error:
        print(json.dumps(dict(outcome='REFUSED', errorCode=str(error), submissionIssued=False), ensure_ascii=False), flush=True)
        return 2
    except OSError:
        print(json.dumps(dict(outcome='UNKNOWN', errorCode='LOCAL_DURABLE_IO_FAILED',
                              submissionOutcome='NOT_PROVEN', retryAllowed=False)), flush=True)
        return 2


if __name__ == '__main__':
    sys.exit(main())
