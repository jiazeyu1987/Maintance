"""Independent signed remote wait originals; client exit never proves them."""
import base64
from datetime import datetime

from recovery_engine import canonical, check_pin, current_window, pinned_json, require


def signed_terminal(ref, policy):
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    value = pinned_json(ref)
    require(set(value) == {'schemaVersion', 'keySha256', 'payload', 'signature'} and
            value['schemaVersion'] == 'RecoveryRemoteSignedTerminal/v1', 'REMOTE_SIGNED_TERMINAL_REQUIRED')
    keys = [item for item in policy['remoteTerminalKeyPins'] if item['sha256'] == value['keySha256']]
    require(len(keys) == 1, 'REMOTE_TERMINAL_AUTHORITY_UNKNOWN')
    key = load_pem_public_key(check_pin(keys[0])); require(isinstance(key, Ed25519PublicKey), 'REMOTE_TERMINAL_KEY_INVALID')
    key.verify(base64.b64decode(value['signature'], validate=True), canonical(value['payload']))
    return value['payload']


def remote_terminal(ref, intent_pin, expected, policy):
    value = signed_terminal(ref, policy)
    fields = {'schemaVersion', 'operationId', 'action', 'targetIdentityPin', 'sourceScopePin', 'recoveryPoint',
              'commandIntentPin', 'executionHostIdentityPin', 'originalProcessPin', 'exitEvidencePin', 'validFrom', 'validUntil'}
    require(set(value) == fields and value['schemaVersion'] == 'RecoveryRemoteTerminal/v1' and
            value['commandIntentPin'] == intent_pin and
            all(value[key] == expected[key] for key in ('operationId', 'action', 'targetIdentityPin', 'sourceScopePin',
                                                       'recoveryPoint', 'executionHostIdentityPin')), 'REMOTE_TERMINAL_BINDING_INVALID')
    current_window(value); check_pin(value['executionHostIdentityPin'])
    process = pinned_json(value['originalProcessPin']); exit_record = pinned_json(value['exitEvidencePin'])
    require(process['schemaVersion'] == 'RecoveryRemoteProcess/v1' and type(process['nativePid']) is int and process['nativePid'] > 0 and
            type(process['processStartIdentity']) is str and process['processStartIdentity'] and
            process['commandIntentPin'] == intent_pin and process['executionHostIdentityPin'] == value['executionHostIdentityPin'] and
            all(process[key] == expected[key] for key in ('operationId', 'action', 'targetIdentityPin', 'sourceScopePin', 'recoveryPoint')) and
            exit_record['schemaVersion'] == 'RecoveryRemoteWait/v1' and exit_record['originalProcessPin'] == value['originalProcessPin'] and
            exit_record['waitedPid'] == process['nativePid'] and type(exit_record['waitedPid']) is int and
            exit_record['processStartIdentity'] == process['processStartIdentity'] and
            type(exit_record['actualExitCode']) is int and exit_record['actualExitCode'] == 0 and
            exit_record['processTerminated'] is True and exit_record['timedOut'] is False,
            'REMOTE_ORIGINAL_PROCESS_TERMINATION_NOT_PROVEN')
    started = datetime.fromisoformat(process['startedAt'].replace('Z', '+00:00'))
    finished = datetime.fromisoformat(exit_record['finishedAt'].replace('Z', '+00:00'))
    observed = datetime.fromisoformat(value['validFrom'].replace('Z', '+00:00'))
    intent = pinned_json(intent_pin)
    dispatched = datetime.fromisoformat(intent['startedAt'].replace('Z', '+00:00'))
    require(dispatched <= started <= finished <= observed, 'REMOTE_TERMINAL_TIME_BINDING_INVALID')
    return [ref, value['originalProcessPin'], value['exitEvidencePin']]


def verified_step_terminal(result, request, policy):
    step = result['data']; records = step['originalInvocationPins']
    require(records, 'CUTOVER_ORIGINAL_EXITS_REQUIRED')
    remote_refs = []; remote = False; commands = []
    for ref in records:
        record = pinned_json(ref)
        if record.get('schemaVersion') != 'RecoveryCutoverInvocation/v1': continue
        commands.append(record)
        require(record['state'] == 'SUCCEEDED' and type(record['actualExitCode']) is int and record['actualExitCode'] == 0 and
                type(record['nativePid']) is int and record['nativePid'] > 0 and
                record['operationId'] == request['operationId'] and record['action'] == request['action'],
                'CUTOVER_NATIVE_EXIT_NOT_VERIFIED')
        intent = pinned_json(record['commandIntentPin'])
        recipe_ref = policy['cutoverRecipePins'][request['action']]; recipe = pinned_json(recipe_ref)
        require(intent['schemaVersion'] == 'RecoveryCutoverCommandIntent/v1' and intent['recipePin'] == recipe_ref and
                all(intent[key] == request[key] for key in ('operationId', 'action', 'targetIdentityPin', 'sourceScopePin')) and
                intent['recoveryPoint'] == step['recoveryPoint'] and
                all(record[key] == intent[key] for key in ('toolPin', 'configurationPin', 'argvSha256', 'executionKind', 'executionHostIdentityPin')) and
                any(intent['toolPin'] == command['toolPin'] and intent['configurationPin'] == command['configurationPin'] and
                    intent['argvSha256'] == __import__('recovery_engine').digest(command['argv']) and
                    intent['executionKind'] == command['executionKind'] and
                    intent['executionHostIdentityPin'] == command['executionHostIdentityPin'] for command in recipe['commands']),
                'CUTOVER_COMMAND_INTENT_NOT_APPROVED')
        if record['executionKind'] == 'REMOTE':
            expected = {key: request[key] for key in ('operationId', 'action', 'targetIdentityPin', 'sourceScopePin')}
            expected.update(recoveryPoint=step['recoveryPoint'], executionHostIdentityPin=record['executionHostIdentityPin'])
            remote_refs.extend(remote_terminal(record['remoteTerminalProofPin'], record['commandIntentPin'], expected, policy)); remote = True
        else:
            require(record['executionKind'] == 'LOCAL' and record['remoteTerminalProofPin'] is None,
                    'CUTOVER_EXECUTION_KIND_INVALID')
    recipe = pinned_json(policy['cutoverRecipePins'][request['action']])
    require(len(commands) == len(recipe['commands']) and
            len({record['commandIntentPin']['sha256'] for record in commands}) == len(commands), 'CUTOVER_NATIVE_EXIT_MISSING')
    require(all(record['toolPin'] == command['toolPin'] and record['configurationPin'] == command['configurationPin'] and
                record['argvSha256'] == __import__('recovery_engine').digest(command['argv']) and
                record['executionKind'] == command['executionKind'] and
                record['executionHostIdentityPin'] == command['executionHostIdentityPin']
                for record, command in zip(commands, recipe['commands'])),
            'CUTOVER_COMMAND_ORDER_MISMATCH')
    return (True if remote else None), remote_refs
