"""Private child of recovery_minimal.py; no signing or lease configuration."""
import argparse
from copy import deepcopy
import re
import sys

from recovery_engine import absolute, load, pin, utc, write
from recovery_minimal_plan import configuration_contract, request_contract


PROGRAM_FAILURE_FIELDS = ('programExecutionPhase', 'programNativeEvidencePin',
    'programProtectionCustodyPin', 'programGenerationPin', 'replacementReceiptPin',
    'programSqlCleanupPin', 'actualNativeExitCode')


def operation_result(request, started, state, code, data, pins, exit_code):
    return dict(schemaVersion='backup-restore-operation-result/v1', operationId=request['operationId'],
        requestId=request['operationId'], action=request['action'], state=state, failureCode=code,
        message='RESTORE_COMMANDS_COMPLETED_WITHOUT_VERIFICATION' if state == 'SUCCEEDED' else code,
        data=data, originalResultPins=pins, startedAt=started, finishedAt=utc(), actualExitCode=exit_code)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('configuration', 'request', 'output'):
        parser.add_argument('--'+key, required=True)
    args = parser.parse_args(argv)
    started = utc(); request = load(args.request); request_contract(request)
    native = None
    try:
        configuration = load(args.configuration); configuration_contract(configuration)
        from recovery_minimal_runtime import execute
        data, native = execute(configuration, request, absolute(args.output).parent,
                               [pin(args.configuration), pin(args.request)])
        result = operation_result(request, started, 'SUCCEEDED', None, data, native.original_pins, 0)
        exit_code = 0
    except Exception as error:
        native = getattr(error, 'native', native)
        code = getattr(error, 'code', type(error).__name__)
        if not re.fullmatch('[A-Z][A-Z0-9_]{0,127}', code):
            code = 'RESTORE_'+type(error).__name__.upper()
        unknown = bool(getattr(error, 'unknown', False))
        if native is not None and native.mutation_dispatched and native.last_exit is None:
            unknown = True
        evidence = getattr(error, 'evidence', None)
        program = (type(evidence) is dict and
                   evidence.get('programExecutionPhase') in ('NOT_STARTED', 'PREPARATION', 'RESTORE'))
        if program:
            unknown = unknown or evidence.get('terminalUnknown') is True
        data = dict(partialTargetRetained=True, retryPermitted=False, errorType=type(error).__name__,
                    actualNativeExitCode=None if native is None else native.last_exit,
                    mutationDispatched=bool(native is not None and native.mutation_dispatched) or
                    (not program and
                     (absolute(args.output).parent/'replacement-preparation/replacement-intent.json').exists()))
        pins = [] if native is None else native.original_pins
        if program:
            # Only the producer's finite program handoff belongs in data. The
            # request, failure code, worker terminal state/exit and retention
            # policy remain authoritative here, including READY failures that
            # reference an already successful replacement receipt.
            data.update({key: deepcopy(evidence[key]) for key in PROGRAM_FAILURE_FIELDS if key in evidence})
            # Program intent precedes read-only construction. Only actual
            # native/producer dispatch facts establish a program mutation.
            data['mutationDispatched'] = data['mutationDispatched'] or evidence.get('mutationDispatched') is True
            data['terminalUnknown'] = unknown
            aggregate = deepcopy(evidence.get('originalResultPins', []))
            # Preserve actual last-native originals even if an incomplete
            # producer handoff omitted them; never reduce the legacy facts.
            for reference in pins:
                if reference not in aggregate:
                    aggregate.append(deepcopy(reference))
            pins = aggregate
            data['originalResultPins'] = deepcopy(pins)
        if code == 'ARCHIVED_PAYLOAD_CHANGED' and hasattr(error, 'archive_diagnostic'):
            data['archiveDiagnostic'] = error.archive_diagnostic
        exit_code = 2 if unknown else 1
        result = operation_result(request, started, 'TERMINAL_UNKNOWN' if unknown else 'FAILED_RETAINED', code,
                                  data, pins, exit_code)
    write(absolute(args.output), result)
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
