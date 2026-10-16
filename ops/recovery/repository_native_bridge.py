"""Authenticated native observation/control transport for the publisher installer.

The configured W02 verifier observes its actual held native claim. This client
requires a fresh challenge-bound signed response; schema booleans alone never
establish native ownership, writer coverage or original capture completeness.
"""
import argparse
import base64
import hashlib
import os
from pathlib import Path
import secrets
import subprocess

from repository_records import (Deadline, RepositoryError, absolute, atomic_output,
                                document, exact, pin_file, read_pin, require,
                                signed_pin, utc, write_new)


def exchange(config_pin, action, request_pin, output_path):
    config = document(read_pin(config_pin))
    require(config['schemaVersion'] in ('RepositoryBackupSource/v1', 'RepositoryNativeBackupSource/v1'), 'REPOSITORY_NATIVE_SOURCE_INVALID')
    from repository_host_view import select
    select(config['hostViewPin'] if config['schemaVersion'] == 'RepositoryBackupSource/v1' else None)
    request = document(read_pin(request_pin))
    deadline = Deadline(request['remainingMilliseconds'])
    require(action in {'read-original', 'publish-control', 'observe-initialized', 'observe-owner', 'observe-prepared', 'observe-intent', 'observe-capture', 'observe-workspace', 'observe-readback', 'read-current-input', 'release-peer'}, 'REPOSITORY_NATIVE_ACTION_INVALID')
    transport = config['nativeVerifierCommand']
    exact(transport, 'schemaVersion executablePin programPins arguments workingDirectory', 'RepositoryNativeCommand/v1')
    read_pin(transport['executablePin'], 64 * 1024 * 1024)
    require(type(transport['programPins']) is list and transport['programPins'], 'REPOSITORY_NATIVE_PROGRAM_REQUIRED')
    for pin in transport['programPins']:
        read_pin(pin, 32 * 1024 * 1024)
    require(type(transport['arguments']) is list and all(type(arg) is str and '\x00' not in arg for arg in transport['arguments']), 'REPOSITORY_NATIVE_ARGUMENTS_INVALID')
    from repository_records import safe_path
    safe_path(transport['workingDirectory'])
    challenge = secrets.token_hex(32)
    carrier = Path(request_pin['path']).with_name(Path(request_pin['path']).name + '.native-request')
    answer_path = carrier.with_name(carrier.name + '.answer')
    invocation = {'schemaVersion': 'RepositoryNativeRequest/v1', 'action': action, 'challenge': challenge, 'request': request, 'sourceConfigPin': config_pin, 'remainingMilliseconds': int(deadline.remaining() * 1000)}
    write_new(carrier, invocation)
    operation_pin = request['operationRequestPin']
    read_pin(operation_pin)
    argv = [transport['executablePin']['path'], *transport['arguments'], '--operation-request', operation_pin['path'], '--operation-sha256', operation_pin['sha256'], '--request', str(carrier), '--output', str(answer_path)]
    with carrier.with_name(carrier.name + '.stdout').open('xb') as stdout, carrier.with_name(carrier.name + '.stderr').open('xb') as stderr:
        process = subprocess.Popen(argv, cwd=transport['workingDirectory'], stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
        try:
            actual_exit = process.wait(timeout=deadline.remaining())
        except subprocess.TimeoutExpired as error:
            write_new(carrier.with_name(carrier.name + '.terminal'), {'pid': process.pid, 'actualExitCode': process.poll(), 'state': 'TERMINAL_UNKNOWN', 'at': utc()})
            raise RepositoryError('REPOSITORY_NATIVE_VERIFIER_TERMINAL_UNKNOWN', unknown=True, actual_exit=process.poll()) from error
        except RepositoryError as error:
            write_new(carrier.with_name(carrier.name + '.terminal'), {'pid': process.pid, 'actualExitCode': process.poll(), 'state': 'TERMINAL_UNKNOWN', 'at': utc()})
            raise RepositoryError('REPOSITORY_NATIVE_VERIFIER_TERMINAL_UNKNOWN', unknown=True, actual_exit=process.poll()) from error
    write_new(carrier.with_name(carrier.name + '.terminal'), {'pid': process.pid, 'actualExitCode': actual_exit, 'state': 'TERMINAL_UNKNOWN' if actual_exit == 2 else 'EXITED', 'at': utc()})
    if actual_exit == 2:
        raise RepositoryError('REPOSITORY_NATIVE_VERIFIER_TERMINAL_UNKNOWN', unknown=True, actual_exit=actual_exit)
    require(actual_exit == 0, 'REPOSITORY_NATIVE_VERIFIER_FAILED')
    from repository_records import verify_signed
    response = verify_signed(document(read_pin(pin_file(answer_path), 128 * 1024 * 1024)),
                             config['nativeAuthorityKeyPins'])
    exact(response, 'schemaVersion challenge action sourceConfigPin requestPin result', 'RepositoryNativeResponse/v1')
    require(response['challenge'] == challenge and response['action'] == action and response['sourceConfigPin'] == config_pin and response['requestPin'] == pin_file(carrier), 'REPOSITORY_NATIVE_RESPONSE_REPLAYED')
    require(type(response['result']) is dict, 'REPOSITORY_NATIVE_RESPONSE_INVALID')
    receipt = document(read_pin(pin_file(str(answer_path) + '.native-receipt.json')))
    exact(receipt, 'schemaVersion nativeResponsePin transportedResponsePin requestPin', 'RepositoryNativeCarrierReceipt/v1')
    peer = document(read_pin(config['nativePeerConfigPin']))['payload']
    operation = document(read_pin(operation_pin))
    from pathlib import PurePosixPath
    native_answer = (PurePosixPath(peer['sessionRoot']) /
                     hashlib.sha256(operation['requestId'].encode('utf-8')).hexdigest() /
                     'inbox' / (pin_file(carrier)['sha256'] + '.answer')).as_posix()
    require(receipt['requestPin'] == pin_file(carrier) and
            receipt['transportedResponsePin'] == pin_file(answer_path) and
            receipt['nativeResponsePin']['path'] == native_answer and
            read_pin(receipt['nativeResponsePin'], 128 * 1024 * 1024) ==
            read_pin(pin_file(answer_path), 128 * 1024 * 1024), 'REPOSITORY_NATIVE_RESPONSE_ORIGINAL_CHANGED')
    deadline.check()
    atomic_output(output_path, {'schemaVersion': 'RepositoryNativeBridgeResult/v1', 'action': action,
        'nativeResponsePin': receipt['nativeResponsePin'], 'actualExitCode': actual_exit, 'result': response['result']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('config', 'config-sha256', 'action', 'request', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    config_pin = pin_file(absolute(args.config))
    require(config_pin['sha256'] == args.config_sha256, 'REPOSITORY_NATIVE_CONFIG_CHANGED')
    exchange(config_pin, args.action, pin_file(absolute(args.request)), absolute(args.output))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Only a code is emitted; verifier stdout/stderr remain private local evidence.
        import sys
        print(error.code if isinstance(error, RepositoryError) else 'REPOSITORY_NATIVE_' + type(error).__name__.upper(), file=sys.stderr)
        sys.exit(2 if isinstance(error, RepositoryError) and error.unknown else 1)
