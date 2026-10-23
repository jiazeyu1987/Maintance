"""W01 private material selector for W05's finite new-source installation.

No signing, SQL, subprocess, secret read, action alias, or executable CLI.
The selected W05 and mature native modules must already be installed on the
reviewed import graph. Native entry points read authentic Linux originals.
"""
from __future__ import annotations

import re
import sys
import math
import os
from datetime import datetime
from pathlib import PurePosixPath

ACTION = 'INITIALIZE_REVIEWED_FINITE_NEW_SOURCE'
ROOT = '/mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07'
ID = 'backup-server-rehearsal-20261012-r1'
SELECTION_FIELDS = set(('schemaVersion binding action approved installationPin sourceScopePin '
    'reviewPin adapterReviewPin r4InterfacePin initializerPin packagePin policyRowsPin candidateVersionPin '
    'metadataRuntimeAdapterPin policyRuntimeAdapterPin policyAppendBindingPin candidateReviewPin policyApprovalAuthorityPin '
    'entryPin sourcePins driverClassPin cursorClassPin evidenceRoot privateInputsPath privateInputRefs '
    'connectionPublicOptions connectionSecretRefs controllerIdentity hostIdentity issuerSelectionPin '
    'ownershipState owner newSchema leaseState leaseId fenceGeneration exclusiveClaimPin encoder '
    'filePublicBindingPin ddlDefaults maximumSeconds issuedAt expiresAt').split())
BINDING_FIELDS = set(('rehearsalId operationId batchId executor schema serverUuid containerId '
                      'schemaAllocationId imageTag imageDigest').split())
PIN_FIELDS = ('installationPin', 'sourceScopePin', 'reviewPin', 'adapterReviewPin',
    'r4InterfacePin', 'initializerPin', 'packagePin', 'policyRowsPin', 'candidateVersionPin',
    'metadataRuntimeAdapterPin', 'policyRuntimeAdapterPin', 'policyAppendBindingPin',
    'candidateReviewPin', 'policyApprovalAuthorityPin',
    'entryPin', 'driverClassPin', 'cursorClassPin', 'issuerSelectionPin', 'exclusiveClaimPin',
    'filePublicBindingPin')
REVIEW_PINS = ('packagePin', 'initializerPin', 'r4InterfacePin', 'policyRowsPin', 'candidateVersionPin',
               'metadataRuntimeAdapterPin', 'policyRuntimeAdapterPin', 'policyAppendBindingPin', 'candidateReviewPin')
ISSUER_LINK_FIELDS = (*REVIEW_PINS, 'sourceScopePin', 'installationPin', 'entryPin', 'sourcePins',
    'driverClassPin', 'cursorClassPin', 'encoder', 'filePublicBindingPin', 'ddlDefaults',
    'reviewPin', 'adapterReviewPin', 'policyApprovalAuthorityPin', 'controllerIdentity',
    'maximumSeconds', 'owner', 'ownershipState', 'leaseState', 'leaseId', 'fenceGeneration', 'exclusiveClaimPin')
POLICY_AUTHORITY_LINK_FIELDS = (*REVIEW_PINS, 'sourceScopePin', 'controllerIdentity', 'hostIdentity',
    'owner', 'ownershipState', 'leaseState', 'leaseId', 'fenceGeneration', 'exclusiveClaimPin',
    'installationPin', 'reviewPin', 'adapterReviewPin')
ABI_FIELDS = set(('schemaVersion materialRevision initializerPin dependencyPins packagePin planSchemaVersion '
    'createTableCount schemaStatementCount publicRowsMember fileStorageBindingPin rowPath policyRowsPin '
    'metadataRuntimeAdapterPin policyRuntimeAdapterPin policyAppendBindingPin').split())
APPEND_FIELDS = set(('schemaVersion selectedBackendCommit candidateVersionPin targetTenantId '
                     'twoOriginalEntriesPin versionTableAppendPin approvalPin').split())
APPROVAL_FIELDS = set(('schemaVersion selectedBackendCommit policyVersion policyHash targetTenantId '
                      'approvedBy approvedAt approvalReference approvalEvidencePin coverageReportPin').split())
