"""W03 explicit single-operator entry; legacy functions remain separate callers."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

from repository_catalog import Catalog
from repository_records import (Configuration, Deadline, RepositoryError, VERSION,
                                absolute, atomic_output, document, pin_file,
                                read_pin, require, timestamp, utc, write_new)
from repository_retention import (RepositoryLock, capacity_observation,
                                 execute_retention, plan_retention)

SUPPORTED = {'BACKUP_FULL', 'BACKUP_INCREMENTAL', 'LIST_POINTS', 'POINT_DETAIL',
             'READBACK_VERIFY', 'RETENTION_PLAN', 'RETENTION_EXECUTE'}


def configured():
    from repository_host_view import bootstrap
    bootstrap()
    path = os.environ.get('INTRUOYI_REPOSITORY_CONFIG_PATH')
    digest = os.environ.get('INTRUOYI_REPOSITORY_CONFIG_SHA256')
    require(path is not None and digest is not None, 'REPOSITORY_SERVICE_CONFIG_REQUIRED')
    pin = pin_file(absolute(path))
    require(pin['sha256'] == digest, 'REPOSITORY_SERVICE_CONFIG_CHANGED')
    return Configuration(pin)


def protect_evidence_directory(config, path, deadline):
    if os.name == 'nt':
        quoted = str(path).replace("'", "''")
        script = "$ErrorActionPreference='Stop';Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Security') -ErrorAction Stop;$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User;$acl=[Security.AccessControl.DirectorySecurity]::new();$acl.SetOwner($sid);$acl.SetAccessRuleProtection($true,$false);$rule=[Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow');$acl.AddAccessRule($rule);Set-Acl -LiteralPath '" + quoted + "' -AclObject $acl"
        process = subprocess.Popen([config.value['powershellPin']['path'], '-NoProfile', '-NonInteractive', '-Command', script], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            code = process.wait(timeout=deadline.remaining())
        except subprocess.TimeoutExpired as error:
            raise RepositoryError('REPOSITORY_EVIDENCE_ACL_TERMINAL_UNKNOWN', unknown=True, actual_exit=process.poll()) from error
        require(code == 0, 'REPOSITORY_PRIVATE_EVIDENCE_ACL_REQUIRED')
    else:
        path.chmod(0o700)


def invoke_publisher(config, request, request_pin, deadline, evidence_dir, current_input=None):
    if config.native_lab:
        require(current_input is None, 'REPOSITORY_LAB_PRODUCTION_CURRENT_INPUT_REFUSED')
        return invoke_native_publisher(config, request, request_pin, deadline, evidence_dir)
    source = document(read_pin(request['sourceOrTargetRef']))
    require(source['schemaVersion'] == 'RepositoryBackupSource/v1' and source['repositoryId'] == config.value['repositoryId'], 'REPOSITORY_SOURCE_CONFIG_INVALID')
    # All executable/script locations come from the independently pinned service config.
    argv = [config.value['powershellPin']['path'], '-NoProfile', '-NonInteractive', '-File', config.value['publisherPin']['path'], '-Mode', 'repository-backup', '-RepositoryRequestPath', request_pin['path'], '-RepositoryRequestSha256', request_pin['sha256'], '-RepositoryInstallerPath', config.value['installerPin']['path'], '-RepositoryInstallerSha256', config.value['installerPin']['sha256'], '-RepositoryConfigurationPath', config.pin['path'], '-RepositoryConfigurationSha256', config.pin['sha256'], '-RepositoryResultPath', (evidence_dir / 'publication.json').as_posix()]
    invocation_pin = write_new(evidence_dir / 'publisher-invocation.json', {'schemaVersion': 'RepositoryPublisherInvocation/v1', 'operationId': request['operationId'], 'requestPin': request_pin, 'publisherPin': config.value['publisherPin'], 'installerPin': config.value['installerPin'], 'powershellPin': config.value['powershellPin'], 'cwd': str(Path(config.value['publisherPin']['path']).parent), 'startedAt': utc(), 'deadlineMilliseconds': int(deadline.remaining() * 1000)})
    config.current()
    argv.extend(['-RepositoryRemainingMilliseconds', str(int(deadline.remaining() * 1000))])
    if current_input is not None:
        require(request['action'] == 'BACKUP_FULL', 'REPOSITORY_CURRENT_INPUT_FULL_REQUIRED')
        argv.append('-RepositoryInitializeCurrentInput')
        input_raw = (json.dumps(current_input, separators=(',', ':'), ensure_ascii=True)+'\n').encode('ascii')
        require(len(input_raw) <= 4*1024*1024, 'REPOSITORY_CURRENT_INPUT_TOO_LARGE')
    input_errors = []
    input_thread = None
    stdout = (evidence_dir / 'publisher.stdout').open('xb')
    stderr = (evidence_dir / 'publisher.stderr').open('xb')
    process = None
    try:
        runtime_environment = dict(os.environ)
        # Module autoload must use the selected runtime, including when the
        # caller is PowerShell 7 and the configured publisher is Windows 5.1.
        runtime_environment['PSModulePath'] = str(Path(config.value['powershellPin']['path']).parent / 'Modules')
        process = subprocess.Popen(argv, cwd=Path(config.value['publisherPin']['path']).parent, env=runtime_environment,
            stdin=subprocess.PIPE if current_input is not None else subprocess.DEVNULL, stdout=stdout, stderr=stderr)
        if current_input is not None:
            def deliver():
                try:
                    process.stdin.write(input_raw); process.stdin.flush(); process.stdin.close()
                except BaseException as error:
                    input_errors.append(type(error).__name__)
            input_thread = threading.Thread(target=deliver, daemon=True, name='repository-current-input')
            input_thread.start()
        write_new(evidence_dir / 'publisher-process.json', {'schemaVersion': 'RepositoryPublisherProcess/v1', 'pid': process.pid, 'invocationPin': invocation_pin, 'startedAt': utc()})
        try:
            actual_exit = process.wait(timeout=deadline.remaining())
        except subprocess.TimeoutExpired as error:
            # No automatic kill/restart: an active owner may still protect the source.
            write_new(evidence_dir / 'publisher-terminal.json', {'state': 'TERMINAL_UNKNOWN', 'pid': process.pid, 'actualExitCode': process.poll(), 'finishedAt': utc(), 'invocationPin': invocation_pin})
            raise RepositoryError('REPOSITORY_PUBLISHER_TERMINAL_UNKNOWN', unknown=True, actual_exit=process.poll()) from error
    except BaseException as error:
        # A budget or evidence write can fail immediately after Popen too.
        # Never turn that still-live process into a known failure/released lock.
        if process is not None and process.poll() is None and not (isinstance(error, RepositoryError) and error.unknown):
            raise RepositoryError('REPOSITORY_PUBLISHER_TERMINAL_UNKNOWN', unknown=True, actual_exit=None) from error
        raise
    finally:
        stdout.close()
        stderr.close()
    terminal_pin = write_new(evidence_dir / 'publisher-terminal.json', {'state': 'EXITED', 'pid': process.pid, 'actualExitCode': actual_exit, 'finishedAt': utc(), 'invocationPin': invocation_pin})
    if input_thread is not None:
        try:
            input_thread.join(timeout=deadline.remaining())
        except RepositoryError as error:
            raise RepositoryError('REPOSITORY_CURRENT_INPUT_DELIVERY_UNKNOWN', unknown=True, actual_exit=actual_exit) from error
        if input_thread.is_alive():
            raise RepositoryError('REPOSITORY_CURRENT_INPUT_DELIVERY_UNKNOWN', unknown=True, actual_exit=actual_exit)
    if input_errors:
        raise RepositoryError('REPOSITORY_CURRENT_INPUT_DELIVERY_UNKNOWN', unknown=True, actual_exit=actual_exit)
    if actual_exit == 2 or any(document(read_pin(p))['state'] == 'TERMINAL_UNKNOWN'
                              for p in helper_terminals(evidence_dir)):
        raise RepositoryError('REPOSITORY_NATIVE_HELPER_TERMINAL_UNKNOWN', unknown=True, actual_exit=actual_exit)
    owner_terminal = evidence_dir / 'owner-terminal.json'
    if owner_terminal.exists() and document(read_pin(pin_file(owner_terminal)))['state'] == 'TERMINAL_UNKNOWN':
        raise RepositoryError('REPOSITORY_ORIGINAL_OWNER_TERMINAL_UNKNOWN', unknown=True, actual_exit=actual_exit)
    require(actual_exit == 0, 'REPOSITORY_PUBLISHER_FAILED')
    result_pin = pin_file(evidence_dir / 'publication.json')
    publication = document(read_pin(result_pin))
    require(publication['actualExitCode'] == 0, 'REPOSITORY_ORIGINAL_OWNER_EXIT_FAILED')
    return publication, [invocation_pin, terminal_pin, result_pin], actual_exit


def invoke_native_publisher(config, request, request_pin, deadline, evidence_dir):
    from repository_native_lab import execution_host
    from repository_native_publisher import preflight
    preflight(config, request_pin)
    host = execution_host(config.value['executionHostPin'], config.value['authorityKeyPins'])
    command = config.value['publisherCommand']
    output = evidence_dir / 'publication.json'
    invocation = write_new(evidence_dir / 'publisher-invocation.json', dict(
        schemaVersion='RepositoryNativePublisherInvocation/v1', configurationPin=config.pin,
        requestPin=request_pin, command=command, executionHostPin=config.value['executionHostPin'],
        labContextPin=config.lab_context_pin, at=utc()))
    argv = [command['executablePin']['path'], *command['arguments'], '--configuration', config.pin['path'],
        '--configuration-sha256', config.pin['sha256'], '--request', request_pin['path'],
        '--request-sha256', request_pin['sha256'], '--output', str(output), '--evidence-root', str(evidence_dir),
        '--remaining-milliseconds', str(int(deadline.remaining()*1000))]
    environment = dict(host['environment'])
    environment['INTRUOYI_REPOSITORY_LAB_CONTEXT_PATH'] = config.lab_context_pin['path']
    environment['INTRUOYI_REPOSITORY_LAB_CONTEXT_SHA256'] = config.lab_context_pin['sha256']
    environment['INTRUOYI_BACKUP_LAB_CONTEXT_PATH'] = config.lab_context_pin['path']
    environment['INTRUOYI_BACKUP_LAB_CONTEXT_SHA256'] = config.lab_context_pin['sha256']
    environment['INTRUOYI_BACKUP_LAB_TRUST_PATH'] = config.lab_launch_trust_pin['path']
    environment['INTRUOYI_BACKUP_LAB_TRUST_SHA256'] = config.lab_launch_trust_pin['sha256']
    config.authorization(request, request['sourceOrTargetRef'])
    with (evidence_dir/'publisher.stdout').open('xb') as stdout, (evidence_dir/'publisher.stderr').open('xb') as stderr:
        process = subprocess.Popen(argv,cwd=command['workingDirectory'],env=environment,
                                   stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
        try:
            write_new(evidence_dir/'publisher-process.json',dict(pid=process.pid,invocationPin=invocation))
            code = process.wait(timeout=deadline.remaining())
        except BaseException as error:
            write_new(evidence_dir/'publisher-terminal.json',dict(state='TERMINAL_UNKNOWN',pid=process.pid,
                actualExitCode=process.poll(),invocationPin=invocation,at=utc()))
            raise RepositoryError('REPOSITORY_NATIVE_PUBLISHER_TERMINAL_UNKNOWN',unknown=True,
                                  actual_exit=process.poll()) from error
    terminal = write_new(evidence_dir/'publisher-terminal.json',dict(state='TERMINAL_UNKNOWN' if code==2 else 'EXITED',
        pid=process.pid,actualExitCode=code,invocationPin=invocation,at=utc()))
    if code==2: raise RepositoryError('REPOSITORY_NATIVE_PUBLISHER_TERMINAL_UNKNOWN',unknown=True,actual_exit=code)
    require(code==0, 'REPOSITORY_NATIVE_PUBLISHER_FAILED')
    publication_pin=pin_file(output)
    publication=document(read_pin(publication_pin))
    require(publication['actualExitCode']==0, 'REPOSITORY_NATIVE_ORIGINAL_OWNER_EXIT_FAILED')
    return publication,[invocation,terminal,publication_pin],code


def native_readback(config, request, request_pin, catalog, evidence_dir, deadline):
    from repository_native_publisher import preflight
    from repository_native_readback import SmbReadback
    from repository_records import signed_pin
    preflight(config, request_pin)
    source=document(read_pin(request['sourceOrTargetRef']))
    peer=signed_pin(source['nativePeerConfigPin'],config.value['authorityKeyPins'])
    point,manifest=catalog.load(request['selectedPointPin'])
    selected_manifest,archive=catalog.manifest(point)
    require(selected_manifest==manifest,'REPOSITORY_NATIVE_POINT_CHANGED')
    material=dict(manifestPin=point['manifestPin'],payloadTreePin=manifest['payloadTreePin'],payloadRefs=manifest['payloadRefs'])
    tree=document(read_pin(manifest['payloadTreePin']))
    with RepositoryLock(config,request) as owner:
        owner.check()
        with SmbReadback(peer['readbackConfig'],deadline) as reader:
            connection_id,originals=reader.verify(str(archive),tree,material)
        owner.check()
        require(connection_id, 'REPOSITORY_NATIVE_INDEPENDENT_CONNECTION_REQUIRED')
        result_pin=write_new(evidence_dir/'readback-original.json',dict(schemaVersion='RepositoryNativePointReadback/v1',
            requestPin=request_pin,pointPin=request['selectedPointPin'],independentConnectionId=connection_id,
            originalRecordsPin=originals,serverDurabilityVerified=False,independentFailureDomain=False,at=utc()))
    return result_pin


def helper_terminals(evidence_dir):
    """Collect only this request's actual child terminal records."""
    result = []
    for path in sorted(evidence_dir.rglob('*')):
        if not path.is_file() or not (path.name.endswith('.terminal') or
                path.name.startswith('installer-') and path.name.endswith('-terminal.json')):
            continue
        reference = pin_file(path)
        value = document(read_pin(reference))
        require(value.get('state') in {'EXITED', 'TERMINAL_UNKNOWN'} and
                (value.get('actualExitCode') is None or type(value['actualExitCode']) is int),
                'REPOSITORY_HELPER_TERMINAL_INVALID')
        result.append(reference)
    return result


