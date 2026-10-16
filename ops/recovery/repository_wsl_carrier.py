"""Pinned Windows WSL command carrier. Its exit is only transport evidence."""
import argparse
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

from repository_records import (Deadline, RepositoryError, absolute, document, exact,
                                pin_file, read_pin, require, utc, write_new)

HOST_FIELDS = ('schemaVersion transport hostOs hostId bootId uid sourceProfilePin '
               'pythonPin dispatcherPin scriptPin workingDirectory evidenceRoot '
               'launcherPin launcherArguments environment resourceObserverPin')


def configuration(reference):
    from repository_host_view import select
    value = document(read_pin(reference))
    exact(value, 'schemaVersion executionHostPin windowsHostViewPin nativeHostViewPin nativeServiceConfigurationPin nativePeerConfigurationPin nativeDependencyPins',
          'RepositoryWslCarrierConfig/v1')
    select(value['windowsHostViewPin'])
    host = document(read_pin(value['executionHostPin']))
    exact(host, HOST_FIELDS, 'RecoveryControlExecutionHost/v1')
    require(host['transport'] == 'WSL' and host['hostOs'] == 'Linux' and host['uid'] == 0 and
            type(host['hostId']) is str and host['hostId'] and type(host['bootId']) is str and host['bootId'],
            'REPOSITORY_WSL_HOST_PROFILE_INVALID')
    launcher = host['launcherArguments']
    require(type(launcher) is list and len(launcher) == 5 and
            launcher[0] == '--distribution' and type(launcher[1]) is str and launcher[1] and
            '\x00' not in launcher[1] and launcher[2:] == ['--user', 'root', '--exec'],
            'REPOSITORY_WSL_LAUNCHER_ARGUMENTS_INVALID')
    return value, host


def validate(reference):
    value, host = configuration(reference)
    require(type(host['environment']) is dict and
            all(type(k) is str and type(v) is str and '\x00' not in k + v and '=' not in k
                for k, v in host['environment'].items()), 'REPOSITORY_WSL_ENVIRONMENT_INVALID')
    for name in ('sourceProfilePin', 'pythonPin', 'dispatcherPin', 'scriptPin', 'launcherPin'):
        read_pin(host[name], 128 * 1024 * 1024)
    registration = document(read_pin(host['sourceProfilePin']))
    require(registration['schemaVersion'] == 'RecoveryLocalEnvironmentRegistration/v1' and
            registration['usableForExecution'] is True and
            registration['host']['selectedExecutionHost'] is not None,
            'REPOSITORY_WSL_ENVIRONMENT_NOT_USABLE')
    for name in ('nativeHostViewPin', 'nativeServiceConfigurationPin', 'nativePeerConfigurationPin'):
        read_pin(value[name], 64 * 1024 * 1024)
    require(type(value['nativeDependencyPins']) is list and value['nativeDependencyPins'],
            'REPOSITORY_WSL_DEPENDENCIES_REQUIRED')
    for dependency in value['nativeDependencyPins']:
        read_pin(dependency, 32 * 1024 * 1024)
    for path in (value['executionHostPin']['path'], value['nativeHostViewPin']['path'],
                 value['nativeServiceConfigurationPin']['path'], value['nativePeerConfigurationPin']['path'],
                 host['pythonPin']['path'], host['dispatcherPin']['path'], host['scriptPin']['path'],
                 host['workingDirectory'], host['evidenceRoot']):
        require(PurePosixPath(path).is_absolute() and not path.startswith('//') and '..' not in PurePosixPath(path).parts,
                'REPOSITORY_WSL_NATIVE_PATH_REQUIRED')
        absolute(path)
    require(Path(host['launcherPin']['path']).name.lower() == 'wsl.exe', 'REPOSITORY_WSL_LAUNCHER_REQUIRED')
    require(absolute(host['workingDirectory']).is_dir() and absolute(host['evidenceRoot']).is_dir(),
            'REPOSITORY_WSL_NATIVE_ROOT_REQUIRED')
    require(host['resourceObserverPin'] is not None, 'REPOSITORY_WSL_RESOURCE_OBSERVER_REQUIRED')
    read_pin(host['resourceObserverPin'], 32 * 1024 * 1024)
    return value, host


def command(reference, operation_pin, launch=False, request_pin=None, output=None):
    value, host = validate(reference)
    read_pin(operation_pin)
    require((launch and request_pin is None and output is None) or
            (not launch and request_pin is not None and output is not None), 'REPOSITORY_WSL_ACTION_INVALID')
    argv = [host['launcherPin']['path'], *host['launcherArguments'], host['pythonPin']['path'], '-B',
            host['dispatcherPin']['path'], '--profile', value['executionHostPin']['path'],
            '--profile-sha256', value['executionHostPin']['sha256'], '--carrier', reference['path'],
            '--carrier-sha256', reference['sha256'], '--host-view', value['nativeHostViewPin']['path'],
            '--host-view-sha256', value['nativeHostViewPin']['sha256'],
            '--operation-request', operation_pin['path'], '--operation-sha256', operation_pin['sha256']]
    if launch:
        argv.append('--launch')
    else:
        read_pin(request_pin)
        require(type(output) is str and not absolute(output).exists(), 'REPOSITORY_WSL_OUTPUT_EXISTS')
        argv += ['--request', request_pin['path'], '--request-sha256', request_pin['sha256'], '--output', output]
    return argv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('carrier', 'carrier-sha256', 'operation-request', 'operation-sha256'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--request'); parser.add_argument('--output')
    args = parser.parse_args()
    require(os.name == 'nt', 'REPOSITORY_WSL_WINDOWS_CARRIER_REQUIRED')
    reference = pin_file(args.carrier)
    require(reference['sha256'] == args.carrier_sha256, 'REPOSITORY_WSL_CARRIER_CONFIG_CHANGED')
    # Install the approved view before reading any native Pin.
    configuration(reference)
    operation = pin_file(args.operation_request)
    require(operation['sha256'] == args.operation_sha256, 'REPOSITORY_WSL_OPERATION_CHANGED')
    deadline = Deadline(document(read_pin(operation))['deadlineMilliseconds'])
    argv = command(reference, operation, args.launch,
                   None if args.request is None else pin_file(args.request), args.output)
    process = subprocess.Popen(argv, stdin=sys.stdin.buffer, stdout=sys.stdout.buffer, stderr=sys.stderr.buffer,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        return process.wait(timeout=deadline.remaining())
    except (subprocess.TimeoutExpired, RepositoryError) as error:
        write_new(Path(args.operation_request).with_name(Path(args.operation_request).name +
            ('.owner' if args.launch else '.' + Path(args.request).name) + '.wsl-terminal.json'),
            dict(schemaVersion='RepositoryWslCarrierTerminal/v1', requestPin=operation,
                 carrierConfigPin=reference, launcherPid=process.pid, actualExitCode=process.poll(),
                 state='TERMINAL_UNKNOWN', at=utc()))
        raise RepositoryError('REPOSITORY_WSL_LAUNCHER_TERMINAL_UNKNOWN', unknown=True,
                              actual_exit=process.poll()) from error


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    try:
        sys.exit(main())
    except Exception as error:
        print(error.code if isinstance(error, RepositoryError) else
              'REPOSITORY_WSL_' + type(error).__name__.upper(), file=sys.stderr)
        sys.exit(2 if isinstance(error, RepositoryError) and error.unknown else 1)