OWNED_CHAIN_FIELDS = {'schemaVersion', 'model', 'controllerIdentity', 'supervisorIdentity', 'workerIdentity', 'deadline'}
OWNED_CHAIN_IDENTITY_FIELDS = {'pid', 'parent', 'group', 'session', 'startTicks', 'uid', 'gid'}
POLICY_HEAD = 'b08c05524702c4e3503034d7fe13f7dd87032ccf'
POLICY_VERSION = '2026-09-approved-01'
POLICY_HASH = '398f26d41f55833706bc98d687c597681141cc27f190235e4a8f18395c0be3c4'
VERSION_DDL_HASH = '174f9dca565ea70856bb2d1bb8f5b5505ea3089862708555310b83a766b71556'
ORIGINAL_ENTRIES_HASH = 'e12f72e50887fc14ee552e2433b3ddba8df5c339e09e5f63680a607a48d53c91'
REJECTED_R2_CANDIDATE_HASHES = {
    'fe0e42f9d5f62494fd0e69424748676dc6a8bf2a27bfb15e99868c1b84544550',
    '2bf6e5452572df3b2fa50e95a0f09e05b7e67bc3a879c2d6b1f364ca4cc53351',
    '498ba0afa49cffa92ca9a4b1c0db8aa1d5e8dd059100142aeb5bbcce14f7c11a'}


class SelectionError(RuntimeError):
    """Only a fixed code is exposed; no input values or exception text."""


def need(condition, code):
    if not condition:
        raise SelectionError(code)


def pin(value):
    need(type(value) is dict and set(value) == {'path', 'bytes', 'sha256'},
         'SOURCE_CONTROL_EXACT_PIN_REQUIRED')
    path = value['path']
    need(type(path) is str and path.startswith('/') and
         str(PurePosixPath(path)) == path and '..' not in PurePosixPath(path).parts and
         not any(c in path for c in ('\x00', '\r', '\n', '\\')) and
         type(value['bytes']) is int and value['bytes'] > 0 and
         type(value['sha256']) is str and re.fullmatch(r'[a-f0-9]{64}', value['sha256']),
         'SOURCE_CONTROL_EXACT_PIN_REQUIRED')


def select_action(selection):
    """Shape/selection check only. An unsigned object grants no authority."""
    need(type(selection) is dict and selection.get('action') == ACTION,
         'SOURCE_CONTROL_EXPLICIT_INSTALLATION_ACTION_REQUIRED')
    for field in PIN_FIELDS:
        need(field in selection, 'SOURCE_CONTROL_REQUIRED_PIN_MISSING')
        pin(selection[field])
    need(set(selection) == SELECTION_FIELDS and
         selection['schemaVersion'] == 'W05FiniteSourceInstallationAuthorization/v1',
         'SOURCE_CONTROL_INSTALLATION_SELECTION_SHAPE')
    b = selection['binding']
    need(type(b) is dict and set(b) == BINDING_FIELDS and
         all(type(v) is str and v and len(v) <= 512 and
             not any(c in v for c in ('\x00', '\r', '\n')) for v in b.values()) and
         b['rehearsalId'] == ID and re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]{0,63}', b['schema']) and
         b['schema'] not in {'mysql', 'sys', 'information_schema', 'performance_schema'},
         'SOURCE_CONTROL_EXACT_NEW_SOURCE_BINDING_REQUIRED')
    need(selection['approved'] is True and selection['newSchema'] is True and
         selection['owner'] == b['executor'] and
         selection['ownershipState'] == selection['leaseState'] == 'HELD' and
         type(selection['leaseId']) is str and bool(selection['leaseId']) and
         type(selection['fenceGeneration']) is int and selection['fenceGeneration'] > 0,
         'SOURCE_CONTROL_CURRENT_HELD_POSITIVE_CLAIM_REQUIRED')
    need(type(selection['sourcePins']) is list and selection['sourcePins'],
         'SOURCE_CONTROL_CONSUMER_PINS_REQUIRED')
    paths = set()
    for source in selection['sourcePins']:
        pin(source)
        need(source['path'] not in paths, 'SOURCE_CONTROL_DUPLICATE_SOURCE_PIN')
        paths.add(source['path'])
    need(selection['entryPin'] in selection['sourcePins'], 'SOURCE_CONTROL_ENTRY_NOT_SELECTED')
    need(type(selection['maximumSeconds']) is int and 0 < selection['maximumSeconds'] <= 300,
         'SOURCE_CONTROL_FINITE_WINDOW_REQUIRED')
    return ACTION


