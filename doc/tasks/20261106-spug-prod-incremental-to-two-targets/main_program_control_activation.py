"""Explicit MAIN controller generation activation. Import/prepare never contacts hosts.

Only --activate dispatches the compiled program. Failed or ambiguous attempts are
retained privately and never retried automatically. Fixtures verify local contracts,
not installation. This module neither stages engines nor publishes selectors.
"""
import argparse
import ast
import copy
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import tarfile

import main_program_installation_selection as contract
from installation_history_custody import SCRIPT as ORIGINAL_CUSTODY_PROGRAM

TASK = Path(__file__).resolve().parent
PRIVATE = Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
SOURCES = ('intruoyi-57-safe-20261024-v1', 'intruoyi-59-safe-20261024-v1', 'intruoyi-PROD57-20261019')
ORDER = (('59', 'target'), ('58', 'target'), ('57', 'target'), ('57', 'source'))
RECEIPT_FIELDS = ('sourceCommit', 'engine', 'ownerConfigurationPin', 'controlConfigurationPin')
COVERAGE_FLAGS = ('all14PackageContractsCovered', 'bothVariantsAll31InnerCasesCovered',
                  'variants34AndMountProtection15Covered', 'original71RegressionCovered',
                  'failedR5PreservedAsFailure', 'failedR7PreservedAsFailure')
PACKAGE_TEST_FILE = 'scripts/tests/test_recovery_main_program_package.py'
PACKAGE_SUITE_NODE = PACKAGE_TEST_FILE + '::test_producer_history_and_sql_lifecycle_run_from_actual_package'
COVERAGE_PHASES = {
    'regression-r3': (dict(actualPassed=71), [
        'scripts/tests/test_recovery_program_evidence.py::test_success_historical_validator_accepts_real_two_phase_native_sql_and_custody_after_close',
        'scripts/tests/test_recovery_program_evidence.py::test_historical_proof_does_not_require_an_active_host_reservation',
        'scripts/tests/test_recovery_program_evidence.py::test_subsequent_real_generation_does_not_replace_the_original_target_pin',
        'scripts/tests/test_recovery_program_evidence.py::test_failure_proof_preserves_actual_exits_and_unknown_without_granting_success',
        'scripts/tests/test_retained_replacement_retry.py', 'scripts/tests/test_legacy_main_clearance.py']),
    'regression-r5': (dict(actualPassed=8, actualOverallStatus='FAIL',
        reusedOnlyUnchangedCompletedPrefix=True), [PACKAGE_TEST_FILE, 'scripts/tests/test_backup_variants.py']),
    'regression-r6': (dict(actualPassed=2, suiteFile='test_recovery_program_producer_contract.py',
        actualInnerCasesPerVariant=6, variants=['standard', 'lightweight']),
        [PACKAGE_SUITE_NODE + '[producer-standard]', PACKAGE_SUITE_NODE + '[producer-lightweight]']),
    'regression-r7': (dict(actualPassed=1, actualOverallStatus='FAIL', reusedOnlyUnchangedCompletedPrefix=True,
        suiteFile='test_recovery_program_producer_sql_lifecycle.py', actualInnerCasesPerVariant=6, variants=['standard']),
        [PACKAGE_SUITE_NODE + '[sql-lifecycle-standard]', PACKAGE_SUITE_NODE + '[sql-lifecycle-lightweight]']),
    'regression-r8': (dict(actualPassed=2, suiteFile='test_recovery_source_archive_protection.py',
        actualInnerCasesPerVariant=19, variants=['standard', 'lightweight']),
        [PACKAGE_SUITE_NODE + '[source-protection-standard]', PACKAGE_SUITE_NODE + '[source-protection-lightweight]']),
    'regression-r9': (dict(actualPassed=49), ['scripts/tests/test_backup_variants.py',
        'scripts/tests/test_archive_view_stacked_linux.py', 'scripts/tests/test_archive_view_readonly_linux.py',
        'scripts/tests/test_main_archive_view.py', 'scripts/tests/test_archive_view_protection_linux.py']),
    'regression-r10': (dict(actualPassed=1, suiteFile='test_recovery_program_producer_sql_lifecycle.py',
        actualInnerCasesPerVariant=6, variants=['lightweight']), [PACKAGE_SUITE_NODE + '[sql-lifecycle-lightweight]']),
}


def need(value, code):
    if not value:
        raise ValueError('MAIN_ACTIVATION_' + code)


# One pure implementation is executed locally for baseline validation and is
# included verbatim in the remote program. It performs no I/O at definition time.
ENVIRONMENT_PROGRAM = r'''
def parse_declared_environment(raw):
 need(type(raw) is str and raw.startswith('Environment=') and raw.endswith('\n') and
  not any(c in raw[:-1] for c in ('\n','\r','\x00','\\')),'SYSTEMD_ENVIRONMENT_FORMAT_INVALID')
 result={}
 for token in shlex.split(raw[len('Environment='):-1],posix=True):
  need('=' in token,'SYSTEMD_ENVIRONMENT_FORMAT_INVALID');key,value=token.split('=',1)
  need(re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',key) and key not in result,'SYSTEMD_ENVIRONMENT_FORMAT_INVALID')
  result[key]=value
 return result

def verify_environment_values(configuration,raw,*,baseline=None,systemd_raw=None):
 need(type(configuration) is dict and all(type(k) is str and type(v) is str for k,v in configuration.items()),'CONTROL_ENVIRONMENT_INVALID')
 need(type(raw) is bytes and raw.endswith(b'\0'),'CONTROL_ENVIRONMENT_FORMAT_INVALID')
 environment={}
 for part in raw[:-1].split(b'\0'):
  need(b'=' in part,'CONTROL_ENVIRONMENT_FORMAT_INVALID');key,value=part.split(b'=',1)
  need(key and key not in environment,'CONTROL_ENVIRONMENT_FORMAT_INVALID');environment[key]=value
 if baseline is None:
  need(all(environment.get(k.encode())==v.encode() for k,v in configuration.items()),'CONTROL_ENVIRONMENT_CHANGED')
  return dict(mode='CONFIG_EXACT',environmentSha256=hashlib.sha256(raw).hexdigest())
 need(hashlib.sha256(raw).hexdigest()==baseline['environmentSha256'],'ORIGINAL_ENVIRONMENT_CHANGED')
 need(type(systemd_raw) is str and systemd_raw==baseline['systemdEnvironmentRaw'] and
  hashlib.sha256(systemd_raw.encode('utf-8')).hexdigest()==baseline['systemdEnvironmentSha256'],'SYSTEMD_ENVIRONMENT_CHANGED')
 declared=parse_declared_environment(systemd_raw)
 need(declared==baseline['declaredEnvironment'] and all(environment.get(k.encode())==v.encode() for k,v in declared.items()),'SYSTEMD_DECLARED_ENVIRONMENT_CHANGED')
 need(configuration.get('PYTHONDONTWRITEBYTECODE')=='1' and type(configuration.get('PYTHONPATH')) is str and configuration['PYTHONPATH'] and
  all(environment.get(k.encode())==configuration[k].encode() for k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE')),'CONTROL_PYTHON_ENVIRONMENT_CHANGED')
 return dict(mode='ORIGINAL_BASELINE',environmentSha256=baseline['environmentSha256'],systemdEnvironmentSha256=baseline['systemdEnvironmentSha256'])
'''
exec(ENVIRONMENT_PROGRAM)

BASELINE_FIELDS = {'schemaVersion', 'status', 'host', 'observedAt', 'unitObservationPin', 'privateSnapshotPin',
                   'controllers', 'serverFilesWritten', 'controlServicesReloaded', 'backupDispatched', 'restoreDispatched'}
BASELINE_ROW_FIELDS = {'service', 'pid', 'engine', 'controlConfigurationPin', 'ownerConfigurationPin', 'argvSha256',
                       'unitPin', 'dropinPins', 'environmentSha256', 'systemdEnvironmentSha256'}
ENVIRONMENT_PRIVATE_FIELDS = {'systemdEnvironmentRaw', 'declaredEnvironment'}
OBSERVATION_FALSE_FIELDS = ('serverFilesWritten', 'controlServicesReloaded', 'backupDispatched', 'restoreDispatched')
CONTINUATION_COMMIT = '899730de38c0e883245c11f2ad7986424ecbaf80'
CONTINUATION_STEM = 'main-program-control-activation-59-target-899730d'
CONTINUATION_SERVICE = 'spug-main-restore-59-20261104-v3.service'
CONTINUATION_FILE = 'main-program-control-initial-continuation-59-target-899730d-r2.json'
CONTINUATION_OBSERVATION_FILE = 'main-program-control-initial-observation-59-target-899730d-r2.json'
PRIOR_FAILURE_SHA256 = '09233019f9a6cb10928c22343ad022891c174ede712cb6767a6d1edcb77b8dfa'
PRIOR_SCRIPT_SHA256 = '61f05b3a58a0146794c4d2bdb4331517228bc7142e79005677fc4f76af41f94c'
PRESWITCH_FAILURE_PIN = dict(bytes=11308, sha256='ddaba033b95684ef14e471c6c8a72e13f2f8b97c971d37041d07c82fede335ff')
PRESWITCH_ATTEMPT_PIN = dict(bytes=7107, sha256='1a0b1706d08a05947f117d9060ea486cd2806f3cf23ecade7864dba4d273f968')
PRESWITCH_COMMAND_PIN = dict(bytes=119, sha256='dba053ff3f43a1ddde5d766ccf3367507eb19adc545efb53d256bb14033ca701')
PRESWITCH_SCRIPT_SHA256 = '6bb5cb1ba7f5c7f5277dfd425c205ee8cabe3de0617dce4a7dca79941cbf0619'
PRESWITCH_COMMAND_SHA256 = 'dba053ff3f43a1ddde5d766ccf3367507eb19adc545efb53d256bb14033ca701'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


# Shared, bounded evidence checks for this reviewed v4 source-policy upgrade.
# This pure reader is embedded verbatim in both candidate and activation gates;
# historical consumption never reads live state or evaluates the current clock.
SOURCE_POLICY_PROGRAM = r'''
def source_policy_pin(value):
 need(type(value) is dict and set(value)=={'path','bytes','sha256'} and
  type(value['path']) is str and value['path'] and type(value['bytes']) is int and value['bytes']>0 and
  type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}',value['sha256']),'SOURCE_POLICY_PIN_INVALID')
def source_policy_limits(value):
 need(type(value) is dict and type(value.get('maxChainPoints')) is int and 1<=value['maxChainPoints']<=1024 and
  type(value.get('maxChainAgeSeconds')) is int and value['maxChainAgeSeconds']>0,'SOURCE_POLICY_LIMITS_INVALID')
 return {key:value[key] for key in ('maxChainPoints','maxChainAgeSeconds')}
def source_policy_time(value):
 from datetime import datetime
 need(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)',value),
  'SOURCE_POLICY_TIME_INVALID')
 try:datetime.fromisoformat(value.replace('Z','+00:00'))
 except ValueError:raise ValueError('SOURCE_POLICY_TIME_INVALID') from None
def source_policy_scope(value):
 need(type(value) is dict and set(value)=={'profile','coveragePin','sourceBaselinePin','sourceConfigRef','sourceExpected','chain','policy','rootAuditPin','rootManifestPin'} and
  value['profile']=='incremental-chain-policy-admission/v1','SOURCE_POLICY_SCOPE_INVALID')
 for key in ('coveragePin','sourceBaselinePin','rootAuditPin'):
  ref=value[key]
  need(type(ref) is dict and set(ref)=={'file','bytes','sha256'} and type(ref['file']) is str and ref['file'] and
   type(ref['bytes']) is int and ref['bytes']>0 and type(ref['sha256']) is str and re.fullmatch('[0-9a-f]{64}',ref['sha256']),
   'SOURCE_POLICY_LOCAL_PIN_INVALID')
 need(value['rootAuditPin']['file']=='automatic-full-audit.json','SOURCE_POLICY_ROOT_AUDIT_REQUIRED')
 source_policy_pin(value['rootManifestPin'])
 need(type(value['sourceConfigRef']) is str and value['sourceConfigRef'],'SOURCE_POLICY_SOURCE_INVALID')
 chain=value['chain'];need(type(chain) is list and len(chain)==3,'SOURCE_POLICY_ORIGINAL_CHAIN_REQUIRED')
 ids=[];pins=[]
 for index,row in enumerate(chain):
  need(type(row) is dict and set(row)=={'operationId','pointType','pointPin','epochBindingPin'} and
   type(row['operationId']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',row['operationId']) and
   row['pointType']==('FULL' if index==0 else 'INCREMENTAL'),'SOURCE_POLICY_POINT_IDENTITY_CHANGED')
  for key in ('pointPin','epochBindingPin'):source_policy_pin(row[key])
  ids.append(row['operationId']);pins.append(row['pointPin']['path'])
 need(len(set(ids))==len(set(pins))==3 and value['sourceExpected']==dict(baseFullRef=ids[0],parentChainRef=ids[-1],generationId=ids[0]),
  'SOURCE_POLICY_ORIGINAL_CHAIN_CHANGED')
 need(source_policy_limits(value['policy'])==value['policy'],'SOURCE_POLICY_LIMIT_FIELDS_INVALID')
def source_policy_plan(plan,transition,reason):
 fields={'schemaVersion','sourceConfigRef','state','reasonCode','parentChainRef','baseFullRef','generationId','chainDepth',
  'pointType','finishedAt','baseFinishedAt','basePointType','parentPointType','evidenceDigest','planDigest'}
 need(type(plan) is dict and set(plan)==fields and plan['schemaVersion']=='AutomaticIncrementalPlan/v1' and
  plan['sourceConfigRef']==transition['sourceConfigRef'],'SOURCE_POLICY_PLAN_SCHEMA_CHANGED')
 need(all(type(plan[k]) is str and re.fullmatch('[0-9a-f]{64}',plan[k]) for k in ('evidenceDigest','planDigest')) and
  hashlib.sha256(canonical({k:v for k,v in plan.items() if k!='planDigest'})).hexdigest()==plan['planDigest'],
  'SOURCE_POLICY_PLAN_DIGEST_CHANGED')
 need(reason in (None,'INCREMENTAL_CHAIN_AGE_EXPIRED') and plan['reasonCode']==reason,'SOURCE_POLICY_REASON_NOT_APPROVED')
 if reason is None:
  need(plan['state']=='READY' and all(plan[k]==v for k,v in transition['sourceExpected'].items()) and
   type(plan['chainDepth']) is int and plan['chainDepth']==3 and plan['pointType']==plan['parentPointType']=='INCREMENTAL' and
   plan['basePointType']=='FULL','SOURCE_POLICY_READY_CHAIN_CHANGED')
  for key in ('finishedAt','baseFinishedAt'):source_policy_time(plan[key])
 else:
  need(plan['state']=='BASELINE_REQUIRED' and type(plan['chainDepth']) is int and plan['chainDepth']==0 and
   all(plan[k] is None for k in ('parentChainRef','baseFullRef','generationId','pointType','finishedAt','baseFinishedAt',
    'basePointType','parentPointType')),'SOURCE_POLICY_EXPIRED_PLAN_CHANGED')
def validate_source_policy_admission(transition,proof):
 source_policy_scope(transition)
 need(type(proof) is dict and set(proof)=={'transition','rootManifestPin','rootCreatedAt','reasonCode','plan'} and
  proof['transition']==transition,'SOURCE_POLICY_CANDIDATE_PROOF_REQUIRED')
 source_policy_pin(proof['rootManifestPin']);source_policy_time(proof['rootCreatedAt'])
 need(proof['rootManifestPin']==transition['rootManifestPin'],'SOURCE_POLICY_ROOT_MANIFEST_CHANGED')
 source_policy_plan(proof['plan'],transition,proof['reasonCode'])
def validate_source_policy_transition(transition,observed):
 source_policy_scope(transition)
 need(type(observed) is dict and observed.get('physicalLockVerified') is True,'SOURCE_POLICY_PHYSICAL_LOCK_REQUIRED')
 for key in ('sourcePlanBefore','sourcePlanBeforeLocked'):
  source_policy_plan(observed.get(key),transition,None)
 before=observed.get('candidateBefore');after=observed.get('candidateAfter')
 need(type(before) is dict and before==after and before.get('sourceCaptureVerified') is True and
  type(before.get('epoch')) is dict and before['epoch'].get('state')=='READY','SOURCE_POLICY_CANDIDATE_CHANGED')
 proof=before.get('sourcePolicyAdmission');validate_source_policy_admission(transition,proof)
 need(observed.get('sourcePlanAfter')==proof['plan'],'SOURCE_POLICY_ACTUAL_HTTP_CHANGED')
'''
exec(SOURCE_POLICY_PROGRAM)


