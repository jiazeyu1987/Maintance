"""Consume W01's actual native records, with independently selected subject pins."""
from pathlib import Path

from recovery_diagnostics_evidence import summarize_execution
from recovery_diagnostics_io import DiagnosticError, digest, exact, provisioned_inputs, require


def same(record, expected, fields, code='ORIGINAL_CURRENT_IDENTITY_MISMATCH'):
    require(type(record) is dict, 'ORIGINAL_RECORD_REQUIRED')
    for name in fields:
        require(name in record and type(record[name]) is type(expected[name]) and
                record[name] == expected[name], code)


def current_host_profile(profile, native, reader):
    """Verify the current v2 pinned profile; never infer a host from this observer."""
    exact(profile, ('schemaVersion', 'transport', 'hostOs', 'hostId', 'bootId', 'uid',
                    'sourceProfilePin', 'pythonPin', 'dispatcherPin', 'scriptPin',
                    'workingDirectory', 'evidenceRoot', 'launcherPin', 'launcherArguments',
                    'environment', 'resourceObserverPin', 'namespaceRegistrationPin'),
          'NATIVE_HOST_PROFILE_FIELDS_INVALID')
    require(profile['schemaVersion'] == 'RecoveryControlExecutionHost/v2',
            'NATIVE_HOST_PROFILE_MISMATCH')
    same(profile, native['clockDomain'], ('hostId', 'bootId'), 'NATIVE_HOST_PROFILE_MISMATCH')
    require(profile['hostOs'] in ('Linux', 'Windows') and profile['transport'] in ('LOCAL', 'WSL'),
            'NATIVE_HOST_TRANSPORT_INVALID')
    if profile['transport'] == 'WSL':
        require(profile['hostOs'] == 'Linux' and profile['launcherArguments'] ==
                ['--distribution', 'br20261010-w01w07-native', '--user', 'root', '--exec'],
                'NATIVE_FIXED_WSL_REQUIRED')
        reader.read(profile['launcherPin'], json_record=False)
        require(Path(profile['launcherPin']['path']).name.lower() == 'wsl.exe',
                'NATIVE_WSL_LAUNCHER_REQUIRED')
    else:
        require(profile['launcherPin'] is None and profile['launcherArguments'] == [],
                'NATIVE_LOCAL_LAUNCHER_FIELDS_INVALID')
    require(type(profile['environment']) is dict and bool(profile['environment']) and
            all(type(k) is str and type(v) is str for k, v in profile['environment'].items()),
            'NATIVE_ENVIRONMENT_REQUIRED')
    require(all(type(profile[k]) is str and Path(profile[k]).is_absolute()
                for k in ('workingDirectory', 'evidenceRoot')), 'NATIVE_HOST_DIRECTORIES_INVALID')
    source = reader.read(profile['sourceProfilePin'])
    require(type(source) is dict, 'NATIVE_SOURCE_PROFILE_INVALID')
    for key in ('pythonPin', 'dispatcherPin', 'scriptPin'):
        reader.read(profile[key], json_record=False)
    if profile['resourceObserverPin'] is not None:
        reader.read(profile['resourceObserverPin'], json_record=False)
    if source.get('schemaVersion') == 'RecoveryLocalEnvironmentRegistration/v1':
        require(source.get('usableForExecution') is True and type(source.get('host')) is dict and
                source['host'].get('selectedExecutionHost') is not None,
                'NATIVE_SOURCE_ENVIRONMENT_NOT_USABLE')
    if profile['hostOs'] == 'Windows':
        require(profile['uid'] is None and profile['namespaceRegistrationPin'] is None,
                'WINDOWS_NAMESPACE_REGISTRATION_REFUSED')
        return None
    require(type(profile['uid']) is int and profile['uid'] == 0, 'NAMESPACE_NATIVE_ROOT_REQUIRED')
    registration = reader.read(profile['namespaceRegistrationPin'])
    exact(registration, ('schemaVersion', 'taskId', 'hostId', 'bootId', 'uid', 'daemon', 'namespaces'),
          'NAMESPACE_REGISTRATION_FIELDS_INVALID')
    require(registration['schemaVersion'] == 'RecoveryControlNamespaceRegistration/v1' and
            registration['taskId'] == '20261010-backup-restore-modular-development',
            'NAMESPACE_REGISTRATION_VERSION_INVALID')
    same(registration, profile, ('hostId', 'bootId', 'uid'), 'NAMESPACE_HOST_IDENTITY_MISMATCH')
    require(source.get('schemaVersion') == 'RecoveryLocalEnvironmentRegistration/v1' and
            source.get('usableForExecution') is True and type(source.get('host')) is dict and
            source['host'].get('namespaceRegistrationPin') == profile['namespaceRegistrationPin'] and
            source['host'].get('selectedExecutionHost') is not None,
            'NAMESPACE_REGISTRATION_NOT_SOURCE_ANCHORED')
    daemon = registration['daemon']
    exact(daemon, ('pid', 'startTimeTicks', 'executablePin'), 'NAMESPACE_DAEMON_FIELDS_INVALID')
    require(type(daemon['pid']) is int and daemon['pid'] > 1 and
            type(daemon['startTimeTicks']) is int and daemon['startTimeTicks'] > 0,
            'NAMESPACE_DAEMON_IDENTITY_REQUIRED')
    reader.read(daemon['executablePin'], json_record=False)
    require(Path(daemon['executablePin']['path']).name == 'dockerd', 'NAMESPACE_DOCKER_DAEMON_REQUIRED')
    exact(registration['namespaces'], ('net', 'mount'), 'NAMESPACE_SET_INVALID')
    for key, filename in (('net', 'net'), ('mount', 'mnt')):
        namespace = registration['namespaces'][key]
        exact(namespace, ('path', 'device', 'inode'), 'NAMESPACE_FD_IDENTITY_FIELDS_INVALID')
        require(namespace['path'] == '/proc/%d/ns/%s' % (daemon['pid'], filename) and
                type(namespace['device']) is int and namespace['device'] >= 0 and
                type(namespace['inode']) is int and namespace['inode'] > 0,
                'NAMESPACE_FD_IDENTITY_REQUIRED')
    return registration