def validate_links(s, *, source, claim, issuer, review, adapter, installation, abi, append_binding, candidate_review):
    """Validate links already authenticated by SourceCustody; never mint flags."""
    select_action(s)
    b = s['binding']
    need(claim.get('binding') == b and claim.get('state') == 'HELD' and
         claim.get('owner') == s['owner'] and claim.get('leaseId') == s['leaseId'] and
         type(claim.get('fenceGeneration')) is int and claim['fenceGeneration'] == s['fenceGeneration'],
         'SOURCE_CONTROL_CURRENT_CLAIM_LINK_REQUIRED')
    need(source.get('binding') == b and source.get('newSchema') is True and
         source.get('oldSourceAdminWriteAllowed') is False and source.get('tenant122SeedAllowed') is False and
         source.get('sourceRoot') == ROOT + '/source/main-chain-20261013-r1' and
         source.get('aggregateMemoryBudgetBytes') == 8 * 1024**3 and
         source.get('aggregateDiskBudgetBytes') == 80 * 1024**3 and
         source.get('oldContainersMayChange') is False and source.get('hostGlobalMayChange') is False and
         source.get('sourceSqlWriteScope') == 'FINITE_INITIALIZATION_ONLY',
         'SOURCE_CONTROL_NEW_SOURCE_SCOPE_REQUIRED')
    need(review.get('accepted') is True and review.get('materialRevision') == 'r4' and
         review.get('ownerField') == 'mainChainSourceBootstrapPackaging20261013.r4' and
         all(review.get(k) == s[k] for k in REVIEW_PINS),
         'SOURCE_CONTROL_FINAL_REVIEWED_MATERIAL_REQUIRED')
    need(adapter.get('accepted') is True and adapter.get('action') == ACTION and
         adapter.get('entryPin') == s['entryPin'] and adapter.get('sourcePins') == s['sourcePins'],
         'SOURCE_CONTROL_FINAL_REVIEWED_CONSUMER_REQUIRED')
    # Dedicated issuer selection supplement: do not rename a GoView permission.
    need(issuer.get('schemaVersion') == 'W05FiniteSourceInstallationIssuerSelection/v1' and
         issuer.get('role') == 'AUTHORIZED_FINITE_SOURCE_INSTALLATION_ISSUER' and
         issuer.get('action') == ACTION and issuer.get('binding') == b and
         issuer.get('authorityKeyPin') is not None,
         'SOURCE_CONTROL_SPECIFIC_INDEPENDENT_ISSUER_REQUIRED')
    pin(issuer['authorityKeyPin'])
    need(type(issuer.get('fenceGeneration')) is int and
         all(issuer.get(k) == s[k] for k in ISSUER_LINK_FIELDS),
         'SOURCE_CONTROL_ISSUER_MATERIAL_AND_CURRENT_CLAIM_REQUIRED')
    identity, host = issuer.get('identity'), issuer.get('hostIdentity')
    controller = s['controllerIdentity']
    identity_fields = {'pid', 'parent', 'group', 'session', 'startTicks', 'uid', 'gid'}
    need(type(identity) is dict and set(identity) == identity_fields and
         type(controller) is dict and set(controller) == identity_fields and
         type(host) is dict and set(host) == {'hostname', 'bootId', 'namespaces'} and
         type(s['hostIdentity']) is dict and set(s['hostIdentity']) == set(host) and
         type(host['namespaces']) is dict and type(s['hostIdentity']['namespaces']) is dict and
         set(host['namespaces']) == set(s['hostIdentity']['namespaces']) == {'pid', 'mnt', 'net', 'user'},
         'SOURCE_CONTROL_EXACT_NATIVE_IDENTITY_REQUIRED')
    need(type(identity['uid']) is int and identity['uid'] > 0 and
         type(identity['gid']) is int and identity['gid'] > 0 and
         controller['uid'] == controller['gid'] == 0 and identity != controller and
         host['bootId'] == s['hostIdentity']['bootId'] and
         host['namespaces']['mnt'] != s['hostIdentity']['namespaces']['mnt'] and
         all(host['namespaces'][k] == s['hostIdentity']['namespaces'][k] for k in ('pid', 'net', 'user')) and
         issuer.get('keyIsolationModel') == 'separate-mount-namespace-capability-free-sql-worker/v1',
         'SOURCE_CONTROL_INDEPENDENT_ISSUER_CUSTODY_REQUIRED')
    keyref = issuer['privateKeyReference']
    need(set(keyref) == {'path', 'uid', 'gid', 'mode'} and type(keyref['mode']) is int and
         keyref['uid'] == identity['uid'] and keyref['gid'] == identity['gid'] and keyref['mode'] == 0o600 and
         type(keyref['path']) is str and keyref['path'].startswith(ROOT + '/') and
         '..' not in PurePosixPath(keyref['path']).parts,
         'SOURCE_CONTROL_ISSUER_KEY_REFERENCE_REQUIRED')
    selected = installation['filePins'] + installation['dependencyPins']
    need(all(s[k] in selected for k in ('initializerPin', 'packagePin', 'policyRowsPin')),
         'SOURCE_CONTROL_R4_STATIC_MATERIAL_NOT_INSTALLED')
    need(installation.get('schemaVersion') == 'RepositoryNativeInstallation/v2' and
         all(p in selected for p in s['sourcePins'] + [s['driverClassPin'], s['cursorClassPin']]),
         'SOURCE_CONTROL_REVIEWED_NATIVE_GRAPH_REQUIRED')
    validate_r4_abi(s, installation, abi, append_binding)
    validate_candidate(s, installation, candidate_review)