def dispatch(config, request, request_pin, deadline, evidence_dir, current_input=None):
    require(request['action'] in SUPPORTED, 'REPOSITORY_ACTION_UNSUPPORTED')
    config.request(request)
    if config.native_lab:
        config.authorization(request, request['sourceOrTargetRef'])
    catalog = Catalog(config, deadline)
    action = request['action']
    require(current_input is None or action == 'BACKUP_FULL', 'REPOSITORY_CURRENT_INPUT_FULL_REQUIRED')
    keys = set(request['inputPins'])
    allowed = {'recoveryVerificationReport'} if action in ('LIST_POINTS', 'POINT_DETAIL', 'READBACK_VERIFY') else {'retentionPlan'} if action == 'RETENTION_EXECUTE' else set()
    require(keys <= allowed, 'REPOSITORY_UNEXPECTED_INPUT')
    report_pin = request['inputPins'].get('recoveryVerificationReport')
    if action == 'LIST_POINTS':
        rows = catalog.list(report_pin)
        return {'points': [row[1] for row in rows if row[0] is not None], 'pointPins': [row[0] for row in rows if row[0] is not None], 'incompleteArchives': [row[1] for row in rows if row[0] is None], 'capacity': capacity_observation(catalog) if all(row[0] is not None and row[1]['integrityState'] == 'COMPLETE' for row in rows) else {'state': 'BLOCKED', 'failureCode': 'REPOSITORY_INCOMPLETE_ARCHIVES'}}, [row[0] for row in rows if row[0] is not None], None
    if action in ('POINT_DETAIL', 'READBACK_VERIFY'):
        require(request['selectedPointPin'] is not None, 'REPOSITORY_POINT_REQUIRED')
        point = catalog.grade(request['selectedPointPin'], report_pin)
        require(action != 'READBACK_VERIFY' or point['rehearsalEligible'], point['blockedReason'] or 'REPOSITORY_READBACK_FAILED')
        pins=[request['selectedPointPin']]
        if action == 'READBACK_VERIFY' and config.native_lab:
            pins.append(native_readback(config,request,request_pin,catalog,evidence_dir,deadline))
        return point, pins, None
    if action == 'RETENTION_PLAN':
        planned = plan_retention(catalog, request)
        pin = write_new(evidence_dir / 'retention-plan.json', planned)
        return planned, [pin], None
    if action == 'RETENTION_EXECUTE':
        require(keys == {'retentionPlan'}, 'REPOSITORY_RETENTION_PLAN_REQUIRED')
        result = execute_retention(catalog, request, request['inputPins']['retentionPlan'], evidence_dir)
        return result, [write_new(evidence_dir / 'retention-result.json', result)], None
    config.copy_protection()
    config.authorization(request, request['sourceOrTargetRef'])
    if action == 'BACKUP_INCREMENTAL':
        require(request['selectedPointPin'] is not None, 'REPOSITORY_INCREMENTAL_PARENT_REQUIRED')
        chain = catalog.chain(request['selectedPointPin'])
        require(len(chain) < config.policy['maxChainPoints'] and (datetime.now(timezone.utc) - timestamp(chain[0][2]['createdAt'])).total_seconds() < config.policy['maxChainAgeSeconds'], 'REPOSITORY_NEW_FULL_REQUIRED')
    else:
        require(request['selectedPointPin'] is None, 'REPOSITORY_FULL_PARENT_FORBIDDEN')
    with RepositoryLock(config, request) as owner:
        owner.check()
        if current_input is None:
            publication, pins, actual_exit = invoke_publisher(config, request, request_pin, deadline, evidence_dir)
        else:
            publication, pins, actual_exit = invoke_publisher(config, request, request_pin, deadline, evidence_dir, current_input)
        owner.check()
        point_pin, point = catalog.register(publication, request)
        binding = catalog.binding(point_pin, point)
        sidecar_pin = pin_file(Path(point_pin['path']).with_name('recovery-repository-binding.json'))
        return point, pins + [point_pin, sidecar_pin, binding['recoveryMaterialPin'], binding['objectContentIndexPin']], actual_exit


