"""Native WSL entry: verify approved host, code and original inputs before peer."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from repository_records import (RepositoryError, document, exact, pin_file,
                                read_pin, require, safe_path)
from repository_host_view import select
from repository_wsl_carrier import HOST_FIELDS


def checked(path, digest):
    reference = pin_file(path)
    require(reference['sha256'] == digest, 'REPOSITORY_WSL_NATIVE_INPUT_CHANGED')
    return reference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('profile', 'profile-sha256', 'carrier', 'carrier-sha256', 'host-view',
                 'host-view-sha256', 'operation-request', 'operation-sha256'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--request'); parser.add_argument('--request-sha256'); parser.add_argument('--output')
    args = parser.parse_args()
    require(sys.platform.startswith('linux') and os.geteuid() == 0,
            'REPOSITORY_WSL_NATIVE_ROOT_REQUIRED')
    view = checked(args.host_view, args.host_view_sha256)
    info = safe_path(view['path']).stat()
    require(info.st_uid == info.st_gid == 0 and info.st_mode & 0o777 == 0o600,
            'REPOSITORY_WSL_PRIVATE_HOST_VIEW_REQUIRED')
    select(view)
    profile_pin = checked(args.profile, args.profile_sha256)
    profile = document(read_pin(profile_pin))
    exact(profile, HOST_FIELDS, 'RecoveryControlExecutionHost/v1')
    require(profile['transport'] == 'WSL' and profile['hostOs'] == 'Linux' and profile['uid'] == 0 and
            profile['hostId'] == Path('/etc/machine-id').read_text(encoding='ascii').strip() and
            profile['bootId'] == Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip(),
            'REPOSITORY_WSL_ACTUAL_HOST_MISMATCH')
    for name in ('pythonPin', 'dispatcherPin', 'scriptPin', 'sourceProfilePin', 'resourceObserverPin'):
        require(profile[name] is not None, 'REPOSITORY_WSL_PROFILE_PIN_REQUIRED')
        read_pin(profile[name], 128 * 1024 * 1024)
    for reference in (profile_pin, profile['dispatcherPin'], profile['scriptPin']):
        info = safe_path(reference['path']).stat()
        require(info.st_uid == info.st_gid == 0 and info.st_mode & 0o777 == 0o600,
                'REPOSITORY_WSL_PRIVATE_NATIVE_PROGRAM_REQUIRED')
    require(Path(sys.executable).absolute() == safe_path(profile['pythonPin']['path']) and
            Path(__file__).absolute() == safe_path(profile['dispatcherPin']['path']),
            'REPOSITORY_WSL_NATIVE_PROGRAM_CHANGED')
    registration = document(read_pin(profile['sourceProfilePin']))
    require(registration['schemaVersion'] == 'RecoveryLocalEnvironmentRegistration/v1' and
            registration['usableForExecution'] is True and
            registration['host']['selectedExecutionHost'] is not None,
            'REPOSITORY_WSL_ENVIRONMENT_NOT_USABLE')
    carrier_pin = checked(args.carrier, args.carrier_sha256)
    carrier = document(read_pin(carrier_pin))
    exact(carrier, 'schemaVersion executionHostPin windowsHostViewPin nativeHostViewPin nativeServiceConfigurationPin nativePeerConfigurationPin nativeDependencyPins',
          'RepositoryWslCarrierConfig/v1')
    require(carrier['executionHostPin'] == profile_pin and carrier['nativeHostViewPin'] == view,
            'REPOSITORY_WSL_NATIVE_PROFILE_NOT_SELECTED')
    dependencies = carrier['nativeDependencyPins']
    approved = {safe_path(p['path']): p for p in dependencies}
    require(len(approved) == len(dependencies) and
            profile['dispatcherPin'] in dependencies and profile['scriptPin'] in dependencies,
            'REPOSITORY_WSL_NATIVE_DEPENDENCIES_REQUIRED')
    for file in Path(__file__).absolute().parent.glob('repository_*.py'):
        require(file in approved, 'REPOSITORY_WSL_NATIVE_DEPENDENCY_NOT_APPROVED')
        read_pin(approved[file], 32 * 1024 * 1024)
        info = file.stat()
        require(info.st_uid == info.st_gid == 0 and info.st_mode & 0o777 == 0o600,
                'REPOSITORY_WSL_PRIVATE_NATIVE_DEPENDENCY_REQUIRED')
    checked(args.operation_request, args.operation_sha256)
    argv = [profile['pythonPin']['path'], '-B', profile['scriptPin']['path'],
            '--service-configuration', carrier['nativeServiceConfigurationPin']['path'],
            '--service-sha256', carrier['nativeServiceConfigurationPin']['sha256'],
            '--configuration', carrier['nativePeerConfigurationPin']['path'],
            '--configuration-sha256', carrier['nativePeerConfigurationPin']['sha256'],
            '--operation-request', args.operation_request, '--operation-sha256', args.operation_sha256]
    if args.launch:
        require(args.request is None and args.output is None, 'REPOSITORY_WSL_NATIVE_ACTION_INVALID')
        argv.append('--launch')
    else:
        require(args.request is not None and args.request_sha256 is not None and args.output is not None,
                'REPOSITORY_WSL_NATIVE_ACTION_INVALID')
        checked(args.request, args.request_sha256)
        argv += ['--request', args.request, '--output', args.output]
    environment = dict(profile['environment'])
    require(all(type(k) is str and type(v) is str and '\x00' not in k + v and '=' not in k
                for k, v in environment.items()), 'REPOSITORY_WSL_ENVIRONMENT_INVALID')
    require(not any(k.startswith('INTRUOYI_REPOSITORY_HOST_VIEW_') for k in environment),
            'REPOSITORY_WSL_RESERVED_ENVIRONMENT')
    environment['INTRUOYI_REPOSITORY_HOST_VIEW_PATH'] = view['path']
    environment['INTRUOYI_REPOSITORY_HOST_VIEW_SHA256'] = view['sha256']
    root = safe_path(profile['evidenceRoot']); work = safe_path(profile['workingDirectory'])
    for path in (root, work):
        info = path.stat()
        require(path.is_dir() and info.st_uid == info.st_gid == 0 and info.st_mode & 0o777 == 0o700,
                'REPOSITORY_WSL_PRIVATE_NATIVE_ROOT_REQUIRED')
    peer = subprocess.Popen(argv, cwd=work, env=environment,
                            stdin=sys.stdin.buffer, stdout=sys.stdout.buffer, stderr=sys.stderr.buffer)
    return peer.wait()


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    try:
        sys.exit(main())
    except Exception as error:
        print(error.code if isinstance(error, RepositoryError) else
              'REPOSITORY_WSL_NATIVE_' + type(error).__name__.upper(), file=sys.stderr)
        sys.exit(2 if isinstance(error, RepositoryError) and error.unknown else 1)
