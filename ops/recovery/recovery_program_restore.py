"""Restore a registered MAIN program and its data under one original custody.

The replacement entry owns the physical source lock and claim. This module
never retries a dispatched load/HTTP command, restarts retained applications,
changes the original owner/reservation, or publishes an incomplete generation.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import re

from recovery_engine import Budget, RecoveryError, absolute, canonical, pin, pinned_json, require, utc, write


NATIVE_LIMIT = 64*1024*1024
METADATA_LIMIT = 4*1024*1024
RECEIPT_LIMIT = 65536
DOCKER_API_VERSION = '1.41'


def _unique(references):
    result, paths = [], {}
    for reference in references:
        if reference is None: continue
        path = reference['path']
        require(path not in paths or paths[path] == reference, 'PROGRAM_RESTORE_EVIDENCE_CONFLICT')
        if path not in paths:
            paths[path] = deepcopy(reference); result.append(deepcopy(reference))
    return result


def _references(value):
    if type(value) is dict:
        if set(value) == {'path','bytes','sha256'}:
            yield value
        else:
            for item in value.values(): yield from _references(item)
    elif type(value) in (list,tuple):
        for item in value: yield from _references(item)


def _write_once(path, value, *, limit=METADATA_LIMIT):
    """Persist one terminal snapshot, without the generation reader's 4MiB cap."""
    require(not os.path.lexists(path), 'PROGRAM_RESTORE_EVIDENCE_ALREADY_EXISTS')
    require(0 < len(canonical(value)) <= limit, 'PROGRAM_RESTORE_EVIDENCE_LIMIT')
    return write(path, value)


def _program_pins(claim):
    """The fixed, bounded program journals are independent of native outcomes."""
    references = []
    for name in ('program-import','program-switch'):
        root = claim/name
        if not root.exists(): continue
        for path in sorted(root.iterdir()):
            allowed = (path.name in {'preparation.json','load-intent.json','load-result.json','load-failure.json'}
                if name == 'program-import' else path.name in {'intent.json','result.json','failure.json',
                    'frontend-created-observation.json','backend-created-observation.json',
                    'frontend-verified.json','backend-verified.json'} or
                    re.fullmatch(r'[0-9]{4,}-(?:intent|result)\.json',path.name))
            if allowed:
                references.append(pin(path))
    return references


def _program_status(claim):
    mutation, unknown = False, False
    imported, switched = claim/'program-import', claim/'program-switch'
    if (imported/'load-intent.json').exists():
        mutation = True
        unknown = not (imported/'load-result.json').exists()
        if (imported/'load-failure.json').exists():
            unknown = pinned_json(pin(imported/'load-failure.json'))['state'] == 'TERMINAL_UNKNOWN'
    if switched.exists():
        for path in switched.iterdir():
            if not re.fullmatch(r'[0-9]{4,}-intent\.json',path.name): continue
            mutation = True
            if not path.with_name(path.name.replace('-intent.json','-result.json')).exists():
                unknown = True
    return mutation, unknown