def validate_r4_abi(s, installation, abi, append_binding):
    need(type(abi) is dict and set(abi) == ABI_FIELDS and
         abi.get('schemaVersion') == 'W05ReviewedFiniteSourceR4Bindings/v1' and
         abi.get('materialRevision') == 'r4' and
         abi.get('planSchemaVersion') == 'W02FiniteSourceInitialInstallation/v4' and
         all(abi.get(k) == s[k] for k in ('initializerPin', 'packagePin', 'policyRowsPin',
             'metadataRuntimeAdapterPin', 'policyRuntimeAdapterPin', 'policyAppendBindingPin')) and
         abi.get('publicRowsMember') == 'business-ui-metadata-parameters.json' and
         abi.get('rowPath') == ['rows'] and type(abi.get('createTableCount')) is int and
         abi['createTableCount'] == 99 and type(abi.get('schemaStatementCount')) is int and
         abi['schemaStatementCount'] == 272,
         'SOURCE_CONTROL_EXPLICIT_REVIEWED_R4_ABI_REQUIRED')
    selected = installation['filePins'] + installation['dependencyPins']
    need(type(abi['dependencyPins']) is list and abi['dependencyPins'], 'SOURCE_CONTROL_R4_DEPENDENCIES_REQUIRED')
    module_names = []
    paths = set()
    for dependency in abi['dependencyPins']:
        pin(dependency)
        need(dependency in selected and dependency['path'] not in paths,
             'SOURCE_CONTROL_R4_EXACT_INSTALLED_DEPENDENCY_REQUIRED')
        paths.add(dependency['path'])
        module_names.append(PurePosixPath(dependency['path']).name)
    need(all(module_names.count(name) == 1 for name in (
          'ddl_core.py', 'source_bootstrap_material.py', 'task_file_storage_binding.py',
          'metadata_runtime_poststate.py', 'policy_registration_material.py', 'policy_runtime_append.py')),
         'SOURCE_CONTROL_R4_COMPLETE_ADAPTER_GRAPH_REQUIRED')
    for key, name in (('metadataRuntimeAdapterPin', 'metadata_runtime_poststate.py'),
                      ('policyRuntimeAdapterPin', 'policy_runtime_append.py'),
                      ('fileStorageBindingPin', 'task_file_storage_binding.py')):
        pin(abi[key])
        need(abi[key] in abi['dependencyPins'] and PurePosixPath(abi[key]['path']).name == name,
             'SOURCE_CONTROL_R4_ADAPTER_PIN_NOT_SELECTED')
    validate_append_binding(s, append_binding)
    ddl = append_binding['versionTableAppendPin']
    helpers = [p for p in abi['dependencyPins'] if PurePosixPath(p['path']).name == 'policy_registration_material.py']
    need(len(helpers) == 1 and ddl in abi['dependencyPins'] and
         ddl['path'] == str(PurePosixPath(helpers[0]['path']).parent / 'gxp-audit-policy-version.append.sql') and
         ddl['bytes'] == 868 and ddl['sha256'] == VERSION_DDL_HASH,
         'SOURCE_CONTROL_EXACT_VERSION_DDL_SIBLING_REQUIRED')
    original = append_binding['twoOriginalEntriesPin']
    need(original in selected and original['bytes'] == 3445 and original['sha256'] == ORIGINAL_ENTRIES_HASH,
         'SOURCE_CONTROL_EXACT_POLICY_ORIGINALS_REQUIRED')


def validate_append_binding(s, binding):
    need(type(binding) is dict and set(binding) == APPEND_FIELDS and
         binding['schemaVersion'] == 'W02PermissionPolicyRegistrationAppend/v2' and
         binding['selectedBackendCommit'] == POLICY_HEAD and type(binding['targetTenantId']) is int and
         binding['targetTenantId'] == 1 and binding['candidateVersionPin'] == s['candidateVersionPin'],
         'SOURCE_CONTROL_EXACT_FIRST_INSTALL_POLICY_BINDING_REQUIRED')
    for key in ('candidateVersionPin', 'twoOriginalEntriesPin', 'versionTableAppendPin', 'approvalPin'):
        pin(binding[key])


