"""W07 local observations, retained diagnostics and rehearsal request generation.

Only W01 may dispatch the generated requests to W04/W05/W06. This module has
no subprocess, database, NAS, clock setter or external notification implementation.
"""
import time

from recovery_diagnostics_evidence import summarize_legacy
from recovery_diagnostics_originals import summarize_current_execution
from recovery_diagnostics_io import (Contracts, DiagnosticError, absolute_path, atomic_json,
                                    digest, exact, parse_json, pin_file, provisioned_inputs, require, state_lock,
                                    timestamp_ns, utc_now)


ACTIONS = {'OBSERVE_OPERATION', 'DIAGNOSE_EXECUTION', 'PLAN_REHEARSAL'}


class Diagnostics:
    def __init__(self, request, reader):
        self.request, self.reader = request, reader
        self.policy = reader.read(request['policyPin'])
        require(type(self.policy) is dict and type(self.policy.get('diagnostics')) is dict,
                'DIAGNOSTICS_CONFIG_REQUIRED')
        self.config = self.policy['diagnostics']
        for field in ('schemaPin', 'evidenceRoot', 'stateRoot'):
            require(field in self.config, 'DIAGNOSTICS_CONFIG_' + field.upper() + '_MISSING')
        self.contracts = Contracts(reader.read(self.config['schemaPin']))
        self.contracts.validate('OperationRequest', request)
        require(request['action'] in ACTIONS, 'ACTION_UNSUPPORTED')
        reader.read(request['sourceOrTargetRef'])
        reader.verify_nested(request)
        reader.verify_nested({k: v for k, v in self.config.items() if k != 'executionSubjectBindingPin'})
        self.state_root = absolute_path(self.config['stateRoot'])
        self.evidence_root = absolute_path(self.config['evidenceRoot'])
        require(self.state_root.is_dir() and self.evidence_root.is_dir(), 'LOCAL_ROOT_MISSING')
        require(self.state_root != self.evidence_root, 'SEPARATE_LOCAL_ROOTS_REQUIRED')
        self.request_hash = digest(request)
        self.alerts = []
        self.previous = None

    def setting(self, key, kind):
        require(key in self.config and type(self.config[key]) is kind,
                'DIAGNOSTICS_CONFIG_' + key.upper() + '_INVALID')
        value = self.config[key]
        if kind is int:
            require(value > 0, 'DIAGNOSTICS_CONFIG_' + key.upper() + '_INVALID')
        return value

    def alert(self, code, severity='ERROR'):
        if not any(a['code'] == code for a in self.alerts):
            self.alerts.append({'code': code, 'severity': severity, 'externalNotificationSent': False})

    def read_input(self, key, schema=None):
        require(key in self.request['inputPins'], 'INPUT_' + key.upper() + '_MISSING')
        record = self.reader.read(self.request['inputPins'][key])
        if schema:
            self.contracts.validate(schema, record)
        if key != 'executionEvidence':
            self.reader.verify_nested(record)
        return record

    def execute(self, started_at):
        cache = self.state_root / ('request-' + digest(self.request['requestId']) + '.json')
        with state_lock(self.state_root):
            self.reader.budget.check()
            if cache.exists():
                saved = parse_json(cache.read_bytes())
                require(saved['requestHash'] == self.request_hash, 'REQUEST_ID_CONTENT_CONFLICT')
                if self.request['action'] == 'PLAN_REHEARSAL' or 'executionSubjectBindingPin' in self.config:
                    trust = provisioned_inputs(self.reader, self.request['policyPin'])
                    for name in ('executionSubjectBindingPin', 'approvedRehearsalTemplatePin',
                                 'rehearsalTemplateApprovalPin'):
                        require(trust[name] == self.config.get(name), 'CACHED_INPUT_NOT_IN_PROVISIONED_TRUST')
                self.contracts.validate('OperationResult', saved['result'])
                self.reader.verify_nested(saved['result'])
                return saved['result']
            if self.request['action'] == 'OBSERVE_OPERATION':
                data = self.observe()
            elif self.request['action'] == 'DIAGNOSE_EXECUTION':
                data = self.diagnose()
            else:
                data = self.plan_rehearsal()
            self.reader.budget.check()
            data['alerts'] = self.alerts
            data['observedAt'] = utc_now()
            evidence = self.evidence_root / ('observation-' + self.request_hash + '.json')
            atomic_json(evidence, data)
            result = {'schemaVersion': 'backup-restore-operation-result/v1',
                      'operationId': self.request['operationId'], 'requestId': self.request['requestId'],
                      'action': self.request['action'], 'state': data['state'],
                      'failureCode': data['failureCode'], 'message': self.request['action'] + ': ' + data['state'],
                      'data': data, 'originalResultPins': [*self.reader.pins, pin_file(evidence)],
                      'startedAt': started_at, 'finishedAt': utc_now(),
                      'actualExitCode': data.get('actualExitCode')}
            self.contracts.validate('OperationResult', result)
            atomic_json(cache, {'requestHash': self.request_hash, 'result': result})
            return result

    def observe(self):
        require(set(self.request['inputPins']) <= {'operationStatus', 'executionEvidence'},
                'ACTION_INPUT_KEYS_INVALID')
        status = self.read_input('operationStatus', 'OperationStatus')
        now_ns = time.time_ns()
        age_ns = now_ns - timestamp_ns(status['updatedAt'])
        stale_ns = self.setting('statusStaleAfterMilliseconds', int) * 1_000_000
        state_file = self.state_root / ('operation-' + digest({k: status[k] for k in
                                        ('operationId', 'requestId', 'action')}) + '.json')
        previous = parse_json(state_file.read_bytes()) if state_file.exists() else None
        if previous:
            require(previous['status']['requestId'] == status['requestId'] and
                    previous['status']['action'] == status['action'], 'OPERATION_ID_REUSED')
        originals = []
        for pin in status['originalResultPins']:
            original = self.reader.read(pin)
            if type(original) is dict and original.get('schemaVersion') == 'backup-restore-operation-result/v1':
                self.contracts.validate('OperationResult', original)
                # Stage results may share the operation but have distinct child
                # request/actions. Only the exact final executor result settles
                # the outer status, and all stage originals remain pinned.
                if original['requestId'] == status['requestId'] and original['action'] == status['action']:
                    require(original['operationId'] == status['operationId'], 'OBSERVED_RESULT_IDENTITY_MISMATCH')
                    originals.append(original)
        require(len(originals) <= 1, 'OBSERVED_FINAL_RESULT_AMBIGUOUS')
        current = originals[-1] if originals else None
        state, code, actual = 'TERMINAL_UNKNOWN', 'ORIGINAL_TERMINAL_MISSING', None
        if status['state'] == 'BLOCKED':
            state, code = 'FAILED_RETAINED', 'OBSERVED_OPERATION_BLOCKED'
        if current:
            actual = current['actualExitCode']
            if status['state'] != current['state']:
                code = 'STATUS_RESULT_STATE_MISMATCH'
            elif current['state'] == 'TERMINAL_UNKNOWN':
                code = 'ORIGINAL_TERMINAL_UNKNOWN'
            elif current['state'] == 'FAILED_RETAINED' or actual is not None and actual != 0:
                state, code = 'FAILED_RETAINED', 'ORIGINAL_EXECUTION_FAILED'
            elif current['failureCode'] is None and current['data'] is not None:
                state, code = 'SUCCEEDED', None
            else:
                code = 'ORIGINAL_SUCCESS_EVIDENCE_MISSING'
        if age_ns < 0:
            state, code = 'TERMINAL_UNKNOWN', 'STATUS_WALL_TIME_IN_FUTURE'
        elif status['state'] in ('RUNNING', 'QUEUED') and age_ns > stale_ns:
            state, code = 'TERMINAL_UNKNOWN', 'STALE_OPERATION_REQUIRES_RECONCILIATION'
        if previous and previous['status']['state'] in ('SUCCEEDED', 'FAILED_RETAINED', 'TERMINAL_UNKNOWN') and \
                status['state'] in ('QUEUED', 'RUNNING'):
            state, code = 'TERMINAL_UNKNOWN', 'PERSISTED_OPERATION_STATE_REGRESSED'
        data = {'schemaVersion': 'recovery-operation-observation/v1', 'state': state,
                'failureCode': code, 'actualExitCode': actual, 'observedOperationId': status['operationId'],
                'observedStatus': status['state'], 'phase': status['phase'],
                'statusAgeMilliseconds': age_ns // 1_000_000, 'nextAction': status['nextAction'],
                'restartObservation': {'priorObservationPresent': previous is not None,
                                       'originalProcessTerminal': None, 'resourcesTerminal': None,
                                       'resourceReleasePerformed': False, 'automaticRetryPerformed': False}}
        if state == 'SUCCEEDED' and 'executionEvidence' not in self.request['inputPins']:
            # The fixed OperationStatus does not prove the original resource
            # terminal. Keep the observed operation success as a source fact,
            # but do not declare this terminal observation reconciled.
            data.update(state='TERMINAL_UNKNOWN', failureCode='RESOURCE_TERMINAL_EVIDENCE_MISSING')
        if 'executionEvidence' in self.request['inputPins']:
            evidence = self.read_input('executionEvidence')
            summary = summarize_current_execution(evidence, self.request['inputPins']['executionEvidence'],
                self.reader, self.config.get('executionSubjectBindingPin'), self.request['policyPin'], self.contracts,
                self.setting('clockGuardMilliseconds', int) * 1_000_000)
            old_epoch = None if previous is None else previous.get('executorEpoch')
            identity = summary.get('subjectIdentity')
            if identity is not None and any(identity[k] != status[k] for k in ('operationId', 'requestId', 'action')):
                summary.update(state='TERMINAL_UNKNOWN', failureCode='OBSERVED_CURRENT_IDENTITY_MISMATCH')
            if identity is not None and previous and previous.get('subjectIdentity') is not None and \
                    identity != previous['subjectIdentity']:
                summary.update(state='TERMINAL_UNKNOWN', failureCode='PERSISTED_EXECUTION_IDENTITY_CHANGED')
            data['restartObservation'].update(executorEpochChanged=old_epoch is not None and
                                              identity is not None and old_epoch != identity['observerEpoch'],
                                              originalProcessTerminal=summary['processTerminal'],
                                              resourcesTerminal=summary['resourceTerminal'])
            data['execution'] = summary
            if summary['state'] != 'SUCCEEDED':
                data.update(state=summary['state'], failureCode=summary['failureCode'],
                            actualExitCode=summary['actualExitCode'])
            elif current is not None and data['state'] == 'SUCCEEDED':
                expected_cli = {'SUCCEEDED': 0, 'FAILED_RETAINED': 1, 'TERMINAL_UNKNOWN': 2}[current['state']]
                if summary['cliExitCode'] != expected_cli or summary['childExecutorExitCode'] != actual:
                    data.update(state='TERMINAL_UNKNOWN', failureCode='CLI_CHILD_RESULT_EXIT_MISMATCH')
        data['restartObservation']['reconciliationRequired'] = data['state'] == 'TERMINAL_UNKNOWN'
        if data['failureCode']:
            self.alert(data['failureCode'])
        atomic_json(state_file, {'status': status, 'observedAt': utc_now(),
                                'executorEpoch': None if 'executionEvidence' not in self.request['inputPins'] or
                                summary.get('subjectIdentity') is None else summary['subjectIdentity']['observerEpoch'],
                                'subjectIdentity': None if 'executionEvidence' not in self.request['inputPins'] else
                                summary.get('subjectIdentity'), 'observation': data})
        return data

    def diagnose(self):
        require(set(self.request['inputPins']) == {'executionEvidence'}, 'ACTION_INPUT_KEYS_INVALID')
        evidence = self.read_input('executionEvidence')
        if evidence.get('schemaVersion') == 'diagnostic-evidence/v1':
            binding = self.config.get('legacyDiagnosticBinding')
            require(type(binding) is dict and type(binding.get('subjectOperationId')) is str and
                    binding.get('evidencePin') == self.request['inputPins']['executionEvidence'],
                    'LEGACY_DIAGNOSTIC_BINDING_MISSING')
            require('legacySchemaPin' in self.config, 'LEGACY_SCHEMA_PIN_MISSING')
            contracts = Contracts(self.reader.read(self.config['legacySchemaPin']))
            data = summarize_legacy(evidence, self.reader, contracts, binding)
            data['subjectOperationId'] = binding['subjectOperationId']
        else:
            data = summarize_current_execution(evidence, self.request['inputPins']['executionEvidence'],
                self.reader, self.config.get('executionSubjectBindingPin'), self.request['policyPin'], self.contracts,
                self.setting('clockGuardMilliseconds', int) * 1_000_000)
        data['diagnosticInvocation'] = {k: self.request[k] for k in ('operationId', 'requestId', 'action')}
        data['schemaVersion'] = 'recovery-execution-diagnosis/v1'
        data['originalEvidencePin'] = self.request['inputPins']['executionEvidence']
        data['rawStreamsPublished'] = False
        data['systemClockModified'] = False
        data['diagnosticExpansion'] = 'CALL_PATH_FIRST; OS_EVIDENCE_ONLY_WITH_CONCRETE_FAILURE'
        if data['failureCode']:
            self.alert(data['failureCode'])
        if data['timedOut']:
            self.alert('EXECUTION_TIMEOUT')
        for problem in data['clockProblems']:
            self.alert(problem)
        return data

    def rehearsal_eligible(self, point):
        return (point['integrityState'] == 'COMPLETE' and point['rehearsalEligible'] and
                point['blockedReason'] in (None, 'REPOSITORY_CURRENT_RECOVERY_PASSED_REQUIRED'))

    def chain(self, pin):
        point = self.reader.read(pin)
        self.contracts.validate('RepositoryPoint', point)
        parents = point['parentPointPins']
        chain = parents + [pin]
        require(len(chain) <= 256, 'REPOSITORY_CHAIN_LIMIT_EXCEEDED')
        require(len({p['path'] for p in chain}) == len(chain), 'REPOSITORY_CHAIN_CYCLE')
        source_identity, prior_created = None, None
        for index, reference in enumerate(chain):
            candidate = self.reader.read(reference)
            self.contracts.validate('RepositoryPoint', candidate)
            self.reader.verify_nested(candidate)
            require(self.rehearsal_eligible(candidate), 'REHEARSAL_POINT_INELIGIBLE')
            require(candidate['generationId'] == point['generationId'] and
                    candidate['parentPointPins'] == parents[:index], 'REPOSITORY_ANCESTOR_PREFIX_INVALID')
            require(candidate['pointType'] == ('FULL' if index == 0 else 'INCREMENTAL'),
                    'REPOSITORY_CHAIN_BASELINE_INVALID')
            require(bool(candidate['payloadRefs']), 'REPOSITORY_PAYLOAD_MISSING')
            manifest = self.reader.read(candidate['manifestPin'])
            require(manifest.get('schemaVersion') == 'RepositoryManifest/v1', 'REPOSITORY_MANIFEST_REQUIRED')
            for field in ('backupId', 'generationId', 'pointType', 'parentPointPins',
                          'commonRecoveryPoint', 'payloadRefs'):
                require(manifest.get(field) == candidate[field], 'REPOSITORY_MANIFEST_POINT_MISMATCH')
            require('sourceIdentityPin' in manifest and 'createdAt' in manifest, 'REPOSITORY_SOURCE_TIME_REQUIRED')
            self.reader.verify_nested(manifest)
            if source_identity is None:
                source_identity = manifest['sourceIdentityPin']
                scope = self.reader.read(self.config['currentContext']['sourceScopePin'])
                require(scope.get('schemaVersion') == 'RecoverySourceScope/v1' and
                        scope.get('sourceIdentityPin') == source_identity, 'REPOSITORY_SOURCE_SCOPE_MISMATCH')
            require(manifest['sourceIdentityPin'] == source_identity, 'REPOSITORY_CHAIN_SOURCE_MISMATCH')
            created = timestamp_ns(manifest['createdAt'])
            require(prior_created is None or created > prior_created, 'REPOSITORY_CHAIN_ORDER_INVALID')
            prior_created = created
        return chain

    def report_status(self, report_pin, point_pin, chain_pins, context):
        report = self.reader.read(report_pin)
        self.contracts.validate('RecoveryVerificationReport', report)
        self.reader.verify_nested(report)
        reasons = list(report['invalidatedBy'])
        if report['verdict'] != 'PASSED':
            reasons.append('VERIFICATION_' + report['verdict'])
        verification_result = self.reader.read(self.setting('verificationResultPin', dict))
        self.contracts.validate('OperationResult', verification_result)
        require(verification_result['action'] == 'VERIFY_RECOVERY' and verification_result['data'] == report and
                verification_result['operationId'] == report['operationId'], 'VERIFICATION_RESULT_BINDING_INVALID')
        if verification_result['state'] != 'SUCCEEDED' or verification_result['failureCode'] is not None:
            reasons.append('VERIFICATION_ORIGINAL_EXECUTION_NOT_SUCCEEDED')
        report_age_ns = time.time_ns() - timestamp_ns(verification_result['finishedAt'])
        if report_age_ns < 0:
            reasons.append('VERIFICATION_WALL_TIME_IN_FUTURE')
        elif report_age_ns > self.setting('rehearsalIntervalMilliseconds', int) * 1_000_000:
            reasons.append('VERIFICATION_EXPIRED')
        if report['mode'] != 'REHEARSAL':
            reasons.append('VERIFICATION_MODE_CHANGED')
        if report['backupAndChainPins'] != chain_pins:
            reasons.append('BACKUP_CHAIN_CHANGED')
        for field in ('sourceScopePin', 'targetIdentityPin', 'toolAndVersionPins'):
            if report[field] != context[field]:
                reasons.append(field.upper() + '_CHANGED')
        plan = self.reader.read(report['planPin'])
        self.contracts.validate('RestorePlan', plan)
        self.reader.verify_nested(plan)
        if plan['operationId'] != report['operationId'] or plan['restoreId'] != report['restoreId'] or \
                plan['mode'] != report['mode']:
            reasons.append('VERIFICATION_PLAN_IDENTITY_MISMATCH')
        if (plan['candidatePin'] != point_pin or plan['orderedChainPins'] != chain_pins or
                plan['sideEffectPolicyPin'] != context['sideEffectPolicyPin'] or
                plan['targetRef'] != self.reader.read(self.setting('approvedRehearsalTemplatePin', dict))['sourceOrTargetRef']):
            reasons.append('PLAN_INPUTS_CHANGED')
        for field, schema in (('restoreResultPin', 'RestoreExecutionResult'),
                              ('applicationStartPin', 'ApplicationStartResult')):
            result = self.reader.read(report[field])
            self.contracts.validate(schema, result)
            self.reader.verify_nested(result)
            if result['state'] != 'SUCCEEDED' or result['operationId'] != report['operationId'] or \
                    result['restoreId'] != report['restoreId'] or result['targetIdentityPin'] != report['targetIdentityPin']:
                reasons.append('VERIFICATION_ORIGINAL_RESULT_MISMATCH')
            if field == 'restoreResultPin' and (result['planPin'] != report['planPin'] or
                    result['recoveryPoint'] != plan['recoveryPoint'] or result['writeProtectionState'] != 'ENFORCED'):
                reasons.append('VERIFICATION_RESTORE_BINDING_INVALID')
            if field == 'applicationStartPin':
                isolation = self.reader.read(result['sideEffectIsolationPin'])
                self.reader.verify_nested(isolation)
                if (result['restoreResultPin'] != report['restoreResultPin'] or
                        isolation.get('schemaVersion') != 'RecoverySideEffectIsolation/v1' or
                        isolation.get('operationId') != report['operationId'] or
                        isolation.get('targetIdentityPin') != report['targetIdentityPin'] or
                        isolation.get('state') != 'ENFORCED' or
                        isolation.get('policyPin') != context['sideEffectPolicyPin'] or
                        isolation.get('writeProtectionState') != 'ENFORCED' or
                        isolation.get('sourceWritesPerformed') is not False):
                    reasons.append('VERIFICATION_APPLICATION_BINDING_INVALID')
        if not report['dataEvidencePins'] or not report['playwrightEvidencePins']:
            reasons.append('VERIFICATION_REAL_PATH_EVIDENCE_MISSING')
        for field in ('rtoObservation', 'rpoObservation'):
            observation = report[field]
            if observation['state'] != 'MEASURED' or observation['observedMilliseconds'] is None or \
                    observation['objectiveMilliseconds'] is None or not observation['evidencePins']:
                reasons.append(field.upper() + '_UNKNOWN')
            elif observation['observedMilliseconds'] > observation['objectiveMilliseconds']:
                reasons.append(field.upper() + '_EXCEEDED')
        return report, sorted(set(reasons)), report_age_ns // 1_000_000

    def plan_rehearsal(self):
        require(set(self.request['inputPins']) <= {'repositoryPoint', 'recoveryVerificationReport'},
                'ACTION_INPUT_KEYS_INVALID')
        require(self.request['mode'] == 'REHEARSAL', 'PLAN_REHEARSAL_MODE_REQUIRED')
        selected = self.request['inputPins'].get('repositoryPoint')
        require(selected is not None, 'INPUT_REPOSITORYPOINT_MISSING')
        require(self.request['selectedPointPin'] == selected, 'SELECTED_POINT_MISMATCH')
        catalog = self.reader.read(self.setting('catalogPin', dict))
        exact(catalog, ('schemaVersion', 'sourceScopePin', 'points'), 'CATALOG_SHAPE_INVALID')
        require(catalog['schemaVersion'] == 'recovery-diagnostics-catalog/v1', 'CATALOG_VERSION_INVALID')
        require(type(catalog['points']) is list and catalog['points'], 'CATALOG_POINTS_MISSING')
        context = self.config.get('currentContext')
        exact(context, ('sourceScopePin', 'targetIdentityPin', 'toolAndVersionPins', 'sideEffectPolicyPin'),
              'CURRENT_CONTEXT_REQUIRED')
        self.reader.verify_nested(context)
        require(context['sourceScopePin'] == catalog['sourceScopePin'], 'CATALOG_SOURCE_SCOPE_MISMATCH')
        require(type(context['toolAndVersionPins']) is list and context['toolAndVersionPins'],
                'CURRENT_TOOL_VERSION_PINS_MISSING')
        trust = provisioned_inputs(self.reader, self.request['policyPin'])
        for name in ('approvedRehearsalTemplatePin', 'rehearsalTemplateApprovalPin'):
            require(trust[name] is not None and trust[name] == self.config.get(name),
                    'REHEARSAL_INPUT_NOT_IN_PROVISIONED_TRUST')
        template = self.reader.read(self.setting('approvedRehearsalTemplatePin', dict))
        self.contracts.validate('OperationRequest', template)
        self.reader.verify_nested(template)
        require(template['action'] == 'REHEARSAL' and template['mode'] == 'REHEARSAL' and
                template['authorizationRefs'] and template['leaseRef'] is not None,
                'APPROVED_REHEARSAL_TEMPLATE_REQUIRED')
        approval = self.reader.read(self.setting('rehearsalTemplateApprovalPin', dict))
        exact(approval, ('schemaVersion', 'templatePin', 'permittedPointPins', 'currentContext',
                         'validFrom', 'validUntil'), 'REHEARSAL_TEMPLATE_APPROVAL_INVALID')
        require(approval['schemaVersion'] == 'RecoveryRehearsalTemplateApproval/v1' and
                approval['templatePin'] == self.config['approvedRehearsalTemplatePin'] and
                approval['currentContext'] == context, 'REHEARSAL_TEMPLATE_APPROVAL_MISMATCH')
        self.reader.verify_nested(approval)
        require(timestamp_ns(approval['validFrom']) <= time.time_ns() < timestamp_ns(approval['validUntil']),
                'REHEARSAL_TEMPLATE_APPROVAL_EXPIRED')
        target = self.reader.read(template['sourceOrTargetRef'])
        policy = self.reader.read(template['policyPin'])
        require(target.get('schemaVersion') == 'RecoveryEnvironmentConfig/v1' and
                target.get('targetIdentityPin') == context['targetIdentityPin'] and
                target.get('sourceScopePin') == context['sourceScopePin'] and
                policy.get('schemaVersion') == 'RecoveryEnvironmentPolicy/v1' and
                template['policyPin'] == context['sideEffectPolicyPin'], 'REHEARSAL_TEMPLATE_CONTEXT_MISMATCH')
        complete, seen = [], set()
        catalog_keys = {digest(entry['pointPin']) for entry in catalog['points']
                        if type(entry) is dict and 'pointPin' in entry}
        for entry in catalog['points']:
            exact(entry, ('pointPin', 'completedAt'), 'CATALOG_ENTRY_INVALID')
            key = digest(entry['pointPin'])
            require(key not in seen, 'CATALOG_DUPLICATE_POINT')
            seen.add(key)
            point = self.reader.read(entry['pointPin'])
            self.contracts.validate('RepositoryPoint', point)
            if not self.rehearsal_eligible(point):
                continue
            chain_pins = self.chain(entry['pointPin'])
            require(all(digest(pin) in catalog_keys for pin in chain_pins), 'CHAIN_OUTSIDE_SOURCE_CATALOG')
            complete.append({'pointPin': entry['pointPin'], 'completedAt': entry['completedAt'],
                             'completedNs': timestamp_ns(entry['completedAt']), 'chainPins': chain_pins})
        require(bool(complete), 'LATEST_COMPLETE_POINT_MISSING')
        complete.sort(key=lambda entry: (entry['completedNs'], digest(entry['pointPin'])))
        require(len(complete) == 1 or complete[-1]['completedNs'] != complete[-2]['completedNs'],
                'LATEST_COMPLETE_POINT_AMBIGUOUS')
        latest = complete[-1]
        require(latest['pointPin'] == selected, 'REQUEST_NOT_LATEST_COMPLETE_POINT')
        longest = max(complete, key=lambda entry: (len(entry['chainPins']), entry['completedNs']))
        now_ns = time.time_ns()
        age_ns = now_ns - latest['completedNs']
        state, code = 'SUCCEEDED', None
        if age_ns < 0:
            state, code = 'TERMINAL_UNKNOWN', 'BACKUP_WALL_TIME_IN_FUTURE'
            self.alert(code)
        elif age_ns > self.setting('freshnessMaximumAgeMilliseconds', int) * 1_000_000:
            self.alert('LATEST_COMPLETE_POINT_STALE')
        schedule = self.setting('scheduleId', str)
        require(bool(schedule), 'SCHEDULE_ID_REQUIRED')
        interval_ms = self.setting('rehearsalIntervalMilliseconds', int)
        report_pin = self.request['inputPins'].get('recoveryVerificationReport')
        report, invalidated, report_age = (None, ['RECOVERY_VERIFICATION_MISSING'], None) if report_pin is None else \
            self.report_status(report_pin, latest['pointPin'], latest['chainPins'], context)
        latest_proven = None
        if report is not None and report['verdict'] == 'PASSED':
            latest_proven = {'reportPin': report_pin, 'chainPins': report['backupAndChainPins'],
                             'current': not invalidated, 'verdict': report['verdict'],
                             'ageMilliseconds': report_age}
        for reason in invalidated:
            self.alert(reason)
        acceptance_verdict = 'UNKNOWN' if report is None else report['verdict']
        if acceptance_verdict == 'PASSED' and invalidated:
            acceptance_verdict = 'STALE'
        # Never compare persisted monotonic absolutes across process/boot domains.
        # A wall reversal produces UNKNOWN instead of extending the interval.
        ledger = self.state_root / ('schedule-' + digest(schedule) + '.json')
        history = parse_json(ledger.read_bytes()) if ledger.exists() else {'rounds': []}
        exact(history, ('rounds',), 'SCHEDULE_HISTORY_INVALID')
        require(type(history['rounds']) is list, 'SCHEDULE_HISTORY_INVALID')
        requests = []
        roles = [('LATEST_COMPLETE', latest)]
        if longest['pointPin'] != latest['pointPin']:
            roles.append(('LONGEST_SUPPORTED_CHAIN', longest))
        require(type(approval['permittedPointPins']) is list and
                all(entry['pointPin'] in approval['permittedPointPins'] for _, entry in roles),
                'REHEARSAL_POINT_NOT_APPROVED')
        for role, entry in roles:
            # Bind the selection, complete chain, current validation/context and
            # request semantics. An input change invalidates prior deduplication.
            basis = {'scheduleId': schedule, 'pointPin': entry['pointPin'],
                     'chainPins': entry['chainPins'], 'context': context, 'reportPin': report_pin,
                     'invalidatedBy': invalidated, 'templatePin': self.config['approvedRehearsalTemplatePin'],
                     'approvalPin': self.config['rehearsalTemplateApprovalPin']}
            fingerprint = digest(basis)
            previous = [r for r in history['rounds'] if r['basisSha256'] == fingerprint]
            last = previous[-1] if previous else None
            if last is not None:
                delta_ns = now_ns - timestamp_ns(last['plannedAt'])
                if delta_ns < 0:
                    state, code = 'TERMINAL_UNKNOWN', 'SCHEDULE_WALL_CLOCK_REVERSED'
                    self.alert(code)
                    continue
                if delta_ns < interval_ms * 1_000_000:
                    requests.append({'role': role, 'deduplicated': True, 'requestPin': last['requestPin']})
                    self.reader.read(last['requestPin'])
                    continue
            if state == 'TERMINAL_UNKNOWN':
                continue
            round_number = len(previous) + 1
            identity = digest({'basisSha256': fingerprint, 'round': round_number})
            generated = dict(template)
            generated.update(operationId='rehearsal-' + identity, requestId='rehearsal-' + identity,
                             action='REHEARSAL', mode='REHEARSAL', selectedPointPin=entry['pointPin'],
                             inputPins={'repositoryPoint': entry['pointPin']})
            self.contracts.validate('OperationRequest', generated)
            path = self.evidence_root / ('rehearsal-request-' + identity + '.json')
            atomic_json(path, generated)
            request_pin = pin_file(path)
            history['rounds'].append({'basisSha256': fingerprint, 'round': round_number,
                                      'plannedAt': utc_now(), 'requestPin': request_pin})
            requests.append({'role': role, 'deduplicated': False, 'requestPin': request_pin})
        atomic_json(ledger, history)
        return {'schemaVersion': 'recovery-rehearsal-observation/v1', 'state': state, 'failureCode': code,
                'latestCompletePointPin': latest['pointPin'], 'latestCompleteAgeMilliseconds': age_ns // 1_000_000,
                'latestProvenRecovery': latest_proven, 'invalidatedBy': invalidated,
                'recoveryAcceptanceVerdict': acceptance_verdict,
                'longestSupportedChainPin': longest['pointPin'], 'requests': requests,
                'dispatchRequiredBy': 'W01', 'recoveryExecuted': False,
                'localPlanningOnly': True, 'externalNotificationSent': False}