def make_source_policy_transition(inputs, coverage, baseline, old_owner, owner, *, root_audit=None, root_audit_pin=None):
    # This call is made only after complete coverage validation. A caller cannot
    # select the exception through an input flag or an unrecognized profile.
    if not (inputs.get('schemaVersion') == 'MainProgramControlActivationInputs/v4' and
            inputs.get('suffix') == '57' and inputs.get('role') == 'source' and
            coverage.get('schemaVersion') == 'MainProgramControlCoverage/v2' and
            coverage.get('profile') == 'incremental-chain-policy-admission/v1'):
        return None
    policy = source_policy_limits(owner)
    need(policy == source_policy_limits(old_owner), 'SOURCE_POLICY_OWNER_LIMITS_CHANGED')
    need(baseline.get('sourceConfigRef') == SOURCES[0], 'SOURCE_POLICY_SOURCE_CHANGED')
    chain = baseline.get('chain')
    need(type(chain) is list and len(chain) == 3, 'SOURCE_POLICY_ORIGINAL_CHAIN_REQUIRED')
    root = chain[0]
    need(type(root_audit) is dict and root_audit.get('schemaVersion') == 'AutomaticBackupChainAudit/v1' and
        root_audit.get('status') == 'PASS' and root_audit.get('sourceConfigRef') == baseline['sourceConfigRef'] and
        root_audit.get('operationId') == root_audit.get('generationId') == root['operationId'] and
        root_audit.get('pointType') == 'FULL' and root_audit.get('state') == 'SUCCEEDED' and
        type(root_audit.get('actualExitCode')) is int and root_audit['actualExitCode'] == 0 and
        root_audit.get('sourceRestored') is True and root_audit.get('pointPin') == root['pointPin'] and
        root_audit.get('epochBindingPin') == root['epochBindingPin'] and root_audit.get('chain') == [root] and
        root_audit.get('parentPointPins') == [], 'SOURCE_POLICY_ROOT_AUDIT_REQUIRED')
    value = dict(profile=coverage['profile'], coveragePin=inputs['coveragePin'],
        sourceBaselinePin=inputs['sourceBaselinePin'], sourceConfigRef=baseline['sourceConfigRef'],
        sourceExpected=dict(baseFullRef=chain[0]['operationId'], parentChainRef=baseline['operationId'],
            generationId=baseline['generationId']), chain=chain, policy=policy,
        rootAuditPin=root_audit_pin, rootManifestPin=root_audit['manifestPin'])
    source_policy_scope(value)
    return copy.deepcopy(value)


def read_document(path):
    return json.loads(Path(path).read_bytes().decode('utf-8'), object_pairs_hook=contract.document)