def validate_candidate(s, installation, review):
    need(type(review) is dict and review.get('schemaVersion') == 'W01FiniteSourceInstallationCandidateReview/v1' and
         review.get('accepted') is True and review.get('candidateRevision') == 'normal-onboarding-r3' and
         review.get('candidateVersionPin') == s['candidateVersionPin'],
         'SOURCE_CONTROL_FINAL_ACCEPTED_CANDIDATE_REQUIRED')
    pin(review.get('reviewEvidencePin'))
    artifacts = review.get('candidateArtifactPins')
    need(type(artifacts) is list and artifacts, 'SOURCE_CONTROL_ACTUAL_CANDIDATE_ARTIFACT_PINS_REQUIRED')
    for candidate in [s['candidateVersionPin'], *artifacts]:
        pin(candidate)
        need(candidate['sha256'] not in REJECTED_R2_CANDIDATE_HASHES,
             'SOURCE_CONTROL_REJECTED_R2_CANDIDATE_PIN')
        need(candidate in installation['filePins'] + installation['dependencyPins'],
             'SOURCE_CONTROL_FINAL_CANDIDATE_NOT_INSTALLED')


def validate_policy_approval(s, approval, binding, authority):
    """Scoped link validation only; True is reserved for native custody below."""
    select_action(s)
    validate_append_binding(s, binding)
    need(type(approval) is dict and set(approval) == APPROVAL_FIELDS and
         approval['schemaVersion'] == 'FirstInstallationPermissionPolicyApproval/v1' and
         approval['selectedBackendCommit'] == POLICY_HEAD and approval['policyVersion'] == POLICY_VERSION and
         approval['policyHash'] == POLICY_HASH and type(approval['targetTenantId']) is int and
         approval['targetTenantId'] == 1 and type(approval['approvedBy']) is int and approval['approvedBy'] > 0 and
         type(approval['approvedAt']) is str and type(approval['approvalReference']) is str and
         0 < len(approval['approvalReference'].strip()) <= 256 and
         approval['approvalReference'] != 'CODEX-IMPLEMENTATION-20260908',
         'SOURCE_CONTROL_REAL_FIRST_INSTALL_POLICY_APPROVAL_REQUIRED')
    for key in ('approvalEvidencePin', 'coverageReportPin'):
        pin(approval[key])
    try:
        approved_at = datetime.fromisoformat(approval['approvedAt'])
    except ValueError:
        raise SelectionError('SOURCE_CONTROL_REAL_APPROVAL_SERVER_LOCAL_TIME_REQUIRED') from None
    need(approved_at.tzinfo is None and approved_at <= datetime.now(),
         'SOURCE_CONTROL_REAL_APPROVAL_SERVER_LOCAL_TIME_REQUIRED')
    need(type(authority) is dict and
         authority.get('schemaVersion') == 'W01FiniteSourceInstallationPolicyApprovalAuthority/v1' and
         authority.get('approved') is True and authority.get('action') == ACTION and
         authority.get('binding') == s['binding'] and
         type(authority.get('fenceGeneration')) is int and
         all(authority.get(k) == s[k] for k in POLICY_AUTHORITY_LINK_FIELDS) and
         authority.get('approvalPin') == binding['approvalPin'] and
         all(authority.get(k) == approval[k] for k in APPROVAL_FIELDS - {'schemaVersion'}),
         'SOURCE_CONTROL_NATIVE_SCOPED_POLICY_AUTHORITY_REQUIRED')


def require_window_binding(selection, records):
    def stamp(value):
        need(type(value) is str, 'SOURCE_CONTROL_AUTHORITY_WINDOW_BINDING_REQUIRED')
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            raise SelectionError('SOURCE_CONTROL_AUTHORITY_WINDOW_BINDING_REQUIRED') from None
        need(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0,
             'SOURCE_CONTROL_AUTHORITY_WINDOW_BINDING_REQUIRED')
        return parsed
    start, end = stamp(selection['issuedAt']), stamp(selection['expiresAt'])
    for record in records:
        need(stamp(record['issuedAt']) <= start < end <= stamp(record['expiresAt']),
             'SOURCE_CONTROL_AUTHORITY_WINDOW_BINDING_REQUIRED')


