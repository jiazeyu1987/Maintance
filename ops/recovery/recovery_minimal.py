"""W04 main restore entry: --configuration PATH --request PATH --output PATH."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys

from recovery_engine import absolute, canonical, check_pin, load, pin, require, utc, write
from recovery_minimal_plan import configuration_contract, disjoint, request_contract
from recovery_minimal_worker import operation_result


def validate_result(value, request, child_exit):
    fields = {'schemaVersion', 'operationId', 'requestId', 'action', 'state', 'failureCode', 'message',
              'data', 'originalResultPins', 'startedAt', 'finishedAt', 'actualExitCode'}
    require(type(value) is dict and set(value) == fields and
            value['schemaVersion'] == 'backup-restore-operation-result/v1' and
            value['operationId'] == value['requestId'] == request['operationId'] and
            value['action'] == request['action'] and type(value['actualExitCode']) is int and
            value['actualExitCode'] == child_exit and value['state'] in
            ('SUCCEEDED', 'FAILED_RETAINED', 'TERMINAL_UNKNOWN') and
            type(value['data']) is dict and type(value['originalResultPins']) is list and
            value['startedAt'] and value['finishedAt'], 'WORKER_RESULT_INVALID')
    require((child_exit, value['state']) in ((0, 'SUCCEEDED'), (1, 'FAILED_RETAINED'), (2, 'TERMINAL_UNKNOWN')),
            'WORKER_EXIT_RESULT_MISMATCH')
    if child_exit == 0:
        data = value['data']
        require(value['failureCode'] is None and value['originalResultPins'] and
                data['targetConfigRef'] == request['targetConfigRef'] and data['orderedChainPins'] and
                data['databaseResultPins'] and data['objectResultPins'] and
                data['consistencyPin'] and data['derivedPin'] and data['applicationStartPin'],
                'WORKER_SUCCESS_OUTPUT_INCOMPLETE')
    else:
        require(type(value['failureCode']) is str and value['failureCode'], 'WORKER_FAILURE_CODE_MISSING')

    def inspect(item):
        if type(item) is dict:
            if set(item) == {'path', 'bytes', 'sha256'}:
                check_pin(item, content=False)
            else:
                for value in item.values(): inspect(value)
        elif type(item) is list:
            for value in item: inspect(value)
    inspect(value['data']); inspect(value['originalResultPins'])


def run_child(argv, root, seconds):
    """Retain the actual child exit; a deadline never authorizes redispatch."""
    started = utc(); process = None; timed_out = False
    stdout, stderr = root/'child.stdout', root/'child.stderr'
    with stdout.open('xb') as out, stderr.open('xb') as err:
        os.chmod(stdout, 0o600); os.chmod(stderr, 0o600)
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                   start_new_session=os.name == 'posix')
        try:
            process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == 'posix':
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Persist null below; the caller retains TERMINAL_UNKNOWN.
                pass
    receipt = dict(operation='W04_RESTORE_CHILD', startedAt=started, finishedAt=utc(),
        actualExitCode=process.poll(), timedOut=timed_out,
        argvSha256=hashlib.sha256(canonical(argv)).hexdigest(), stdoutPin=pin(stdout), stderrPin=pin(stderr))
    reference = write(root/'child-exit.json', receipt)
    return receipt, reference


def run(configuration_path, request_path, output_path):
    request = load(request_path); request_contract(request)
    configuration = load(configuration_path); configuration_contract(configuration)
    operations = absolute(configuration['operationsRoot'])
    output = absolute(str(output_path))
    if output.exists():
        previous = load(output)
        require(previous.get('schemaVersion') == 'backup-restore-operation-result/v1' and
                previous.get('operationId') == request['operationId'], 'OUTPUT_ALREADY_BELONGS_TO_ANOTHER_OPERATION')
    operations.mkdir(parents=True, exist_ok=True, mode=0o700)
    root = operations/request['operationId']; started = utc()
    try:
        root.mkdir(mode=0o700)
    except FileExistsError:
        if not (root/'operation.json').exists():
            result = operation_result(request, started, 'TERMINAL_UNKNOWN', 'ORIGINAL_OPERATION_ADMISSION_INCOMPLETE',
                dict(originalOperationId=request['operationId'], retryPermitted=False), [], None)
            publish(output, result)
            return result
        record = load(root/'operation.json')
        require(pinned_request(record) == request and record['configurationSha256'] == hashlib.sha256(canonical(configuration)).hexdigest(),
                'OPERATION_ID_INPUT_CONFLICT')
        result_path = root/'result.json'
        if result_path.exists():
            result = load(result_path)
        elif (root/'child-exit.json').exists():
            receipt = load(root/'child-exit.json'); receipt_pin = pin(root/'child-exit.json')
            try:
                require(not receipt['timedOut'] and receipt['actualExitCode'] is not None, 'ORIGINAL_CHILD_TIMEOUT')
                result = load(root/'worker-result.json')
                validate_result(result, request, receipt['actualExitCode'])
                result['originalResultPins'].extend([pin(root/'worker-result.json'), receipt_pin])
            except Exception as error:
                result = operation_result(request, record['startedAt'], 'TERMINAL_UNKNOWN',
                    getattr(error, 'code', 'ORIGINAL_CHILD_OUTPUT_'+type(error).__name__.upper()),
                    dict(originalOperationId=request['operationId'], retryPermitted=False), [receipt_pin],
                    receipt['actualExitCode'])
            write(result_path, result)
        else:
            result = operation_result(request, record['startedAt'], 'TERMINAL_UNKNOWN',
                'ORIGINAL_OPERATION_STILL_RUNNING_OR_INTERRUPTED',
                dict(originalOperationId=request['operationId'], retryPermitted=False), [], None)
        publish(output, result)
        return result
    # Admission precedes dispatch. An incomplete journal is never executed again.
    request_ref = write(root/'request.json', request)
    configuration_ref = write(root/'configuration.json', configuration)
    with (root/'operation.json').open('xb') as stream:
        os.chmod(root/'operation.json', 0o600)
        stream.write(canonical(dict(operationId=request['operationId'], requestPin=request_ref,
            configurationSha256=hashlib.sha256(canonical(configuration)).hexdigest(), startedAt=started)))
        stream.flush(); os.fsync(stream.fileno())
    worker_output = root/'worker-result.json'
    try:
        require(request['action'] == 'RESTORE', 'CAPTURE_ACTION_REQUIRES_W03_ENTRY')
        check_pin(configuration['pythonPin'], content=False)
        worker = Path(__file__).with_name('recovery_minimal_worker.py')
        argv = [configuration['pythonPin']['path'], str(worker), '--configuration', configuration_ref['path'],
                '--request', request_ref['path'], '--output', str(worker_output)]
        receipt, receipt_pin = run_child(argv, root, configuration['deadlineMilliseconds']/1000)
        if receipt['timedOut'] or receipt['actualExitCode'] is None:
            result = operation_result(request, started, 'TERMINAL_UNKNOWN', 'ORIGINAL_CHILD_TIMEOUT',
                dict(originalOperationId=request['operationId'], retryPermitted=False), [receipt_pin], receipt['actualExitCode'])
        else:
            result = load(worker_output)
            validate_result(result, request, receipt['actualExitCode'])
            result['originalResultPins'].extend([pin(worker_output), receipt_pin])
    except Exception as error:
        # A child without complete validated output has no inferred success.
        launched = (root/'child.stdout').exists()
        result = operation_result(request, started, 'TERMINAL_UNKNOWN' if launched else 'FAILED_RETAINED',
            getattr(error, 'code', 'MINIMAL_ENTRY_'+type(error).__name__.upper()),
            dict(originalOperationId=request['operationId'], retryPermitted=False, errorType=type(error).__name__),
            [pin(root/'child-exit.json')] if (root/'child-exit.json').exists() else [],
            load(root/'child-exit.json')['actualExitCode'] if (root/'child-exit.json').exists() else None)
    write(root/'result.json', result)
    publish(output, result)
    return result


def pinned_request(record):
    from recovery_engine import pinned_json
    return pinned_json(record['requestPin'])


def publish(path, result):
    if path.exists():
        previous = load(path)
        require(previous.get('schemaVersion') == 'backup-restore-operation-result/v1' and
                previous.get('operationId') == result['operationId'], 'OUTPUT_ALREADY_BELONGS_TO_ANOTHER_OPERATION')
    write(path, result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('configuration', 'request', 'output'):
        parser.add_argument('--'+key, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.configuration, args.request, args.output)
    except Exception as error:
        # Do not write an output path that failed source/target admission.
        sys.stderr.write(getattr(error, 'code', 'MINIMAL_ENTRY_'+type(error).__name__.upper())+'\n')
        return 1
    return {'SUCCEEDED': 0, 'FAILED_RETAINED': 1, 'TERMINAL_UNKNOWN': 2}[result['state']]


if __name__ == '__main__':
    sys.exit(main())