def current_namespace_entry(originals, profile, registration, native, intent, execution_root):
    """Consume the dispatcher's retained entry, without inspecting live namespaces."""
    entries = [(pin, value) for pin, value in originals if type(value) is dict and
               type(value.get('schemaVersion')) is str and
               value['schemaVersion'].startswith('RecoveryControlNamespaceEntry/')]
    if profile['hostOs'] == 'Windows':
        require(not entries, 'WINDOWS_NAMESPACE_ENTRY_REFUSED')
        return
    require(len(entries) == 1, 'NAMESPACE_ENTRY_MISSING_OR_AMBIGUOUS')
    entry_pin, entry = entries[0]
    require(entry['schemaVersion'] == 'RecoveryControlNamespaceEntry/v1',
            'NAMESPACE_ENTRY_VERSION_INVALID')
    require(Path(entry_pin['path']).parent == execution_root, 'NAMESPACE_ENTRY_ROOT_MISMATCH')
    exact(entry, ('schemaVersion', 'namespaceRegistrationPin', 'hostId', 'bootId', 'daemon',
                  'namespaces', 'enteredMonotonicNs', 'operationId', 'requestId', 'requestPin',
                  'profilePin', 'attemptId'), 'NAMESPACE_ENTRY_FIELDS_INVALID')
    same(entry, native, ('operationId', 'requestId', 'requestPin', 'profilePin', 'attemptId'),
         'NAMESPACE_ENTRY_SUBJECT_MISMATCH')
    same(entry, profile, ('namespaceRegistrationPin', 'hostId', 'bootId'),
         'NAMESPACE_ENTRY_HOST_MISMATCH')
    # Canonical equality also refuses bool-for-int substitutions in nested identities.
    require(all(digest(entry[k]) == digest(registration[k]) for k in ('daemon', 'namespaces')),
            'NAMESPACE_ENTRY_IDENTITY_MISMATCH')
    require(type(entry['enteredMonotonicNs']) is int and type(intent['startedMonotonicNs']) is int and
            0 <= entry['enteredMonotonicNs'] <= intent['startedMonotonicNs'],
            'NAMESPACE_ENTRY_CLOCK_BINDING_INVALID')