def validate_owned_controller_chain(proof, *, controller_identity, worker_identity, deadline,
                                    current_controller, current_supervisor, current_worker):
    """Pure checks of an already authenticated W05 proof; never creates one."""
    need(type(proof) is dict and set(proof) == OWNED_CHAIN_FIELDS and
         proof['schemaVersion'] == 'W05AuthenticatedOwnedSourceChain/v1' and
         proof['model'] == 'linux-owned-child-subreaper-v1' and
         type(deadline) in (int, float) and math.isfinite(deadline) and
         type(proof['deadline']) in (int, float) and math.isfinite(proof['deadline']) and
         proof['deadline'] == deadline, 'SOURCE_CONTROL_AUTHENTIC_OWNED_CHAIN_REQUIRED')
    identities = (controller_identity, worker_identity, proof['controllerIdentity'],
                  proof['supervisorIdentity'], proof['workerIdentity'],
                  current_controller, current_supervisor, current_worker)
    need(all(type(value) is dict and set(value) == OWNED_CHAIN_IDENTITY_FIELDS and
             all(type(item) is int for item in value.values()) and
             all(value[key] > 0 for key in ('pid', 'group', 'session', 'startTicks')) and
             all(value[key] >= 0 for key in ('parent', 'uid', 'gid')) for value in identities),
         'SOURCE_CONTROL_EXACT_OWNED_CHAIN_IDENTITY_REQUIRED')
    controller, supervisor, worker = (proof[key] for key in
        ('controllerIdentity', 'supervisorIdentity', 'workerIdentity'))
    need(controller == controller_identity == current_controller and
         supervisor == current_supervisor and worker == worker_identity == current_worker and
         len({controller['pid'], supervisor['pid'], worker['pid']}) == 3 and
         supervisor['parent'] == controller['pid'] and worker['parent'] == supervisor['pid'],
         'SOURCE_CONTROL_CURRENT_OWNED_CHAIN_CHANGED')


def require_owned_controller(custody):
    """Called only after exact custody/provider/control installation admission.

    W05 derives worker proof from its held SCM_CREDENTIALS-authenticated ACK.
    W01 observes all three current identities; no ancestor search or Boolean
    authorization. A detached snapshot detects later mutable proof changes.
    """
    need(sys.platform == 'linux', 'SOURCE_CONTROL_NATIVE_ORIGINAL_ACCESS_REQUIRED')
    from recovery_native_goview_authority import stable_identity
    controller = custody.selection['controllerIdentity']
    deadline = custody.deadline
    actual_worker = stable_identity(os.getpid())
    need(actual_worker == custody.process_identity, 'SOURCE_CONTROL_ACTUAL_PROCESS_IDENTITY_CHANGED')
    need(type(custody.worker) is bool, 'SOURCE_CONTROL_ACTUAL_OWNED_CONTROLLER_REQUIRED')
    if custody.worker is False:
        need(actual_worker == controller and stable_identity(controller['pid']) == controller,
             'SOURCE_CONTROL_ACTUAL_OWNED_CONTROLLER_REQUIRED')
        return None
    method = getattr(custody, 'require_owned_controller_chain', None)
    need(callable(method) and getattr(method, '__self__', None) is custody and
         getattr(type(custody), 'require_owned_controller_chain', None) is getattr(method, '__func__', None) and
         getattr(getattr(method, '__func__', None), '__module__', None) == type(custody).__module__,
         'SOURCE_CONTROL_NATIVE_OWNED_CHAIN_PROVIDER_REQUIRED')
    proof = method(controller.copy(), deadline)
    need(custody.deadline == deadline, 'SOURCE_CONTROL_OWNED_CHAIN_DEADLINE_CHANGED')
    need(type(proof) is dict and set(proof) == OWNED_CHAIN_FIELDS,
         'SOURCE_CONTROL_AUTHENTIC_OWNED_CHAIN_REQUIRED')
    # Validate shape before selecting any PID for a native observation.
    validate_owned_controller_chain(proof, controller_identity=controller,
        worker_identity=custody.process_identity, deadline=deadline,
        current_controller=proof['controllerIdentity'], current_supervisor=proof['supervisorIdentity'],
        current_worker=proof['workerIdentity'])
    snapshot = {key: value.copy() if type(value) is dict else value for key, value in proof.items()}
    validate_owned_controller_chain(snapshot, controller_identity=controller,
        worker_identity=custody.process_identity, deadline=deadline,
        current_controller=stable_identity(controller['pid']),
        current_supervisor=stable_identity(snapshot['supervisorIdentity']['pid']),
        current_worker=stable_identity(os.getpid()))
    return snapshot


