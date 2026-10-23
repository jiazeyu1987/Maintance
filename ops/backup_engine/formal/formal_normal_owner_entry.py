"""Explicit private recipe entry for the same native control/archive owner.

This executable does not supply a deployment author. Its independently pinned
assembly must retain the actual native sources, transport and signed authority.
Missing assembly/configuration is an error before any capture or service action.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time

if __name__ == '__main__': sys.dont_write_bytecode = True

import formal_snapshot_linux as snapshot
from formal_normal_owner import NormalOwnerInputs, pin, require, strict_document, run_owner

TASK_ID = '20261010-full-incremental-capture-dev'
OWNER_THREAD_ID = '01a124c0-93ee-7320-b90c-8a08ee921c72'
MODULE_GROUP = 'W02'
EXECUTION_CONTRACT_SHA256 = '03daad32188896c4270b3313ff30d10e6828857e89c05bde576b65dfc934b6e3'
FUNCTION_IDS = {'F01.1', 'F01.2', 'F01.3', 'F03.1', 'F03.2', 'F03.3',
                'F03.4', 'F03.5', 'F03.6', 'F04.1', 'F04.2'}


def validate_attribution(contract, creation, attribution):
    """Current development attribution does not grant a runtime operation."""
    require(attribution == dict(taskId=TASK_ID, moduleGroup=MODULE_GROUP, ownerThreadId=OWNER_THREAD_ID),
            'BACKUP_INTERFACE_AUTHORITY_INVALID')
    require(type(contract) is dict and contract.get('schemaVersion') == 'backup-restore-execution-contract/v1' and
            contract.get('taskId') == '20261010-backup-restore-modular-development' and
            contract.get('status') == 'frozen_for_code_development', 'BACKUP_INTERFACE_AUTHORITY_INVALID')
    require(type(contract.get('assignments')) is list, 'BACKUP_INTERFACE_AUTHORITY_INVALID')
    matches = [row for row in contract['assignments'] if type(row) is dict and row.get('group') == MODULE_GROUP]
    require(len(matches) == 1 and matches[0].get('taskId') == TASK_ID and
            set(matches[0].get('functionIds', [])) == FUNCTION_IDS, 'BACKUP_INTERFACE_AUTHORITY_INVALID')
    require(type(creation) is dict and creation.get('schemaVersion') == 'backup-restore-thread-creation-results/v1' and
            type(creation.get('records')) is list, 'BACKUP_INTERFACE_AUTHORITY_INVALID')
    matches = [row for row in creation['records'] if type(row) is dict and row.get('moduleId') == MODULE_GROUP]
    require(len(matches) == 1 and matches[0].get('taskId') == TASK_ID and
            matches[0].get('threadId') == OWNER_THREAD_ID, 'BACKUP_INTERFACE_AUTHORITY_INVALID')


def validate_recipe(value):
    fields = {'schemaVersion', 'action', 'totalSeconds', 'attribution', 'executionContractPin', 'creationResultsPin',
              'claimRoot', 'claimBinding', 'nativeAssemblyProgramPin', 'nativeAssemblyConfigPin'}
    if type(value) is dict and value.get('schemaVersion')=='backup-lab-normal-owner-recipe/v1':
        from formal_backup_lab import validate_recipe as validate_lab_recipe
        return validate_lab_recipe(value)
    require(type(value) is dict and value.get('schemaVersion') in
            {'backup-normal-owner-recipe/v1', 'backup-normal-owner-recipe/v2'}, 'BACKUP_INTERFACE_SCHEMA_INVALID')
    initializing = value['schemaVersion'] == 'backup-normal-owner-recipe/v2'
    if initializing:
        fields |= {'nativeInitializationProgramPin', 'nativeInitializationConfigPin'}
    require(type(value) is dict and set(value) == fields and
            value['action'] == 'serve-approved-backup-owner' and type(value['totalSeconds']) is int and
            1 <= value['totalSeconds'] <= 7200 and type(value['claimRoot']) is str and
            value['claimRoot'].startswith('/') and '\\' not in value['claimRoot'] and
            type(value['claimBinding']) is dict, 'BACKUP_INTERFACE_SCHEMA_INVALID')
    for key in ('executionContractPin', 'creationResultsPin', 'nativeAssemblyProgramPin', 'nativeAssemblyConfigPin'):
        pin(value[key])
    if initializing:
        pin(value['nativeInitializationProgramPin']); pin(value['nativeInitializationConfigPin'])
    require(value['executionContractPin']['sha256'] == EXECUTION_CONTRACT_SHA256,
            'BACKUP_INTERFACE_AUTHORITY_INVALID')
    return value


def run_approved_normal_owner(request_path, expected_request_sha256, *, request_fd, response_fd):
    from formal_filesystem_watchdog import require_native_runtime
    require_native_runtime()
    require(os.geteuid() == 0 and type(expected_request_sha256) is str and
            re.fullmatch(r'[0-9a-f]{64}', expected_request_sha256), 'BACKUP_INTERFACE_AUTHORITY_INVALID')
    import formal_boot_state as boot
    started = time.monotonic(); originals = {}; directories = {}
    def original(reference, limit):
        pin(reference); path = boot._absolute(reference['path'])
        pair = boot._read_secure(path, 0o600, limit, no_atime=True)
        require(len(pair[0]) == reference['bytes'] and hashlib.sha256(pair[0]).hexdigest() == reference['sha256'],
                'BACKUP_INTERFACE_SOURCE_CHANGED')
        require(path not in originals, 'BACKUP_INTERFACE_SCHEMA_INVALID')
        with boot._directory(path.parent, no_atime=True) as (_, chain): directories[path.parent] = chain
        originals[path] = (pair, limit)
        return pair[0]
    request = boot._absolute(request_path)
    first = boot._read_secure(request, 0o600, 65536, no_atime=True)
    require(hashlib.sha256(first[0]).hexdigest() == expected_request_sha256, 'BACKUP_INTERFACE_SOURCE_CHANGED')
    recipe = validate_recipe(strict_document(first[0], 65536))
    original(dict(path=str(request), bytes=len(first[0]), sha256=expected_request_sha256), 65536)
    contract = strict_document(original(recipe['executionContractPin'], 1024*1024), 1024*1024)
    creation = strict_document(original(recipe['creationResultsPin'], 1024*1024), 1024*1024)
    validate_attribution(contract, creation, recipe['attribution'])
    program = original(recipe['nativeAssemblyProgramPin'], 1024*1024)
    config_raw = original(recipe['nativeAssemblyConfigPin'], 16*1024*1024)
    config = strict_document(config_raw, 16*1024*1024)
    lab = recipe['schemaVersion']=='backup-lab-normal-owner-recipe/v1'
    initializing = recipe['schemaVersion'] in ('backup-normal-owner-recipe/v2','backup-lab-normal-owner-recipe/v1')
    if initializing:
        initialization_program = original(recipe['nativeInitializationProgramPin'], 4*1024*1024)
        initialization_profile = strict_document(original(recipe['nativeInitializationConfigPin'], 65536), 65536)
        if lab:
            require(type(initialization_profile) is dict and
                    initialization_profile.get('schemaVersion')=='RepositoryLabNativeInitialization/v1' and
                    initialization_profile.get('labContextPin')==recipe['labContextPin'],
                    'BACKUP_LAB_EXPLICIT_INITIALIZER_REQUIRED')
    deadline = started + recipe['totalSeconds']; claim = None; inputs = None
    outer = snapshot.observation_deadline.get()
    if outer is not None: deadline = min(deadline, outer)
    token = snapshot.observation_deadline.set(deadline)
    def originals_guard():
        require(time.monotonic() < deadline, 'BACKUP_INTERFACE_BUDGET_EXPIRED')
        for path, chain in directories.items(): boot._directory_unchanged(path, chain)
        for path, (pair, limit) in originals.items():
            require(boot._read_secure(path, 0o600, limit, no_atime=True) == pair, 'BACKUP_INTERFACE_SOURCE_CHANGED')
        for path, (pair, _) in originals.items():
            require(boot._signature(path.lstat()) == pair[1], 'BACKUP_INTERFACE_SOURCE_CHANGED')
        for path, chain in directories.items(): boot._directory_unchanged(path, chain)
        require(time.monotonic() < deadline, 'BACKUP_INTERFACE_BUDGET_EXPIRED')
    lab_token = None
    try:
        originals_guard()
        if lab:
            from formal_backup_lab import launch_authority, active_lab
            authority=launch_authority(originals_guard)
            authority.verify_service(initialization_profile['configurationPin'])
            require(recipe['labContextPin']==config.get('labContextPin')==authority.context_pin,
                    'BACKUP_LAB_CONTEXT_CHANGED')
            from formal_backup_lab import LAB_ROOT
            require(recipe['claimBinding'].get('operationId')==authority.request['operationId'] and
                    recipe['claimBinding'].get('sourceFingerprint')==authority.identity['sourceFingerprint'] and
                    recipe['claimBinding'].get('databaseUuid')==authority.identity['databaseUuid'] and
                    Path(LAB_ROOT) in Path(recipe['claimRoot']).parents,
                    'BACKUP_LAB_OPERATION_CLAIM_CHANGED')
            from formal_backup_lab import verify_runtime_derivation
            verify_runtime_derivation(recipe,config,initialization_profile,authority)
            lab_token=active_lab.set(authority)
        claim = snapshot.FormalMaintenanceClaim(recipe['claimRoot'], recipe['claimBinding'], resume=True)
        originals_guard()
        require(all(pair[1][0] == claim.root.stat().st_dev for pair, _ in originals.values()),
                'BACKUP_INTERFACE_SOURCE_CHANGED')
        # No assembly input is consumed before the actual acquiring PID/FD
        # installs the current publisher originals and receives its exact ACK.
        initialization_guard = None
        if initializing:
            initialization_name = 'formal_approved_current_input_' + recipe['nativeInitializationProgramPin']['sha256']
            require(initialization_name not in sys.modules, 'BACKUP_INTERFACE_SEQUENCE_INVALID')
            initialization_spec = importlib.util.spec_from_file_location(initialization_name,
                recipe['nativeInitializationProgramPin']['path'])
            require(initialization_spec is not None and initialization_spec.loader is not None,
                    'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
            initializer = importlib.util.module_from_spec(initialization_spec); sys.modules[initialization_name] = initializer
            exec(compile(initialization_program, recipe['nativeInitializationProgramPin']['path'], 'exec'), initializer.__dict__)
            require(callable(getattr(initializer, 'initialize_current_owner', None)),
                    'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
            _, initialization_guard = initializer.initialize_current_owner(claim, initialization_profile, config,
                request_fd=request_fd, response_fd=response_fd, guard=originals_guard, deadline=deadline)
            require(callable(initialization_guard), 'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        def held_originals_guard():
            originals_guard()
            if lab:authority.check()
            if initializing: initialization_guard()
            originals_guard()
        name = 'formal_approved_native_assembly_' + recipe['nativeAssemblyProgramPin']['sha256']
        require(name not in sys.modules, 'BACKUP_INTERFACE_SEQUENCE_INVALID')
        spec = importlib.util.spec_from_file_location(name, recipe['nativeAssemblyProgramPin']['path'])
        require(spec is not None and spec.loader is not None, 'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        module = importlib.util.module_from_spec(spec); sys.modules[name] = module
        exec(compile(program, recipe['nativeAssemblyProgramPin']['path'], 'exec'), module.__dict__)
        originals_guard()
        require(callable(getattr(module, 'assemble_original_normal_owner', None)),
                'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        inputs = module.assemble_original_normal_owner(claim, config, original_guard=held_originals_guard, deadline=deadline)
        require(type(inputs) is NormalOwnerInputs and inputs.program_reference == recipe['nativeAssemblyProgramPin'],
                'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        def control_guard():
            held_originals_guard(); inputs.adapter.control_guard(); held_originals_guard()
        result = run_owner(claim, inputs=inputs, control=(request_fd, response_fd), guard=control_guard, deadline=deadline)
        require(result['state'] == 'OWNER_CLOSE_CONFIRMED_PENDING_ORIGINAL_EXIT', 'BACKUP_INTERFACE_TERMINAL_UNKNOWN')
        return result
    except BaseException as error:
        if getattr(error, 'retainClaim', False) and claim is not None:
            # Installation/handshake uncertainty is fail-stop. Keep this exact
            # native claim/FD alive for resource coordination; never close and
            # reacquire, replay, capture, restore or release on another thread.
            reason = getattr(error, 'code', str(error))
            if not (type(reason) is str and re.fullmatch(r'[A-Z][A-Z0-9_]{0,127}', reason)):
                reason = 'BACKUP_INTERFACE_INITIALIZATION_RETAINED'
            failure = dict(state='TERMINAL_UNKNOWN', failureCode=reason, exceptionType=type(error).__name__,
                           holderPid=os.getpid(), claimFd=claim._fd, claimRoot=str(claim.root),
                           originalClaimLockIdentity=list(claim._lock_identity))
            try:
                claim._write(claim.root/'initialization-failure.json', json.dumps(failure,
                    separators=(',', ':')).encode('ascii'))
            except BaseException as record_error:
                failure['recordWriteFailure'] = type(record_error).__name__
            finally:
                try:
                    print(json.dumps(failure, separators=(',', ':')), file=sys.stderr, flush=True)
                finally:
                    while True: time.sleep(1)
        raise
    finally:
        try:
            try:
                if inputs is not None: inputs.adapter.close()
            finally:
                if claim is not None: claim.close()
        finally:
            if lab_token is not None: active_lab.reset(lab_token)
            snapshot.observation_deadline.reset(token)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--expected-request-sha256', required=True)
    parser.add_argument('--request-fd', type=int, default=0)
    parser.add_argument('--response-fd', type=int, default=1)
    args = parser.parse_args(argv)
    try:
        run_approved_normal_owner(args.request, args.expected_request_sha256,
                                  request_fd=args.request_fd, response_fd=args.response_fd)
        # stdout is exclusively the original wire; exit is observed by W03.
        return 0
    except BaseException as error:
        code = getattr(error, 'code', 'BACKUP_INTERFACE_COMPONENT_FAILED')
        if not (type(code) is str and re.fullmatch(r'[A-Z][A-Z0-9_]{0,127}', code)):
            code = 'BACKUP_INTERFACE_COMPONENT_FAILED'
        state = getattr(error, 'ownerTerminalState', 'FAILED_RETAINED')
        details = dict(state=state, failureCode=code, sourceRestored=getattr(error, 'sourceRestored', False), disasterRecoveryVerified=False)
        for attribute in ('recoveryFailureCode', 'failureRecordError', 'failureResponseError'):
            if hasattr(error, attribute): details[attribute] = getattr(error, attribute)
        print(json.dumps(details, separators=(',', ':')), file=sys.stderr)
        return 2 if state == 'TERMINAL_UNKNOWN' else 1


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    raise SystemExit(main())