def summarize_current_execution(envelope, envelope_pin, reader, binding_pin, policy_pin, contracts, guard_ns):
    """Missing/old/mismatched original evidence cannot settle the current action."""
    try:
        require(binding_pin is not None, 'CURRENT_EXECUTION_BINDING_MISSING')
        trust = provisioned_inputs(reader, policy_pin)
        require(trust['executionSubjectBindingPin'] == binding_pin, 'SUBJECT_BINDING_NOT_IN_PROVISIONED_TRUST')
        selected = reader.read(binding_pin)
        exact(selected, ('schemaVersion', 'nativeProcessBindingPin', 'executionEvidencePin',
                         'operationResultPin'), 'CURRENT_EXECUTION_BINDING_INVALID')
        require(selected['schemaVersion'] == 'RecoveryDiagnosticSubjectBinding/v1' and
                selected['executionEvidencePin'] == envelope_pin, 'CURRENT_EXECUTION_EVIDENCE_MISMATCH')
        execution_root = Path(selected['nativeProcessBindingPin']['path']).parent
        require(Path(envelope_pin['path']).parent == execution_root and
                Path(selected['operationResultPin']['path']).parent == execution_root,
                'CURRENT_EXECUTION_RESULT_ROOT_MISMATCH')
        native = reader.read(selected['nativeProcessBindingPin'])
        require(native.get('schemaVersion') == 'RecoveryControlObservationBinding/v1',
                'NATIVE_PROCESS_BINDING_VERSION_INVALID')
        require(type(native.get('pid')) is int and native['pid'] > 0 and
                type(native.get('processStartedAt')) is str and native['processStartedAt'],
                'NATIVE_PROCESS_IDENTITY_REQUIRED')
        # W01 records OS process creation identity (Linux boot/start ticks or
        # Windows FILETIME). It is not a UTC timestamp and must stay opaque.
        subject = reader.read(native['requestPin'])
        contracts.validate('OperationRequest', subject)
        same(native, subject, ('operationId', 'requestId'))
        require(native['attemptId'] and native['observerEpoch'], 'NATIVE_ATTEMPT_IDENTITY_REQUIRED')
        exact(native['clockDomain'], ('hostId', 'bootId'), 'CLOCK_DOMAIN_INVALID')
        profile = reader.read(native['profilePin'])
        registration = current_host_profile(profile, native, reader)
        intent = reader.read(native['intentPin'])
        require(intent.get('schemaVersion') == 'RecoveryControlNativeIntent/v1', 'NATIVE_INTENT_VERSION_INVALID')
        fields = ('operationId', 'requestId', 'requestPin', 'attemptId', 'observerEpoch', 'clockDomain', 'profilePin')
        same(intent, native, fields)
        require(intent.get('pythonPin') == profile['pythonPin'] and intent.get('scriptPin') == profile['scriptPin'],
                'NATIVE_EXECUTOR_PROFILE_MISMATCH')
        require(envelope.get('schemaVersion') == 'recovery-execution-evidence/v1', 'EXECUTION_VERSION_INVALID')
        same(envelope, native, ('operationId', 'attemptId', 'observerEpoch', 'clockDomain'))
        require(type(envelope.get('originalPins')) is list and native['intentPin'] in envelope['originalPins'] and
                native['requestPin'] in envelope['originalPins'] and native['profilePin'] in envelope['originalPins'] and
                profile['sourceProfilePin'] in envelope['originalPins'], 'CURRENT_EXECUTION_ORIGINALS_MISSING')
        originals = []
        for reference in envelope['originalPins']:
            if reference not in envelope['streamRefs'].values():
                record = reader.read(reference)
                originals.append((reference, record))
            else:
                reader.read(reference, json_record=False)
        current_namespace_entry(originals, profile, registration, native, intent, execution_root)
        exits = [(p, r) for p, r in originals if type(r) is dict and
                 r.get('schemaVersion') == 'RecoveryControlNativeExit/v1']
        resources = [(p, r) for p, r in originals if type(r) is dict and
                     r.get('schemaVersion') == 'RecoveryControlResourceObservation/v1']
        require(len(exits) == 1, 'NATIVE_ORIGINAL_EXIT_MISSING_OR_AMBIGUOUS')
        exit_pin, exited = exits[0]
        require(Path(exit_pin['path']).parent == execution_root and
                Path(native['intentPin']['path']).parent == execution_root,
                'CURRENT_EXECUTION_ORIGINAL_ROOT_MISMATCH')
        same(exited, native, ('operationId', 'requestId', 'requestPin', 'attemptId', 'observerEpoch',
                             'clockDomain', 'intentPin', 'pid', 'processStartedAt'))
        require(type(exited.get('cliExitCode')) is int and exited.get('processTerminal') is True,
                'NATIVE_ORIGINAL_EXIT_UNKNOWN')
        require(envelope['exits'] == {'executor': exited['cliExitCode'], 'runner': None, 'test': None} and
                envelope['processTerminal'] is True, 'ORIGINAL_ENVELOPE_FACT_MISMATCH')
        require(type(exited.get('timedOut')) is bool and
                (not exited['timedOut'] or envelope['timedOut']), 'NATIVE_TIMEOUT_FACT_MISMATCH')
        require(len(resources) == 1, 'RESOURCE_TERMINAL_EVIDENCE_MISSING')
        _, resource = resources[0]
        same(resource, native, ('operationId', 'requestId', 'requestPin', 'attemptId', 'observerEpoch',
                               'clockDomain', 'pid', 'processStartedAt'))
        require(resource.get('originalExitPin') == exit_pin and type(resource.get('resourceTerminal')) is bool and
                type(resource.get('originalPins')) is list and resource['originalPins'],
                'RESOURCE_OBSERVATION_BINDING_INVALID')
        require(resource['resourceTerminal'] == envelope['resourceTerminal'], 'ORIGINAL_ENVELOPE_FACT_MISMATCH')
        reader.verify_nested(resource)
        for reference in envelope['streamRefs'].values():
            require(reference is not None and reference in envelope['originalPins'], 'ORIGINAL_STREAM_MISSING')
            require(Path(reference['path']).parent == Path(exit_pin['path']).parent,
                    'NATIVE_STREAM_EXECUTION_ROOT_MISMATCH')
            reader.read(reference, json_record=False)
        samples = envelope['samples']
        require(samples and samples[0]['phase'] == 'DISPATCH' and samples[-1]['phase'] == 'ORIGINAL_EXIT' and
                samples[0]['monotonicNs'] >= intent['startedMonotonicNs'] and
                samples[-1]['monotonicNs'] >= exited['observedMonotonicNs'] and
                samples[-1]['bytes'] == sum(p['bytes'] for p in envelope['streamRefs'].values()),
                'NATIVE_CLOCK_TRANSPORT_BINDING_INVALID')
        result = reader.read(selected['operationResultPin'])
        contracts.validate('OperationResult', result)
        same(result, subject, ('operationId', 'requestId', 'action'), 'SUBJECT_RESULT_IDENTITY_MISMATCH')
        summary = summarize_execution(envelope, guard_ns)
        expected_cli = {'SUCCEEDED': 0, 'FAILED_RETAINED': 1, 'TERMINAL_UNKNOWN': 2}[result['state']]
        require(exited['cliExitCode'] == expected_cli, 'CLI_RESULT_EXIT_MISMATCH')
        if result['state'] == 'SUCCEEDED':
            require(result['failureCode'] is None and result['data'] is not None and
                    result['actualExitCode'] in (None, 0), 'SUBJECT_SUCCESS_RESULT_INVALID')
        identity = {name: native[name] for name in ('operationId', 'requestId', 'attemptId', 'pid',
                    'processStartedAt', 'observerEpoch')}
        identity.update(action=subject['action'], **native['clockDomain'])
        summary.update(subjectIdentity=identity, subjectRequestPin=native['requestPin'],
                       cliExitCode=exited['cliExitCode'], childExecutorExitCode=result['actualExitCode'],
                       currentOriginalsVerified=True, actualExitCode=result['actualExitCode'])
        return summary
    except (DiagnosticError, KeyError, TypeError) as error:
        code = error.code if isinstance(error, DiagnosticError) else 'NATIVE_ORIGINAL_FIELDS_INVALID'
        return {'state': 'TERMINAL_UNKNOWN', 'failureCode': code, 'actualExitCode': None,
                'cliExitCode': None, 'childExecutorExitCode': None, 'exits': None,
                'timedOut': None, 'timeoutLayer': None, 'elapsedNs': None,
                'clockProblems': [], 'clockSetter': 'UNKNOWN', 'processTerminal': None,
                'resourceTerminal': None, 'currentOriginalsVerified': False}
