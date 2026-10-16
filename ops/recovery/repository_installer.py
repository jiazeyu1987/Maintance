"""Installer preflight for the original publisher; no capture emulation."""
import argparse
from pathlib import Path

from repository_records import (Configuration, absolute, atomic_output, document,
                                exact, pin_file, read_pin, require, safe_path)


def preflight(configuration_pin, request_pin):
    config = Configuration(configuration_pin)
    if config.native_lab:
        from repository_native_publisher import preflight as native_preflight
        return native_preflight(config, request_pin)
    request = document(read_pin(request_pin))
    config.request(request)
    config.authorization(request, request['sourceOrTargetRef'])
    config.copy_protection()
    source = document(read_pin(request['sourceOrTargetRef']))
    exact(source, 'schemaVersion repositoryId sourceIdentityPin pythonPin netExePin ownerCommand nativeVerifierCommand nativeAuthorityKeyPins nativePeerConfigPin bootstrapBinding baseSchemaPin controlAddendumPin workspacePin workspaceDirectory workspaceOwnerSid localStagingRoot localRootCreationTicks nasCredentialPin nasReleaseRoot approvedNasRoot evidenceSigningKeyPin prepareRequestPin captureRequestPin hostViewPin wslCarrierConfigPin', 'RepositoryBackupSource/v1')
    require(source['hostViewPin'] is not None and source['hostViewPin'] == config.value['hostViewPin'],
            'REPOSITORY_NATIVE_HOST_VIEW_NOT_SELECTED')
    from repository_wsl_carrier import validate
    carrier, host = validate(source['wslCarrierConfigPin'])
    require(carrier['windowsHostViewPin'] == source['hostViewPin'] and
            carrier['nativePeerConfigurationPin'] == source['nativePeerConfigPin'] and
            host['scriptPin'] is not None, 'REPOSITORY_WSL_SOURCE_PROFILE_MISMATCH')
    native_service = document(read_pin(carrier['nativeServiceConfigurationPin']))
    require(native_service == config.value, 'REPOSITORY_WSL_SERVICE_CONFIG_MISMATCH')
    require(source['repositoryId'] == config.value['repositoryId'] and source['sourceIdentityPin'] == config.policy['sourceIdentityPin'], 'REPOSITORY_SOURCE_NOT_APPROVED')
    require(absolute(source['workspaceDirectory']) == config.root, 'REPOSITORY_WORKSPACE_TARGET_MISMATCH')
    require(absolute(source['workspacePin']['path']) == config.root / 'workspace-config.json', 'REPOSITORY_WORKSPACE_CONFIG_LOCATION_MISMATCH')
    require(absolute(source['localStagingRoot']) != config.root and config.root not in absolute(source['localStagingRoot']).parents and absolute(source['localStagingRoot']) not in config.root.parents, 'REPOSITORY_STAGING_OVERLAP')
    safe_path(source['localStagingRoot'])
    require(type(source['localRootCreationTicks']) is int and source['localRootCreationTicks'] > 0, 'REPOSITORY_LOCAL_ROOT_IDENTITY_REQUIRED')
    require(type(source['nativeAuthorityKeyPins']) is list and source['nativeAuthorityKeyPins'], 'REPOSITORY_NATIVE_AUTHORITY_REQUIRED')
    for pin in source['nativeAuthorityKeyPins']:
        read_pin(pin, 65536)
    from repository_records import signed_pin
    peer = signed_pin(source['nativePeerConfigPin'], config.value['authorityKeyPins'])
    require(peer['schemaVersion'] == 'RepositoryNativePeerConfig/v1' and
            peer['repositoryId'] == config.value['repositoryId'] and
            peer['sourceIdentityPin'] == config.policy['sourceIdentityPin'],
            'REPOSITORY_NATIVE_PEER_CONFIG_SCOPE_MISMATCH')
    require(peer['programPin'] == host['scriptPin'] and peer['hostViewPin'] == carrier['nativeHostViewPin'],
            'REPOSITORY_WSL_PEER_PROFILE_MISMATCH')
    for pin in peer['nativeImplementationPins'].values():
        require(pin in carrier['nativeDependencyPins'], 'REPOSITORY_WSL_PEER_DEPENDENCY_NOT_SELECTED')
    for name in ('pythonPin', 'netExePin', 'baseSchemaPin', 'controlAddendumPin', 'workspacePin', 'nasCredentialPin', 'evidenceSigningKeyPin'):
        read_pin(source[name], 64 * 1024 * 1024)
    require(source['bootstrapBinding']['nasWorkspaceConfigSha256'] == source['workspacePin']['sha256'], 'REPOSITORY_WORKSPACE_BINDING_MISMATCH')
    for name in ('ownerCommand', 'nativeVerifierCommand'):
        command = source[name]
        exact(command, 'schemaVersion executablePin programPins arguments workingDirectory', 'RepositoryNativeCommand/v1')
        read_pin(command['executablePin'], 64 * 1024 * 1024)
        require(type(command['programPins']) is list and command['programPins'], 'REPOSITORY_NATIVE_PROGRAM_REQUIRED')
        for pin in command['programPins']:
            read_pin(pin, 32 * 1024 * 1024)
        require(type(command['arguments']) is list and all(type(arg) is str and '\x00' not in arg for arg in command['arguments']), 'REPOSITORY_NATIVE_ARGUMENTS_INVALID')
        require(safe_path(command['workingDirectory']).is_dir(), 'REPOSITORY_NATIVE_WORKDIR_REQUIRED')
        require(peer['programPin'] in command['programPins'], 'REPOSITORY_NATIVE_PEER_PROGRAM_REQUIRED')
        require('--operation-request' not in command['arguments'] and '--operation-sha256' not in command['arguments'],
                'REPOSITORY_NATIVE_OPERATION_ARGUMENT_FORBIDDEN')
        expected = ['-B', config.implementation['wslCarrier']['path'], '--carrier',
                    source['wslCarrierConfigPin']['path'], '--carrier-sha256', source['wslCarrierConfigPin']['sha256']]
        if name == 'ownerCommand':
            expected.append('--launch')
        require(command['executablePin'] == source['pythonPin'] and command['arguments'] == expected and
                all(config.implementation[role] in command['programPins'] for role in ('wslCarrier', 'records', 'hostView')),
                'REPOSITORY_WSL_COMMAND_NOT_APPROVED')
    config.current()
    return {'schemaVersion': 'RepositoryInstallerPreflight/v1', 'requestPin': request_pin, 'sourceConfigPin': request['sourceOrTargetRef'], 'configurationPin': configuration_pin}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('configuration', 'configuration-sha256', 'request', 'request-sha256', 'output'):
        parser.add_argument('--' + field, required=True)
    args = parser.parse_args()
    config_pin, request_pin = pin_file(absolute(args.configuration)), pin_file(absolute(args.request))
    require(config_pin['sha256'] == args.configuration_sha256 and request_pin['sha256'] == args.request_sha256, 'REPOSITORY_INSTALLER_INPUT_CHANGED')
    atomic_output(absolute(args.output), preflight(config_pin, request_pin))


if __name__ == '__main__':
    import sys
    from repository_records import RepositoryError
    try:
        main()
    except Exception as error:
        print(error.code if isinstance(error, RepositoryError) else 'REPOSITORY_INSTALLER_' + type(error).__name__.upper(), file=sys.stderr)
        sys.exit(1)