def execute(configuration, request, root, input_pins, original_execute, native_type, selected_chain,
            *, claim, replacement, source_lock_fd):
    """Run only the explicit registered-program branch of replacement.execute."""
    from recovery_archive_guard import ArchivePathGuard
    from recovery_backup_epoch import _assert_lock, begin_restore, complete_restore
    from recovery_minimal_plan import disjoint
    from recovery_program_activation import snapshot_restore, stage_generation
    from recovery_program_execution import bind_execution, resolve_execution_configuration
    from recovery_program_native import MainNativeExecutionContext
    from recovery_program_protection import ProtectionCustody
    from recovery_program_source import resolve_source_program
    from recovery_program_archive import inspect_program_archive
    from recovery_program_import import prepare_image_import, load_image_import
    from recovery_program_resources import admit_program_resources
    from recovery_program_containers import UnixDocker, switch_stopped_programs
    from recovery_program_derivation import derive
    from recovery_program_sql_staging import close_sql_staging
    from recovery_target_preservation import TargetPreservation
    from recovery_resource_admission import admit
    from recovery_replace import preparation_intent, preparation_preflight, quiesce

    root, claim = absolute(str(root)), absolute(str(claim))
    policy = configuration['targetProgramPolicies'][request['targetConfigRef']]
    budget = None
    leases, natives, records = [], [], list(input_pins)
    context = custody = generation_pin = started = receipt_pin = None
    native_snapshot = custody_snapshot = frozen = None
    phase, active = 'NOT_STARTED', None
    preservation = target_preservation = None
    outer_unknown = False

    def original_guard():
        budget.remaining()
        _assert_lock(policy['backupEpochPolicy'], source_lock_fd)
        for lease in leases: lease.check()
        budget.remaining()

    def add_native(native):
        nonlocal active
        if native is not None:
            if not any(value is native for value in natives): natives.append(native)
            active = native

    def snapshots():
        nonlocal native_snapshot, custody_snapshot, generation_pin, frozen
        if frozen is not None: return deepcopy(frozen)
        if generation_pin is None and os.path.lexists(claim/'generation.json'):
            # An exclusive stage may publish and then fail its final guard.
            # Preserve the physical result without claiming ctx.stage succeeded.
            generation_pin = pin(claim/'generation.json')
        # Terminal observation remains readable after a failed guard/timeout.
        # These files are fixed once, before either terminal replacement receipt.
        native_value = None if context is None else context.snapshot()
        custody_value = None if custody is None else custody.snapshot()
        if native_value is not None:
            native_snapshot = _write_once(claim/'native-execution-evidence.json',native_value,limit=NATIVE_LIMIT)
        if custody_value is not None:
            custody_snapshot = _write_once(claim/'protection-custody-evidence.json',custody_value)
        program = _program_pins(claim)
        if (root/'resource-admission-program.json').exists():
            program.append(pin(root/'resource-admission-program.json'))
        sql_cleanup_pin = None
        for name in ('sql-staging-cleanup-intent.json','sql-staging-cleanup.json'):
            if os.path.lexists(root/name):
                reference = pin(root/name)
                program.append(reference)
                if name == 'sql-staging-cleanup.json': sql_cleanup_pin = reference
        preservation_pins=[]
        preservation_pin=None
        if preservation is not None:
            preservation_pins=list(preservation._pins.values())
            final=getattr(preservation,'_final',None)
            if final is not None:preservation_pin=deepcopy(final.reference)
            # Failure records are immutable originals even if publication did
            # not complete. Their presence never grants clear authority.
            for folder in (preservation.root,preservation.session._journal):
                failure=folder/'failure.json'
                if os.path.lexists(failure):preservation_pins.append(pin(failure))
        mutation, unknown = _program_status(claim)
        mutation = mutation or bool(native_value and native_value['mutationDispatched'])
        unknown = unknown or bool(native_value and native_value['terminalUnknown']) or outer_unknown
        detailed = _unique([*records,*program,*preservation_pins,generation_pin,native_snapshot,custody_snapshot,
            *(reference for native in natives for reference in native.original_pins),
            *(native_value['originalResultPins'] if native_value is not None else []),
            *(custody_value['originalResultPins'] if custody_value is not None else [])])
        # The fixed epoch receipt is limited to 64KiB. Per-HTTP originals and
        # observations remain in the detailed result, never the small receipt.
        compact_program = [reference for reference in program if Path(reference['path']).name in {
            'preparation.json','load-intent.json','load-result.json','load-failure.json',
            'intent.json','result.json','failure.json','resource-admission-program.json',
            'sql-staging-cleanup-intent.json','sql-staging-cleanup.json'}]
        compact = _unique([*records,*compact_program,preservation_pin,generation_pin,native_snapshot,custody_snapshot])
        frozen = dict(programExecutionPhase=phase,programNativeEvidencePin=native_snapshot,
            programProtectionCustodyPin=custody_snapshot,programGenerationPin=deepcopy(generation_pin),
            programSqlCleanupPin=deepcopy(sql_cleanup_pin),targetPreservationPin=preservation_pin,
            mutationDispatched=mutation,terminalUnknown=unknown,
            actualNativeExitCode=None if native_value is None else native_value['lastExitCode'],
            originalResultPins=detailed, receiptOriginalResultPins=compact)
        return deepcopy(frozen)

    def result_data():
        value = snapshots(); value.pop('receiptOriginalResultPins')
        # A later outer failure may conservatively retain uncertainty without
        # changing any already frozen successful receipt or native observation.
        value['terminalUnknown'] = value['terminalUnknown'] or outer_unknown
        return value

    def terminal_receipt(state, failure_code=None):
        value = snapshots()
        compact = value.pop('receiptOriginalResultPins')
        value['originalResultPins'] = compact
        value.update(state=state,operationId=request['operationId'],targetConfigRef=request['targetConfigRef'],
            databaseUuid=replacement['databaseUuid'],failureCode=failure_code,finishedAt=utc())
        return _write_once(claim/'replacement-result.json',value,limit=RECEIPT_LIMIT)

    def close_execution():
        if context is not None: context.close()
        for lease in reversed(leases): lease.close()
        leases.clear()
        closed = set()
        for native in natives:
            close_sql_staging(native)
            guard = getattr(native,'archive_guard',None)
            if guard is not None and id(guard) not in closed:
                guard.close(); closed.add(id(guard))

    try:
        require('backupEpoch' in replacement and replacement['backupEpoch'] == policy['backupEpochPolicy'],
                'PROGRAM_TARGET_EPOCH_BINDING_INVALID')
        budget = Budget(configuration['deadlineMilliseconds'])
        source, capture_policy, chain = selected_chain(configuration, request)
        require(all(step[2]['objects']['method'] == 'PHYSICAL_FILES' for step in chain),
                'REPLACEMENT_PHYSICAL_ARCHIVE_REQUIRED')
        require(all(disjoint(replacement['stateRoot'],path) for path in source['archiveRoots']),
                'REPLACEMENT_STATE_ARCHIVE_OVERLAP')
        context_pin = snapshot_restore(policy,request['operationId'],source_lock_fd,guard=original_guard)
        records.append(context_pin)
        binding_pin = bind_execution(configuration,request,root,context_pin,source_lock_fd,guard=original_guard)
        records.append(binding_pin)
        preparation = root/'replacement-preparation'; preparation.mkdir(mode=0o700)
        previous = pinned_json(pinned_json(context_pin)['targetPin'])
        intent = preparation_intent(request,previous,replacement,preparation); records.append(intent)
        original_guard()
        started = begin_restore(policy['backupEpochPolicy'],request['operationId'],source_lock_fd,
            intent_pin=intent)
        original_guard()
        context = MainNativeExecutionContext(configuration,request,root,binding_pin=binding_pin,
            lock_fd=source_lock_fd,budget=budget,guard=original_guard)
        phase = 'PREPARATION'
        effective, _ = resolve_execution_configuration(configuration,request,root,binding_pin=binding_pin,
            lock_fd=source_lock_fd,guard=context._check)
        view = context.preparation(effective)
        target = effective['targets'][request['targetConfigRef']]
        # The typed view is installed before the constructor's first identity DB.
        native = native_type(effective,request,source,capture_policy,chain,target,preparation,input_pins,
            native_context=view)
        add_native(native)
        custody = ProtectionCustody.from_preparation(native)
        native.protection_custody = custody

        source_program = resolve_source_program(configuration,request,chain,guard=context._check)
        require(all(source_program['roleImages'][role] == native.config_services[role]['imageId']
                    for role in ('mysql','minio','redis')), 'PROGRAM_DATA_IMAGE_BINDING_CHANGED')
        watched = _unique([*_references(source_program),
            *(reference for step in chain for reference in
              [step[0],step[3],step[1]['manifestPin'],
               source['repositoryBindingPinsByManifestSha256'][step[1]['manifestPin']['sha256']]])])
        leases.append(ArchivePathGuard.capture(reference['path'] for reference in watched))
        again_source, again_policy, again_chain = selected_chain(configuration,request)
        require((source,capture_policy,chain) == (again_source,again_policy,again_chain) and
                resolve_source_program(configuration,request,again_chain,guard=context._check) == source_program,
                'PROGRAM_RESTORE_SOURCE_CHANGED')
        # Full tar/config/layer proof and every metadata pin precede protection,
        # application stop, native import, and all database/object reset writes.
        inspect_program_archive(source_program['archivePin'],source_program['roleImages'],guard=context._check,
            architecture=source_program['architecture'],max_archive_bytes=source_program['maxArchiveBytes'])
        records.append(_write_once(claim/'source-program.json',source_program))
        admit(effective,request,root,'replacement',reservation_configuration=configuration,
            execution_binding_pin=binding_pin,execution_lock_fd=source_lock_fd,execution_guard=context._check)
        admit_program_resources(native,source_program,claim,reservation_configuration=configuration,
            execution_binding_pin=binding_pin,execution_lock_fd=source_lock_fd)
        records.append(pin(root/'resource-admission-program.json'))
        import_root = claim/'program-import'; import_root.mkdir(mode=0o700)
        import_plan = prepare_image_import(source_program['archivePin'],source_program['roleImages'],import_root,
            guard=context._check,architecture=source_program['architecture'],
            max_archive_bytes=source_program['maxArchiveBytes'],max_import_bytes=source_program['maxImportBytes'])
        preservation_policies=configuration.get('targetPreservationPolicies',{})
        if request['targetConfigRef'] in preservation_policies:
            preservation=TargetPreservation.prepare(native,
                policy_pin=preservation_policies[request['targetConfigRef']],
                reservation_pin=pin(root/'resource-reservation.json'))
        with native.timed_stage('target-replacement-quiesce'):
            preparation_preflight(native,replacement)
            quiesce(native,replacement)
        if preservation is not None:
            preservation.capture_and_publish()
            target_preservation=preservation.handoff()
        load_image_import(import_plan,operation_id=request['operationId'],epoch_policy=policy['backupEpochPolicy'],
            lock_fd=source_lock_fd,load=lambda path:native.docker(['image','load','--input',str(path)],mutation=True),
            inspect_image=lambda identity:json.loads(native.docker(['image','inspect',identity]))[0],guard=context._check)
        engine = UnixDocker(guard=context._check,deadline=budget.deadline,api_version=DOCKER_API_VERSION)
        switch_root = claim/'program-switch'; switch_root.mkdir(mode=0o700)
        originals = {role:native.inspect(native.config_services[role]['id']) for role in ('backend','frontend')}
        switched = switch_stopped_programs(originals,pinned_json(import_plan)['archiveProgram'],engine=engine,
            guard=context._check,journal=switch_root,operation_id=request['operationId'],
            epoch_policy=policy['backupEpochPolicy'],lock_fd=source_lock_fd)
        derived = derive(policy,target,switched['receiptPin'],request['operationId'],claim,source_lock_fd,
            guard=context._check)
        # Keep the generated pin independently: stage's lease can fail before
        # context publishes its in-process transition to RESTORE.
        generation_pin = stage_generation(policy,context_pin,target_pin=derived['targetPin'],
            capture_pins={key:value['capturePin'] for key,value in derived['captureBindings'].items()},
            switch_result_pin=switched['receiptPin'],lock_fd=source_lock_fd,guard=context._check)
        context.stage(generation_pin)
        phase = 'RESTORE'
        runtime = claim/'runtime'; runtime.mkdir(mode=0o700)
        restored, _ = resolve_execution_configuration(configuration,request,root,binding_pin=binding_pin,
            generation_pin=generation_pin,lock_fd=source_lock_fd,guard=context._check,runtime=True)
        restore_view = context.restore(restored)
        data, native = original_execute(restored,request,root,input_pins,reservation_configuration=configuration,
            native_context=restore_view,protection_custody=custody,execution_binding_pin=binding_pin,
            execution_generation_pin=generation_pin,execution_lock_fd=source_lock_fd,
            target_preservation=target_preservation)
        add_native(native)
        data.update(native.replacement_finish())
        data.update(result_data())
        receipt_pin = terminal_receipt('SUCCEEDED')
        data['replacementReceiptPin'] = receipt_pin
        data['originalResultPins'] = _unique([*data['originalResultPins'],receipt_pin])
        native.original_pins = deepcopy(data['originalResultPins'])
        native.mutation_dispatched = data['mutationDispatched']
        close_execution()
        original_guard()
        data['sourceBackupEpoch'] = complete_restore(policy['backupEpochPolicy'],request['operationId'],
            started['epochId'],'READY',receipt_pin,source_lock_fd,guard=budget.remaining)
        original_guard()
        return data,native
    except BaseException as error:
        # Capture post-dispatch guard uncertainty before the first receipt is
        # frozen. Native exit observations remain exactly what the child did.
        outer_unknown = outer_unknown or bool(getattr(error,'unknown',False))
        add_native(getattr(error,'native',None))
        # A preexisting terminal receipt is never rewritten, including after
        # READY publication failure. Already fixed snapshots are reused as pins.
        try:
            if receipt_pin is None and not os.path.lexists(claim/'replacement-result.json'):
                receipt_pin = terminal_receipt('FAILED_RETAINED',getattr(error,'code',type(error).__name__))
            evidence = result_data()
            evidence.update(replacementReceiptPin=receipt_pin,partialTargetRetained=True,retryPermitted=False)
            evidence['originalResultPins'] = _unique([*evidence['originalResultPins'],receipt_pin])
            error.evidence = evidence
            error.replacement_receipt_pin = receipt_pin
            error.unknown = bool(getattr(error,'unknown',False) or evidence['terminalUnknown'])
            if active is not None:
                active.mutation_dispatched = evidence['mutationDispatched']
                error.native = active
            close_execution()
            if receipt_pin is not None and started is not None and pinned_json(receipt_pin)['state'] == 'FAILED_RETAINED':
                # Terminal evidence publication is metadata, without granting
                # another native command or restarting/releasing retained data.
                _assert_lock(policy['backupEpochPolicy'],source_lock_fd)
                complete_restore(policy['backupEpochPolicy'],request['operationId'],started['epochId'],
                    'FAILED_RETAINED',receipt_pin,source_lock_fd)
                _assert_lock(policy['backupEpochPolicy'],source_lock_fd)
        except BaseException as recording:
            recording.original_code = getattr(error,'code',type(error).__name__)
            recording.unknown = True
            if hasattr(error,'evidence'): recording.evidence = error.evidence
            if active is not None: recording.native = active
            raise recording from error
        raise
    finally:
        close_execution()