def require_policy_approval(custody, approval, binding):
    """W05's custody method delegates here before any DDL, on authentic Linux.

    The independently provisioned authority binds the exact actual plain approval
    and its evidence. A template or a timestamp never substitutes for that grant.
    """
    need(sys.platform == 'linux', 'SOURCE_CONTROL_NATIVE_ORIGINAL_ACCESS_REQUIRED')
    from installation_native import SourceCustody
    from recovery_environment_contract import decode
    from recovery_native_browser import current_window
    from recovery_native_goview_authority import stable_identity
    from source_installation import left
    need(type(custody) is SourceCustody, 'SOURCE_CONTROL_ACTUAL_NATIVE_CUSTODY_REQUIRED')
    deadline = custody.deadline
    custody.guard()
    s = custody.selection
    select_action(s)
    need(sys.modules[SourceCustody.__module__].__file__ == s['entryPin']['path'],
         'SOURCE_CONTROL_W05_PROVIDER_NOT_SELECTED')
    installed = custody.installation['filePins'] + custody.installation['dependencyPins']
    need(s['entryPin'] in installed and s['entryPin'] in s['sourcePins'],
         'SOURCE_CONTROL_W05_PROVIDER_NOT_INSTALLED')
    custody.raw(s['entryPin'])
    own_pins = [p for p in installed if p['path'] == __file__]
    need(len(own_pins) == 1 and own_pins[0] in s['sourcePins'],
         'SOURCE_CONTROL_SELECTOR_NOT_INSTALLED')
    custody.raw(own_pins[0])
    owned_chain = require_owned_controller(custody)
    need(decode(custody.raw(s['policyAppendBindingPin'])) == binding and
         decode(custody.raw(binding['approvalPin'])) == approval,
         'SOURCE_CONTROL_ACTUAL_POLICY_APPROVAL_PIN_CHANGED')
    for key in ('approvalEvidencePin', 'coverageReportPin'):
        custody.raw(approval[key])
    abi = decode(custody.raw(s['r4InterfacePin']))
    validate_r4_abi(s, custody.installation, abi, binding)
    for key in ('twoOriginalEntriesPin', 'versionTableAppendPin'):
        custody.raw(binding[key])
    candidate = custody.signed(s['candidateReviewPin'])
    validate_candidate(s, custody.installation, candidate)
    custody.raw(candidate['reviewEvidencePin'])
    authority = custody.signed(s['policyApprovalAuthorityPin'])
    need(authority.get('authorityKeyPin') == custody.authority_pin,
         'SOURCE_CONTROL_INDEPENDENT_POLICY_AUTHORITY_REQUIRED')
    validate_policy_approval(s, approval, binding, authority)
    custody.guard()
    issuer = custody.signed(s['issuerSelectionPin'])
    need(stable_identity(issuer['identity']['pid']) == issuer['identity'],
         'SOURCE_CONTROL_CURRENT_ISSUER_IDENTITY_REQUIRED')
    need(decode(custody.raw(s['policyAppendBindingPin'])) == binding and
         decode(custody.raw(binding['approvalPin'])) == approval,
         'SOURCE_CONTROL_ACTUAL_POLICY_APPROVAL_PIN_CHANGED')
    need(require_owned_controller(custody) == owned_chain, 'SOURCE_CONTROL_CURRENT_OWNED_CHAIN_CHANGED')
    need(custody.deadline == deadline, 'SOURCE_CONTROL_OWNED_CHAIN_DEADLINE_CHANGED')
    # No native/source callbacks after the final authentic current originals.
    records = {key: custody.signed(s[key]) for key in ('sourceScopePin', 'exclusiveClaimPin',
        'reviewPin', 'adapterReviewPin', 'issuerSelectionPin', 'candidateReviewPin', 'policyApprovalAuthorityPin')}
    current_selection = custody.signed(custody.selection_pin)
    need(current_selection == s and records['candidateReviewPin'] == candidate and
         records['policyApprovalAuthorityPin'] == authority, 'SOURCE_CONTROL_CURRENT_AUTHORITY_CHANGED')
    validate_links(s, source=records['sourceScopePin'], claim=records['exclusiveClaimPin'],
        issuer=records['issuerSelectionPin'], review=records['reviewPin'], adapter=records['adapterReviewPin'],
        installation=custody.installation, abi=abi, append_binding=binding, candidate_review=candidate)
    validate_policy_approval(s, approval, binding, records['policyApprovalAuthorityPin'])
    need(records['issuerSelectionPin'] == issuer, 'SOURCE_CONTROL_CURRENT_AUTHORITY_CHANGED')
    require_window_binding(s, records.values())
    for value in [current_selection, *records.values()]:
        current_window(value)
    left(deadline)
    return True