def execute(request_path, output_path, *, current_input=None):
    started = utc()
    request_pin = pin_file(absolute(request_path))
    request = document(read_pin(request_pin))
    # Routing identities must be valid before any result can be attributed to a request.
    for key in ('operationId', 'requestId', 'action'):
        require(type(request.get(key)) is str and request[key], 'REPOSITORY_REQUEST_IDENTITY_INVALID')
    result = {'schemaVersion': 'backup-restore-operation-result/v1', 'operationId': request['operationId'], 'requestId': request['requestId'], 'action': request['action'], 'state': 'FAILED_RETAINED', 'failureCode': None, 'message': '', 'data': None, 'originalResultPins': [], 'startedAt': started, 'finishedAt': started, 'actualExitCode': None}
    evidence_dir = None
    owned_evidence = False
    exit_code = 1
    try:
        deadline = Deadline(request['deadlineMilliseconds'])
        config = configured()
        config.request(request)
        if config.native_lab:
            config.authorization(request, request['sourceOrTargetRef'])
        name = hashlib.sha256(request['requestId'].encode('utf-8')).hexdigest()
        evidence_dir = config.evidence / name
        if evidence_dir.exists():
            require(current_input is None, 'REPOSITORY_CURRENT_ATTEMPT_REPLAY_FORBIDDEN')
            saved = document(read_pin(pin_file(evidence_dir / 'request.json')))
            require(saved['requestPin'] == request_pin, 'REPOSITORY_REQUEST_ID_REUSED')
            if not (evidence_dir / 'result.json').exists():
                raise RepositoryError('REPOSITORY_PREVIOUS_EXECUTION_TERMINAL_UNKNOWN', unknown=True)
            prior = document(read_pin(pin_file(evidence_dir / 'result.json')))
            atomic_output(output_path, prior)
            return {'SUCCEEDED': 0, 'FAILED_RETAINED': 1, 'TERMINAL_UNKNOWN': 2}[prior['state']]
        evidence_dir.mkdir()
        owned_evidence = True
        protect_evidence_directory(config, evidence_dir, deadline)
        write_new(evidence_dir / 'request.json', {'requestPin': request_pin, 'version': VERSION, 'startedAt': started})
        if current_input is None:
            data, pins, actual_exit = dispatch(config, request, request_pin, deadline, evidence_dir)
        else:
            data, pins, actual_exit = dispatch(config, request, request_pin, deadline, evidence_dir, current_input)
        result.update(state='SUCCEEDED', data=data, originalResultPins=pins, actualExitCode=actual_exit, message='Repository operation completed')
        exit_code = 0
    except Exception as error:
        # Report the exact exception class/code without exposing path/command/credentials.
        unknown = isinstance(error, RepositoryError) and error.unknown
        result.update(state='TERMINAL_UNKNOWN' if unknown else 'FAILED_RETAINED', failureCode=error.code if isinstance(error, RepositoryError) else 'REPOSITORY_' + type(error).__name__.upper(), message='Repository operation failed; original local evidence retained', actualExitCode=error.actual_exit if isinstance(error, RepositoryError) else None)
        if evidence_dir is not None:
            for helper_pin in helper_terminals(evidence_dir):
                helper = document(read_pin(helper_pin))
                result['originalResultPins'].append(helper_pin)
                if helper['state'] == 'TERMINAL_UNKNOWN':
                    result['state'] = 'TERMINAL_UNKNOWN'
                    result['failureCode'] = 'REPOSITORY_NATIVE_HELPER_TERMINAL_UNKNOWN'
                    unknown = True
            # Recover the real child result even if its later output validation failed.
            terminal_path = evidence_dir / 'publisher-terminal.json'
            if terminal_path.exists():
                terminal_pin = pin_file(terminal_path)
                terminal = document(read_pin(terminal_pin))
                result['actualExitCode'] = terminal['actualExitCode']
                result['originalResultPins'].append(terminal_pin)
                if terminal['state'] == 'TERMINAL_UNKNOWN':
                    result['state'] = 'TERMINAL_UNKNOWN'
                    unknown = True
            owner_terminal_path = evidence_dir / 'owner-terminal.json'
            if owner_terminal_path.exists():
                owner_pin = pin_file(owner_terminal_path)
                original = document(read_pin(owner_pin))
                result['originalResultPins'].append(owner_pin)
                result['actualExitCode'] = original['actualExitCode']
                if original['state'] == 'TERMINAL_UNKNOWN':
                    result['state'] = 'TERMINAL_UNKNOWN'
                    result['failureCode'] = 'REPOSITORY_ORIGINAL_OWNER_TERMINAL_UNKNOWN'
                    unknown = True
        exit_code = 2 if unknown else 1
    result['finishedAt'] = utc()
    if owned_evidence and evidence_dir is not None and not (evidence_dir / 'result.json').exists():
        write_new(evidence_dir / 'result.json', result)
    atomic_output(output_path, result)
    return exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--configuration', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--version', action='version', version=VERSION)
    args = parser.parse_args()
    from repository_minimal import execute as execute_minimal
    return execute_minimal(args.configuration, args.request, args.output)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(error.code if isinstance(error, RepositoryError) else 'REPOSITORY_' + type(error).__name__.upper(), file=sys.stderr)
        sys.exit(1)