def file_pin(path):
    path = Path(path)
    need(not path.is_symlink() and path.is_file(), 'FILE_ALIAS')
    before = path.stat(); raw = path.read_bytes(); after = path.stat()
    need((before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
         (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'FILE_CHANGED')
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def verify_local_pin(path, expected):
    """Verify original evidence bytes without assuming a document format."""
    actual = file_pin(path)
    need(actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256'], 'PIN_CHANGED')
    return actual


def checked_local(path, expected):
    verify_local_pin(path, expected)
    return read_document(path)


def private_document(private, expected, filename):
    path = Path(private) / filename
    need(Path(expected['path']).resolve() == path.resolve(strict=True), 'PRIVATE_PATH_CHANGED')
    return checked_local(path, expected)


def predecessors(suffix, role):
    need((suffix, role) in ORDER, 'ROLE_INVALID')
    return ORDER[:ORDER.index((suffix, role))]


def receipt_successor(previous, commit, engine, owner, control):
    result = copy.deepcopy(previous)
    result.update(sourceCommit=commit, engine=engine, ownerConfigurationPin=owner, controlConfigurationPin=control)
    need(set(previous) == set(result) and all(result[k] == previous[k] for k in previous if k not in RECEIPT_FIELDS),
         'RECEIPT_FIELDS_CHANGED')
    return result


def exclusive_bytes(path, raw):
    path = Path(path)
    need(path.parent.resolve(strict=True) == path.parent and not path.is_symlink(), 'OUTPUT_ALIAS')
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags, 0o600), 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    need(path.read_bytes() == raw, 'OUTPUT_READBACK_FAILED')
    return file_pin(path)


def rotate_receipt(active, archive, expected, updated):
    """Archive original bytes exclusively, compare again, atomically replace once."""
    active, archive = Path(active), Path(archive)
    original = checked_local(active, expected)
    need(set(original) == set(updated) and all(original[k] == updated[k] for k in original if k not in RECEIPT_FIELDS),
         'RECEIPT_FIELDS_CHANGED')
    previous = exclusive_bytes(archive, active.read_bytes())
    need(all(previous[k] == expected[k] for k in ('bytes', 'sha256')), 'ARCHIVE_CHANGED')
    checked_local(active, expected)
    temporary = active.with_name(active.name + '.pending')
    exclusive_bytes(temporary, canonical(updated))
    checked_local(active, expected)
    os.replace(temporary, active)
    if os.name == 'posix':
        fd = os.open(active.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    return dict(previousReceiptPin=previous, currentReceiptPin=file_pin(active))


def safe_systemd(value):
    need(type(value) is str and value and not any(c in value for c in '\r\n\x00%$"\\'), 'SYSTEMD_VALUE_INVALID')
    return value


def make_dropin(service, engine, control_pin, control, existing, commit, guard):
    need(re.fullmatch('[A-Za-z0-9_.@-]+[.]service', service) and
         re.fullmatch('spug-history-prod57-readonly-(57|58|59)[.]service', guard), 'SERVICE_INVALID')
    need(re.fullmatch('[0-9a-f]{40}', commit) and existing and len(existing) == len(set(existing)), 'DROPIN_INPUT_INVALID')
    engine, python = safe_systemd(engine), safe_systemd(control['pythonPin']['path'])
    environment = control['environment']
    need(type(environment) is dict and 'PYTHONPATH' in environment, 'ENVIRONMENT_INVALID')
    env = []
    for name, value in sorted(environment.items()):
        need(re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', name), 'ENVIRONMENT_NAME_INVALID')
        env.append('Environment="' + name + '=' + safe_systemd(value) + '"')
    leading = max(len(n) - len(n.lstrip('z')) for n in existing) + 1
    name = 'z' * leading + '-main-program-' + commit[:7] + '.conf'
    need(all(name > old for old in existing), 'DROPIN_PRECEDENCE_INVALID')
    encoded_pin = canonical(control_pin).decode('utf-8')
    need("'" not in encoded_pin and '%' not in encoded_pin and '$' not in encoded_pin, 'PIN_ARGUMENT_INVALID')
    command = '"' + python + '" -B "' + engine + '/control_entry.py" serve --config-pin ' + "'" + encoded_pin + "'"
    raw = ('[Unit]\nRequires=' + guard + '\nAfter=' + guard + '\n[Service]\n' +
           '\n'.join(env) + '\nLimitNOFILE=65536\nExecStart=\nExecStart=' + command + '\n').encode('utf-8')
    return name, raw


def validate_staging(plan, build, suffix, engine_report, configuration_report):
    for report in (engine_report, configuration_report):
        need(report.get('status') == 'STAGED_NOT_ACTIVATED' and report.get('sourceCommit') == plan['sourceCommit'] and
             report.get('host') == '172.30.30.' + suffix, 'STAGING_IDENTITY_CHANGED')
        need(all(report.get(k) is True for k in ('businessContainersUnchanged', 'configurationUnchanged')) and
             all(report.get(k) is False for k in ('controlServicesReloaded', 'backupDispatched', 'restoreDispatched')),
             'STAGING_PRESERVATION_FAILED')
    rows = plan['controllers'][suffix]
    engines = engine_report.get('engines', [])
    need(len(engines) == len(rows) and len({r['path'] for r in engines}) == len(rows), 'STAGED_ENGINE_COUNT')
    for row in rows:
        match = [value for value in engines if value['path'] == row['engine']]
        need(len(match) == 1 and match[0].get('filesSha256Verified') is True and
             match[0].get('pythonCompileVerified') is True and
             all(type(match[0].get(k)) is type(build[k]) and match[0][k] == build[k]
                 for k in ('fileCount', 'packageSha256', 'fileManifestSha256')) and build['fileCount'] == 147,
             'STAGED_ENGINE_NOT_PROVEN')
    stage = configuration_report['configurationStaging']
    need(configuration_report.get('existingPhysicalLockAcquiredAndReleased') is True and
         stage.get('status') == 'STAGED_NOT_ACTIVATED' and stage.get('registrySelectorsPublished') is False and
         stage.get('historyMaterialsChanged') is False, 'STAGED_CONFIGURATION_SCOPE')
    docs = stage['documents']; candidates = stage['candidates']
    need(len(docs) == plan['documents'][suffix] and len({p['path'] for p in docs}) == len(docs) and
         len(candidates) == len(rows), 'STAGED_CONFIGURATION_COUNT')
    for row, actual in zip(rows, candidates):
        need(all(actual.get(k) == row[k] for k in ('role', 'controlPin', 'ownerPin')) and
             actual.get('actualConfigurationReadPassed') is True and actual.get('actualTargetOrCaptureBindingPassed') is True and
             row['controlPin'] in docs and row['ownerPin'] in docs, 'STAGED_CANDIDATE_CHANGED')
        if row['role'] == 'source':
            need(actual['observedSourceRefs'] == [SOURCES[0]], 'CAPTURE_SOURCE_CHANGED')
        else:
            need(actual['observedSourceRefs'] == list(SOURCES), 'THREE_SOURCES_REQUIRED')
            protections = actual.get('sourceArchiveProtections', [])
            need(len(protections) == 3 and {p['sourceConfigRef'] for p in protections} == set(SOURCES) and
                 all(p.get('actualFactoryPreflightPassed') is True and p.get('mountCommandExecuted') is False and
                     p.get('journalWritten') is False for p in protections), 'ARCHIVE_FACTORY_PROOF_REQUIRED')


def validate_generation_inputs(inputs):
    """Validate the v4 envelope before reading any dependency or creating output."""
    fields = {'schemaVersion', 'sourceCommit', 'suffix', 'role', 'revisionId', 'buildPin', 'planPin',
              'previousControlGenerationPin', 'engineStagedPin', 'configurationStagedPin',
              'unitObservationPin', 'originalEnvironmentObservationPin', 'precedingActivationPins',
              'sourceBaselinePin', 'coveragePin', 'outputFile'}
    need(type(inputs) is dict and set(inputs) == fields and
         inputs['schemaVersion'] == 'MainProgramControlActivationInputs/v4' and
         type(inputs['sourceCommit']) is str and re.fullmatch('[0-9a-f]{40}', inputs['sourceCommit']) and
         type(inputs['revisionId']) is str and re.fullmatch('r[1-9][0-9]*', inputs['revisionId']),
         'GENERATION_INPUTS_INVALID')
    prior = predecessors(inputs['suffix'], inputs['role'])
    short, revision, suffix = inputs['sourceCommit'][:7], inputs['revisionId'], inputs['suffix']
    names = {
        'buildPin': 'release-build-' + short + '.json',
        'planPin': 'main-program-configuration-plan-' + short + '-' + revision + '.json',
        'engineStagedPin': 'main-program-engine-staged-' + suffix + '-' + short + '-' + revision + '.json',
        'configurationStagedPin': 'main-program-configuration-staged-' + suffix + '-' + short + '-' + revision + '.json',
        'unitObservationPin': 'main-program-control-units-' + suffix + '-' + short + '-' + revision + '.json',
        'originalEnvironmentObservationPin': 'main-program-control-environment-baseline-' + suffix + '-' + short + '-' + revision + '.json',
        'sourceBaselinePin': 'automatic-i2-audit.json',
    }
    def reference(value):
        need(type(value) is dict and set(value) == {'file', 'bytes', 'sha256'} and
             type(value['bytes']) is int and value['bytes'] > 0 and contract.sha(value['sha256']),
             'GENERATION_PIN_INVALID')
        try: contract.local_name(value['file'])
        except ValueError as error: raise ValueError('MAIN_ACTIVATION_GENERATION_PIN_INVALID') from error
    for key in (*names, 'previousControlGenerationPin', 'coveragePin'):
        reference(inputs[key])
        if key in names: need(inputs[key]['file'] == names[key], 'GENERATION_INPUT_REVISION_REQUIRED')
    need(type(inputs['precedingActivationPins']) is list and len(inputs['precedingActivationPins']) == len(prior),
         'ACTIVATION_ORDER_REQUIRED')
    for item in inputs['precedingActivationPins']: reference(item)
    need(inputs['outputFile'] == 'main-program-control-activation-' + suffix + '-' + inputs['role'] +
         '-' + short + '-' + revision + '.json', 'GENERATION_OUTPUT_NAME_INVALID')
    return prior


def validate_generation_staging(inputs, plan, build, engine_report, configuration_report):
    """V4 adds generation and retained-file proof to every original stage gate."""
    suffix = inputs['suffix']
    need(plan.get('schemaVersion') == 'MainProgramConfigurationPlan/v2' and
         plan.get('revisionId') == inputs['revisionId'] and
         plan.get('predecessorGenerationPin') == inputs['previousControlGenerationPin'] and
         plan.get('buildPin') == inputs['buildPin'], 'GENERATION_STAGE_PLAN_CHANGED')
    for report in (engine_report, configuration_report):
        need(all(report.get(key) == inputs[key] for key in
             ('revisionId', 'previousControlGenerationPin', 'buildPin', 'planPin')),
             'GENERATION_STAGE_BINDING_CHANGED')
    validate_staging(plan, build, suffix, engine_report, configuration_report)
    stage = configuration_report['configurationStaging']
    new, retained = stage.get('newDocuments'), stage.get('retainedDocuments')
    need(type(new) is list and type(retained) is list and
         new == plan['newDocumentsByHost'][suffix] and retained == plan['retainedDocumentsByHost'][suffix] and
         new + retained == stage['documents'] and
         len({p['path'] for p in new + retained}) == len(new) + len(retained) and
         stage.get('retainedDocumentsVerifiedUnchanged') is True and stage.get('newDocumentsCreatedExclusively') is True,
         'GENERATION_STAGE_RETENTION_NOT_PROVEN')


def validate_generation_coverage(records, inputs, predecessor):
    """Read the original full proof and exact candidate delta, including both tars."""
    from main_program_control_upgrade_plan import validate_delta
    report = records.pinned(inputs['coveragePin'])
    if report.get('schemaVersion') == 'MainProgramControlCoverage/v2':
        from main_program_chain_policy_evidence import validate_chain_policy_coverage
        return validate_chain_policy_coverage(records,inputs,predecessor,file_pin=file_pin,
                                              validate_initial_coverage=validate_coverage)
    fields = {'schemaVersion', 'status', 'baselineCoveragePin', 'baselineBuildPin', 'candidateBuildPin',
              'changedFiles', 'unchangedPackageFiles', 'deltaTestEvidencePins', 'actualPackageEvidencePins', 'failedEvidencePins'}
    need(set(report) == fields and report['schemaVersion'] == 'MainProgramControlCoverage/v1' and
         report['status'] == 'PASS' and report['candidateBuildPin'] == inputs['buildPin'] and
         report['baselineBuildPin'] == predecessor['generation']['buildPin'], 'GENERATION_COVERAGE_INVALID')
    build = records.pinned(report['candidateBuildPin']); old_build = records.pinned(report['baselineBuildPin'])
    need(old_build == predecessor['build'] and old_build.get('exactTestCoveragePin') == report['baselineCoveragePin'],
         'GENERATION_BASELINE_COVERAGE_CHANGED')
    need(build.get('status') == 'PASS' and build.get('targetCommit') == inputs['sourceCommit'] and
         inputs['buildPin']['file'] == 'release-build-' + inputs['sourceCommit'][:7] + '.json' and
         build.get('allFilesShaAndCompileVerified') is True and build.get('newCommits') is False and
         build.get('mergeRequired') is False and build.get('fileCount') == 147,
         'GENERATION_BUILD_NOT_PROVEN')
    local_refs, package_refs, failures = (report[k] for k in
        ('deltaTestEvidencePins', 'actualPackageEvidencePins', 'failedEvidencePins'))
    need(type(local_refs) is list and len(local_refs) == 2 and type(package_refs) is list and len(package_refs) == 2 and
         type(failures) is list and len(failures) >= 1 and local_refs[0].get('file') == 'archive-catalogue-request-reads-result.json' and
         re.fullmatch(r'archive-catalogue-linux-packages-r[1-9][0-9]*\.json', local_refs[1].get('file', '')) and
         re.fullmatch(r'archive-catalogue-package-delta-r[1-9][0-9]*\.json', package_refs[0].get('file', '')) and
         package_refs[1] == local_refs[1], 'GENERATION_COVERAGE_EVIDENCE_SET_INVALID')
    local_proof = records.pinned(local_refs[0]); linux = records.pinned(local_refs[1]); delta = records.pinned(package_refs[0])
    need(local_proof.get('schemaVersion') == 'ArchiveRequestReadsLocalVerification/v1' and
         local_proof.get('tests') == dict(new=23, catalogueRegression=27, registrationRegression=9),
         'GENERATION_SOURCE_TESTS_NOT_PROVEN')
    need(linux.get('schemaVersion') == 'ArchiveCatalogueLinuxPackageVerification/v1' and linux.get('status') == 'PASS' and
         linux.get('sourceCommit') == inputs['sourceCommit'] and type(linux.get('exitCode')) is int and linux['exitCode'] == 0 and
         linux.get('timedOut') is False and linux.get('network') == 'none' and
         all(linux.get(k) is True for k in ('containerRemoved', 'rootFilesystemReadOnly', 'bindsReadOnly', 'nativeTmpfsInputs', 'buildWorktreeClean')) and
         linux.get('installed') is False and linux.get('actualHttpBudgetVerified') is False,
         'GENERATION_LINUX_TESTS_NOT_PROVEN')
    need(type(linux.get('results')) is list and len(linux['results']) == 3 and
         [(r.get('mode'), r.get('tests'), r.get('skipped'), r.get('failures'), r.get('errors')) for r in linux['results']] ==
         [('source', 59, 0, 0, 0), ('standard', 50, 0, 0, 0), ('lightweight', 50, 0, 0, 0)] and
         all(type(r.get(k)) is int for r in linux['results'] for k in ('tests', 'skipped', 'failures', 'errors')),
         'GENERATION_LINUX_RESULTS_INVALID')
    need(linux.get('previousFailurePin') in failures and len({r['file'] for r in failures}) == len(failures),
         'GENERATION_FAILURE_HISTORY_REQUIRED')
    for ref in failures:
        failure = records.pinned(ref)
        need(re.fullmatch(r'archive-catalogue-linux-packages-r[1-9][0-9]*-failure\.json', ref['file']) and
             failure.get('schemaVersion') == 'ArchiveCatalogueLinuxPackageVerificationFailure/v1' and
             failure.get('status') == 'FAIL' and failure.get('sourceCommit') == inputs['sourceCommit'] and
             failure.get('actualTestResultsReceived') is False and failure.get('installed') is False and failure.get('serverWrites') is False,
             'GENERATION_ORIGINAL_FAILURE_CHANGED')
    physical = []
    def checked_bytes(path, reference, *, limit=64 * 1024 * 1024):
        path = Path(path); actual = file_pin(path)
        need(actual['bytes'] <= limit and all(actual[k] == reference[k] for k in ('bytes', 'sha256')),
             'GENERATION_EVIDENCE_PIN_CHANGED')
        raw = path.read_bytes()
        need(file_pin(path) == actual and len(raw) == actual['bytes'] and hashlib.sha256(raw).hexdigest() == actual['sha256'],
             'GENERATION_EVIDENCE_CHANGED_DURING_READ')
        physical.append(actual); return raw
    log_ref = linux['rawLogPin']
    need(re.fullmatch(r'archive-catalogue-linux-packages-r[1-9][0-9]*\.log', log_ref['file']), 'GENERATION_LINUX_LOG_INVALID')
    log = checked_bytes(records.task / log_ref['file'], log_ref).decode('utf-8').replace('\r\n', '\n')
    need(log.count('\nOK\n') == 3 and not any(word in log for word in ('skipped=', 'FAILED (', 'ERROR:', 'FAIL:')),
         'GENERATION_LINUX_LOG_NOT_GREEN')
    root = TASK.parents[2]
    for name, ref in local_proof['files'].items():
        path = root / name
        need(not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts and
             path.resolve(strict=True).is_relative_to(root.resolve(strict=True)), 'GENERATION_SOURCE_EVIDENCE_SCOPE')
        checked_bytes(path, ref)
    candidate_root = Path(build['worktree']).resolve(strict=True)
    for name, sha in linux['sourcePins'].items():
        # The task-owned test is separately pinned; product files come from the committed build checkout.
        base = root if name.startswith('doc/tasks/') else candidate_root
        path = base / name
        need(not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts and
             path.resolve(strict=True).is_relative_to(base.resolve(strict=True)), 'GENERATION_LINUX_SOURCE_SCOPE')
        actual = file_pin(path); need(actual['sha256'] == sha, 'GENERATION_LINUX_SOURCE_CHANGED'); physical.append(actual)
    input_ref = linux['inputArchivePin']
    need(re.fullmatch(r'catalogue-linux-input-r[1-9][0-9]*\.tar', input_ref['file']), 'GENERATION_LINUX_INPUT_INVALID')
    checked_bytes(candidate_root.parent / input_ref['file'], input_ref)
    validate_coverage(records, old_build)
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    for args, expected in ((['rev-parse', 'HEAD'], inputs['sourceCommit']), (['status', '--porcelain', '--untracked-files=all'], '')):
        output = subprocess.run(['git', '-C', str(candidate_root), *args], capture_output=True, env=env, timeout=30, check=True)
        need(output.stdout.decode('utf-8').strip() == expected, 'GENERATION_BUILD_CHECKOUT_CHANGED')
    def package(reference, variant):
        path = Path(reference['path']); actual = file_pin(path)
        need(actual['sha256'] == reference['packageSha256'], 'GENERATION_PACKAGE_BYTES_CHANGED')
        raw = checked_bytes(path, actual)
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
            rows = archive.getmembers(); names = [row.name for row in rows]
            need(len(names) == len(set(names)) and all(row.isfile() and row.size <= 16 * 1024 * 1024 and
                 not PurePosixPath(row.name).is_absolute() and '..' not in PurePosixPath(row.name).parts and
                 str(PurePosixPath(row.name)) == row.name for row in rows) and
                 sum(row.size for row in rows) <= 128 * 1024 * 1024, 'GENERATION_PACKAGE_MEMBER_INVALID')
            metadata = json.loads(archive.extractfile('package.json').read().decode('utf-8'), object_pairs_hook=contract.document)
            files = {row.name: archive.extractfile(row).read() for row in rows if row.name != 'package.json'}
        need(reference['fileCount'] == len(files) == (147 if variant == 'standard' else 146) and
             metadata['files'] == {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()} and
             hashlib.sha256(canonical(metadata['files'])).hexdigest() == metadata['packageSha256'] == reference['fileManifestSha256'],
             'GENERATION_PACKAGE_MANIFEST_CHANGED')
        for name, content in files.items():
            if name.endswith('.py'): compile(content, name, 'exec')
        return files
    need(type(delta.get('packages')) is list and len(delta['packages']) == 2 and
         {r.get('variant') for r in delta['packages']} == {'standard', 'lightweight'}, 'GENERATION_PACKAGE_VARIANTS_INVALID')
    standard = None; before_standard = None; module = 'control/recovery_control_restore_catalogue.py'
    for row in delta['packages']:
        variant = row['variant']; after = package(row, variant); before = package(row['predecessor'], variant)
        need(set(after) == set(before), 'GENERATION_PACKAGE_MEMBER_SET_CHANGED')
        changed = sorted(name for name in after if after[name] != before[name]); evidence = {}
        for name in changed:
            line_only = before[name].replace(b'\r\n', b'\n') == after[name].replace(b'\r\n', b'\n')
            if line_only:
                need(ast.dump(ast.parse(before[name])) == ast.dump(ast.parse(after[name])), 'GENERATION_NORMALIZED_AST_CHANGED')
            evidence[name] = dict(oldBytes=len(before[name]), newBytes=len(after[name]),
                oldSha256=hashlib.sha256(before[name]).hexdigest(), newSha256=hashlib.sha256(after[name]).hexdigest(), lineEndingOnly=line_only)
        need(row['changedFiles'] == changed and row['changedFileEvidence'] == evidence and
             [name for name in changed if not evidence[name]['lineEndingOnly']] == [module], 'GENERATION_UNREVIEWED_PACKAGE_CHANGE')
        module_sha = hashlib.sha256(after[module]).hexdigest()
        result = next(r for r in linux['results'] if r['mode'] == variant)
        need(linux['packagePins'][variant] == dict(packageSha256=row['packageSha256'], moduleSha256=module_sha) and
             result['loadedModuleSha256'] == module_sha and result['actualPackageModuleLoaded'] is True,
             'GENERATION_ACTUAL_PACKAGE_TEST_CHANGED')
        if variant == 'standard':
            standard, before_standard = after, before
            need(report['changedFiles'] == evidence and report['unchangedPackageFiles'] ==
                 {name: hashlib.sha256(raw).hexdigest() for name, raw in after.items() if name not in changed},
                 'GENERATION_COVERAGE_PARTITION_CHANGED')
    source = linux['results'][0]
    need(source['actualPackageModuleLoaded'] is False and source['loadedModuleSha256'] ==
         linux['sourcePins']['backend/src/main/resources/recovery_control_restore_catalogue.py'], 'GENERATION_SOURCE_MODULE_CHANGED')
    validate_delta(delta, build, inputs['buildPin'], old_build, report['baselineBuildPin'], standard, before_standard,
                   inputs['sourceCommit'], predecessor['generation']['sourceCommit'])
    for ref in physical: need(file_pin(ref['path']) == ref, 'GENERATION_EVIDENCE_CHANGED_DURING_READ')
    return dict(coverage=report, build=build, delta=delta, packageFiles=standard,
                previousPackageFiles=before_standard, physicalPins=physical)


def validate_coverage(records, build):
    ref = build.get('exactTestCoveragePin')
    need(ref is not None, 'EXACT_TEST_COVERAGE_REQUIRED')
    coverage = records.pinned(ref)
    need(ref['file'] == 'source-archive-protection-composite-validation-r1.json' and
         coverage.get('schemaVersion') == 'TaskSourceArchiveCoverage/v1' and coverage.get('status') == 'PASS' and
         all(coverage.get(k) is True for k in COVERAGE_FLAGS) and coverage.get('inputCount') == 461 and
         type(coverage.get('inputPins')) is dict and len(coverage['inputPins']) == 461,
         'EXACT_TEST_COVERAGE_NOT_PROVEN')
    phases = coverage.get('evidence', [])
    need(type(phases) is list and all(type(p) is dict for p in phases) and
         [p.get('phase') for p in phases] == list(COVERAGE_PHASES), 'COVERAGE_PHASES_INVALID')
    for item in phases:
        expected, test_files = COVERAGE_PHASES[item['phase']]
        need(set(item) == {'phase', 'reportPin', *expected} and
             all(type(item.get(key)) is type(value) and item[key] == value
                 for key, value in expected.items()), 'COVERAGE_ENTRY_INVALID')
        need(type(item['reportPin']) is dict and
             item['reportPin'].get('file') == 'source-archive-protection-' + item['phase'] + '.json',
             'COVERAGE_REPORT_REVISION_INVALID')
        proof = records.pinned(item['reportPin'])
        need(proof.get('testFiles') == test_files, 'COVERAGE_TEST_GROUP_INVALID')
        if item['phase'] in ('regression-r5', 'regression-r7'):
            need(proof.get('status') == 'FAIL' and type(proof.get('actualExitCode')) is int and
                 proof['actualExitCode'] == 1,
                 'ORIGINAL_FAILURE_NOT_PRESERVED')
        else:
            need(proof.get('status') == 'PASS' and type(proof.get('actualExitCode')) is int and proof['actualExitCode'] == 0,
                 'REGRESSION_NOT_PASSED')
    root = Path(build['worktree']).resolve(strict=True)
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    for args, expected in ((['rev-parse', 'HEAD'], build['targetCommit']),
                           (['status', '--porcelain', '--untracked-files=all'], '')):
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, env=env, timeout=30, check=True)
        need(result.stdout.decode('utf-8').strip() == expected, 'BUILD_WORKTREE_NOT_CLOSED')
    for name, sha in coverage['inputPins'].items():
        path = root / name
        need(PurePosixPath(name).as_posix() == name and not PurePosixPath(name).is_absolute() and
             '..' not in PurePosixPath(name).parts and path.resolve(strict=True).is_relative_to(root) and
             file_pin(path)['sha256'] == sha, 'TESTED_CHECKOUT_BYTES_CHANGED')
    return coverage


def validate_environment_baseline(records, private, inputs, unit, original_controllers):
    ref = inputs['originalEnvironmentObservationPin']
    generation = inputs.get('schemaVersion') == 'MainProgramControlActivationInputs/v4'
    stem = 'main-program-control-environment-baseline-' + inputs['suffix'] + (
        '-' + inputs['sourceCommit'][:7] + '-' + inputs['revisionId'] if generation else '-r2')
    fields = BASELINE_FIELDS | ({'revisionId', 'previousControlGenerationPin'} if generation else set())
    need(ref.get('file') == stem + '.json', 'ENVIRONMENT_BASELINE_REVISION_REQUIRED')
    public = records.pinned(ref)
    need(set(public) == fields and public['schemaVersion'] == 'MainControlEnvironmentBaseline/v1' and
         public['status'] == 'PASS' and public['host'] == '172.30.30.' + inputs['suffix'] and
         public['unitObservationPin'] == inputs['unitObservationPin'] and
         all(public[k] is False for k in OBSERVATION_FALSE_FIELDS), 'ENVIRONMENT_BASELINE_INVALID')
    if generation:
        need(all(public[key] == inputs[key] for key in ('revisionId', 'previousControlGenerationPin')),
             'ENVIRONMENT_GENERATION_CHANGED')
    secret = private_document(private, public['privateSnapshotPin'], stem + '.private.json')
    need(set(secret) == fields - {'privateSnapshotPin'} and
         {k: v for k, v in secret.items() if k != 'controllers'} ==
         {k: v for k, v in public.items() if k not in ('controllers', 'privateSnapshotPin')},
         'ENVIRONMENT_BASELINE_PROJECTION_CHANGED')
    need(type(public['controllers']) is list and type(secret['controllers']) is list and
         len(public['controllers']) == len(secret['controllers']) == len(original_controllers) == len(unit['controllers']),
         'ENVIRONMENT_CONTROLLER_COUNT_CHANGED')
    for row, actual, original, registered in zip(public['controllers'], secret['controllers'], original_controllers, unit['controllers']):
        need(set(row) == BASELINE_ROW_FIELDS and set(actual) == BASELINE_ROW_FIELDS | ENVIRONMENT_PRIVATE_FIELDS and
             {k: v for k, v in actual.items() if k not in ENVIRONMENT_PRIVATE_FIELDS} == row,
             'ENVIRONMENT_CONTROLLER_PROJECTION_CHANGED')
        need(type(row['pid']) is int and row['pid'] > 1 and all(row[k] == original[k] for k in
             ('service', 'pid', 'engine', 'controlConfigurationPin', 'ownerConfigurationPin', 'argvSha256')) and
             all(row[k] == registered[k] for k in ('service', 'pid', 'unitPin', 'dropinPins')),
             'ENVIRONMENT_ORIGINAL_IDENTITY_CHANGED')
        for key in ('controlConfigurationPin', 'ownerConfigurationPin', 'unitPin'):
            contract.remote_pin(row[key])
        need(type(row['dropinPins']) is list, 'ENVIRONMENT_DROPINS_INVALID')
        for item in row['dropinPins']: contract.remote_pin(item)
        need(all(contract.sha(row[k]) for k in ('argvSha256', 'environmentSha256', 'systemdEnvironmentSha256')) and
             type(actual['declaredEnvironment']) is dict and
             parse_declared_environment(actual['systemdEnvironmentRaw']) == actual['declaredEnvironment'] and
             hashlib.sha256(actual['systemdEnvironmentRaw'].encode('utf-8')).hexdigest() == row['systemdEnvironmentSha256'],
             'ENVIRONMENT_DECLARATION_INVALID')
    return dict(publicPin=ref, privatePin=public['privateSnapshotPin'], controllers=copy.deepcopy(secret['controllers']))


def continuation_profile(reference):
    """Two reviewed failures only; no stage-based/general retry selection."""
    name = reference.get('file') if type(reference) is dict else None
    if name == CONTINUATION_FILE:
        return dict(suffix='59', stem=CONTINUATION_STEM, service=CONTINUATION_SERVICE, inputVersion='v2',
            originalVersion='v1', originalInputs=CONTINUATION_STEM + '-inputs.json', key='initialFailureContinuationPin',
            observationFile=CONTINUATION_OBSERVATION_FILE, schema='MainControlActivationInitialContinuation/v1',
            observationSchema='MainControlInitialFailureObservation/v1', stage='initial', error='CONTROL_ENVIRONMENT_CHANGED',
            failurePin=dict(bytes=467, sha256=PRIOR_FAILURE_SHA256), scriptSha256=PRIOR_SCRIPT_SHA256)
    need(name == 'main-program-control-preswitch-continuation-58-target-899730d-r2.json', 'CONTINUATION_SCOPE_INVALID')
    stem = 'main-program-control-activation-58-target-899730d'
    return dict(suffix='58', stem=stem, service='spug-main-restore-58-20261104-v3.service', inputVersion='v3',
        originalVersion='v2', originalInputs=stem + '-v2-inputs.json', key='preSwitchContinuationPin',
        observationFile='main-program-control-preswitch-observation-58-target-899730d-r2.json',
        schema='MainControlActivationPreSwitchContinuation/v1', observationSchema='MainControlPreSwitchFailureObservation/v1',
        stage='candidate-admission', error='ACTIVATION_COMMAND_FAILED_1', failurePin=PRESWITCH_FAILURE_PIN,
        scriptSha256=PRESWITCH_SCRIPT_SHA256)


def continuation_reference_key(continuation):
    return continuation_profile(continuation.get('preSwitchContinuationPin', continuation.get('initialFailureContinuationPin')))['key']


def _validate_continuation(records, private, spec, reference):
    profile = continuation_profile(reference); inputs = spec['inputs']; preswitch = profile['suffix'] == '58'
    need(inputs['schemaVersion'] == 'MainProgramControlActivationInputs/' + profile['inputVersion'] and
         inputs['suffix'] == profile['suffix'] and inputs['role'] == 'target' and inputs['sourceCommit'] == CONTINUATION_COMMIT and
         inputs['outputFile'] == profile['stem'] + '.json', 'INITIAL_CONTINUATION_SCOPE_INVALID')
    value = records.pinned(reference)
    common_keys = {'host', 'service', 'role', 'sourceCommit', 'originalInputsPin', 'priorAttemptPin', 'priorFailurePin',
                   'priorRemoteResultPin', 'originalEnvironmentObservationPin'}
    if preswitch: common_keys |= {'priorRemoteBeforePin', 'priorRemoteCommandPin', 'priorBeforeSnapshotPin', 'priorCommandSnapshotPin'}
    need(set(value) == common_keys | {'schemaVersion', 'status', 'attemptRevision', 'readonlyObservationPin'} and
         value['schemaVersion'] == profile['schema'] and
         value['status'] == 'READY_FOR_EXPLICIT_CONTINUATION' and type(value['attemptRevision']) is int and
         value['attemptRevision'] == 2 and value['host'] == spec['current']['host'] == '172.30.30.' + profile['suffix'] and
         value['service'] == spec['selected']['service'] == profile['service'] and value['role'] == 'target' and
         value['sourceCommit'] == CONTINUATION_COMMIT and
         value['originalEnvironmentObservationPin'] == inputs['originalEnvironmentObservationPin'],
         'INITIAL_CONTINUATION_IDENTITY_INVALID')
    need(value['originalInputsPin']['file'] == profile['originalInputs'], 'ORIGINAL_INPUT_REVISION_REQUIRED')
    original_inputs = records.pinned(value['originalInputsPin'])
    removed = (profile['key'],) if preswitch else ('originalEnvironmentObservationPin', profile['key'])
    expected_inputs = {k: v for k, v in inputs.items() if k not in removed}
    expected_inputs['schemaVersion'] = 'MainProgramControlActivationInputs/' + profile['originalVersion']
    if preswitch: expected_inputs['initialFailureContinuationPin'] = None
    need(original_inputs == expected_inputs, 'CONTINUATION_ORIGINAL_INPUTS_CHANGED')
    failure_ref, attempt_ref = value['priorFailurePin'], value['priorAttemptPin']
    failure = private_document(private, failure_ref, profile['stem'] + '.private.json')
    attempt = private_document(private, attempt_ref, profile['stem'] + '.attempt.private.json')
    need(all(failure_ref[k] == profile['failurePin'][k] for k in ('bytes', 'sha256')) and
         failure.get('status') == 'FAILED' and failure.get('stage') == profile['stage'] and
         failure.get('errorType') == 'ValueError' and failure.get('errorCode') == profile['error'] and
         all(failure.get(k) is False for k in ('activationCompleted', 'backupDispatched', 'restoreDispatched',
             'businessMutationDispatched', 'controlApiQueriesPerformed', 'queryAuditWritesMayOccur')) and
         all(failure.get(k) == value[k] for k in ('host', 'service', 'sourceCommit')),
         'ORIGINAL_INITIAL_FAILURE_REQUIRED')
    original_path_pin = dict(path=str(records.task / value['originalInputsPin']['file']),
        bytes=value['originalInputsPin']['bytes'], sha256=value['originalInputsPin']['sha256'])
    need(set(attempt) == {'status', 'sourceCommit', 'host', 'role', 'scriptSha256', 'remoteDispatched', 'dispatchRequested', 'inputPins'} and
         attempt['status'] == 'PREPARED_NOT_ACTIVATED' and attempt['dispatchRequested'] is True and
         attempt['remoteDispatched'] is False and attempt['scriptSha256'] == profile['scriptSha256'] and
         all(attempt[k] == value[k] for k in ('host', 'role', 'sourceCommit')) and
         original_path_pin in attempt['inputPins'], 'ORIGINAL_ATTEMPT_BINDING_CHANGED')
    if preswitch:
        need(all(attempt_ref[k] == PRESWITCH_ATTEMPT_PIN[k] for k in ('bytes', 'sha256')) and
             all(failure.get(k) is True for k in ('actualImportsVerified', 'originalUnitPinsVerified', 'physicalLockVerified',
                 'completePreviousCustodyVerified', 'originalPathInventoryVerified')), 'ORIGINAL_PRESWITCH_CHECKPOINT_CHANGED')
    remote_ref = value['priorRemoteResultPin']; contract.remote_pin(remote_ref)
    need(remote_ref['path'] == spec['remoteAuditPath'] + '/result.private.json' and
         all(remote_ref[k] == failure_ref[k] for k in ('bytes', 'sha256')), 'ORIGINAL_REMOTE_FAILURE_CHANGED')
    need(value['readonlyObservationPin']['file'] == profile['observationFile'], 'INITIAL_OBSERVATION_REVISION_REQUIRED')
    observation = records.pinned(value['readonlyObservationPin'])
    extra = {'preservation'} if preswitch else set()
    need(set(observation) == common_keys | {'schemaVersion', 'status', 'observedAt', 'controller', 'oldReceiptPin',
         'auditPath', 'auditFiles', 'absentPaths', *OBSERVATION_FALSE_FIELDS} | extra and
         observation['schemaVersion'] == profile['observationSchema'] and observation['status'] == 'PASS' and
         all(observation[k] == value[k] for k in common_keys) and
         all(observation[k] is False for k in OBSERVATION_FALSE_FIELDS), 'INITIAL_OBSERVATION_BINDING_CHANGED')
    private_pins = [attempt_ref, failure_ref]
    audit_files = [remote_ref]
    if preswitch:
        before_ref, command_ref = value['priorRemoteBeforePin'], value['priorRemoteCommandPin']
        for ref in (before_ref, command_ref): contract.remote_pin(ref)
        need(before_ref['path'] == spec['remoteAuditPath'] + '/before.private.json' and
             command_ref['path'] == spec['remoteAuditPath'] + '/command-' + PRESWITCH_COMMAND_SHA256 + '.private.log' and
             all(command_ref[k] == PRESWITCH_COMMAND_PIN[k] for k in ('bytes', 'sha256')), 'PRESWITCH_AUDIT_PATH_CHANGED')
        before = private_document(private, value['priorBeforeSnapshotPin'], 'main-program-control-preswitch-before-58-target-899730d-r1.private.json')
        command_path = Path(private) / ('58-main-activation-command-' + PRESWITCH_COMMAND_SHA256 + '.private.log')
        actual_command_pin = file_pin(command_path)
        need(Path(value['priorCommandSnapshotPin']['path']).resolve() == command_path.resolve(strict=True) and
             all(actual_command_pin[k] == value['priorCommandSnapshotPin'][k] for k in ('bytes', 'sha256')), 'PRESWITCH_COMMAND_SNAPSHOT_CHANGED')
        need(command_path.read_bytes().decode('utf-8').splitlines()[-1] == 'AssertionError: TARGET_EPOCH_POLICY_CHANGED',
             'PRESWITCH_DIAGNOSTIC_CHANGED')
        need(all(value['priorBeforeSnapshotPin'][k] == before_ref[k] and value['priorCommandSnapshotPin'][k] == command_ref[k]
             for k in ('bytes', 'sha256')), 'PRESWITCH_REMOTE_COPY_CHANGED')
        need(set(before) == {'controllers', 'containers', 'fstab', 'mountinfoSha256', 'historyGuard'} and
             observation['preservation'] == dict(containersSha256=hashlib.sha256(canonical(before['containers'])).hexdigest(),
                 fstabPin=before['fstab'], mountinfoSha256=before['mountinfoSha256'],
                 controllersSha256=hashlib.sha256(canonical(before['controllers'])).hexdigest(),
                 historyGuardSha256=hashlib.sha256(canonical(before['historyGuard'])).hexdigest()), 'PRESWITCH_PRESERVATION_CHANGED')
        private_pins += [value['priorBeforeSnapshotPin'], value['priorCommandSnapshotPin']]
        audit_files = [before_ref, command_ref, remote_ref]
    rows = spec['environmentBaseline']['controllers']
    need(len(rows) == 1 and observation['controller'] == {k: v for k, v in rows[0].items() if k not in ENVIRONMENT_PRIVATE_FIELDS} and
         observation['oldReceiptPin'] == spec['oldReceiptPin'] and observation['auditPath'] == spec['remoteAuditPath'] and
         observation['auditFiles'] == audit_files and observation['absentPaths'] == [spec['dropinPath'], spec['archiveReceiptPath'],
         spec['oldReceiptPin']['path'] + '.main-899730d.pending'], 'INITIAL_NO_SWITCH_NOT_PROVEN')
    return dict(value, observation=observation, **{profile['key']: reference}, privatePins=private_pins,
        privateOutputFile=profile['stem'] + '-r2.private.json', attemptFile=profile['stem'] + '-r2.attempt.private.json',
        remoteAuditPath=spec['remoteAuditPath'] + '-r2')


def validate_initial_continuation(records, private, spec):
    reference = spec['inputs']['initialFailureContinuationPin']
    if reference is None: return None
    need(continuation_profile(reference)['suffix'] == '59', 'INITIAL_CONTINUATION_SCOPE_INVALID')
    return _validate_continuation(records, private, spec, reference)


def load_continuation_originals(records, private, reference, identity):
    """Pure immutable proof loader shared with publication; core may exist."""
    profile = continuation_profile(reference); suffix = profile['suffix']; value = records.pinned(reference)
    need(identity == dict(host='172.30.30.' + suffix, service=profile['service'], role='target', sourceCommit=CONTINUATION_COMMIT),
         'CONTINUATION_IDENTITY_CHANGED')
    need(value['originalInputsPin']['file'] == profile['originalInputs'], 'ORIGINAL_INPUT_REVISION_REQUIRED')
    original = records.pinned(value['originalInputsPin'])
    need(original['schemaVersion'] == 'MainProgramControlActivationInputs/' + profile['originalVersion'], 'ORIGINAL_INPUT_VERSION_CHANGED')
    inputs = dict(original, schemaVersion='MainProgramControlActivationInputs/' + profile['inputVersion'],
        originalEnvironmentObservationPin=value['originalEnvironmentObservationPin'], **{profile['key']: reference})
    if suffix == '58':
        need(inputs.pop('initialFailureContinuationPin') is None, 'ORIGINAL_INPUT_CONTINUATION_CHANGED')
    plan = records.pinned(original['planPin'])
    secret = private_document(private, plan['privatePlanPin'], 'main-program-configuration-plan-r4.private.json')
    need(plan['sourceCommit'] == secret['sourceCommit'] == CONTINUATION_COMMIT and
         [{k: row[k] for k in ('role', 'service', 'engine', 'controlPin', 'ownerPin')} for row in secret['controllers'][suffix]] ==
         plan['controllers'][suffix], 'CONTINUATION_PLAN_CHANGED')
    selected = secret['controllers'][suffix]
    need(len(selected) == 1 and selected[0]['role'] == 'target' and selected[0]['service'] == identity['service'], 'CONTINUATION_CONTROL_CHANGED')
    selected = selected[0]; current = copy.deepcopy(secret['currentSelections'][suffix])
    need(current['host'] == identity['host'] and len(current['controllers']) == 1, 'CONTINUATION_CONTROL_CHANGED')
    need(original['unitObservationPin']['file'] == 'main-program-control-units-' + suffix + '-r1.json' and
         original['engineStagedPin']['file'] == 'main-program-engine-staged-' + suffix + '-r4.json', 'CONTINUATION_ORIGINAL_REVISION_CHANGED')
    unit = records.pinned(original['unitObservationPin']); engine = records.pinned(original['engineStagedPin'])
    row = current['controllers'][0]
    matches = [r for r in engine['controls'] if r['service'] == row['service'] and r['pid'] == row['pid']]
    need(len(matches) == 1, 'CONTINUATION_ORIGINAL_PROCESS_CHANGED'); row['argvSha256'] = matches[0]['argvSha256']
    baseline = validate_environment_baseline(records, private, inputs, unit, current['controllers'])
    control = next(d['value'] for d in secret['documentsByHost'][suffix] if d['pin'] == selected['controlPin'])
    name, _ = make_dropin(selected['service'], selected['engine'], selected['controlPin'], control,
        unit['controllers'][0]['existingNames'], CONTINUATION_COMMIT, unit['requiredHistoryGuard'])
    root = PurePosixPath(selected['engine']).parent
    context = dict(inputs=inputs, current=current, selected=selected, oldReceiptPin=current['activeReceiptPin'],
        environmentBaseline=baseline, dropinPath=unit['controllers'][0]['directory'] + '/' + name,
        archiveReceiptPath=str(root / 'configuration/target-installation-before-main-899730d.json'),
        remoteAuditPath=str(root / 'configuration/main-activation-target-899730d'))
    result = _validate_continuation(records, private, context, reference)
    result['context'] = context
    result['privatePins'] += [plan['privatePlanPin'], baseline['privatePin']]
    return result


def prepare(task, private, inputs_file):
    records = contract.Records(task); inputs = records.read(inputs_file)
    fields = {'schemaVersion', 'sourceCommit', 'suffix', 'role', 'buildPin', 'planPin',
              'previousAutomaticSelectionPin', 'engineStagedPin', 'configurationStagedPin',
              'unitObservationPin', 'precedingActivationPins', 'sourceBaselinePin', 'outputFile'}
    version = inputs.get('schemaVersion')
    generation = version == 'MainProgramControlActivationInputs/v4'
    bundle = None; coverage = None
    if generation:
        validate_generation_inputs(inputs)
        fields = set(inputs)
    if version == 'MainProgramControlActivationInputs/v2':
        fields |= {'originalEnvironmentObservationPin', 'initialFailureContinuationPin'}
    elif version == 'MainProgramControlActivationInputs/v3':
        fields |= {'originalEnvironmentObservationPin', 'preSwitchContinuationPin'}
    need(set(inputs) == fields and version in ('MainProgramControlActivationInputs/v1', 'MainProgramControlActivationInputs/v2', 'MainProgramControlActivationInputs/v3', 'MainProgramControlActivationInputs/v4') and
         re.fullmatch('[0-9a-f]{40}', inputs['sourceCommit']), 'INPUTS_INVALID')
    suffix, role = inputs['suffix'], inputs['role']; prior = predecessors(suffix, role)
    contract.local_name(inputs['outputFile'])
    need(inputs['outputFile'] == 'main-program-control-activation-' + suffix + '-' + role + '-' + inputs['sourceCommit'][:7] +
         ('-' + inputs['revisionId'] if generation else '') + '.json',
         'OUTPUT_NAME_INVALID')
    if generation:
        from main_program_control_generation import load_control_generation
        from main_program_control_upgrade_plan import validate_control_upgrade_plan
        bundle = load_control_generation(task, private, inputs['previousControlGenerationPin'])
        coverage = validate_generation_coverage(records, inputs, bundle)
        build = coverage['build']; plan = records.pinned(inputs['planPin']); refs = bundle['targets']
        targets = {h: bundle['controllersByHost'][h][0] for h in ('58', '59')}
        private_name = 'main-program-configuration-plan-' + inputs['sourceCommit'][:7] + '-' + inputs['revisionId'] + '.private.json'
        secret = private_document(private, plan['privatePlanPin'], private_name)
        need(plan.get('predecessorGenerationPin') == inputs['previousControlGenerationPin'] and
             plan.get('previousPlanPin') == bundle['generation']['planPin'] and plan.get('buildPin') == inputs['buildPin'] and
             plan.get('revisionId') == inputs['revisionId'] and
             inputs['sourceBaselinePin'] == bundle['generation']['sourceBaselinePin'], 'GENERATION_PLAN_BINDING_CHANGED')
        material = lambda ref: dict(pin=ref, raw=(records.task / ref['file']).read_bytes())
        need(plan['packageDeltaPin'] in coverage['coverage']['actualPackageEvidencePins'], 'GENERATION_PLAN_DELTA_CHANGED')
        validate_control_upgrade_plan(plan, secret, source_commit=inputs['sourceCommit'], revision_id=inputs['revisionId'],
            build_document=material(inputs['buildPin']), package_delta_document=material(plan['packageDeltaPin']),
            package_files=coverage['packageFiles'], previous_package_files=coverage['previousPackageFiles'], predecessor=bundle,
            private_plan_path=plan['privatePlanPin']['path'], observed_at=plan['observedAt'])
    else:
        targets = contract._previous(records, inputs['previousAutomaticSelectionPin'])
        refs = {'57': 'intruoyi-main-57-safe-restore-20261105-v2', **{h: r['targetConfigRef'] for h, r in targets.items()}}
        build = contract._build(records, inputs); plan = contract._plan(records, inputs, refs)
        validate_coverage(records, build)
        secret = private_document(private, plan['privatePlanPin'], 'main-program-configuration-plan-r4.private.json')
    need(plan.get('sourceRefs') == list(SOURCES) and plan.get('sourceArchiveProtectionCount') == 9,
         'SOURCE_VIEW_PLAN_REQUIRED')
    need(secret['sourceCommit'] == inputs['sourceCommit'] and secret['status'] == plan['status'] and secret['build'] == build,
         'PRIVATE_PLAN_GENERATION_CHANGED')
    for h in ('57', '58', '59'):
        need([{k: r[k] for k in ('role', 'service', 'engine', 'controlPin', 'ownerPin')}
              for r in secret['controllers'][h]] == plan['controllers'][h], 'PRIVATE_PLAN_CONTROLLERS_CHANGED')
        selected = secret['currentSelections'][h]
        need(selected['currentControlGenerationPin' if generation else 'currentInstallationSelectionPin'] ==
             inputs['previousControlGenerationPin' if generation else 'previousAutomaticSelectionPin'], 'ORIGINAL_SELECTION_CHANGED')
        for item in selected['localInstallationPins']:
            path = Path(item['path'])
            need(path.resolve().parent in ({Path(task).resolve(), Path(private).resolve()} if generation else {Path(task).resolve()}),
                 'ORIGINAL_EVIDENCE_SCOPE')
            verify_local_pin(path, item)
    def fixed(name, reference):
        need(reference['file'] == name, 'INPUT_REVISION_REQUIRED')
        return records.pinned(reference)
    stage_revision = inputs['sourceCommit'][:7] + '-' + inputs['revisionId'] if generation else 'r4'
    unit_revision = stage_revision if generation else 'r1'
    engine = fixed('main-program-engine-staged-' + suffix + '-' + stage_revision + '.json', inputs['engineStagedPin'])
    configuration = fixed('main-program-configuration-staged-' + suffix + '-' + stage_revision + '.json', inputs['configurationStagedPin'])
    if generation: validate_generation_staging(inputs, plan, build, engine, configuration)
    else: validate_staging(plan, build, suffix, engine, configuration)
    unit = fixed('main-program-control-units-' + suffix + '-' + unit_revision + '.json', inputs['unitObservationPin'])
    unit_private = private_document(private, unit['privateSnapshotPin'], 'main-program-control-units-' + suffix + '-' + unit_revision + '.private.json')
    need(unit['schemaVersion'] == 'MainControlUnitObservation/v1' and unit['status'] == 'PASS' and
         unit['host'] == '172.30.30.' + suffix and unit['historyGuardEnabledAndActive'] is True and
         unit['originalWorkingDirectoriesHaveNoWorker'] is True, 'UNIT_OBSERVATION_REQUIRED')
    if generation:
        need(all(unit.get(k) == inputs[k] for k in ('sourceCommit', 'revisionId', 'previousControlGenerationPin')) and
             all(unit.get(k) is False for k in OBSERVATION_FALSE_FIELDS), 'GENERATION_UNIT_BINDING_CHANGED')
    need({k: v for k, v in unit_private.items() if k not in ('controllers', 'historyGuardProperties')} ==
         {k: v for k, v in unit.items() if k not in ('controllers', 'privateSnapshotPin')} and
         [{k: v for k, v in r.items() if k != 'properties'} for r in unit_private['controllers']] == unit['controllers'],
         'UNIT_PRIVATE_PROJECTION_CHANGED')
    current = copy.deepcopy(secret['currentSelections'][suffix]); preceding = []
    need(len(inputs['precedingActivationPins']) == len(prior), 'ACTIVATION_ORDER_REQUIRED')
    for (host, previous_role), ref in zip(prior, inputs['precedingActivationPins']):
        if generation:
            need(ref['file'] == 'main-program-control-activation-' + host + '-' + previous_role + '-' +
                 inputs['sourceCommit'][:7] + '-' + inputs['revisionId'] + '.json', 'GENERATION_ACTIVATION_ORDER_CHANGED')
        planned = next(r for r in plan['controllers'][host] if r['role'] == previous_role)
        core = contract._activation(records, ref, inputs, build, planned, host, refs[host], targets.get(host))
        preceding.append(core)
        if host == suffix:
            need(suffix == '57' and role == 'source' and previous_role == 'target', 'PEER_REPLACEMENT_INVALID')
            current['controllers'][-1] = {k: core[k] for k in contract.CONTROLLER_KEYS}
            current['controllers'][-1]['dropinPin'] = core['dropinPin']
    old_index = 0 if role == 'source' or suffix != '57' else 1
    selected = secret['controllers'][suffix][old_index]; old = current['controllers'][old_index]
    need(selected['previousControlPin'] == old['controlConfigurationPin'] and
         selected['previousOwnerPin'] == old['ownerConfigurationPin'] and selected['service'] == old['service'],
         'PREVIOUS_CONFIGURATION_CHANGED')
    for row, observed in zip(secret['currentSelections'][suffix]['controllers'], unit['controllers']):
        need(row['service'] == observed['service'] and row['pid'] == observed['pid'], 'OBSERVED_CONTROL_CHANGED')
    for row in current['controllers']:
        if suffix == '57' and role == 'source' and row['service'] == current['controllers'][-1]['service']:
            continue
        matching = [r for r in engine['controls'] if r['service'] == row['service'] and r['pid'] == row['pid']]
        need(len(matching) == 1 and contract.sha(matching[0].get('argvSha256')), 'STAGED_ARGV_PROOF_REQUIRED')
        row['argvSha256'] = matching[0]['argvSha256']
    environment_baseline = None
    if version in ('MainProgramControlActivationInputs/v2', 'MainProgramControlActivationInputs/v3', 'MainProgramControlActivationInputs/v4'):
        originals = copy.deepcopy(secret['currentSelections'][suffix]['controllers'])
        for row in originals:
            matching = [r for r in engine['controls'] if r['service'] == row['service'] and r['pid'] == row['pid']]
            need(len(matching) == 1 and contract.sha(matching[0].get('argvSha256')), 'BASELINE_ARGV_PROOF_REQUIRED')
            row['argvSha256'] = matching[0]['argvSha256']
        environment_baseline = validate_environment_baseline(records, private, inputs, unit, originals)
        for row in current['controllers']:
            original = next(r for r in environment_baseline['controllers'] if r['service'] == row['service'])
            row['environmentMode'] = 'ORIGINAL_BASELINE' if row['pid'] == original['pid'] else 'CONFIG_EXACT'
    docs = secret['documentsByHost'][suffix]
    need([d['pin'] for d in docs] == configuration['configurationStaging']['documents'], 'STAGED_DOCUMENTS_CHANGED')
    for document in docs:
        raw = canonical(document['value']); ref = document['pin']
        contract.remote_pin(ref)
        need(len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256'], 'DOCUMENT_BYTES_CHANGED')
    control = next(d['value'] for d in docs if d['pin'] == selected['controlPin'])
    old_unit = unit['controllers'][old_index]
    dropin_name, dropin_raw = make_dropin(selected['service'], selected['engine'], selected['controlPin'],
        control, old_unit['existingNames'], inputs['sourceCommit'], unit['requiredHistoryGuard'])
    baseline = records.pinned(inputs['sourceBaselinePin'])
    need(inputs['sourceBaselinePin']['file'] == 'automatic-i2-audit.json' and baseline['status'] == 'PASS' and
         baseline['sourceConfigRef'] == SOURCES[0] and baseline['pointType'] == 'INCREMENTAL' and
         baseline['state'] == 'SUCCEEDED' and baseline['actualExitCode'] == 0 and baseline['sourceRestored'] is True and
         len(baseline['chain']) == 3 and baseline['chain'][-1]['operationId'] == baseline['operationId'],
         'ORIGINAL_I2_BASELINE_REQUIRED')
    source_expected = dict(baseFullRef=baseline['chain'][0]['operationId'], parentChainRef=baseline['operationId'],
                           generationId=baseline['generationId'])
    root = PurePosixPath(selected['engine']).parent
    old_receipt = current['activeReceiptPin'] if suffix != '57' else None
    inventory = None
    if suffix != '57':
        inventory = records.read('protected-history-' + suffix + '.json')
        custody = bundle['custodyByHost'][suffix] if generation else targets[suffix]['extendedCustody']
        need(inventory['status'] == 'PASS' and inventory['host'] == '172.30.30.' + suffix and
             len(inventory['evidencePins']) == inventory['protectedFiles'] and
             len({p['path'] for p in inventory['evidencePins']}) == len(inventory['evidencePins']),
             'HISTORICAL_INVENTORY_REQUIRED')
        active = [p for p in inventory['evidencePins'] if p['path'] == old_receipt['path']]
        legacy = custody['legacyCustody'] if generation else custody
        need(active == [legacy['originalActiveReceiptPin']], 'ORIGINAL_ACTIVE_RECEIPT_NOT_ACCOUNTED')
        need((custody['selectedCurrentReceiptPin'] if generation else custody['steps'][-1]['currentReceiptPin']) == old_receipt,
             'CUSTODY_CURRENT_RECEIPT_CHANGED')
    helper_pins = [file_pin(Path(__file__).resolve()), file_pin(TASK / 'installation_history_custody.py'),
                   file_pin(TASK / 'main_program_installation_selection.py')]
    spec = dict(inputs=inputs, selected=selected, old=old, current=current, unit=unit_private,
        build=build, targetConfigRef=refs[suffix], documents=[d['pin'] for d in docs],
        protections=secret['sourceArchiveProtections'][suffix],
        historyPins=[r['pin'] for r in secret['originalMetadata'] if r['originalHost'] == current['host']],
        sourceExpected=source_expected, sourceEvidencePins=[baseline[k] for k in ('pointPin', 'manifestPin', 'epochBindingPin')],
        oldReceiptPin=old_receipt, previousCustody=(bundle['custodyByHost'][suffix] if generation else targets[suffix].get('extendedCustody')) if suffix != '57' else None,
        originalInventory=inventory, helperPins=helper_pins, environmentBaseline=environment_baseline,
        archiveReceiptPath=str(root / 'configuration' / ('target-installation-before-main-' + inputs['sourceCommit'][:7] + '.json')),
        dropinPath=old_unit['directory'] + '/' + dropin_name, dropinText=dropin_raw.decode('utf-8'),
        remoteAuditPath=str(root / 'configuration' / ('main-activation-' + role + '-' + inputs['sourceCommit'][:7])),
        inputPins=records.path_pins(), privatePlanPin=plan['privatePlanPin'], privateUnitPin=unit['privateSnapshotPin'])
    spec['immutablePrivatePins'] = [environment_baseline['privatePin']] if environment_baseline is not None else []
    if generation:
        spec['activationInputsPin'] = records.references[inputs_file]
        spec['helperPins'] += [file_pin(TASK / name) for name in ('main_program_control_generation.py', 'main_program_control_upgrade_plan.py')]
        spec['immutablePrivatePins'] += bundle['inputPins'] + coverage['physicalPins']
        spec['remoteAuditPath'] += '-' + inputs['revisionId']
        if suffix == '57' and role == 'source':
            owner = next(d['value'] for d in docs if d['pin'] == selected['ownerPin'])
            old_owner = next(d['value'] for d in bundle['privatePlan']['documentsByHost']['57']
                             if d['pin'] == old['ownerConfigurationPin'])
            root_audit = records.read('automatic-full-audit.json') if coverage['coverage'].get('schemaVersion') == 'MainProgramControlCoverage/v2' else None
            transition = make_source_policy_transition(inputs, coverage['coverage'], baseline, old_owner, owner,
                root_audit=root_audit, root_audit_pin=records.references.get('automatic-full-audit.json'))
            if transition is not None:
                spec['sourcePolicyTransition'] = transition
    spec['continuation'] = validate_initial_continuation(records, private, spec) if version.endswith('/v2') else None
    if version.endswith('/v3'):
        need(suffix == '58' and role == 'target', 'PRESWITCH_CONTINUATION_SCOPE_INVALID')
        spec['continuation'] = load_continuation_originals(records, private, inputs['preSwitchContinuationPin'],
            dict(host=current['host'], service=selected['service'], role=role, sourceCommit=inputs['sourceCommit']))
        expected = spec['continuation']['context']
        need(all(expected[k] == spec[k] for k in ('inputs', 'selected', 'oldReceiptPin', 'environmentBaseline',
             'dropinPath', 'archiveReceiptPath', 'remoteAuditPath')), 'CONTINUATION_PREPARED_CONTEXT_CHANGED')
    if spec['continuation'] is not None:
        continuation = spec['continuation']
        spec['remoteAuditPath'] = continuation['remoteAuditPath']
        spec['immutablePrivatePins'] += continuation['privatePins']
        need(not any(p.exists() or p.is_symlink() for p in (Path(task) / inputs['outputFile'],
             Path(private) / continuation['attemptFile'], Path(private) / continuation['privateOutputFile'])),
             'ACTIVATION_ATTEMPT_EXISTS')
    spec['inputPins'] = records.path_pins()
    payload = 'SPEC=' + repr(spec) + '\nCANDIDATE_GATE=' + repr(CANDIDATE_GATE) + '\nSOURCE_IDLE=' + repr(SOURCE_IDLE) + '\n' + ORIGINAL_CUSTODY_PROGRAM + '\n' + REMOTE_SCRIPT
    compile(payload, '<main-program-control-activation>', 'exec')
    return spec, payload


def project_core(spec, observed):
    need(observed.get('status') == 'PASS' and observed.get('activationCompleted') is True,
         'ACTUAL_ACTIVATION_REQUIRED')
    if spec['inputs'].get('schemaVersion') == 'MainProgramControlActivationInputs/v4':
        need(observed.get('activationInputsPin') == spec['activationInputsPin'] and
             all(observed.get(key) == spec['inputs'][key] for key in ('coveragePin', 'previousControlGenerationPin', 'revisionId')),
             'GENERATION_EVIDENCE_CHANGED')
        if spec['inputs']['suffix'] != '57':
            custody = observed.get('currentLayeredCustodyObservation', {})
            need(custody.get('status') == 'PASS' and custody.get('originalInventoryVerified') is True and
                 custody.get('selectedCurrentReceiptPin') == observed.get('currentReceiptPin'),
                 'GENERATION_FINAL_CUSTODY_REQUIRED')
    continuation = spec.get('continuation')
    if continuation:
        key = continuation_reference_key(continuation)
        flag = 'preSwitchFailureRevalidated' if key == 'preSwitchContinuationPin' else 'initialFailureRevalidated'
        need(type(observed.get('attemptRevision')) is int and observed['attemptRevision'] == 2 and
             observed.get(flag) is True and all(observed.get(k) == continuation[k]
             for k in (key, 'priorAttemptPin', 'priorFailurePin', 'priorRemoteResultPin')),
             'INITIAL_CONTINUATION_NOT_REVALIDATED')
    flags = ('actualImportsVerified', 'originalUnitPinsVerified', 'physicalLockVerified', 'epochVerified',
             'historyGuardVerified', 'apiVerified', 'argvVerified', 'environmentVerified', 'limitVerified',
             'noWorkersVerified', 'businessContainersUnchanged', 'fstabAndMountsUnchanged',
             'previousControlFilesPreserved', 'originalTargetObjectsUnchanged')
    need(all(observed.get(k) is True for k in flags), 'ACTIVATION_CHECKPOINT_REQUIRED')
    row, inputs, build = spec['selected'], spec['inputs'], spec['build']
    need(observed.get('sourceCommit') == inputs['sourceCommit'], 'OBSERVED_GENERATION_CHANGED')
    if inputs['role'] == 'target':
        need(observed.get('directlyAdmittedSources') == list(SOURCES) and observed.get('archiveViewsPreflightVerified') is True,
             'ACTUAL_THREE_SOURCE_ADMISSION_REQUIRED')
    else:
        need(observed.get('sourceCaptureVerified') is True and observed.get('sourceBaselineVerified') is True,
             'ACTUAL_SOURCE_BINDING_REQUIRED')
        if spec.get('sourcePolicyTransition') is not None:
            validate_source_policy_transition(spec['sourcePolicyTransition'], observed)
    need(observed.get('host') == '172.30.30.' + inputs['suffix'] and observed.get('service') == row['service'] and
         observed.get('backupDispatched') is False and observed.get('restoreDispatched') is False and
         type(observed.get('pid')) is int and observed['pid'] > 1 and observed['pid'] != spec['old']['pid'],
         'ACTUAL_CONTROL_IDENTITY_REQUIRED')
    value = dict(schemaVersion='MainProgramControlActivation/v1', status='PASS', role=inputs['role'],
        host=observed['host'], sourceCommit=inputs['sourceCommit'], buildPin=inputs['buildPin'], planPin=inputs['planPin'],
        service=row['service'], engine=row['engine'], pid=observed['pid'], controlConfigurationPin=row['controlPin'],
        ownerConfigurationPin=row['ownerPin'], dropinPin=observed['dropinPin'],
        fileCount=build['fileCount'], fileManifestSha256=build['fileManifestSha256'], packageSha256=build['packageSha256'],
        targetConfigRef=None if inputs['role'] == 'source' else spec['targetConfigRef'],
        **{k: True for k in contract.TRUE_FLAGS}, **{k: False for k in contract.FALSE_FLAGS})
    if inputs['suffix'] == '57': value['activeReceiptPin'] = None
    else:
        need(observed.get('receiptRotated') is True, 'RECEIPT_ROTATION_NOT_PROVEN')
        need(observed.get('completePreviousCustodyVerified') is True and observed.get('originalPathInventoryVerified') is True,
             'ORIGINAL_CUSTODY_AND_PATH_INVENTORY_REQUIRED')
        value.update(previousReceiptPin=observed['previousReceiptPin'], currentReceiptPin=observed['currentReceiptPin'])
    class Projection:
        def pinned(self, ref): return value
    contract._activation(Projection(), {}, inputs, build, row, inputs['suffix'], value['targetConfigRef'],
                         dict(currentReceiptPin=spec['oldReceiptPin']))
    return value


def run_request(task, private, inputs_file, *, activate=False, transport=None):
    spec, payload = prepare(task, private, inputs_file)
    return dispatch_prepared(task, private, spec, payload, activate=activate, transport=transport)


def dispatch_prepared(task, private, spec, payload, *, activate=False, transport=None):
    """A single dispatch boundary. The CLI reaches it only after full prepare."""
    prepared = dict(status='PREPARED_NOT_ACTIVATED', sourceCommit=spec['inputs']['sourceCommit'],
                    host=spec['current']['host'], role=spec['inputs']['role'],
                    scriptSha256=hashlib.sha256(payload.encode('utf-8')).hexdigest(), remoteDispatched=False)
    if not activate: return prepared
    output = Path(task) / spec['inputs']['outputFile']
    continuation = spec.get('continuation')
    private_output = Path(private) / (continuation['privateOutputFile'] if continuation else output.name.replace('.json', '.private.json'))
    attempt = Path(private) / (continuation['attemptFile'] if continuation else output.name.replace('.json', '.attempt.private.json'))
    need(not any(p.exists() or p.is_symlink() for p in (output, private_output, attempt)), 'ACTIVATION_ATTEMPT_EXISTS')
    attempt_value = dict(prepared, inputPins=spec['inputPins'], dispatchRequested=True)
    if continuation:
        key = continuation_reference_key(continuation)
        attempt_value.update(attemptRevision=2, **{key: continuation[key]})
    exclusive_bytes(attempt, canonical(attempt_value))
    if transport is None:
        from common import remote
        transport = remote
    observed = transport(spec['current']['host'], payload, timeout=600)
    exclusive_bytes(private_output, canonical(observed))
    need(observed.get('status') == 'PASS', 'REMOTE_ACTIVATION_FAILED_CHECK_PRIVATE_REPORT')
    for ref in spec['inputPins']: verify_local_pin(Path(ref['path']), ref)
    for ref in spec['helperPins']: need(file_pin(Path(ref['path'])) == ref, 'HELPER_CHANGED_DURING_ACTIVATION')
    checked_local(Path(spec['privatePlanPin']['path']), spec['privatePlanPin'])
    checked_local(Path(spec['privateUnitPin']['path']), spec['privateUnitPin'])
    for ref in spec.get('immutablePrivatePins', []):
        actual = file_pin(Path(ref['path']))
        need(all(actual[k] == ref[k] for k in ('bytes', 'sha256')), 'PRIVATE_ORIGINAL_CHANGED_DURING_ACTIVATION')
    core = project_core(spec, observed)
    exclusive_bytes(output, canonical(core))
    return dict(status='PASS', report=output.name, pid=core['pid'], role=core['role'], host=core['host'])


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument('--inputs', required=True)
    value.add_argument('--activate', action='store_true')
    value.add_argument('--task', type=Path, default=TASK)
    value.add_argument('--private', type=Path, default=PRIVATE)
    return value


# Both subprocess gates load only the exact candidate package on the host.
CANDIDATE_GATE = r'''
import hashlib,json,pathlib,re,sys
def need(value,code):
 if not value:raise ValueError(code)
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
''' + SOURCE_POLICY_PROGRAM + r'''
from types import SimpleNamespace
from recovery_control_smallapp_native import Native
from recovery_control_target_availability import available
from recovery_main_target import archive_view
from recovery_program_targets import resolve_configuration
from recovery_program_generation import resolve_capture
from recovery_backup_epoch import read_current
def source_policy_admission(native,owner,old,transition,epoch,engine):
 from repository_records import incremental_chain_policy,incremental_chain_admission
 from recovery_control_incremental_plan import validate_epoch
 source_policy_scope(transition)
 for name in ('repository_records','recovery_control_incremental_plan','recovery_control_smallapp_native'):
  module=sys.modules[name]
  need(pathlib.Path(module.__file__).resolve().is_relative_to(pathlib.Path(engine).resolve()),'SOURCE_POLICY_IMPORTED_OLD_MODULE')
 policy=incremental_chain_policy(owner)
 need(policy==incremental_chain_policy(old)==transition['policy'],'SOURCE_POLICY_OWNER_LIMITS_CHANGED')
 source=transition['sourceConfigRef'];config=native.configuration()
 need(source in config['sourceConfigurations'] and native.document(config['sourceConfigurations'][source])==owner,
  'SOURCE_POLICY_OWNER_BINDING_CHANGED')
 need(native.source_epoch(config,source)==epoch and epoch.get('state')=='READY','SOURCE_POLICY_EPOCH_CHANGED')
 pins=[];evidence=[];manifest=None
 for index,row in enumerate(transition['chain']):
  point=native.document(row['pointPin']);bound=native.document(row['epochBindingPin'])
  need(point.get('schemaVersion')=='RepositoryPoint/v1' and point.get('backupId')==row['operationId'] and
   point.get('pointType')==row['pointType'] and point.get('generationId')==transition['sourceExpected']['generationId'] and
   point.get('parentPointPins')==pins,'SOURCE_POLICY_ORIGINAL_POINT_CHANGED')
  need(validate_epoch(epoch,bound,source_ref=source,reference=row['operationId'],point_pin=row['pointPin'],
   result_pin=bound['resultPin']) is None,'SOURCE_POLICY_POINT_EPOCH_CHANGED')
  evidence.extend([row['pointPin'],row['epochBindingPin']]);pins.append(row['pointPin'])
  if index==0:
   manifest_pin=point['manifestPin'];manifest=native.document(manifest_pin);evidence.append(manifest_pin)
   need(manifest_pin==transition['rootManifestPin'],'SOURCE_POLICY_ROOT_MANIFEST_CHANGED')
   need(manifest.get('schemaVersion')=='RepositoryManifest/v1' and manifest.get('backupId')==row['operationId'] and
    manifest.get('generationId')==row['operationId'] and manifest.get('pointType')=='FULL' and manifest.get('parentPointPins')==[],
    'SOURCE_POLICY_ROOT_MANIFEST_CHANGED')
 reason=incremental_chain_admission(policy,manifest['createdAt'],len(pins))
 need(reason in (None,'INCREMENTAL_CHAIN_AGE_EXPIRED'),'SOURCE_POLICY_REASON_NOT_APPROVED')
 plan=native.incremental_plan(source)
 proof=dict(transition=transition,rootManifestPin=manifest_pin,rootCreatedAt=manifest['createdAt'],reasonCode=reason,plan=plan)
 validate_source_policy_admission(transition,proof)
 # The planner preserves its own deadline/integrity checks. The installer also
 # closes this observation over its original pins, epoch and real policy clock.
 for ref in evidence:native.document(ref)
 need(native.source_epoch(config,source)==epoch,'SOURCE_POLICY_EPOCH_CHANGED')
 need(incremental_chain_admission(policy,manifest['createdAt'],len(pins))==reason,'SOURCE_POLICY_CHANGED_DURING_GATE')
 return proof
def validate_target_epoch_admission(owner,old,target_ref,resolved,binding,read_document,read_epoch):
 assert owner['targets']==old['targets'] and resolved['targets']==old['targets'],'ORIGINAL_TARGET_OBJECT_CHANGED'
 policy=owner.get('targetBackupEpochPolicies',{}).get(target_ref)
 previous=old.get('targetBackupEpochPolicies',{}).get(target_ref)
 if previous is not None:assert policy==previous,'TARGET_EPOCH_POLICY_CHANGED'
 program=owner.get('targetProgramPolicies',{}).get(target_ref)
 assert isinstance(policy,dict) and isinstance(program,dict) and program.get('backupEpochPolicy')==policy,'TARGET_PROGRAM_EPOCH_BINDING_REQUIRED'
 # The public resolver has already validated the complete journal, initial
 # READY event, baseline identity and all generation proofs. Reuse that binding.
 assert isinstance(binding,dict) and binding.get('policy')==program and all(program[k] in binding.get('evidencePins',[]) for k in
  ('baselineTargetPin','initialEpochPin')),'TARGET_PROGRAM_PROOF_REQUIRED'
 baseline=read_document(program['baselineTargetPin'])
 assert baseline==old['targets'][target_ref],'TARGET_PROGRAM_BASELINE_CHANGED'
 assert baseline['replacement']['databaseUuid']==policy['databaseUuid'] and baseline['replacement']['lockPath']==policy['sourceLockPath'],'TARGET_PROGRAM_PHYSICAL_SCOPE_CHANGED'
 epoch=read_epoch(policy);assert epoch['state']=='READY','TARGET_EPOCH_NOT_READY'
 return policy,epoch
value=json.loads(sys.argv[1]);native=Native(value['controlPin']);control=native.configuration()
owner=native.document(value['ownerPin']);old=native.document(value['oldOwnerPin'])
assert control['workingDirectory']==str(pathlib.Path(value['engine']).parent),'CANDIDATE_WORKING_DIRECTORY_CHANGED'
for name in ('recovery_control_smallapp_native','recovery_control_target_availability','recovery_main_target','recovery_program_generation'):
 module=sys.modules[name];assert pathlib.Path(module.__file__).resolve().is_relative_to(pathlib.Path(value['engine'])),'IMPORTED_OLD_MODULE'
result=dict(actualConfigurationReadPassed=True)
if value['role']=='target':
 target_ref=value['targetConfigRef'];resolved,binding=resolve_configuration(owner,target_ref)
 policy,epoch=validate_target_epoch_admission(owner,old,target_ref,resolved,binding,native.document,read_current)
 results=[]
 for source_ref in value['sources']:
  assert available(native,value['ownerPin'],target_ref,source_ref,observe_main=True),'DIRECT_SOURCE_NOT_AVAILABLE'
  expected=value['protections'][source_ref]
  assert owner['sources'][source_ref]['archiveMountProtection']==expected,'SOURCE_ARCHIVE_PROTECTION_CHANGED'
  def refuse(*args,**kwargs):raise AssertionError('PREFLIGHT_MUTATION_ATTEMPTED')
  probe=SimpleNamespace(config=owner['targets'][target_ref],source=owner['sources'][source_ref],
    original=dict(operationId='main-activation-preflight-'+value['commit'][:7]),command=refuse)
  protection=archive_view(probe)
  assert protection is not None and protection.configuration==expected,'ARCHIVE_FACTORY_CHANGED'
  assert not protection.journal.exists(),'PREFLIGHT_JOURNAL_ALREADY_EXISTS'
  protection.preflight()
  assert not protection.journal.exists(),'PREFLIGHT_JOURNAL_WRITTEN'
  results.append(source_ref)
 result.update(directlyAdmittedSources=results,archiveViewsPreflightVerified=True,epochPolicy=policy,
  epoch=read_current(policy))
else:
 source_ref=value['sources'][0];policy=control['sourceProgramPolicies'][source_ref]
 capture_pin=policy['captureConfigurationPins'][source_ref]
 resolved,_=resolve_capture(policy,source_ref,capture_pin)
 assert resolved==capture_pin and owner['sources'][source_ref]['configurationPath']==capture_pin['path'],'CAPTURE_BINDING_CHANGED'
 capture=native.document(capture_pin);epoch_policy=control['sourceEpochPolicies'][source_ref]
 assert capture['source']['sourceIdentity']==epoch_policy['sourceIdentity'] and capture['source']['databaseUuid']==epoch_policy['databaseUuid'] and capture['sourceLockPath']==epoch_policy['sourceLockPath'],'PHYSICAL_CAPTURE_CHANGED'
 epoch=read_current(epoch_policy);assert epoch['state']=='READY','SOURCE_EPOCH_NOT_READY'
 result.update(sourceCaptureVerified=True,capturePin=capture_pin,epochPolicy=epoch_policy,epoch=epoch)
 if value.get('sourcePolicyTransition') is not None:
  assert value['sourcePolicyTransition']['sourceConfigRef']==source_ref,'SOURCE_POLICY_SOURCE_CHANGED'
  result['sourcePolicyAdmission']=source_policy_admission(native,owner,old,value['sourcePolicyTransition'],epoch,value['engine'])
print(json.dumps(result))
'''

SOURCE_IDLE = r'''
import json,sys,time
from recovery_control_smallapp_native import Native
from recovery_control_smallapp import Ledger
pin,source=json.loads(sys.argv[1]);native=Native(pin);control=native.configuration();deadline=time.monotonic()+90
def guard():
 if time.monotonic()>=deadline:raise ValueError('SOURCE_IDLE_QUERY_BUDGET_EXCEEDED')
Ledger(control['ledgerRoot'],native).require_source_idle(source,guard=guard)
print(json.dumps(dict(sourceIdle=True)))
'''

REMOTE_SCRIPT = r'''
import datetime,errno,fcntl,hashlib,json,os,pathlib,re,shlex,stat,subprocess,sys,time,urllib.request,urllib.error
def need(value,code):
 if not value:raise ValueError(code)
''' + ENVIRONMENT_PROGRAM + SOURCE_POLICY_PROGRAM + r'''
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def pin(path):
 p=pathlib.Path(path);before=p.lstat();need(p.resolve(strict=True)==p and stat.S_ISREG(before.st_mode) and before.st_nlink==1,'REMOTE_FILE_ALIAS')
 raw=p.read_bytes();after=p.lstat();need((before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'REMOTE_FILE_CHANGED')
 return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(ref):
 need(pin(ref['path'])==ref,'REMOTE_PIN_CHANGED');return json.loads(pathlib.Path(ref['path']).read_bytes())
def create(path,raw,mode=0o600):
 p=pathlib.Path(path);need(p.parent.resolve(strict=True)==p.parent,'REMOTE_OUTPUT_ALIAS')
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
 with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
 need(p.read_bytes()==raw,'REMOTE_WRITE_READBACK_FAILED');return pin(p)
def run(args,timeout=90,env=None):
 result=subprocess.run(args,capture_output=True,timeout=timeout,env=env)
 if result.returncode:
  name='command-'+hashlib.sha256(result.stdout+result.stderr).hexdigest()+'.private.log'
  if audit.exists() and not (audit/name).exists():create(audit/name,result.stdout+result.stderr)
  raise ValueError('ACTIVATION_COMMAND_FAILED_'+str(result.returncode))
 return result.stdout
def properties(service):
 raw=run(['systemctl','show',service,'-p','MainPID','-p','FragmentPath','-p','DropInPaths','-p','Requires','-p','After','-p','LimitNOFILE','-p','ActiveState','-p','SubState'])
 return dict(line.split('=',1) for line in raw.decode().splitlines() if '=' in line)
def verify_process(row):
 control=read(row['controlConfigurationPin']);read(row['ownerConfigurationPin']);props=properties(row['service'])
 need(props['MainPID']==str(row['pid']) and props['ActiveState']=='active' and props['LimitNOFILE']=='65536','CONTROL_PROCESS_CHANGED')
 proc=pathlib.Path('/proc')/str(row['pid']);args=(proc/'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
 expected=[control['pythonPin']['path'].encode(),b'-B',(row['engine']+'/control_entry.py').encode(),b'serve',b'--config-pin']
 need(len(args)==6 and args[:-1]==expected and json.loads(args[-1])==row['controlConfigurationPin'],'CONTROL_ARGV_CHANGED')
 if 'argvSha256' in row:need(hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()==row['argvSha256'],'ORIGINAL_ARGV_HASH_CHANGED')
 else:need(args[-1]==canonical(row['controlConfigurationPin']),'NEW_ARGV_ENCODING_CHANGED')
 if 'dropinPin' in row:need(pin(row['dropinPin']['path'])==row['dropinPin'],'PEER_DROPIN_CHANGED')
 original=next(r for r in SPEC['unit']['controllers'] if r['service']==row['service'])
 expected_dropins=[r['path'] for r in original['dropinPins']]
 if 'dropinPin' in row and row['dropinPin']['path'] not in expected_dropins:expected_dropins.append(row['dropinPin']['path'])
 need(props['FragmentPath']==original['unitPin']['path'] and props['DropInPaths'].split()==expected_dropins,'LOADED_UNIT_OR_DROPINS_CHANGED')
 need((proc/'exe').resolve()==pathlib.Path(control['pythonPin']['path']).resolve(),'CONTROL_EXECUTABLE_CHANGED')
 raw=(proc/'environ').read_bytes();baseline=None;systemd_raw=None
 registered=SPEC.get('environmentBaseline')
 if registered is not None:
  matches=[r for r in registered['controllers'] if r['service']==row['service']]
  need(len(matches)==1,'ENVIRONMENT_BASELINE_MISSING');candidate=matches[0]
  mode='ORIGINAL_BASELINE' if row['pid']==candidate['pid'] else 'CONFIG_EXACT'
  need(row.get('environmentMode')==mode,'ENVIRONMENT_MODE_CHANGED')
  if mode=='ORIGINAL_BASELINE':
   need(all(row[k]==candidate[k] for k in ('service','pid','engine','controlConfigurationPin','ownerConfigurationPin','argvSha256')),'ENVIRONMENT_ORIGINAL_IDENTITY_CHANGED')
   need(pin(candidate['unitPin']['path'])==candidate['unitPin'] and all(pin(p['path'])==p for p in candidate['dropinPins']),'ENVIRONMENT_UNIT_CHANGED')
   baseline=candidate;systemd_raw=run(['systemctl','show',row['service'],'-p','Environment']).decode('utf-8')
 environment_proof=verify_environment_values(control['environment'],raw,baseline=baseline,systemd_raw=systemd_raw)
 need(any(line.startswith('Max open files') and line.split()[3:5]==['65536','65536'] for line in (proc/'limits').read_text().splitlines()),'CONTROL_LIMIT_CHANGED')
 return dict(service=row['service'],pid=row['pid'],argvSha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),
  executable=str((proc/'exe').resolve()),environmentVerification=environment_proof,properties=props)

def verify_continuation_originals(continuation,stage,error):
 observation=continuation['observation'];previous=read(continuation['priorRemoteResultPin'])
 need(previous['status']=='FAILED' and previous['stage']==stage and previous['errorCode']==error and
  all(previous[k] is False for k in ('activationCompleted','backupDispatched','restoreDispatched','businessMutationDispatched','controlApiQueriesPerformed','queryAuditWritesMayOccur')),'ORIGINAL_INITIAL_FAILURE_CHANGED')
 old_audit=pathlib.Path(observation['auditPath'])
 expected=sorted(ref['path'].rsplit('/',1)[-1] for ref in observation['auditFiles'])
 need(not old_audit.is_symlink() and sorted(p.name for p in old_audit.iterdir())==expected,'ORIGINAL_AUDIT_SET_CHANGED')
 for path in observation['absentPaths']:
  p=pathlib.Path(path);need(not p.exists() and not p.is_symlink(),'INITIAL_CONTINUATION_WRITE_FOUND')
 need(pin(SPEC['oldReceiptPin']['path'])==SPEC['oldReceiptPin'],'INITIAL_CONTINUATION_RECEIPT_CHANGED')

def verify_initial_continuation():
 continuation=SPEC.get('continuation')
 if continuation is None or 'preSwitchContinuationPin' in continuation:return
 verify_continuation_originals(continuation,'initial','CONTROL_ENVIRONMENT_CHANGED')
 for row in SPEC['current']['controllers']:verify_process(row)

def verify_preswitch_continuation():
 continuation=SPEC.get('continuation')
 if continuation is None or 'preSwitchContinuationPin' not in continuation:return
 verify_continuation_originals(continuation,'candidate-admission','ACTIVATION_COMMAND_FAILED_1')
 before=read(continuation['priorRemoteBeforePin'])
 command=continuation['priorRemoteCommandPin'];need(pin(command['path'])==command,'PRESWITCH_DIAGNOSTIC_CHANGED')
 need(snapshot()==before['containers'] and pin('/etc/fstab')==before['fstab'] and
  hashlib.sha256(mounts()).hexdigest()==before['mountinfoSha256'],'PRESWITCH_BUSINESS_OR_MOUNTS_CHANGED')
 need([verify_process(row) for row in SPEC['current']['controllers']]==before['controllers'] and
  guard()==before['historyGuard'],'PRESWITCH_PROCESS_OR_GUARD_CHANGED')
def verify_package(row):
 root=pathlib.Path(row['engine']);package=json.loads((root/'package.json').read_bytes())
 need(len(package['files'])==row['fileCount'] and package['packageSha256']==row['fileManifestSha256'] and hashlib.sha256(canonical(package['files'])).hexdigest()==row['fileManifestSha256'],'PACKAGE_MANIFEST_CHANGED')
 for name,sha in package['files'].items():
  p=pathlib.PurePosixPath(name);need(not p.is_absolute() and '..' not in p.parts and str(p)==name,'PACKAGE_MEMBER_PATH_INVALID')
  need(pin(root/name)['sha256']==sha,'PACKAGE_MEMBER_CHANGED')
 return pin(root/'package.json')
def no_workers(rows):
 need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESOURCE_RESERVATION')
 roots={read(r['controlConfigurationPin'])['workingDirectory'] for r in rows};expected={r['pid'] for r in rows}
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdecimal():continue
  try:args=(p/'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
  except (FileNotFoundError,ProcessLookupError):continue
  if any(root.encode() in arg for root in roots for arg in args):
   need(int(p.name) in expected and any(arg.endswith(b'/control_entry.py') for arg in args),'UNEXPECTED_CONTROL_OR_WORKER')
def snapshot():
 ids=run(['/usr/bin/docker','--host','unix:///var/run/docker.sock','ps','-aq','--no-trunc']).decode().split();need(ids,'NO_BUSINESS_INVENTORY')
 values=json.loads(run(['/usr/bin/docker','--host','unix:///var/run/docker.sock','inspect',*ids]))
 return {r['Id']:dict(image=r['Image'],restartCount=r['RestartCount'],state={k:r['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},
  definitionSha256=hashlib.sha256(canonical(dict({k:r[k] for k in ('Path','Args','HostConfig','Config')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])))).hexdigest()) for r in values}
def mounts():return pathlib.Path('/proc/self/mountinfo').read_bytes()
def guard():
 value=properties(SPEC['unit']['requiredHistoryGuard'])
 need(value['ActiveState']=='active' and value['SubState']=='exited' and run(['systemctl','is-enabled',SPEC['unit']['requiredHistoryGuard']]).strip()==b'enabled','HISTORY_GUARD_NOT_ACTIVE')
 for ref in SPEC['unit']['historyUnitPins']:need(pin(ref['path'])==ref,'HISTORY_GUARD_PIN_CHANGED')
 return value
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ValueError('CONTROL_REDIRECT_REJECTED')
def http(control,path,process):
 ref=control['authCredentialRef'];credential=pathlib.Path(ref['path']);info=credential.lstat()
 need(credential.resolve(strict=True)==credential and stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_size<=2048 and info.st_uid==ref['uid']==0 and info.st_gid==ref['gid']==0 and stat.S_IMODE(info.st_mode)==ref['mode']==0o600,'CREDENTIAL_IDENTITY_CHANGED')
 headers=json.loads(credential.read_bytes())['headers'];opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
 request=urllib.request.Request('http://127.0.0.1:'+str(control['listenPort'])+path,headers=headers)
 deadline=time.monotonic()+45
 for attempt in range(16):
  need(properties(process['service'])['MainPID']==str(process['pid']),'HTTP_CONTROL_PID_CHANGED')
  try:
   with opener.open(request,timeout=max(1,deadline-time.monotonic())) as response:
    need(response.status==200,'CONTROL_HTTP_STATUS');raw=response.read(16*1024*1024+1);need(len(raw)<=16*1024*1024,'CONTROL_HTTP_LIMIT');return json.loads(raw)
  except urllib.error.URLError as error:
   if not isinstance(error.reason,ConnectionRefusedError) or attempt==15 or time.monotonic()+1>=deadline:raise
   time.sleep(1)
 raise ValueError('CONTROL_HTTP_STARTUP_EXHAUSTED')
def package_gate():
 args=dict(role=selected['role'],controlPin=selected['controlPin'],ownerPin=selected['ownerPin'],oldOwnerPin=old['ownerConfigurationPin'],
  engine=selected['engine'],targetConfigRef=SPEC['targetConfigRef'],sources=list(SOURCES),protections=SPEC['protections'],commit=inputs['sourceCommit'])
 if SPEC.get('sourcePolicyTransition') is not None:args['sourcePolicyTransition']=SPEC['sourcePolicyTransition']
 return json.loads(run([control['pythonPin']['path'],'-B','-c',CANDIDATE_GATE,canonical(args).decode()],timeout=180,env=dict(os.environ,**control['environment'])))
def source_plan(process,configuration,*,expected=None):
 result=http(configuration,'/incremental-plan?sourceConfigRef='+SOURCES[0],process)
 if expected is None:
  need(result.get('state')=='READY' and all(result.get(k)==v for k,v in SPEC['sourceExpected'].items()),'SOURCE_BASELINE_CHANGED')
  if SPEC.get('sourcePolicyTransition') is not None:source_policy_plan(result,SPEC['sourcePolicyTransition'],None)
 else:
  transition=SPEC.get('sourcePolicyTransition');need(transition is not None,'SOURCE_POLICY_SCOPE_REQUIRED')
  source_policy_plan(result,transition,expected['reasonCode'])
  need(result==expected,'SOURCE_POLICY_ACTUAL_HTTP_CHANGED')
 return result
def original_units():
 for original in SPEC['unit']['controllers']:
  need(pin(original['unitPin']['path'])==original['unitPin'],'ORIGINAL_UNIT_CHANGED')
  for ref in original['dropinPins']:need(pin(ref['path'])==ref,'ORIGINAL_DROPIN_CHANGED')
def retained_custody():
 custody=SPEC['previousCustody']
 if custody is None:return
 need(custody['service']==old['service'] and custody['targetConfigRef']==SPEC['targetConfigRef'] and custody['selectedOwnerPin']==old['ownerConfigurationPin'] and custody['selectedControlPin']==old['controlConfigurationPin'],'PREVIOUS_CUSTODY_BINDING_CHANGED')
 if custody.get('schemaVersion')=='MainProgramReceiptCustody/v1':
  need(custody['selectedCurrentReceiptPin']==SPEC['oldReceiptPin'],'PREVIOUS_CUSTODY_CHAIN_CHANGED')
  current=custody
  if 'currentReceiptPin' in out:
   current=json.loads(canonical(custody))
   step=dict(sourceCommit=inputs['sourceCommit'],engine=selected['engine'],previousReceiptPin=out['previousReceiptPin'],
    currentReceiptPin=out['currentReceiptPin'],ownerConfigurationPin=selected['ownerPin'],controlConfigurationPin=selected['controlPin'],
    dropinPin=out['dropinPin'],packagePin=out['packageJsonPin'])
   current['mainSteps'].append(step)
   current.update(selectedOwnerPin=selected['ownerPin'],selectedControlPin=selected['controlPin'],selectedCurrentReceiptPin=out['currentReceiptPin'])
  out['currentLayeredCustodyObservation']=verify_layered_receipt_custody(current)
  need(out['currentLayeredCustodyObservation']['status']=='PASS','ORIGINAL_LAYERED_CUSTODY_FAILED')
  steps=custody['legacyCustody']['steps']+custody['mainSteps'];packages=[]
  for step in steps:
   package_path=pathlib.Path(step['engine'])/'package.json';package=json.loads(package_path.read_bytes());reference=pin(package_path)
   if 'packagePin' in step:need(reference==step['packagePin'],'HISTORICAL_PACKAGE_IDENTITY_CHANGED')
   verify_package(dict(engine=step['engine'],fileCount=len(package['files']),fileManifestSha256=package['packageSha256']))
   packages.append(reference)
  if 'custodyPackagePins' in out:need(packages==out['custodyPackagePins'],'HISTORICAL_PACKAGE_IDENTITY_CHANGED')
  else:out['custodyPackagePins']=packages
  return
 steps=custody['steps'];need([s['sourceCommit'] for s in steps]==custody['expectedGenerationCommits'] and steps[-1]['currentReceiptPin']==SPEC['oldReceiptPin'],'PREVIOUS_CUSTODY_CHAIN_CHANGED')
 for index,step in enumerate(steps):
  previous=read(step['previousReceiptPin'])
  expected=custody['originalActiveReceiptPin'] if index==0 else steps[index-1]['currentReceiptPin']
  need(all(step['previousReceiptPin'][k]==expected[k] for k in ('bytes','sha256')),'HISTORICAL_RECEIPT_CHAIN_CHANGED')
  for key in ('ownerConfigurationPin','controlConfigurationPin','dropinPin'):need(pin(step[key]['path'])==step[key],'HISTORICAL_CONFIGURATION_CHANGED')
  package_path=pathlib.Path(step['engine'])/'package.json';package=json.loads(package_path.read_bytes())
  package_reference=pin(package_path)
  if 'custodyPackagePins' in out:need(package_reference in out['custodyPackagePins'],'HISTORICAL_PACKAGE_IDENTITY_CHANGED')
  verify_package(dict(engine=step['engine'],fileCount=len(package['files']),fileManifestSha256=package['packageSha256']))
 if 'custodyPackagePins' not in out:out['custodyPackagePins']=[pin(pathlib.Path(s['engine'])/'package.json') for s in steps]
def original_inventory():
 inventory=SPEC['originalInventory']
 if inventory is None:return
 need(len(inventory['evidencePins'])==inventory['protectedFiles'],'ORIGINAL_INVENTORY_COUNT_CHANGED')
 active_path=SPEC['oldReceiptPin']['path'];active_expected=out.get('currentReceiptPin',SPEC['oldReceiptPin'])
 active_count=0
 for reference in inventory['evidencePins']:
  if reference['path']==active_path:
   active_count+=1;need(pin(active_path)==active_expected,'ORIGINAL_ACTIVE_PATH_CHANGED')
  else:need(pin(reference['path'])==reference,'ORIGINAL_INVENTORY_PATH_CHANGED')
 need(active_count==1,'ORIGINAL_ACTIVE_PATH_NOT_VERIFIED')
 # The old verifier's complete verified set remains authoritative. Its one active
 # path is checked above against this activation's explicit current pin.
 for reference in out['previousCustodyObservation']['verifiedPins']:
  if reference['path']==active_path:need(pin(active_path)==active_expected,'CUSTODY_ACTIVE_PATH_CHANGED')
  else:need(pin(reference['path'])==reference,'CUSTODY_ORIGINAL_PATH_CHANGED')
 if 'previousReceiptPin' in out:
  need(pin(out['previousReceiptPin']['path'])==out['previousReceiptPin'],'NEW_ARCHIVED_ORIGINAL_RECEIPT_CHANGED')
  need(all(out['previousReceiptPin'][key]==SPEC['oldReceiptPin'][key] for key in ('bytes','sha256')),'NEW_ARCHIVE_NOT_ORIGINAL_BYTES')
 out['originalPathInventoryVerified']=True
def preserve(rows):
 need(snapshot()==before and pin('/etc/fstab')==fstab and mounts()==before_mounts,'BUSINESS_OR_MOUNTS_CHANGED')
 for item in original_rows:
  read(item['controlConfigurationPin']);read(item['ownerConfigurationPin']);verify_package(item)
 original_units();retained_custody();original_inventory();guard();no_workers(rows)
 for ref in SPEC['historyPins']:need(pin(ref['path'])==ref,'HISTORICAL_METADATA_CHANGED')
 for ref in SPEC['documents']:need(pin(ref['path'])==ref,'CANDIDATE_CONFIGURATION_CHANGED')
 for row in rows:verify_process(row)
 if selected['role']=='source':
  for ref in SPEC['sourceEvidencePins']:read(ref)
audit=pathlib.Path(SPEC['remoteAuditPath']);need(audit.parent.resolve(strict=True)==audit.parent and not audit.exists(),'ATTEMPT_ALREADY_EXISTS_OR_ALIAS')
inputs=SPEC['inputs'];selected=SPEC['selected'];old=SPEC['old'];SOURCES=('intruoyi-57-safe-20261024-v1','intruoyi-59-safe-20261024-v1','intruoyi-PROD57-20261019')
original_rows=SPEC['current']['controllers'];rows=list(original_rows);lock=None;out=dict(status='FAILED',activationCompleted=False,host=SPEC['current']['host'],service=selected['service'],
 sourceCommit=inputs['sourceCommit'],stage='initial',backupDispatched=False,restoreDispatched=False,
 businessMutationDispatched=False,controlApiQueriesPerformed=False,queryAuditWritesMayOccur=False)
if inputs.get('schemaVersion')=='MainProgramControlActivationInputs/v4':
 out.update(activationInputsPin=SPEC['activationInputsPin'],**{k:inputs[k] for k in ('coveragePin','previousControlGenerationPin','revisionId')})
continuation=SPEC.get('continuation');audit_created=False
if continuation:
 continuation_key='preSwitchContinuationPin' if 'preSwitchContinuationPin' in continuation else 'initialFailureContinuationPin'
 continuation_flag='preSwitchFailureRevalidated' if continuation_key=='preSwitchContinuationPin' else 'initialFailureRevalidated'
 out.update(attemptRevision=2,**{continuation_flag:False},**{k:continuation[k] for k in
  (continuation_key,'priorAttemptPin','priorFailurePin','priorRemoteResultPin')})
try:
 verify_initial_continuation()
 verify_preswitch_continuation()
 if continuation:out[continuation_flag]=True
 audit.mkdir(mode=0o700);audit_created=True
 control=read(selected['controlPin']);owner=read(selected['ownerPin']);old_control=read(old['controlConfigurationPin']);old_owner=read(old['ownerConfigurationPin'])
 for row in original_rows:verify_process(row);verify_package(row)
 original_units();retained_custody();no_workers(rows);guard()
 if SPEC['previousCustody'] is not None:
  out['previousCustodyObservation']=(verify_layered_receipt_custody(SPEC['previousCustody']) if
   SPEC['previousCustody'].get('schemaVersion')=='MainProgramReceiptCustody/v1' else verify_installation_receipt_custody(SPEC['previousCustody']))
  need(out['previousCustodyObservation']['status']=='PASS','ORIGINAL_V1_CUSTODY_FAILED')
  out['completePreviousCustodyVerified']=True
  original_inventory()
 for existing_row,original in zip(rows,SPEC['unit']['controllers']):
  names=sorted(p.name for p in pathlib.Path(original['directory']).glob('*.conf'))
  expected_names=sorted(original['existingNames']+([pathlib.Path(existing_row['dropinPin']['path']).name] if 'dropinPin' in existing_row and existing_row['dropinPin'] not in original['dropinPins'] else []))
  need(names==expected_names,'ORIGINAL_OR_PEER_DROPIN_SET_CHANGED')
 unit=next(r for r in SPEC['unit']['controllers'] if r['service']==selected['service'])
 directory=pathlib.Path(unit['directory']);need(directory.resolve(strict=True)==directory and sorted(p.name for p in directory.glob('*.conf'))==unit['existingNames'],'DROPIN_SET_CHANGED')
 need(all(pathlib.Path(SPEC['dropinPath']).name>name for name in unit['existingNames']),'DROPIN_NOT_LAST')
 before=snapshot();before_mounts=mounts();fstab=pin('/etc/fstab')
 create(audit/'before.private.json',canonical(dict(controllers=[verify_process(r) for r in rows],containers=before,fstab=fstab,mountinfoSha256=hashlib.sha256(before_mounts).hexdigest(),historyGuard=guard())))
 for ref in SPEC['documents']:read(ref)
 candidate=dict(selected,controlConfigurationPin=selected['controlPin'],ownerConfigurationPin=selected['ownerPin'],fileCount=147,fileManifestSha256=SPEC['build']['fileManifestSha256'])
 package_pin=verify_package(candidate)
 for role in ('repository','recovery','control'):
  reply=json.loads(run([control['pythonPin']['path'],'-B',selected['engine']+'/'+role+'_entry.py','--check-imports'],env=dict(os.environ,**control['environment'])))
  need(reply.get('role')==role,'ACTUAL_IMPORT_FAILED')
 out.update(actualImportsVerified=True,originalUnitPinsVerified=True,packageJsonPin=package_pin)
 if selected['role']=='source':
  out['stage']='source-idle'
  result=json.loads(run([old_control['pythonPin']['path'],'-B','-c',SOURCE_IDLE,canonical([old['controlConfigurationPin'],SOURCES[0]]).decode()],timeout=100,env=dict(os.environ,**old_control['environment'])))
  need(result.get('sourceIdle') is True,'SOURCE_NOT_IDLE')
  out.update(controlApiQueriesPerformed=True,queryAuditWritesMayOccur=True)
  out['sourcePlanBefore']=source_plan(old,old_control)
  for ref in SPEC['sourceEvidencePins']:read(ref)
  policy=old_control['sourceEpochPolicies'][SOURCES[0]];lock_path=policy['sourceLockPath']
  peer=rows[-1];peer_owner=read(peer['ownerConfigurationPin'])
  need(peer_owner['targetBackupEpochPolicies'][SPEC['targetConfigRef']]==policy,'SOURCE_TARGET_EPOCH_MISMATCH')
 else:lock_path=old_owner['targets'][SPEC['targetConfigRef']]['replacement']['lockPath']
 p=pathlib.Path(lock_path);need(p.resolve(strict=True)==p,'PHYSICAL_LOCK_ALIAS');lock=os.open(p,os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC)
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 info=os.fstat(lock);need(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and (info.st_dev,info.st_ino)==(p.stat().st_dev,p.stat().st_ino),'PHYSICAL_LOCK_IDENTITY_CHANGED')
 out['physicalLockVerified']=True;no_workers(rows);out['stage']='candidate-admission'
 if SPEC.get('sourcePolicyTransition') is not None:
  out['sourcePlanBeforeLocked']=source_plan(old,old_control)
 first=package_gate();out['candidateBefore']=first
 if selected['role']=='source':
  need(first['epochPolicy']==old_control['sourceEpochPolicies'][SOURCES[0]],'SOURCE_EPOCH_POLICY_CHANGED')
  out['sourceCaptureVerified']=first['sourceCaptureVerified']
 else:
  out.update(directlyAdmittedSources=first['directlyAdmittedSources'],archiveViewsPreflightVerified=first['archiveViewsPreflightVerified'])
 preserve(rows)
 # Authenticate existing registration only; direct three-source admission above is separate.
 if selected['role']=='target':
  existing=http(old_control,'/selections?targetConfigRef='+SPEC['targetConfigRef'],old)
  need(any(r.get('sourceConfigRef')==SOURCES[0] and SPEC['targetConfigRef'] in r.get('freshTargetConfigRefs',[]) for r in existing.get('applications',[])),'EXISTING_SELECTION_UNAVAILABLE')
  out['existingRegistrationBefore']=existing
  out.update(controlApiQueriesPerformed=True,queryAuditWritesMayOccur=True)
 archive=None
 if SPEC['oldReceiptPin'] is not None:
  receipt=read(SPEC['oldReceiptPin']);need(receipt['sourceCommit']==old['sourceCommit'] and receipt['engine']==old['engine'] and receipt['ownerConfigurationPin']==old['ownerConfigurationPin'] and receipt['controlConfigurationPin']==old['controlConfigurationPin'],'ACTIVE_RECEIPT_IDENTITY_CHANGED')
  archive=create(SPEC['archiveReceiptPath'],pathlib.Path(SPEC['oldReceiptPin']['path']).read_bytes())
  need(all(archive[k]==SPEC['oldReceiptPin'][k] for k in ('bytes','sha256')),'RECEIPT_ARCHIVE_CHANGED')
 out['stage']='write-dropin'
 create(audit/'previous-unit.private.txt',run(['systemctl','cat',selected['service']]))
 out['dropinPin']=create(SPEC['dropinPath'],SPEC['dropinText'].encode('utf-8'),0o644)
 run(['systemd-analyze','verify',unit['unitPin']['path']])
 preserve(rows);out['stage']='restart-selected-control'
 run(['systemctl','daemon-reload']);run(['systemctl','restart',selected['service']])
 props=properties(selected['service']);pid=int(props['MainPID']);need(pid>1 and pid!=old['pid'],'NEW_PID_REQUIRED')
 need(SPEC['unit']['requiredHistoryGuard'] in props['Requires'].split() and SPEC['unit']['requiredHistoryGuard'] in props['After'].split(),'HISTORY_GUARD_DEPENDENCY_MISSING')
 new=dict(candidate,pid=pid,sourceCommit=inputs['sourceCommit'],dropinPin=out['dropinPin'],environmentMode='CONFIG_EXACT')
 rows=[new if r['service']==new['service'] else r for r in rows];out['pid']=pid
 out['processAfter']=verify_process(new);out['stage']='new-api'
 if selected['role']=='source':
  expected=first['sourcePolicyAdmission']['plan'] if SPEC.get('sourcePolicyTransition') is not None else None
  out['sourcePlanAfter']=source_plan(new,control,expected=expected);out['sourceBaselineVerified']=True
 else:
  new_selection=http(control,'/selections?targetConfigRef='+SPEC['targetConfigRef'],new)
  need(any(r.get('sourceConfigRef')==SOURCES[0] and SPEC['targetConfigRef'] in r.get('freshTargetConfigRefs',[]) for r in new_selection.get('applications',[])),'NEW_EXISTING_SELECTION_UNAVAILABLE')
  out['existingRegistrationAfter']=new_selection
 out.update(controlApiQueriesPerformed=True,queryAuditWritesMayOccur=True)
 final=package_gate();need(final==first,'CANDIDATE_ADMISSION_OR_EPOCH_CHANGED');out['candidateAfter']=final
 if SPEC.get('sourcePolicyTransition') is not None:validate_source_policy_transition(SPEC['sourcePolicyTransition'],out)
 preserve(rows);verify_package(candidate)
 if archive is not None:
  need(pin(archive['path'])==archive,'RECEIPT_ARCHIVE_CHANGED');read(SPEC['oldReceiptPin'])
  updated=dict(receipt,sourceCommit=inputs['sourceCommit'],engine=selected['engine'],ownerConfigurationPin=selected['ownerPin'],controlConfigurationPin=selected['controlPin'])
  need(set(updated)==set(receipt) and all(updated[k]==receipt[k] for k in receipt if k not in ('sourceCommit','engine','ownerConfigurationPin','controlConfigurationPin')),'RECEIPT_UNRELATED_FIELDS_CHANGED')
  active=pathlib.Path(SPEC['oldReceiptPin']['path']);temporary=active.with_name(active.name+'.main-'+inputs['sourceCommit'][:7]+'.pending')
  create(temporary,canonical(updated));read(SPEC['oldReceiptPin']);os.replace(temporary,active)
  fd=os.open(active.parent,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(fd)
  finally:os.close(fd)
  need(json.loads(active.read_bytes())==updated,'RECEIPT_PUBLICATION_CHANGED')
  out.update(previousReceiptPin=archive,currentReceiptPin=pin(active),receiptRotated=True)
 preserve(rows)
 out.update(status='PASS',activationCompleted=True,stage='complete',epochVerified=True,historyGuardVerified=True,
  apiVerified=True,argvVerified=True,environmentVerified=True,limitVerified=True,noWorkersVerified=True,
  businessContainersUnchanged=True,fstabAndMountsUnchanged=True,previousControlFilesPreserved=True,originalTargetObjectsUnchanged=True,
  containersBefore=before,containersAfter=snapshot(),fstabPin=fstab,mountinfoSha256=hashlib.sha256(before_mounts).hexdigest(),
  controllersAfter=rows,registrySelectorsPublished=False,threeSourceSelectionsVerified=False)
except BaseException as error:
 out.update(status='FAILED',activationCompleted=False,errorType=type(error).__name__,errorCode=str(error))
finally:
 if lock is not None:fcntl.flock(lock,fcntl.LOCK_UN);os.close(lock)
out['observedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
if audit_created:create(audit/'result.private.json',canonical(out))
print(json.dumps(out))
'''


if __name__ == '__main__':
    args = parser().parse_args()
    print(json.dumps(run_request(args.task, args.private, args.inputs, activate=args.activate), ensure_ascii=False))
