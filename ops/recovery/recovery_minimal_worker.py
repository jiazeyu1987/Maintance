"""Private child of recovery_minimal.py; no signing or lease configuration."""
import argparse
import re
import sys

from recovery_engine import absolute, load, pin, utc, write
from recovery_minimal_plan import configuration_contract, request_contract


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
        exit_code = 2 if unknown else 1
        data = dict(partialTargetRetained=True, retryPermitted=False, errorType=type(error).__name__,
                    actualNativeExitCode=None if native is None else native.last_exit)
        result = operation_result(request, started, 'TERMINAL_UNKNOWN' if unknown else 'FAILED_RETAINED', code,
                                  data, [] if native is None else native.original_pins, exit_code)
    write(absolute(args.output), result)
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
