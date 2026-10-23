"""Fresh EXECUTOR self-admission originals, produced by real owned children."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import time

from recovery_environment_contract import canonical, decode, exact, pin_file, require, utc, utc_now
from recovery_native_process import (PROCESS_FIELDS, REHEARSAL_ID, lab_path, pinned_bytes,
                                     persist_bytes, signed_payload)

ADMISSION_SCHEMA = 'RepositoryLabNativeInstallationAdmission/v1'
ADMISSION_FIELDS = set('schemaVersion rehearsalId collectionId sequence phase operationRequestPin serviceBindingPin launchPin installationPin nativeRuntimeTrustPin nativeRuntimeProofPin producerIdentityPin invocationPin manifestResultPin startedAt finishedAt issuedAt expiresAt'.split())
PHASE_FIELDS = ('rehearsalId', 'collectionId', 'sequence', 'phase', 'operationRequestPin', 'serviceBindingPin')
INVOCATION_FIELDS = set('schemaVersion state processProfile processResultPin operationId restoreId targetIdentityPin recoveryPoint stage actualExitCode startedAt finishedAt sourcePins resultPin commandId command argv cwd'.split())


def installation_argv(installation, entry_pin, installation_pin, authority_pin):
    from recovery_native_observation import wire_canonical
    require(entry_pin in installation['filePins'], 'NATIVE_ADMISSION_ENTRY_NOT_INSTALLED')
    return [installation['pythonPin']['path'], entry_pin['path'], 'admit-installation',
            '--installation-pin', wire_canonical(installation_pin).decode('utf-8'),
            '--authority-pin', wire_canonical(authority_pin).decode('utf-8')]


def installation_sources(installation, entry_pin):
    selected = [p for p in installation['filePins'] if p['path'].endswith('.py')]
    directory = PurePosixPath(entry_pin['path']).parent
    require(entry_pin in selected and all(any(p['path'] == str(directory / name) for p in selected)
            for name in ('repository_native_runtime.py', 'repository_records.py', 'recovery_environment_supervisor.py')),
            'NATIVE_ADMISSION_HELPER_NOT_INSTALLED')
    return selected + [installation['pythonPin']]


def unique_originals(pins, root):
    originals = {}
    for pin in pins:
        require(root in lab_path(pin['path']).parents, 'NATIVE_ADMISSION_ORIGINAL_OUTSIDE_ROOT')
        require(pin['path'] not in originals or originals[pin['path']] == pin,
                'NATIVE_ADMISSION_CONFLICTING_ORIGINAL')
        originals[pin['path']] = pin
        require(len(originals) <= 4096, 'NATIVE_ADMISSION_GRAPH_LIMIT')
        pinned_bytes(pin)
    return list(originals.values())


def invocation_originals(invocation_pin, authority_pin, root):
    from recovery_native_signer import verify_parent_terminal
    call = decode(pinned_bytes(invocation_pin))
    exact(call, INVOCATION_FIELDS, 'NATIVE_ADMISSION_INVOCATION_SHAPE')
    process = signed_payload(call['processResultPin'], authority_pin)
    exact(process, PROCESS_FIELDS, 'NATIVE_ADMISSION_PROCESS_SHAPE')
    require(call['schemaVersion'] == 'RecoveryInvocation/v1' and call['state'] == 'SUCCEEDED' and
            call['processProfile'] == 'linux-owned-child-subreaper-v1' and
            process['schemaVersion'] == 'RecoveryNativeProcessResult/v1' and
            process['rehearsalId'] == REHEARSAL_ID and process['terminationKind'] == 'EXITED' and
            type(process['actualExitCode']) is int and type(process['waitStatus']) is int and
            process['actualExitCode'] == process['waitStatus'] == 0 and process['descendantState'] == 'REAPED' and
            all(call[k] == process[k] for k in INVOCATION_FIELDS -
                {'schemaVersion', 'state', 'processProfile', 'processResultPin'}),
            'NATIVE_ADMISSION_ACTUAL_NATIVE_EXIT_REQUIRED')
    directory = lab_path(invocation_pin['path']).parent
    parent_pin = pin_file(directory / 'supervisor-terminal.json')
    original_pin = pin_file(directory / 'process-original.json')
    require(decode(pinned_bytes(original_pin)) == process, 'NATIVE_ADMISSION_PROCESS_ORIGINAL_CHANGED')
    verify_parent_terminal(process, decode(pinned_bytes(parent_pin)))
    pins = [invocation_pin, call['processResultPin'], process['stdoutPin'], process['stderrPin'],
            process['resultPin'], parent_pin, original_pin]
    return unique_originals(pins, root), call, process


def validate_admission_records(payload, call, process, manifest_bytes, stderr_bytes, context):
    """Validate already authenticated originals; callers also recheck their Pins."""
    from recovery_native_observation import wire_canonical
    exact(payload, ADMISSION_FIELDS, 'NATIVE_ADMISSION_SHAPE')
    require(payload['schemaVersion'] == ADMISSION_SCHEMA and payload['rehearsalId'] == REHEARSAL_ID and
            payload['operationRequestPin'] == context.launch['operationRequestPin'] and
            payload['serviceBindingPin'] in context.provision['serviceBindingPins'] and
            payload['launchPin'] == context.launch_pin and
            payload['installationPin'] == context.launch['installationPin'] and
            payload['nativeRuntimeTrustPin'] == context.installation['nativeRuntimeTrustPin'] and
            payload['nativeRuntimeProofPin'] == context.proof_pin and
            payload['producerIdentityPin'] == context.provision['producerIdentityPin'],
            'NATIVE_ADMISSION_PROTECTED_SELECTION')
    command_id = f'observe-{payload["sequence"]}-{payload["phase"].lower()}-installation'
    require(process['argv'] == call['argv'] == context.installation_command and
            process['commandId'] == call['commandId'] == command_id and
            process['command'] == call['command'] == wire_canonical(context.installation_command).decode('utf-8') and
            process['sourcePins'] == call['sourcePins'] == installation_sources(
                context.installation, context.launch['producerEntryPin']) and
            process['pythonPin'] == context.installation['pythonPin'] and
            process['nativeRuntimeProofPin'] == context.proof_pin and
            process['terminationKind'] == 'EXITED' and type(process['actualExitCode']) is int and
            type(process['waitStatus']) is int and process['actualExitCode'] == process['waitStatus'] == 0 and
            call['state'] == 'SUCCEEDED' and call['actualExitCode'] == 0 and process['descendantState'] == 'REAPED',
            'NATIVE_ADMISSION_LITERAL_EXECUTION_REQUIRED')
    require(payload['manifestResultPin'] == call['resultPin'] == process['resultPin'] == process['stdoutPin'] and
            manifest_bytes == wire_canonical(context.installation) and stderr_bytes == b'' and
            context.native_trust['runtimeRole'] == 'EXECUTOR', 'NATIVE_ADMISSION_FULL_MANIFEST_REQUIRED')
    require(payload['startedAt'] == call['startedAt'] == process['startedAt'] and
            payload['finishedAt'] == call['finishedAt'] == process['finishedAt'] and
            max(utc(context.launch['issuedAt']), utc(context.proof['issuedAt']),
                utc(context.producer_identity['issuedAt']), utc(context.grant['notBefore']),
                utc(context.lease['notBefore'])) <= utc(payload['startedAt']) < utc(payload['finishedAt']) <=
            utc(payload['issuedAt']) <= datetime.now(timezone.utc) < utc(payload['expiresAt']) <= utc(context.expires_at) and
            (datetime.now(timezone.utc) - utc(payload['startedAt'])).total_seconds() * 1000 <=
            context.provision['maximumAgeMilliseconds'] and time.monotonic() < context.deadline,
            'NATIVE_ADMISSION_ACTUAL_INTERVAL')


def admit_installation_original(payload, context):
    context.guard()
    originals, call, process = invocation_originals(payload['invocationPin'], context.authority_pin,
        lab_path(context.launch['evidenceRoot'], directory=True))
    context.admit_process(process)
    parent = decode(pinned_bytes(pin_file(lab_path(payload['invocationPin']['path']).parent /
                                         'supervisor-terminal.json')))
    verify_admission_parent(parent, process, context.producer_identity)
    validate_admission_records(payload, call, process, pinned_bytes(process['stdoutPin']),
                               pinned_bytes(process['stderrPin']), context)
    return originals


def verify_admission_parent(parent, process, producer):
    from recovery_native_signer import verify_parent_terminal
    verify_parent_terminal(process, parent)
    terminal = parent['terminal']; supervisor = terminal['supervisorIdentity']
    require(terminal.get('kind') == 'TERMINAL' and terminal.get('workerDispatched') is True and
            terminal.get('failureCode') is None and supervisor['pid'] == process['supervisorPid'] and
            supervisor['parent'] == producer['pid'] and supervisor['uid'] == producer['uid'] == 0 and
            supervisor['gid'] == producer['gid'] == 0 and supervisor['startTicks'] >= producer['startTicks'],
            'NATIVE_ADMISSION_ACTUAL_PRODUCER_PARENT_REQUIRED')


def produce_installation_admission(request, context, process):
    from recovery_native_observation import wire_canonical
    context.guard()
    prefix = f'observe-{request["sequence"]}-{request["phase"].lower()}'
    invocation = process.run(command_id=prefix + '-installation', argv=context.installation_command,
        cwd=context.provision['workingDirectory'],
        source_pins=installation_sources(context.installation, context.launch['producerEntryPin']),
        binding=context.operation_binding)
    call = decode(pinned_bytes(invocation))
    require(pinned_bytes(call['resultPin']) == wire_canonical(context.installation),
            'NATIVE_ADMISSION_CHILD_MANIFEST_CHANGED')
    payload = {k: request[k] for k in PHASE_FIELDS}
    payload.update(schemaVersion=ADMISSION_SCHEMA, launchPin=context.launch_pin,
        installationPin=context.launch['installationPin'], nativeRuntimeTrustPin=context.installation['nativeRuntimeTrustPin'],
        nativeRuntimeProofPin=context.proof_pin, producerIdentityPin=context.provision['producerIdentityPin'],
        invocationPin=invocation, manifestResultPin=call['resultPin'], startedAt=call['startedAt'],
        finishedAt=call['finishedAt'], issuedAt=utc_now(), expiresAt=context.expires_at)
    require(utc(request['issuedAt']) <= utc(payload['startedAt']), 'NATIVE_ADMISSION_PREDATES_INTENT')
    originals = admit_installation_original(payload, context)
    original = persist_bytes(process.root / (prefix + '-installation-original.json'), canonical(payload))
    signed = process.signer.sign(original, deadline=process.deadline, worker_uid=process.uid)
    require(signed_payload(signed, context.authority_pin) == payload, 'NATIVE_ADMISSION_SIGNED_PAYLOAD_CHANGED')
    return signed, payload, [signed] + originals