def selected_material(selection_pin, authority_pin, *, deadline):
    """Same Linux controller calls W05 execute_owned later, with fresh guards.

    This returns Pins only and starts nothing. The external owner must select
    both trust environment values independently before this call. The W05
    custody verifier reads current signed originals and admits the native graph.
    """
    need(sys.platform == 'linux', 'SOURCE_CONTROL_NATIVE_ORIGINAL_ACCESS_REQUIRED')
    from installation_native import SourceCustody
    from recovery_environment_contract import decode
    from recovery_native_browser import current_window
    from recovery_native_goview_authority import stable_identity
    from source_installation import left
    custody = SourceCustody(selection_pin, authority_pin, deadline)
    s = custody.selection
    installed = custody.installation['filePins'] + custody.installation['dependencyPins']
    need(sys.modules[SourceCustody.__module__].__file__ == s['entryPin']['path'],
         'SOURCE_CONTROL_W05_PROVIDER_NOT_SELECTED')
    own_pins = [p for p in installed if p['path'] == __file__]
    need(len(own_pins) == 1 and own_pins[0] in s['sourcePins'],
         'SOURCE_CONTROL_SELECTOR_NOT_INSTALLED')
    custody.raw(own_pins[0])
    issuer = custody.signed(s['issuerSelectionPin'])
    need(issuer['authorityKeyPin'] == authority_pin, 'SOURCE_CONTROL_INDEPENDENT_AUTHORITY_MISMATCH')
    abi = decode(custody.raw(s['r4InterfacePin']))
    append_binding = decode(custody.raw(s['policyAppendBindingPin']))
    candidate_review = custody.signed(s['candidateReviewPin'])
    approval = decode(custody.raw(append_binding['approvalPin']))
    policy_authority = custody.signed(s['policyApprovalAuthorityPin'])
    documents = {key: custody.signed(s[key]) for key in
                 ('sourceScopePin', 'exclusiveClaimPin', 'reviewPin', 'adapterReviewPin')}
    validate_links(s, source=documents['sourceScopePin'],
        claim=documents['exclusiveClaimPin'], issuer=issuer,
        review=documents['reviewPin'], adapter=documents['adapterReviewPin'],
        installation=custody.installation, abi=abi, append_binding=append_binding, candidate_review=candidate_review)
    require_policy_approval(custody, approval, append_binding)
    current_window(issuer)
    need(stable_identity(issuer['identity']['pid']) == issuer['identity'],
         'SOURCE_CONTROL_CURRENT_ISSUER_IDENTITY_REQUIRED')
    custody.guard()
    need(decode(custody.raw(s['r4InterfacePin'])) == abi, 'SOURCE_CONTROL_CURRENT_ISSUER_OR_ABI_CHANGED')
    need(decode(custody.raw(s['policyAppendBindingPin'])) == append_binding and
         decode(custody.raw(append_binding['approvalPin'])) == approval,
         'SOURCE_CONTROL_ACTUAL_POLICY_APPROVAL_PIN_CHANGED')
    # Finish all source/native/process callbacks before the last authentic reads.
    documents['issuerSelectionPin'] = issuer
    documents['candidateReviewPin'] = candidate_review
    documents['policyApprovalAuthorityPin'] = policy_authority
    current = {key: custody.signed(s[key]) for key in documents}
    current_selection = custody.signed(selection_pin)
    need(current_selection == s and current == documents, 'SOURCE_CONTROL_CURRENT_AUTHORITY_CHANGED')
    validate_links(s, source=current['sourceScopePin'], claim=current['exclusiveClaimPin'],
        issuer=current['issuerSelectionPin'], review=current['reviewPin'], adapter=current['adapterReviewPin'],
        installation=custody.installation, abi=abi, append_binding=append_binding, candidate_review=candidate_review)
    validate_policy_approval(s, approval, append_binding, current['policyApprovalAuthorityPin'])
    require_window_binding(s, current.values())
    for value in [current_selection, *current.values()]:
        current_window(value)
    left(deadline)
    return dict(schemaVersion='W01FiniteSourceInstallationR4ControlMaterial/v1', action=ACTION,
        binding=s['binding'].copy(), selectionPin=selection_pin.copy(), authorityKeyPin=authority_pin.copy(),
        sourceScopePin=s['sourceScopePin'].copy(), exclusiveClaimPin=s['exclusiveClaimPin'].copy(),
        issuerSelectionPin=s['issuerSelectionPin'].copy(), r4InterfacePin=s['r4InterfacePin'].copy(),
        policyAppendBindingPin=s['policyAppendBindingPin'].copy(), candidateReviewPin=s['candidateReviewPin'].copy(),
        policyApprovalAuthorityPin=s['policyApprovalAuthorityPin'].copy(), executionReleased=False)
