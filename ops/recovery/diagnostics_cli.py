"""Frozen W07 interface: --request absolute.json --output absolute.json.

Runtime prerequisite: Python 3.10+ and jsonschema. Explicit pinned policy
configuration is mandatory; missing configuration never selects another tree.
"""
import time
CLI_START_NS = time.monotonic_ns()

import argparse
import sys

from recovery_diagnostics import Diagnostics
from recovery_diagnostics_io import (Budget, DiagnosticError, Reader, absolute_path,
                                    atomic_json, parse_json, pin_file, require, utc_now)


def run(request_path, output_path, started_ns=None):
    start_ns = time.monotonic_ns() if started_ns is None else started_ns
    started_at = utc_now()
    request, reader = None, None
    output = absolute_path(output_path)
    if output.exists():
        print('OUTPUT_ALREADY_EXISTS', file=sys.stderr)
        return 1
    output_safe = False
    try:
        path = absolute_path(request_path)
        require(path != output, 'REQUEST_OUTPUT_COLLISION')
        require(path.stat().st_size <= 16_777_216, 'REQUEST_SIZE_LIMIT_EXCEEDED')
        request = parse_json(path.read_bytes())
        require(type(request) is dict, 'REQUEST_OBJECT_REQUIRED')
        require(all(type(request.get(key)) is str and request[key] for key in
                    ('operationId', 'requestId', 'action')), 'REQUEST_IDENTITY_REQUIRED')
        # Reject any referenced input path before a failure result can overwrite
        # it. This check also runs when later schema/prerequisite checks fail.
        def protect_inputs(value):
            if type(value) is dict:
                if set(value) == {'path', 'bytes', 'sha256'}:
                    require(absolute_path(value['path']) != output, 'OUTPUT_INPUT_COLLISION')
                else:
                    for child in value.values():
                        protect_inputs(child)
            elif type(value) is list:
                for child in value:
                    protect_inputs(child)
        protect_inputs(request)
        output_safe = True
        budget = Budget(request.get('deadlineMilliseconds'), start_ns)
        reader = Reader(budget)
        reader.forbidden_paths.add(output)
        reader.read(pin_file(path))
        policy = reader.read(request['policyPin'])
        protect_inputs(policy)
        if type(policy) is dict and type(policy.get('diagnostics')) is dict:
            config = policy['diagnostics']
            for root in ('stateRoot', 'evidenceRoot'):
                if root in config and output.is_relative_to(absolute_path(config[root])):
                    output_safe = False
                    raise DiagnosticError('OUTPUT_PERSISTENT_ROOT_COLLISION')
        diagnostics = Diagnostics(request, reader)
        # Never overwrite input evidence, originals or local persistent state.
        require(output not in (diagnostics.state_root, diagnostics.evidence_root), 'OUTPUT_ROOT_COLLISION')
        if output.is_relative_to(diagnostics.state_root) or output.is_relative_to(diagnostics.evidence_root):
            output_safe = False
            raise DiagnosticError('OUTPUT_PERSISTENT_ROOT_COLLISION')
        require(all(absolute_path(pin['path']) != output for pin in reader.pins), 'OUTPUT_INPUT_COLLISION')
        result = diagnostics.execute(started_at)
    except (DiagnosticError, OSError, KeyError, TypeError) as error:
        if isinstance(error, DiagnosticError) and error.code in (
                'OUTPUT_INPUT_COLLISION', 'OUTPUT_ROOT_COLLISION', 'OUTPUT_PERSISTENT_ROOT_COLLISION'):
            output_safe = False
        if not output_safe:
            print(error.code if isinstance(error, DiagnosticError) else 'REQUEST_PREREQUISITE_FAILED',
                  file=sys.stderr)
            return 1
        if request is None or not all(type(request.get(key)) is str and request[key] for key in
                                      ('operationId', 'requestId', 'action')):
            # A malformed identity cannot be represented by the frozen result.
            print('REQUEST_INVALID_NO_RESULT_IDENTITY', file=sys.stderr)
            return 1
        code = error.code if isinstance(error, DiagnosticError) else 'DIAGNOSTIC_PREREQUISITE_OR_IO_FAILED'
        unknown = isinstance(error, DiagnosticError) and error.unknown
        result = {'schemaVersion': 'backup-restore-operation-result/v1',
                  'operationId': request['operationId'], 'requestId': request['requestId'],
                  'action': request['action'], 'state': 'TERMINAL_UNKNOWN' if unknown else 'FAILED_RETAINED',
                  'failureCode': code, 'message': code, 'data': None,
                  'originalResultPins': [] if reader is None else reader.pins,
                  'startedAt': started_at, 'finishedAt': utc_now(), 'actualExitCode': None}
    try:
        atomic_json(output, result, replace=False)
    except (DiagnosticError, OSError):
        print('OPERATION_RESULT_OUTPUT_FAILED', file=sys.stderr)
        return 1
    return {'SUCCEEDED': 0, 'FAILED_RETAINED': 1, 'TERMINAL_UNKNOWN': 2}[result['state']]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        return run(args.request, args.output, started_ns=CLI_START_NS)
    except DiagnosticError as error:
        print(error.code, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
