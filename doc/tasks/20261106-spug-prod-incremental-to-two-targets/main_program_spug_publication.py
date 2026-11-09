"""Explicit MAIN registration/configuration publication; prepare is local only.

No backup/restore is dispatched. An attempted apply is never automatically retried.
Minimal PASS is projected only after actual control and product readbacks. Private
inputs and rich stage evidence stay in the explicitly selected private directory.
"""
import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import uuid

import main_program_control_activation as activation
import main_program_installation_selection as contract

TASK = Path(__file__).resolve().parent
PRIVATE = Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
SOURCES = activation.SOURCES
HOSTS = ('57', '58', '59')
HISTORICAL_REGISTRATION_PLAN_SHA256 = 'def93cfb18192a38875e9e7edaccf45927c14398fe3eb3c46bcda7ca08b3def4'
CONTAINER = 'f615a60c76f46e4f6ae20ea6298f737fb9786684ce941fcc15763654461265bf'
DOCKER = 'C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
RUNTIME = 'C:/Spug/runtime/ops/spug'
PRODUCT_FILES = ('smallapp_entry.py', 'smallapp_adapter.py', 'smallapp-entry.locations.conf',
    *('smallapp-ui/' + n for n in ('app.js','simple.js','index.html','simple.css',
                                  'embedded.js','embedded.css','package-catalog.js','package-catalog.css')))
SETTINGS = dict(simple='/var/lib/intruoyi-spug/smallapp-simple-settings.json',
    entry='/var/lib/intruoyi-spug/smallapp-entry-settings.json',
    bridge='/run/intruoyi-spug/smallapp-bridge.private.json')
TRUE_CHECKS = ('publicationCompleted','selectorsReadBack','actualNativeSelectionsVerified',
    'productSettingsReadBack','historicalFingerprintsUnchanged','oldFilesPreserved',
    'protectedSpugUnchanged','businessContainersUnchanged','fstabAndMountsUnchanged',
    'oldTasksUnchanged','productFilesUnchanged','controlIdentityVerified')


def need(value, code):
    if not value:
        raise ValueError('MAIN_SPUG_' + code)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def read_document(path):
    return json.loads(Path(path).read_bytes().decode('utf-8'), object_pairs_hook=contract.document)


def file_pin(path):
    path = Path(path)
    need(path.is_absolute() and path.parent.resolve(strict=True) == path.parent and
         not path.is_symlink() and path.is_file(), 'FILE_ALIAS')
    before = path.stat()
    need(before.st_nlink == 1, 'FILE_HARDLINK')
    raw = path.read_bytes(); after = path.stat()
    identity = lambda s: (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    need(identity(before) == identity(after), 'FILE_CHANGED')
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def checked_local(path, expected):
    actual = file_pin(path)
    need(type(expected) is dict and set(expected) == {'path','bytes','sha256'} and
         type(expected['bytes']) is int and expected['bytes'] > 0 and
         type(expected['sha256']) is str and re.fullmatch('[0-9a-f]{64}',expected['sha256']) and
         actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256'], 'PIN_CHANGED')
    return read_document(path)


def verify_bytes(reference):
    need(file_pin(reference['path']) == reference, 'ORIGINAL_BYTES_CHANGED')
    raw = Path(reference['path']).read_bytes()
    need(hashlib.sha256(raw).hexdigest() == reference['sha256'] and len(raw) == reference['bytes'],
         'ORIGINAL_BYTES_CHANGED')
    return raw


def sync_parent(path):
    if os.name == 'posix':
        fd = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)


def exclusive_bytes(path, raw):
    path = Path(path)
    need(path.is_absolute() and path.parent.resolve(strict=True) == path.parent and
         not path.is_symlink(), 'OUTPUT_ALIAS')
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600),'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    sync_parent(path)
    need(path.read_bytes() == raw, 'OUTPUT_READBACK_FAILED')
    return file_pin(path)


def preflight_replace(active, archive, staged, expected):
    paths = [Path(p) for p in (active,archive,staged)]
    need(len(set(paths)) == 3, 'PUBLICATION_PATH_COLLISION')
    for path in paths:
        need(path.is_absolute() and path.parent.resolve(strict=True) == path.parent and
             not path.is_symlink(), 'PUBLICATION_PATH_ALIAS')
    active, archive, staged = paths
    need(not archive.exists() and not staged.exists(), 'PUBLICATION_ATTEMPT_EXISTS')
    if expected is None:
        need(not active.exists(), 'EXPECTED_ABSENT_FILE_EXISTS')
    else:
        need(file_pin(active) == expected, 'ORIGINAL_PIN_CHANGED')


def replace_once(active, archive, staged, expected, raw):
    """One exact file transition. Never repair, overwrite a backup, or resume."""
    active, archive, staged = map(Path,(active,archive,staged))
    preflight_replace(active,archive,staged,expected)
    if expected is None:
        return dict(previousPin=None, installedPin=exclusive_bytes(active,raw))
    original = active.read_bytes()
    need(file_pin(active) == expected, 'ORIGINAL_PIN_CHANGED')
    previous = exclusive_bytes(archive,original)
    need(all(previous[k] == expected[k] for k in ('bytes','sha256')), 'ORIGINAL_BACKUP_CHANGED')
    need(file_pin(active) == expected, 'ORIGINAL_PIN_CHANGED')
    exclusive_bytes(staged,raw)
    need(file_pin(active) == expected, 'ORIGINAL_PIN_CHANGED')
    os.replace(staged,active); sync_parent(active)
    need(active.read_bytes() == raw, 'INSTALLED_READBACK_FAILED')
    return dict(previousPin=previous, installedPin=file_pin(active))


def bridge_fingerprint(connection):
    submit, query = connection.get('submitUrl'), connection.get('queryUrlTemplate')
    need(type(submit) is str and type(query) is str and query.count('{operationId}') == 1,
         'HISTORY_ROUTE_ENDPOINT_INVALID')
    # Exactly HttpBridge's persisted fingerprint, including its default ASCII JSON.
    return hashlib.sha256(json.dumps([submit,query.replace('{operationId}','operation-check')],
                                     separators=(',',':')).encode()).hexdigest()


def validate_history_routes(secret):
    old = secret['originalSpug']; before = old['bridge']['value']; after = secret['bridgeSettings']
    need(bridge_fingerprint(before) == bridge_fingerprint(after), 'HISTORY_ROUTE_ROOT_CHANGED')
    need(after.get('sourceConnections') == before.get('sourceConnections'), 'HISTORY_ROUTE_EXECUTION_MAPPING_CHANGED')
    connections = {name:row['value'] for name,row in old['connections'].items()}
    new = dict(connections)
    need(not set(connections) & set(secret['newConnections']), 'HISTORY_ROUTE_OLD_CONNECTION_OVERWRITE')
    new.update(secret['newConnections'])
    counts = {}
    for lane in ('sourceConnections','targetConnections'):
        previous, updated = before.get(lane,{}), after.get(lane,{})
        need(type(previous) is dict and type(updated) is dict and set(previous) <= set(updated),
             'HISTORY_ROUTE_REMOVED')
        for ref,name in previous.items():
            need(name in connections and updated[ref] in new, 'HISTORY_ROUTE_CONNECTION_MISSING')
            original, candidate = connections[name], new[updated[ref]]
            need(bridge_fingerprint(original) == bridge_fingerprint(candidate), 'HISTORY_ROUTE_FINGERPRINT_CHANGED')
            for key in ('credentialRef','selectionUrl'):
                need(candidate.get(key) == original.get(key), 'HISTORY_ROUTE_AUTH_OR_SELECTION_CHANGED')
            permitted = {'sourceConfigRefs','targetConfigRefs','selectedTargetPreflight'}
            need({k:v for k,v in original.items() if k not in permitted} ==
                 {k:v for k,v in candidate.items() if k not in permitted}, 'HISTORY_ROUTE_UNAPPROVED_CHANGE')
            for key in ('sourceConfigRefs','targetConfigRefs'):
                need(set(original.get(key,[])) <= set(candidate.get(key,[])), 'HISTORY_ROUTE_SCOPE_REMOVED')
        counts[lane] = len(previous)
    return dict(sourceRouteCount=counts['sourceConnections'],targetRouteCount=counts['targetConnections'],
                rootFingerprintUnchanged=True)


def validate_selection_routes(secret):
    bridge = secret['bridgeSettings']; routes = bridge.get('selectionConnections')
    need(type(routes) is dict and set(routes) == set(SOURCES), 'SELECTION_ROUTE_THREE_EXPLICIT_SOURCES_REQUIRED')
    execution = set(bridge.get('sourceConnections',{}).values()) | set(bridge.get('targetConnections',{}).values())
    for ref,name in routes.items():
        need(type(name) is str and re.fullmatch('[A-Za-z0-9_.-]+[.]json',name) and
             name in secret['newConnections'] and name not in execution, 'SELECTION_ROUTE_CONNECTION_NOT_DISTINCT')
        value = secret['newConnections'][name]
        need(type(value.get('sourceConfigRefs')) is list and set(value['sourceConfigRefs']) == set(SOURCES) and
             len(value['sourceConfigRefs']) == 3 and value.get('targetConfigRefs') == [] and
             ('selectedTargetPreflight' not in value or value['selectedTargetPreflight'] is False),
             'SELECTION_ROUTE_SCOPE_INVALID')
    targets = bridge.get('targetConnections',{})
    for target in secret['programTargets']:
        name = targets.get(target)
        need(name in secret['newConnections'], 'SELECTION_ROUTE_TARGET_CONNECTION_REQUIRED')
        value = secret['newConnections'][name]
        need(value.get('selectedTargetPreflight') is True and
             set(SOURCES) <= set(value.get('sourceConfigRefs',[])) and
             target in value.get('targetConfigRefs',[]), 'SELECTION_ROUTE_TARGET_ADMISSION_REQUIRED')


def validate_settings(secret, *, historical_registration_plan=None):
    original = secret['originalSpug']; entry = secret['entrySettings']; old_entry = original['entry']['value']
    need(set(entry) == set(old_entry) and len(entry['applications']) == len(old_entry['applications']) == 33 and
         entry['tasks'] == old_entry['tasks'] and len(entry['tasks']) == 3 and
         entry['initialOperationIds'] == old_entry['initialOperationIds'] and
         entry['registrationVersions'] == old_entry['registrationVersions'], 'SETTINGS_TASK_OR_APPLICATION_CHANGED')
    for old,new in zip(old_entry['applications'],entry['applications']):
        allowed = {'targetConfigRefs','registrationSha256'} if old['applicationId'] in SOURCES else set()
        need({k:v for k,v in old.items() if k not in allowed} ==
             {k:v for k,v in new.items() if k not in allowed} and
             set(old['targetConfigRefs']) <= set(new['targetConfigRefs']), 'SETTINGS_UNAPPROVED_APPLICATION_CHANGE')
    old_simple, simple = original['simple']['value'], secret['simpleSettings']
    historical_pin = None
    expected_binding_count = len(old_simple['bindings'])
    if historical_registration_plan is not None:
        path = Path(historical_registration_plan)
        need(path.is_absolute() and path.name == 'historical-registration-plan-r1.private.json',
             'SETTINGS_HISTORICAL_PATH_CHANGED')
        historical_pin = file_pin(path)
        need(historical_pin['sha256'] == HISTORICAL_REGISTRATION_PLAN_SHA256,
             'SETTINGS_HISTORICAL_PIN_CHANGED')
        approved = checked_local(path, historical_pin)
        need(approved['state'] == 'PLAN_ONLY' and
             all(approved['originalSpug'][key] == original[key] for key in ('simple','entry','bridge')),
             'SETTINGS_HISTORICAL_ORIGINAL_CHANGED')
        template = approved['simpleSettings']
        targets = secret['programTargets']
        extra = template['bindings'][-1]
        need(len(template['bindings']) == expected_binding_count+1 and
             extra['applicationId'] == SOURCES[-1] and
             extra['applicationId'] not in {row['applicationId'] for row in old_simple['bindings']} and
             len(targets) == len(set(targets)) == 3 and
             set(extra['overwriteTargetServers']) == {'172.30.30.'+suffix for suffix in HOSTS} and
             set(extra['overwriteTargetServers'].values()) == set(extra['restoreProgressBindings']) == set(targets) and
             simple == template, 'SETTINGS_HISTORICAL_TEMPLATE_CHANGED')
        expected_binding_count += 1
    need({k:v for k,v in old_simple.items() if k not in ('bindings','catalogueRestoreBindings')} ==
         {k:v for k,v in simple.items() if k not in ('bindings','catalogueRestoreBindings')} and
         len(simple['bindings']) == expected_binding_count, 'SETTINGS_SIMPLE_CHANGED')
    for old,new in zip(old_simple['bindings'],simple['bindings']):
        allowed = {'overwriteTargetServers','restoreProgressBindings','selectable'} if old['applicationId'] in SOURCES else set()
        need({k:v for k,v in old.items() if k not in allowed} ==
             {k:v for k,v in new.items() if k not in allowed}, 'SETTINGS_UNAPPROVED_BINDING_CHANGE')
        for key in ('overwriteTargetServers','restoreProgressBindings'):
            need(all(new.get(key,{}).get(k) == v for k,v in old.get(key,{}).items()), 'SETTINGS_OLD_TARGET_ROUTE_CHANGED')
    routes = simple.get('catalogueRestoreBindings',{})
    need(type(routes) is dict and all(routes.get(k) == v for k,v in old_simple.get('catalogueRestoreBindings',{}).items()) and
         all(app in SOURCES for key,app in routes.items() if key not in old_simple.get('catalogueRestoreBindings',{})),
         'SETTINGS_OLD_CATALOGUE_ROUTE_CHANGED')
    old_bridge, bridge = original['bridge']['value'], secret['bridgeSettings']
    allowed = {'sourceConnections','targetConnections','selectionConnections','sourceConfigRefs'}
    need({k:v for k,v in old_bridge.items() if k not in allowed} ==
         {k:v for k,v in bridge.items() if k not in allowed} and
         set(old_bridge['sourceConfigRefs']) <= set(bridge['sourceConfigRefs']), 'SETTINGS_BRIDGE_CHANGED')
    for lane,scope in (('sourceConnections',set(SOURCES)),('targetConnections',set(secret['programTargets']))):
        old, new = old_bridge.get(lane,{}), bridge.get(lane,{})
        need(all(new.get(k) == v for k,v in old.items() if k not in scope) and
             set(new)-set(old) <= scope, 'SETTINGS_UNAPPROVED_ROUTE_CHANGE')
    return historical_pin


def validate_product_selection(payload, configuration, source, target):
    import smallapp_entry
    rows = smallapp_entry.validated_selections(payload,configuration)
    matches = [r for r in rows.values() if r['sourceConfigRef'] == source]
    need(len(matches) == 1 and matches[0].get('historyErrorCode') is None and
         matches[0].get('recoveryPointRefs') and target in matches[0]['freshTargetConfigRefs'],
         'ACTUAL_PRODUCT_BRIDGE_SELECTION_UNAVAILABLE')
    return matches[0]


def private_document(private, reference, filename=None):
    root = Path(private).resolve(strict=True); path = Path(reference['path'])
    need(path.is_absolute() and path.parent == root and path.resolve(strict=True) == path and
         (filename is None or path.name == filename), 'PRIVATE_PATH_CHANGED')
    return checked_local(path,reference)


def validate_packages(private, build):
    need({row['variant'] for row in build['packages']} == {'standard','lightweight'} and
         len(build['packages']) == 2, 'TWO_REAL_PACKAGES_REQUIRED')
    pins = []
    for row in build['packages']:
        expected = 147 if row['variant'] == 'standard' else 146
        path = Path(private)/('package-'+build['targetCommit'][:7])/('backup-restore-'+row['variant']+'.tgz')
        ref = file_pin(path); need(ref['sha256'] == row['packageSha256'], 'PACKAGE_TGZ_CHANGED'); pins.append(ref)
        with tarfile.open(path,'r:gz') as archive:
            members = archive.getmembers(); names = [m.name for m in members]
            need(len(names) == len(set(names)) and all(m.isfile() for m in members), 'PACKAGE_MEMBER_ALIAS')
            manifest = json.loads(archive.extractfile('package.json').read(),object_pairs_hook=contract.document)
            files = manifest['files']
            need(len(files) == expected == row['fileCount'] and set(names) == set(files)|{'package.json'} and
                 hashlib.sha256(canonical(files)).hexdigest() == row['fileManifestSha256'] == manifest['packageSha256'],
                 'PACKAGE_MANIFEST_CHANGED')
            for name,sha in files.items():
                p = PurePosixPath(name)
                need(not p.is_absolute() and '..' not in p.parts and str(p) == name, 'PACKAGE_MEMBER_PATH')
                raw = archive.extractfile(name).read()
                need(hashlib.sha256(raw).hexdigest() == sha, 'PACKAGE_MEMBER_CHANGED')
                if name.endswith('.py'): compile(raw,name,'exec')
    return pins


def resource_files(report):
    fields = {'schemaVersion','status','sourceCommit','worktree','fileCount','files','changedFiles',
              'selectionConnectionsSupported','historyRoutesPreserved','testEvidencePin'}
    need(set(report) == fields and report['schemaVersion'] == 'MainProgramSpugResourceBuild/v1' and
         report['status'] == 'PASS' and type(report['sourceCommit']) is str and
         re.fullmatch('[0-9a-f]{40}',report['sourceCommit']) and type(report['worktree']) is str and
         Path(report['worktree']).is_absolute() and type(report['fileCount']) is int and report['fileCount'] == 11 and
         type(report['files']) is dict and set(report['files']) == {'ops/spug/'+n for n in PRODUCT_FILES} and
         report['changedFiles'] == ['ops/spug/smallapp_adapter.py'] and
         report['selectionConnectionsSupported'] is True and report['historyRoutesPreserved'] is True,
         'RESOURCE_BUILD_CONTRACT_INVALID')
    for value in report['files'].values():
        need(type(value) is dict and set(value) == {'bytes','sha256'} and type(value['bytes']) is int and
             value['bytes'] > 0 and contract.sha(value['sha256']), 'RESOURCE_BUILD_FILE_PIN_INVALID')
    return report['files']


def validate_resource_build(records, reference, private):
    report = records.pinned(reference); files = resource_files(report)
    proof = records.pinned(report['testEvidencePin'])
    fields = {'schemaVersion','status','actualExitCode','actualPassed','actualSkipped','inputPins','logPin'}
    test_path = 'doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_archived_source_catalogue_routing.py'
    need(set(proof) == fields and proof['schemaVersion'] == 'TaskSpugResourceValidation/v1' and proof['status'] == 'PASS' and
         type(proof['actualExitCode']) is int and proof['actualExitCode'] == 0 and
         type(proof['actualPassed']) is int and proof['actualPassed'] > 0 and
         type(proof['actualSkipped']) is int and proof['actualSkipped'] == 0 and
         type(proof['inputPins']) is dict and set(files)|{test_path} <= set(proof['inputPins']),
         'RESOURCE_BUILD_TEST_EVIDENCE_REQUIRED')
    root = Path(report['worktree']); need(root.resolve(strict=True) == root, 'RESOURCE_BUILD_WORKTREE_ALIAS')
    env = dict(os.environ,GIT_OPTIONAL_LOCKS='0')
    def git(args, raw=None):
        result = subprocess.run(['git','-C',str(root),*args],input=raw,capture_output=True,env=env,timeout=30)
        need(result.returncode == 0,'RESOURCE_BUILD_GIT_FAILED'); return result.stdout.decode('utf-8').strip()
    need(git(['rev-parse','HEAD']) == report['sourceCommit'] and
         git(['status','--porcelain','--untracked-files=all']) == '', 'RESOURCE_BUILD_CHECKOUT_NOT_CLOSED')
    pins = []
    for name,sha in proof['inputPins'].items():
        p = PurePosixPath(name)
        need(type(name) is str and str(p) == name and not p.is_absolute() and '..' not in p.parts and
             contract.sha(sha),'RESOURCE_BUILD_TEST_PATH_INVALID')
        path = root/name; actual = file_pin(path); need(actual['sha256'] == sha,'RESOURCE_BUILD_TEST_INPUT_CHANGED')
        if name in files:
            need(all(actual[k] == files[name][k] for k in ('bytes','sha256')), 'RESOURCE_BUILD_FILE_CHANGED')
        # The actual checkout byte representation is pinned separately; normalization
        # through this committed path must still name the exact HEAD blob.
        need(git(['hash-object','--path='+name,'--stdin'],path.read_bytes()) ==
             git(['rev-parse','HEAD:'+name]), 'RESOURCE_BUILD_INDEX_INPUT_CHANGED')
        pins.append(actual)
    log = Path(proof['logPin']['path'])
    need(log.parent == Path(private).resolve(strict=True), 'RESOURCE_BUILD_LOG_SCOPE')
    raw = verify_bytes(proof['logPin']); text = raw.decode('utf-8')
    summaries = re.findall(r'(?m)^\s*(?:=+\s*)?([0-9]+) passed(?:, [0-9]+ warnings?)? in [0-9.]+s[^\r\n]*$',text)
    need(summaries and int(summaries[-1]) == proof['actualPassed'] and
         not re.search(r'\b[0-9]+ (?:failed|skipped|errors?|xfailed|xpassed|deselected)\b',text),
         'RESOURCE_BUILD_TEST_LOG_NOT_PASSED')
    pins.append(proof['logPin'])
    return report,pins


def validate_activation_evidence(core, rich):
    need(rich.get('status') == 'PASS' and rich.get('activationCompleted') is True and
         all(rich.get(k) is True for k in ('actualImportsVerified','originalUnitPinsVerified','physicalLockVerified',
             'epochVerified','historyGuardVerified','apiVerified','argvVerified','environmentVerified','limitVerified',
             'noWorkersVerified',*contract.TRUE_FLAGS)) and
         all(rich.get(k) is False for k in contract.FALSE_FLAGS), 'ACTUAL_ACTIVATION_EVIDENCE_REQUIRED')
    need(all(rich.get(k) == core[k] for k in ('host','service','pid','sourceCommit','dropinPin')),
         'ACTUAL_ACTIVATION_IDENTITY_CHANGED')
    rows = [r for r in rich.get('controllersAfter',[]) if r.get('service') == core['service']]
    need(len(rows) == 1 and all(rows[0].get(k) == core[k] for k in
         ('engine','pid','controlConfigurationPin','ownerConfigurationPin','dropinPin')), 'ACTUAL_CONTROLLER_ROW_CHANGED')
    if core['role'] == 'source':
        need(rich.get('sourceCaptureVerified') is True and rich.get('sourceBaselineVerified') is True,
             'ACTUAL_CAPTURE_EVIDENCE_REQUIRED')
    else:
        need(rich.get('directlyAdmittedSources') == list(SOURCES) and rich.get('archiveViewsPreflightVerified') is True,
             'ACTUAL_SOURCE_ADMISSION_REQUIRED')
    if core['host'] != '172.30.30.57':
        need(rich.get('receiptRotated') is True and rich.get('completePreviousCustodyVerified') is True and
             rich.get('originalPathInventoryVerified') is True and all(rich.get(k) == core[k] for k in
             ('previousReceiptPin','currentReceiptPin')), 'ACTUAL_RECEIPT_CUSTODY_REQUIRED')


def load_activation_evidence(records, private, reference, core):
    """Read original reports or the two explicitly approved, immutable r2 proofs."""
    stem = 'main-program-control-activation-'+core['host'].rsplit('.',1)[-1]+'-'+core['role']+'-'+core['sourceCommit'][:7]
    identity = dict(host='172.30.30.59',service='spug-main-restore-59-20261104-v3.service',role='target',
                    sourceCommit='899730de38c0e883245c11f2ad7986424ecbaf80')
    preswitch_identity = dict(identity,host='172.30.30.58',service='spug-main-restore-58-20261104-v3.service')
    need(type(reference) is dict and type(reference.get('path')) is str, 'ACTIVATION_EVIDENCE_PIN_REQUIRED')
    if Path(reference['path']).name == stem+'.private.json':
        if all(core.get(k) == v for k,v in identity.items()):
            need(reference.get('bytes') == 467 and reference.get('sha256') ==
                 '09233019f9a6cb10928c22343ad022891c174ede712cb6767a6d1edcb77b8dfa',
                 'ACTIVATION_CONTINUATION_ORIGINAL_FAILURE_REPLACED')
        if all(core.get(k) == v for k,v in preswitch_identity.items()):
            need(all(reference.get(k) == activation.PRESWITCH_FAILURE_PIN[k] for k in ('bytes','sha256')),
                 'ACTIVATION_CONTINUATION_ORIGINAL_FAILURE_REPLACED')
        rich = private_document(private,reference,stem+'.private.json')
        validate_activation_evidence(core,rich)
        return rich,[reference]
    if Path(reference['path']).name == 'main-program-control-activation-58-target-899730d-r2.private.json':
        need(all(core.get(k) == v for k,v in preswitch_identity.items()), 'ACTIVATION_CONTINUATION_SCOPE_CHANGED')
        rich = private_document(private,reference,'main-program-control-activation-58-target-899730d-r2.private.json')
        validate_activation_evidence(core,rich)
        need(type(rich.get('attemptRevision')) is int and rich['attemptRevision'] == 2 and
             rich.get('preSwitchFailureRevalidated') is True, 'ACTIVATION_CONTINUATION_REVALIDATION_REQUIRED')
        continuation = activation.load_continuation_originals(records,private,rich.get('preSwitchContinuationPin'),preswitch_identity)
        context = continuation['context']; selected = context['selected']
        need(all(rich.get(k) == continuation[k] for k in
             ('preSwitchContinuationPin','priorAttemptPin','priorFailurePin','priorRemoteResultPin')),
             'ACTIVATION_CONTINUATION_CONTRACT_CHANGED')
        need(all(core.get(k) == context['inputs'][k] for k in ('buildPin','planPin')) and
             all(core.get(k) == selected[source] for k,source in
             (('service','service'),('engine','engine'),('controlConfigurationPin','controlPin'),('ownerConfigurationPin','ownerPin'))) and
             core['dropinPin']['path'] == context['dropinPath'], 'ACTIVATION_CONTINUATION_PREPARED_CONTEXT_CHANGED')
        old_receipt = context['oldReceiptPin']
        need(core['previousReceiptPin']['path'] == context['archiveReceiptPath'] and
             all(core['previousReceiptPin'][k] == old_receipt[k] for k in ('bytes','sha256')) and
             core['currentReceiptPin']['path'] == old_receipt['path'], 'ACTIVATION_CONTINUATION_RECEIPT_CHANGED')
        return rich,[reference,*continuation['privatePins']]
    stem = 'main-program-control-activation-59-target-899730d'
    need(Path(reference['path']).name == stem+'-r2.private.json' and
         all(core.get(k) == v for k,v in identity.items()), 'ACTIVATION_CONTINUATION_SCOPE_CHANGED')
    rich = private_document(private,reference,stem+'-r2.private.json')
    validate_activation_evidence(core,rich)
    need(type(rich.get('attemptRevision')) is int and rich['attemptRevision'] == 2 and
         rich.get('initialFailureRevalidated') is True, 'ACTIVATION_CONTINUATION_REVALIDATION_REQUIRED')
    def local(ref,name):
        need(type(ref) is dict and ref.get('file') == name, 'ACTIVATION_CONTINUATION_LOCAL_FILE_CHANGED')
        return records.pinned(ref)
    continuation = local(rich.get('initialFailureContinuationPin'),
        'main-program-control-initial-continuation-59-target-899730d-r2.json')
    fields = {'schemaVersion','status','attemptRevision',*identity,'originalInputsPin','priorAttemptPin',
              'priorFailurePin','priorRemoteResultPin','readonlyObservationPin','originalEnvironmentObservationPin'}
    need(set(continuation) == fields and continuation['schemaVersion'] == 'MainControlActivationInitialContinuation/v1' and
         continuation['status'] == 'READY_FOR_EXPLICIT_CONTINUATION' and type(continuation['attemptRevision']) is int and
         continuation['attemptRevision'] == 2 and all(continuation[k] == v for k,v in identity.items()) and
         all(rich.get(k) == continuation[k] for k in ('priorAttemptPin','priorFailurePin','priorRemoteResultPin')),
         'ACTIVATION_CONTINUATION_CONTRACT_CHANGED')
    failure_pin, attempt_pin = continuation['priorFailurePin'],continuation['priorAttemptPin']
    need(failure_pin.get('bytes') == 467 and
         failure_pin.get('sha256') == '09233019f9a6cb10928c22343ad022891c174ede712cb6767a6d1edcb77b8dfa' and
         attempt_pin.get('bytes') == 6536 and
         attempt_pin.get('sha256') == '5f539c5e3557da1f6d0f8c4bf141e8e3e9ac64bb58a2ece43cc46c835b2ca1e1',
         'ACTIVATION_CONTINUATION_ORIGINAL_PIN_CHANGED')
    failure = private_document(private,failure_pin,stem+'.private.json')
    attempt = private_document(private,attempt_pin,stem+'.attempt.private.json')
    need(failure['status'] == 'FAILED' and failure['stage'] == 'initial' and failure['errorType'] == 'ValueError' and
         failure['errorCode'] == 'CONTROL_ENVIRONMENT_CHANGED' and all(failure.get(k) is False for k in
         ('activationCompleted','backupDispatched','restoreDispatched','businessMutationDispatched',
          'controlApiQueriesPerformed','queryAuditWritesMayOccur')) and
         all(failure.get(k) == v for k,v in identity.items() if k != 'role') and
         attempt.get('status') == 'PREPARED_NOT_ACTIVATED' and attempt.get('dispatchRequested') is True and
         all(attempt.get(k) == v for k,v in identity.items() if k != 'service') and
         attempt.get('scriptSha256') == '61f05b3a58a0146794c4d2bdb4331517228bc7142e79005677fc4f76af41f94c',
         'ACTIVATION_CONTINUATION_ORIGINAL_FAILURE_CHANGED')
    original_pin = continuation['originalInputsPin']
    original = local(original_pin,stem+'-inputs.json')
    previous_inputs = [p for p in attempt['inputPins'] if Path(p['path']).name == original_pin['file']]
    need(len(previous_inputs) == 1 and all(previous_inputs[0][k] == original_pin[k] for k in ('bytes','sha256')) and
         original.get('schemaVersion') == 'MainProgramControlActivationInputs/v1' and original.get('suffix') == '59' and
         original.get('role') == 'target' and original.get('sourceCommit') == identity['sourceCommit'] and
         original.get('outputFile') == stem+'.json' and
         all(original.get(k) == core.get(k) for k in ('buildPin','planPin')),
         'ACTIVATION_CONTINUATION_ORIGINAL_INPUT_CHANGED')
    observation = local(continuation['readonlyObservationPin'],
        'main-program-control-initial-observation-59-target-899730d-r2.json')
    false_fields = ('serverFilesWritten','controlServicesReloaded','backupDispatched','restoreDispatched')
    fields = {'schemaVersion','status',*identity,'observedAt','originalInputsPin','priorAttemptPin','priorFailurePin',
              'priorRemoteResultPin','originalEnvironmentObservationPin','controller','oldReceiptPin','auditPath',
              'auditFiles','absentPaths',*false_fields}
    need(set(observation) == fields and observation['schemaVersion'] == 'MainControlInitialFailureObservation/v1' and
         observation['status'] == 'PASS' and all(observation.get(k) is False for k in false_fields) and
         all(observation[k] == v for k,v in identity.items()) and all(observation[k] == continuation[k] for k in
         ('originalInputsPin','priorAttemptPin','priorFailurePin','priorRemoteResultPin','originalEnvironmentObservationPin')),
         'ACTIVATION_CONTINUATION_READONLY_OBSERVATION_CHANGED')
    baseline = local(continuation['originalEnvironmentObservationPin'],'main-program-control-environment-baseline-59-r2.json')
    fields = {'schemaVersion','status','host','observedAt','unitObservationPin','privateSnapshotPin','controllers',*false_fields}
    need(set(baseline) == fields and baseline['schemaVersion'] == 'MainControlEnvironmentBaseline/v1' and
         baseline['status'] == 'PASS' and baseline['host'] == identity['host'] and
         all(baseline.get(k) is False for k in false_fields) and
         baseline['unitObservationPin'] == original['unitObservationPin'] and
         baseline['controllers'] == [observation['controller']], 'ACTIVATION_CONTINUATION_BASELINE_CHANGED')
    unit = records.pinned(baseline['unitObservationPin'])
    units = [row for row in unit['controllers'] if row['service'] == identity['service']]
    controller = observation['controller']
    fields = {'service','pid','engine','controlConfigurationPin','ownerConfigurationPin','argvSha256','unitPin',
              'dropinPins','environmentSha256','systemdEnvironmentSha256'}
    need(set(controller) == fields and len(units) == 1 and all(controller[k] == units[0][k] for k in
         ('service','pid','unitPin','dropinPins')) and all(contract.sha(controller[k]) for k in
         ('argvSha256','environmentSha256','systemdEnvironmentSha256')), 'ACTIVATION_CONTINUATION_CONTROLLER_CHANGED')
    private_baseline_pin = baseline['privateSnapshotPin']
    private_baseline = private_document(private,private_baseline_pin,'main-program-control-environment-baseline-59-r2.private.json')
    projected = dict(private_baseline,controllers=[{k:v for k,v in row.items() if k not in
        ('systemdEnvironmentRaw','declaredEnvironment')} for row in private_baseline['controllers']],
        privateSnapshotPin=private_baseline_pin)
    need(projected == baseline and len(private_baseline['controllers']) == 1 and
         hashlib.sha256(private_baseline['controllers'][0]['systemdEnvironmentRaw'].encode('utf-8')).hexdigest() ==
         controller['systemdEnvironmentSha256'], 'ACTIVATION_CONTINUATION_PRIVATE_BASELINE_CHANGED')
    root = PurePosixPath(controller['engine']).parent
    need(root.is_absolute() and root == PurePosixPath(core['engine']).parent,
         'ACTIVATION_CONTINUATION_ENGINE_CHANGED')
    audit = str(root/'configuration/main-activation-target-899730d')
    archived = str(root/'configuration/target-installation-before-main-899730d.json')
    remote_result, old_receipt = continuation['priorRemoteResultPin'],observation['oldReceiptPin']
    contract.remote_pin(remote_result); contract.remote_pin(old_receipt)
    need(remote_result['path'] == audit+'/result.private.json' and
         all(remote_result[k] == failure_pin[k] for k in ('bytes','sha256')) and
         observation['auditPath'] == audit and observation['auditFiles'] == [remote_result] and
         core['previousReceiptPin']['path'] == archived and
         all(core['previousReceiptPin'][k] == old_receipt[k] for k in ('bytes','sha256')) and
         core['currentReceiptPin']['path'] == old_receipt['path'] and observation['absentPaths'] ==
         [core['dropinPin']['path'],archived,old_receipt['path']+'.main-899730d.pending'],
         'ACTIVATION_CONTINUATION_ORIGINAL_AUDIT_OR_RECEIPT_CHANGED')
    return rich,[reference,failure_pin,attempt_pin,private_baseline_pin]


def selector_rows(secret, controllers):
    result = {}
    for suffix in HOSTS:
        rows = [dict(row,role='target') for row in secret['registrations'][suffix]]
        if suffix == '57': rows += [dict(row,role='source') for row in secret['sourceRegistrationSelectors']]
        need(len(rows) == (6 if suffix == '57' else 3), 'SELECTOR_COUNT')
        documents = {row['pin']['path']:row for row in secret['documentsByHost'][suffix]}
        result[suffix] = []
        for row in rows:
            source = row['sourceConfigRef']; need(source in SOURCES, 'SELECTOR_SOURCE')
            control = next(c for c in controllers[suffix] if c['role'] == row['role'])
            configuration = documents[control['controlConfigurationPin']['path']]['value']
            expected = str(PurePosixPath(configuration['registryRoot'])/'applications'/(source+'.pin.json'))
            need(row['selectorPath'] == expected and row['pin']['path'] in documents, 'SELECTOR_SCOPE_CHANGED')
            document = documents[row['pin']['path']]
            need(document['pin'] == row['pin'] and document['value'].get('applicationId') == source and
                 document['value'].get('sourceConfigRef') == source, 'REGISTRATION_IDENTITY_CHANGED')
            ref = row['pin']; raw = canonical(document['value'])
            need(ref['bytes'] == len(raw) and ref['sha256'] == hashlib.sha256(raw).hexdigest(), 'REGISTRATION_PIN_CHANGED')
            app = next(a for a in secret['entrySettings']['applications'] if a['applicationId'] == source)
            need(app['registrationSha256'] == ref['sha256'] and
                 set(secret['programTargets']) <= set(app['targetConfigRefs']), 'REGISTRATION_PROJECTION_CHANGED')
            result[suffix].append(dict(path=expected,value=ref,registrationPin=ref))
        need(len({r['path'] for r in result[suffix]}) == len(rows) and
             {r['sourceConfigRef'] for r in rows} == set(SOURCES), 'SELECTOR_DUPLICATE')
    return result


def prepare(task, private, inputs_file):
    records = contract.Records(task); inputs = records.read(inputs_file)
    if inputs.get('schemaVersion') == 'MainProgramSpugPublicationInputs/v2':
        return prepare_v2(records,private,inputs,records.references[inputs_file])
    fields = {'schemaVersion','sourceCommit','buildPin','planPin','spugResourceBuildPin','previousAutomaticSelectionPin',
              'controllersByHost','activationEvidenceByHost','publicationObservationPin','outputFile'}
    need(set(inputs) == fields and inputs['schemaVersion'] == 'MainProgramSpugPublicationInputs/v1' and
         type(inputs['sourceCommit']) is str and re.fullmatch('[0-9a-f]{40}',inputs['sourceCommit']), 'INPUTS_INVALID')
    commit = inputs['sourceCommit']; short = commit[:7]
    need(inputs['outputFile'] == 'main-program-spug-installation-'+short+'.json', 'OUTPUT_NAME_INVALID')
    previous = contract._previous(records,inputs['previousAutomaticSelectionPin'])
    targets = {'57':'intruoyi-main-57-safe-restore-20261105-v2',**{s:r['targetConfigRef'] for s,r in previous.items()}}
    build = contract._build(records,inputs); plan = contract._plan(records,inputs,targets)
    activation.validate_coverage(records,build)
    package_pins = validate_packages(private,build)
    resource,resource_pins = validate_resource_build(records,inputs['spugResourceBuildPin'],private)
    need(plan.get('sourceRefs') == list(SOURCES) and plan.get('sourceArchiveProtectionCount') == 9,
         'THREE_SOURCE_VIEW_PLAN_REQUIRED')
    secret = private_document(private,plan['privatePlanPin'],'main-program-configuration-plan-r4.private.json')
    need(secret.get('schemaVersion') == 'MainProgramConfigurationInstallationPlan/v1' and
         secret['sourceCommit'] == commit and secret['status'] == plan['status'] and secret['build'] == build,
         'PRIVATE_PLAN_CHANGED')
    secret['programTargets'] = plan['programTargets']
    controllers = {}; private_pins = [plan['privatePlanPin']]
    need(set(inputs['controllersByHost']) == set(HOSTS) == set(inputs['activationEvidenceByHost']), 'FOUR_CONTROLS_REQUIRED')
    for suffix,roles in contract.ROLES.items():
        need(len(inputs['controllersByHost'][suffix]) == len(roles) == len(inputs['activationEvidenceByHost'][suffix]),
             'FOUR_CONTROLS_REQUIRED')
        need([{k:r[k] for k in ('role','service','engine','controlPin','ownerPin')} for r in secret['controllers'][suffix]] ==
             plan['controllers'][suffix], 'PRIVATE_CONTROL_PLAN_CHANGED')
        controllers[suffix] = []
        for index,role in enumerate(roles):
            reference = inputs['controllersByHost'][suffix][index]
            expected_name = 'main-program-control-activation-'+suffix+'-'+role+'-'+short+'.json'
            need(reference['file'] == expected_name, 'ACTIVATION_FILE_REQUIRED')
            core = contract._activation(records,reference,inputs,build,plan['controllers'][suffix][index],
                suffix,None if role == 'source' else targets[suffix],previous.get(suffix))
            proof = inputs['activationEvidenceByHost'][suffix][index]
            rich,evidence_pins = load_activation_evidence(records,private,proof,core)
            private_pins.extend(evidence_pins); controllers[suffix].append(core)
        selected = secret['currentSelections'][suffix]
        need(selected['currentInstallationSelectionPin'] == inputs['previousAutomaticSelectionPin'], 'PREVIOUS_SELECTION_CHANGED')
        for ref in selected['localInstallationPins']:
            path = Path(ref['path']); need(path.parent == Path(task).resolve(strict=True), 'ORIGINAL_EVIDENCE_SCOPE')
            checked_local(path,ref); private_pins.append(ref)
    need(len({r['pid'] for r in controllers['57']}) == 2, 'CONTROL_PID_COLLISION')
    return _prepare_publication_graph(records,inputs,private,plan,secret,controllers,targets,
        private_pins,package_pins,resource,resource_pins)


def _prepare_publication_graph(records, inputs, private, plan, secret, controllers, targets,
                               private_pins, package_pins, resource, resource_pins, *, extra_pins=()):
    commit=inputs['sourceCommit'];short=commit[:7]
    history = validate_history_routes(secret)
    historical_pin = validate_settings(secret,
        historical_registration_plan=Path(private)/'historical-registration-plan-r1.private.json')
    private_pins.append(historical_pin)
    validate_selection_routes(secret)
    selectors = selector_rows(secret,controllers)
    observation = private_document(private,inputs['publicationObservationPin']); private_pins.append(inputs['publicationObservationPin'])
    if inputs['schemaVersion']=='MainProgramSpugPublicationInputs/v2':
        need(set(observation)=={'schemaVersion','sourceCommit','revisionId','controlGenerationPin','spugResourceBuildPin',
            'selectorsByHost','hostPreservationByHost','spug'} and
            observation['schemaVersion']=='MainProgramSpugPublicationObservation/v2' and
            all(observation[k]==inputs[k] for k in ('sourceCommit','revisionId','controlGenerationPin','spugResourceBuildPin')),
            'V2_OBSERVATION_CHANGED')
    else:
        need(set(observation) == {'schemaVersion','sourceCommit','selectorsByHost','hostPreservationByHost','spug'} and
             observation['schemaVersion'] == 'MainProgramSpugPublicationObservation/v1' and
             observation['sourceCommit'] == commit, 'OBSERVATION_REQUIRED')
    need(set(observation['selectorsByHost']) == set(HOSTS) == set(observation['hostPreservationByHost']), 'OBSERVATION_REQUIRED')
    host_specs = {}
    for suffix in HOSTS:
        prior = observation['selectorsByHost'][suffix]
        need(type(prior) is list and len(prior) == len(selectors[suffix]) and
             {r['path'] for r in prior} == {r['path'] for r in selectors[suffix]}, 'ORIGINAL_SELECTOR_SET_CHANGED')
        for row in selectors[suffix]:
            old = next(p for p in prior if p['path'] == row['path'])
            need(set(old) == {'path','pin'}, 'ORIGINAL_SELECTOR_OBSERVATION_INVALID')
            if old['pin'] is not None:
                contract.remote_pin(old['pin']); need(old['pin']['path'] == old['path'], 'ORIGINAL_SELECTOR_PIN_PATH')
            row['expected'] = old['pin']
        baseline = observation['hostPreservationByHost'][suffix]
        need(set(baseline) == {'containers','fstabPin','mountinfoSha256'} and baseline['containers'] and
             contract.sha(baseline['mountinfoSha256']), 'HOST_PRESERVATION_REQUIRED')
        contract.remote_pin(baseline['fstabPin'])
        target = next(r for r in controllers[suffix] if r['role'] == 'target')
        root = PurePosixPath(target['engine']).parent
        host_specs[suffix] = dict(sourceCommit=commit,controllers=controllers[suffix],selectors=selectors[suffix],
            targetConfigRef=targets[suffix],baseline=baseline,auditPath=str(root/('publication-main-program-'+short)),
            sourceRefs=list(SOURCES),historicalPins=[row['pin'] for row in secret['originalMetadata']
                if row['originalHost'] == '172.30.30.'+suffix])
    spug = observation['spug']
    expected_spug = {'containerId','containerSnapshot','protectedContainerId','protectedContainerSnapshot',
                     'entryPid','settings','connections','productPins','taskSnapshotSha256'}
    need(set(spug) == expected_spug and spug['containerId'] == CONTAINER and
         type(spug['protectedContainerId']) is str and re.fullmatch('[0-9a-f]{64}',spug['protectedContainerId']) and
         spug['protectedContainerId'] != CONTAINER and type(spug['entryPid']) is int and spug['entryPid'] > 1 and
         contract.sha(spug['taskSnapshotSha256']) and set(spug['settings']) == set(SETTINGS), 'SPUG_OBSERVATION_INVALID')
    writes = []
    for key,path in SETTINGS.items():
        old = secret['originalSpug'][key]; reference = {k:old[k] for k in ('path','bytes','sha256')}
        contract.remote_pin(reference)
        need(reference['path'] == path and spug['settings'][key] == reference, 'SPUG_ORIGINAL_SETTINGS_CHANGED')
        writes.append(dict(path=path,expected=reference,value=secret[key+'Settings']))
    old_connections = secret['originalSpug']['connections']
    need(set(spug['connections']) == set(old_connections), 'OLD_CONNECTION_SET_CHANGED')
    for name,row in old_connections.items():
        need(re.fullmatch('[A-Za-z0-9_.-]+[.]json',name) and row['path'] == '/run/intruoyi-spug/'+name and
             spug['connections'][name] == {k:row[k] for k in ('path','bytes','sha256')}, 'OLD_CONNECTION_PIN_CHANGED')
    for name,value in secret['newConnections'].items():
        need(re.fullmatch('[A-Za-z0-9_.-]+[.]json',name) and name not in old_connections, 'NEW_CONNECTION_NAME_INVALID')
        writes.insert(0,dict(path='/run/intruoyi-spug/'+name,expected=None,value=value))
    used = set().union(*(set(secret['bridgeSettings'].get(lane,{}).values())
                        for lane in ('sourceConnections','targetConnections','selectionConnections')))
    need(set(secret['newConnections']) <= used and used <= set(old_connections)|set(secret['newConnections']), 'CONNECTION_SET_NOT_CLOSED')
    product_pins = []
    for name in PRODUCT_FILES:
        reference = resource['files']['ops/spug/'+name]
        product_pins.append(dict(path='/opt/intruoyi-spug/'+name,**reference))
    need(spug['productPins'] == product_pins, 'PRODUCT_RESOURCES_NOT_ALREADY_INSTALLED')
    old_bridge = secret['originalSpug']['bridge']['value']
    history_bindings = [dict(lane=lane,ref=ref,fingerprint=bridge_fingerprint(old_connections[name]['value']))
        for lane in ('sourceConnections','targetConnections') for ref,name in old_bridge.get(lane,{}).items()]
    spug_spec = dict(sourceCommit=commit,observation=spug,writes=writes,oldConnections=old_connections,
        sourceRefs=list(SOURCES),targetRefs=plan['programTargets'],history=history,
        historyBindings=history_bindings,rootFingerprint=bridge_fingerprint(old_bridge),
        auditPath='/var/lib/intruoyi-spug/publication-main-program-'+short,settings=secret['entrySettings'])
    helper_pins = [file_pin(Path(p)) for p in (__file__,activation.__file__,contract.__file__)]
    pins = records.path_pins()+private_pins+package_pins+resource_pins+helper_pins+list(extra_pins)
    pins = list({p['path']:p for p in pins}.values())
    return dict(inputs=inputs,inputPins=pins,hostSpecs=host_specs,spugSpec=spug_spec,
                resourceSourceCommit=resource['sourceCommit'])


def publication_schedule():
    return [lane+'-'+phase+('-'+host if host else '')
        for phase in ('preflight','publish','verify')
        for lane,host in [('host','57'),('host','58'),('host','59'),('spug',None)]]


def published_resource_evidence(records, reference, private):
    """An installed resource remains auditable after its build checkout is removed."""
    report=records.pinned(reference);files=resource_files(report)
    proof=records.pinned(report['testEvidencePin'])
    need(set(proof)=={'schemaVersion','status','actualExitCode','actualPassed','actualSkipped','inputPins','logPin'} and
         proof['schemaVersion']=='TaskSpugResourceValidation/v1' and proof['status']=='PASS' and
         type(proof['actualExitCode']) is int and proof['actualExitCode']==0 and
         type(proof['actualPassed']) is int and proof['actualPassed']>0 and
         type(proof['actualSkipped']) is int and proof['actualSkipped']==0 and
         type(proof['inputPins']) is dict and set(files)|{
             'doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_archived_source_catalogue_routing.py'}
         <=set(proof['inputPins']) and all(contract.sha(v) for v in proof['inputPins'].values()) and
         all(proof['inputPins'][name]==pin['sha256'] for name,pin in files.items()),
         'RESOURCE_BUILD_TEST_EVIDENCE_REQUIRED')
    log=Path(proof['logPin']['path'])
    need(log.parent==Path(private).resolve(strict=True),'RESOURCE_BUILD_LOG_SCOPE')
    text=verify_bytes(proof['logPin']).decode('utf-8')
    summaries=re.findall(r'(?m)^\s*(?:=+\s*)?([0-9]+) passed(?:, [0-9]+ warnings?)? in [0-9.]+s[^\r\n]*$',text)
    need(summaries and int(summaries[-1])==proof['actualPassed'] and
         not re.search(r'\b[0-9]+ (?:failed|skipped|errors?|xfailed|xpassed|deselected)\b',text),
         'RESOURCE_BUILD_TEST_LOG_NOT_PASSED')
    return report,[proof['logPin']]


def v2_private_document(private, reference):
    need(type(reference) is dict and set(reference)=={'path','bytes','sha256'} and
         type(reference['path']) is str and type(reference['bytes']) is int and reference['bytes']>0 and
         contract.sha(reference['sha256']), 'V2_PRIVATE_PIN_INVALID')
    need(Path(reference['path']).is_file() and not Path(reference['path']).is_symlink(),
         'V2_PRIVATE_ORIGINAL_REQUIRED')
    return private_document(private,reference)


def v2_context(records, private, inputs, inputs_pin, *, verify_checkout=False):
    fields = {'schemaVersion','sourceCommit','revisionId','controlGenerationPin',
              'spugResourceBuildPin','publicationObservationPin','outputFile'}
    need(type(inputs) is dict and set(inputs)==fields and
         inputs['schemaVersion']=='MainProgramSpugPublicationInputs/v2' and
         type(inputs['sourceCommit']) is str and re.fullmatch('[0-9a-f]{40}',inputs['sourceCommit']) and
         type(inputs['revisionId']) is str and re.fullmatch('r[1-9][0-9]*',inputs['revisionId']), 'V2_INPUTS_INVALID')
    need(inputs['outputFile']=='main-program-spug-installation-'+inputs['sourceCommit'][:7]+'-'+
         inputs['revisionId']+'.json','OUTPUT_NAME_INVALID')
    from main_program_control_generation import load_control_generation
    bundle=load_control_generation(records.task,private,inputs['controlGenerationPin'])
    need(bundle['generation']['sourceCommit']==inputs['sourceCommit'] and
         bundle['plan'].get('schemaVersion')=='MainProgramConfigurationPlan/v2' and
         bundle['plan'].get('revisionId')==inputs['revisionId'], 'V2_GENERATION_CHANGED')
    observation=v2_private_document(private,inputs['publicationObservationPin'])
    observation_fields={'schemaVersion','sourceCommit','revisionId','controlGenerationPin','spugResourceBuildPin',
                        'selectorsByHost','hostPreservationByHost','spug'}
    need(type(observation) is dict and set(observation)==observation_fields and
         observation['schemaVersion']=='MainProgramSpugPublicationObservation/v2' and
         all(observation[k]==inputs[k] for k in ('sourceCommit','revisionId','controlGenerationPin',
             'spugResourceBuildPin')), 'V2_OBSERVATION_CHANGED')
    validator=validate_resource_build if verify_checkout else published_resource_evidence
    resource,resource_pins=validator(records,inputs['spugResourceBuildPin'],private)
    binding={k:inputs[k] for k in ('sourceCommit','revisionId','controlGenerationPin',
                                  'spugResourceBuildPin','publicationObservationPin')}
    binding['publicationInputsPin']=inputs_pin
    return dict(generation=bundle,resource=resource,resourcePins=resource_pins,
                observation=observation,binding=binding)


def prepare_v2(records, private, inputs, inputs_pin):
    context=v2_context(records,private,inputs,inputs_pin,verify_checkout=True)
    bundle=context['generation'];secret=dict(bundle['privatePlan'],programTargets=bundle['plan']['programTargets'])
    spec=_prepare_publication_graph(records,inputs,private,bundle['plan'],secret,bundle['controllersByHost'],
        bundle['targets'],[],[],context['resource'],context['resourcePins'],extra_pins=bundle['inputPins'])
    spec.update(remotePublicationSupported=False,publicationInputsPin=inputs_pin,
        generationPins={k:bundle['generation'][k] for k in ('buildPin','planPin')})
    return spec


def validate_verify_stage(context, bundle, host, result):
    """Shared exact content checks for a completed native verification."""
    if host is not None:
        need(result.get('host')=='172.30.30.'+host and
             result.get('controllers')==bundle['controllersByHost'][host] and
             type(result.get('selectorCount')) is int and result['selectorCount']==(6 if host=='57' else 3) and
             all(result.get(k) is True for k in ('selectorsReadBack','actualNativeSelectionsVerified',
                 'oldFilesPreserved','businessContainersUnchanged','fstabAndMountsUnchanged','controlIdentityVerified')),
             'V2_HOST_PUBLICATION_NOT_PROVEN')
        native=result.get('nativeSelections');controllers=bundle['controllersByHost'][host]
        need(type(native) is list and len(native)==len(controllers) and
             all(type(row) is dict and set(row)=={'service','selections'} for row in native) and
             [row['service'] for row in native]==[c['service'] for c in controllers],
             'V2_NATIVE_CONTROL_SET_CHANGED')
        for row in native:
            applications=row['selections'].get('applications') if type(row['selections']) is dict else None
            need(type(applications) is list and all(type(app) is dict for app in applications),
                 'V2_NATIVE_APPLICATIONS_REQUIRED')
            for source in SOURCES:
                matches=[app for app in applications if app.get('sourceConfigRef')==source]
                need(len(matches)==1 and matches[0].get('historyErrorCode') is None and
                     type(matches[0].get('recoveryPointRefs')) is list and matches[0]['recoveryPointRefs'] and
                     all(type(point) is str and point for point in matches[0]['recoveryPointRefs']) and
                     type(matches[0].get('freshTargetConfigRefs')) is list and
                     bundle['targets'][host] in matches[0]['freshTargetConfigRefs'],
                     'V2_NATIVE_SOURCE_ADMISSION_NOT_PROVEN')
    else:
        expected_pins=[dict(path='/opt/intruoyi-spug/'+name,**context['resource']['files']['ops/spug/'+name])
                       for name in PRODUCT_FILES]
        need(all(type(result.get(k)) is int and result[k]==n for k,n in
                 (('applicationCount',33),('taskCount',3))) and
             result.get('productPins')==expected_pins and
             context['observation']['spug'].get('productPins')==expected_pins and
             all(result.get(k) is True for k in ('productSettingsReadBack','historicalFingerprintsUnchanged',
                 'oldFilesPreserved','protectedSpugUnchanged','oldTasksUnchanged','productFilesUnchanged')),
             'V2_SPUG_PUBLICATION_NOT_PROVEN')
        expected=[dict(sourceConfigRef=source,targetConfigRef=bundle['targets'][host])
                  for host in HOSTS for source in SOURCES]
        need(result.get('bridgeSelections')==expected,'V2_BRIDGE_MATRIX_NOT_PROVEN')


def validate_publication_v2(records, private, selected):
    """Read an explicit full publication; control-only records never imply it.

    Every phase is an independently pinned original. No current/latest scan and
    no remote query is made. Future v2 publishers must emit this exact contract.
    """
    core=records.pinned(selected['spugInstallationPin'])
    need(core.get('schemaVersion')=='MainProgramSpugInstallation/v1' and core.get('status')=='PASS',
         'V2_FULL_SPUG_CORE_REQUIRED')
    stem=contract.local_name(selected['spugInstallationPin']['file'])
    rich_path=Path(private)/stem.replace('.json','.private.json')
    need(rich_path.is_file() and not rich_path.is_symlink(),'V2_PUBLICATION_EVIDENCE_REQUIRED')
    rich_pin=file_pin(rich_path);rich=private_document(private,rich_pin)
    binding_fields={'sourceCommit','revisionId','controlGenerationPin','spugResourceBuildPin',
                    'publicationObservationPin','publicationInputsPin'}
    fields={'schemaVersion','status','stage',*binding_fields,'resourceSourceCommit','stages',
            'selectorCount','applicationCount','taskCount','backupDispatched','restoreDispatched',*TRUE_CHECKS}
    need(set(rich)==fields and rich['schemaVersion']=='MainProgramSpugPublicationEvidence/v2' and
         rich['stage']=='complete', 'V2_PUBLICATION_EVIDENCE_INVALID')
    inputs=records.pinned(rich['publicationInputsPin'])
    context=v2_context(records,private,inputs,rich['publicationInputsPin'])
    bundle=context['generation'];binding=context['binding']
    need(inputs['outputFile']==stem and selected['sourceCommit']==inputs['sourceCommit'] and
         selected['controlGenerationPin']==inputs['controlGenerationPin'] and
         all(rich[k]==v for k,v in binding.items()) and
         rich['resourceSourceCommit']==context['resource']['sourceCommit'],'V2_PUBLICATION_GENERATION_CHANGED')
    spec=dict(inputs=inputs,generationPins={k:bundle['generation'][k] for k in ('buildPin','planPin')})
    need(core==project_core(spec,rich),'V2_FULL_SPUG_CORE_CHANGED')
    stages=rich['stages'];schedule=publication_schedule()
    need(type(stages) is list and len(stages)==12 and all(type(r) is dict and
         set(r)=={'stage','resultPin'} for r in stages) and [r['stage'] for r in stages]==schedule,
         'V2_STAGE_SET_INVALID')
    private_pins=[rich_pin,inputs['publicationObservationPin']]; paths=set()
    for row in stages:
        reference=row['resultPin']
        raw=v2_private_document(private,reference)
        need(reference['path'] not in paths,'V2_STAGE_DUPLICATE');paths.add(reference['path']);private_pins.append(reference)
        need(set(raw)=={'schemaVersion','stage','result',*binding_fields} and
             raw['schemaVersion']=='MainProgramSpugPublicationStage/v2' and raw['stage']==row['stage'] and
             all(raw[k]==v for k,v in binding.items()),'V2_STAGE_BINDING_CHANGED')
        lane,phase,*hosts=row['stage'].split('-');result=raw['result']
        need(type(result) is dict and result.get('status')=='PASS' and result.get('phase')==phase and
             result.get('sourceCommit')==inputs['sourceCommit'] and result.get('backupDispatched') is False and
             result.get('restoreDispatched') is False,'V2_STAGE_NOT_PROVEN')
        if phase!='verify':continue
        validate_verify_stage(context,bundle,hosts[0] if lane=='host' else None,result)
    pins=records.path_pins()+bundle['inputPins']+context['resourcePins']+private_pins
    unique={}
    for pin in pins:
        path=str(Path(pin['path']));pin=dict(pin,path=path)
        need(path not in unique or unique[path]==pin,'V2_INPUT_PIN_CONFLICT');unique[path]=pin
    for pin in unique.values():need(file_pin(pin['path'])==pin,'V2_INPUT_CHANGED_DURING_READ')
    return dict(generation=bundle,inputPins=list(unique.values()))


def project_core(spec, observed):
    inputs = spec['inputs']
    need(observed.get('status') == 'PASS' and observed.get('sourceCommit') == inputs['sourceCommit'] and
         all(observed.get(k) is True for k in TRUE_CHECKS) and
         observed.get('backupDispatched') is False and observed.get('restoreDispatched') is False and
         all(type(observed.get(k)) is int and observed[k] == n for k,n in
             (('selectorCount',12),('applicationCount',33),('taskCount',3))), 'ACTUAL_PUBLICATION_NOT_PROVEN')
    pins=spec['generationPins'] if inputs.get('schemaVersion')=='MainProgramSpugPublicationInputs/v2' else inputs
    return dict(schemaVersion='MainProgramSpugInstallation/v1',status='PASS',sourceCommit=inputs['sourceCommit'],
        buildPin=pins['buildPin'],planPin=pins['planPin'],applicationCount=33,taskCount=3,
        restoreSelectorCount=12,protectedSpugUnchanged=True)


def payload(program, spec, phase):
    return program.replace('__SPEC_JSON__',repr(canonical(dict(spec,phase=phase)).decode('utf-8')),1)


def run_request(task, private, inputs_file, *, apply=False, transport=None):
    return dispatch_prepared(task,private,prepare(task,private,inputs_file),apply=apply,transport=transport)


def dispatch_prepared(task, private, spec, *, apply=False, transport=None):
    prepared = dict(status='PREPARED_NOT_APPLIED',sourceCommit=spec['inputs']['sourceCommit'],remoteDispatched=False)
    if not apply: return prepared
    need(spec['inputs'].get('schemaVersion') != 'MainProgramSpugPublicationInputs/v2',
         'V2_REMOTE_PUBLICATION_NOT_IMPLEMENTED')
    output = Path(task)/spec['inputs']['outputFile']
    rich = Path(private)/output.name.replace('.json','.private.json')
    attempt = Path(private)/output.name.replace('.json','.attempt.private.json')
    need(not any(p.exists() or p.is_symlink() for p in (output,rich,attempt)), 'PUBLICATION_ATTEMPT_EXISTS')
    exclusive_bytes(attempt,canonical(dict(prepared,inputPins=spec['inputPins'],applyRequested=True)))
    evidence = dict(status='FAILED',sourceCommit=spec['inputs']['sourceCommit'],stage='local-inputs',
        retryPermitted=False,backupDispatched=False,restoreDispatched=False,stages=[])
    if 'spugResourceBuildPin' in spec['inputs']:
        evidence.update(spugResourceBuildPin=spec['inputs']['spugResourceBuildPin'],resourceSourceCommit=spec['resourceSourceCommit'])
    try:
        if transport is None: transport = ActualTransport(private,spec['spugSpec'])
        for ref in spec['inputPins']: need(file_pin(ref['path']) == ref,'INPUT_CHANGED_BEFORE_APPLY')
        # All destinations are inspected before any selector or setting is written.
        schedule = [('host',s,'preflight') for s in HOSTS]+[('spug',None,'preflight')]
        schedule += [('host',s,'publish') for s in HOSTS]+[('spug',None,'publish')]
        schedule += [('host',s,'verify') for s in HOSTS]+[('spug',None,'verify')]
        for lane,suffix,phase in schedule:
            evidence['stage'] = lane+'-'+phase+('-'+suffix if suffix else '')
            selected = spec['hostSpecs'][suffix] if lane == 'host' else spec['spugSpec']
            program = HOST_PROGRAM if lane == 'host' else SPUG_PROGRAM
            observed = transport(lane,suffix,phase,payload(program,selected,phase))
            evidence['stages'].append(dict(stage=evidence['stage'],result=observed))
            need(observed.get('status') == 'PASS' and observed.get('phase') == phase and
                 observed.get('sourceCommit') == spec['inputs']['sourceCommit'] and
                 observed.get('backupDispatched') is False and observed.get('restoreDispatched') is False,
                 'ACTUAL_STAGE_FAILED')
        hosts = [r['result'] for r in evidence['stages'] if r['stage'].startswith('host-verify-')]
        spug = evidence['stages'][-1]['result']
        observed = dict(status='PASS',sourceCommit=spec['inputs']['sourceCommit'],publicationCompleted=True,
            selectorCount=sum(h['selectorCount'] for h in hosts),applicationCount=spug['applicationCount'],taskCount=spug['taskCount'],
            selectorsReadBack=all(h.get('selectorsReadBack') is True for h in hosts),
            actualNativeSelectionsVerified=all(h.get('actualNativeSelectionsVerified') is True for h in hosts),
            productSettingsReadBack=spug.get('productSettingsReadBack'),historicalFingerprintsUnchanged=spug.get('historicalFingerprintsUnchanged'),
            oldFilesPreserved=all(h.get('oldFilesPreserved') is True for h in hosts) and spug.get('oldFilesPreserved') is True,
            protectedSpugUnchanged=spug.get('protectedSpugUnchanged'),
            businessContainersUnchanged=all(h.get('businessContainersUnchanged') is True for h in hosts),
            fstabAndMountsUnchanged=all(h.get('fstabAndMountsUnchanged') is True for h in hosts),
            oldTasksUnchanged=spug.get('oldTasksUnchanged'),productFilesUnchanged=spug.get('productFilesUnchanged'),
            controlIdentityVerified=all(h.get('controlIdentityVerified') is True for h in hosts),
            backupDispatched=False,restoreDispatched=False)
        core = project_core(spec,observed)
        for ref in spec['inputPins']: need(file_pin(ref['path']) == ref,'INPUT_CHANGED_DURING_APPLY')
        evidence.update(observed,stage='complete'); exclusive_bytes(rich,canonical(evidence))
        exclusive_bytes(output,canonical(core))
        return dict(status='PASS',report=output.name,sourceCommit=core['sourceCommit'],remoteDispatched=True)
    except BaseException as error:
        evidence.update(status='FAILED',errorType=type(error).__name__,errorCode=str(error))
        if not rich.exists(): exclusive_bytes(rich,canonical(evidence))
        raise ValueError('MAIN_SPUG_PUBLICATION_FAILED_CHECK_PRIVATE_REPORT') from None


class ActualTransport:
    def __init__(self, private, spec):
        self.private,self.spec = Path(private),spec

    def command(self, *args, input=None, timeout=240):
        need(type(timeout) is int and 0 < timeout <= 1800, 'DOCKER_COMMAND_BUDGET_INVALID')
        try:
            result = subprocess.run([DOCKER,*args],input=input,capture_output=True,timeout=timeout)
        except subprocess.TimeoutExpired as error:
            stem = 'main-spug-command-timeout-'+uuid.uuid4().hex
            report = dict(schemaVersion='MainSpugDockerCommandTimeout/v1',status='TIMED_OUT',
                errorType='TimeoutExpired',requestedTimeoutSeconds=timeout,timeoutSeconds=error.timeout,argv=error.cmd)
            for key,raw in (('stdoutPin',error.stdout),('stderrPin',error.stderr)):
                report[key] = None if raw is None else exclusive_bytes(
                    self.private/(stem+('.stdout.private.log' if key == 'stdoutPin' else '.stderr.private.log')),raw)
            exclusive_bytes(self.private/(stem+'.private.json'),canonical(report))
            raise ValueError('MAIN_SPUG_DOCKER_COMMAND_TIMEOUT') from error
        if result.returncode:
            raw = result.stdout+result.stderr
            destination = self.private/('main-spug-command-'+hashlib.sha256(raw).hexdigest()+'.private.log')
            if not destination.exists(): exclusive_bytes(destination,raw)
            raise ValueError('MAIN_SPUG_DOCKER_COMMAND_FAILED')
        return result.stdout

    def inspect_instances(self):
        observation = self.spec['observation']
        rows = json.loads(self.command('inspect',CONTAINER,observation['protectedContainerId']))
        need(len(rows) == 2 and rows[0]['Id'] == CONTAINER and rows[0]['Name'] == '/intruoyi-spug-transfer-spug-1',
             'EXACT_SPUG_CONTAINER_REQUIRED')
        for row,port in zip(rows,('18080','18081')):
            need(row['State']['Running'] is True and row['HostConfig']['PortBindings'].get('80/tcp') ==
                 [{'HostIp':'127.0.0.1','HostPort':port}], 'EXACT_SPUG_LOOPBACK_PORT_REQUIRED')
        mounts = [r for r in rows[0]['Mounts'] if r['Destination'] == '/opt/intruoyi-spug']
        need(len(mounts) == 1 and mounts[0]['Source'].replace('\\','/').lower() == RUNTIME.lower(), 'EXACT_SPUG_RUNTIME_REQUIRED')
        for row,key in zip(rows,('containerSnapshot','protectedContainerSnapshot')):
            need(container_snapshot(row) == observation[key], 'SPUG_INSTANCE_CHANGED')

    def __call__(self,lane,suffix,phase,program):
        if lane == 'host':
            from common import remote
            return remote('172.30.30.'+suffix,program,timeout=600)
        need(lane == 'spug' and suffix is None,'TRANSPORT_LANE_INVALID')
        self.inspect_instances()
        result = json.loads(self.command('exec','-i',CONTAINER,'python3','-B','-',input=program.encode('utf-8')))
        self.inspect_instances()
        result['protectedSpugUnchanged'] = True
        return result


def container_snapshot(row):
    return dict(id=row['Id'],name=row['Name'],image=row['Image'],restartCount=row['RestartCount'],
        state={k:row['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},
        definitionSha256=hashlib.sha256(canonical(dict({k:row[k] for k in ('Path','Args','HostConfig','Config')},
            Mounts=sorted(row['Mounts'],key=lambda m:m['Destination'])))).hexdigest())


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',required=True)
    p.add_argument('--apply',action='store_true')
    p.add_argument('--task',type=Path,default=TASK)
    p.add_argument('--private',type=Path,default=PRIVATE)
    return p


def embedded_helpers():
    functions = (need,canonical,file_pin,verify_bytes,sync_parent,exclusive_bytes,preflight_replace,replace_once,
                 validate_product_selection)
    return 'import os,json,hashlib,re\nfrom pathlib import Path\n'+''.join(inspect.getsource(f)+'\n' for f in functions)


HOST_BODY = r'''
import fcntl,stat,sys,subprocess
SPEC=json.loads(__SPEC_JSON__)
def run(args,env=None):
 r=subprocess.run(args,capture_output=True,env=env,timeout=180)
 need(r.returncode==0,'HOST_COMMAND_FAILED');return r.stdout
def read(ref):
 need(file_pin(ref['path'])==ref,'HOST_PIN_CHANGED');return json.loads(Path(ref['path']).read_bytes())
def preservation():
 ids=run(['/usr/bin/docker','--host','unix:///var/run/docker.sock','ps','-aq','--no-trunc']).decode().split()
 need(ids,'NO_BUSINESS_INVENTORY')
 rows=json.loads(run(['/usr/bin/docker','--host','unix:///var/run/docker.sock','inspect',*ids]))
 values={r['Id']:dict(image=r['Image'],restartCount=r['RestartCount'],state={k:r['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},
  definitionSha256=hashlib.sha256(canonical(dict({k:r[k] for k in ('Path','Args','HostConfig','Config')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])))).hexdigest()) for r in rows}
 need(values==SPEC['baseline']['containers'],'BUSINESS_CONTAINERS_CHANGED')
 need(file_pin('/etc/fstab')==SPEC['baseline']['fstabPin'] and hashlib.sha256(Path('/proc/self/mountinfo').read_bytes()).hexdigest()==SPEC['baseline']['mountinfoSha256'],'FSTAB_OR_MOUNTS_CHANGED')
 for ref in SPEC['historicalPins']:verify_bytes(ref)
def verify_controls():
 controls=[]
 for row in SPEC['controllers']:
  control=read(row['controlConfigurationPin']);owner=read(row['ownerConfigurationPin']);verify_bytes(row['dropinPin'])
  props=dict(line.split('=',1) for line in run(['systemctl','show',row['service'],'-p','MainPID','-p','ActiveState']).decode().splitlines() if '=' in line)
  need(props['MainPID']==str(row['pid']) and props['ActiveState']=='active','CONTROL_PID_CHANGED')
  proc=Path('/proc')/str(row['pid']);args=(proc/'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
  need(len(args)==6 and args[:-1]==[control['pythonPin']['path'].encode(),b'-B',(row['engine']+'/control_entry.py').encode(),b'serve',b'--config-pin'] and json.loads(args[-1])==row['controlConfigurationPin'],'CONTROL_ARGV_CHANGED')
  need((proc/'exe').resolve()==Path(control['pythonPin']['path']).resolve(),'CONTROL_EXECUTABLE_CHANGED')
  environment=dict(v.split(b'=',1) for v in (proc/'environ').read_bytes().split(b'\0') if b'=' in v)
  need(all(environment.get(k.encode())==v.encode() for k,v in control['environment'].items()),'CONTROL_ENVIRONMENT_CHANGED')
  package=json.loads((Path(row['engine'])/'package.json').read_bytes())
  need(len(package['files'])==row['fileCount']==147 and hashlib.sha256(canonical(package['files'])).hexdigest()==package['packageSha256']==row['fileManifestSha256'],'CONTROL_PACKAGE_CHANGED')
  for name,sha in package['files'].items():
   member=Path(name);need(not member.is_absolute() and '..' not in member.parts and str(member)==name,'PACKAGE_MEMBER_PATH')
   need(file_pin(Path(row['engine'])/name)['sha256']==sha,'CONTROL_PACKAGE_MEMBER_CHANGED')
  controls.append((row,control,owner))
 need(not Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESOURCE_RESERVATION')
 roots={c['workingDirectory'] for _,c,_ in controls};pids={r['pid'] for r,_,_ in controls}
 for p in Path('/proc').iterdir():
  if not p.name.isdecimal():continue
  try:args=(p/'cmdline').read_bytes().split(b'\0')
  except (FileNotFoundError,ProcessLookupError):continue
  if any(root.encode() in a for root in roots for a in args):need(int(p.name) in pids,'ACTIVE_OR_UNKNOWN_WORKER')
 return controls
def destinations():
 audit=Path(SPEC['auditPath']);need(audit.parent.resolve(strict=True)==audit.parent,'AUDIT_ALIAS')
 for index,row in enumerate(SPEC['selectors']):
  path=Path(row['path']);backup=audit/('before-'+str(index)+'.private.json');staged=path.with_name(path.name+'.main-program-'+SPEC['sourceCommit'][:7]+'.pending')
  yield row,path,backup,staged
def lock_controls(controls):
 descriptors=[];identities=set()
 try:
  for row,control,owner in controls:
   if row['role']=='source':path=control['sourceEpochPolicies'][SPEC['sourceRefs'][0]]['sourceLockPath']
   else:path=owner['targets'][SPEC['targetConfigRef']]['replacement']['lockPath']
   p=Path(path);need(p.resolve(strict=True)==p,'LOCK_ALIAS');info=p.stat();key=(info.st_dev,info.st_ino)
   if key in identities:continue
   fd=os.open(p,os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC);descriptors.append(fd);actual=os.fstat(fd)
   need(stat.S_ISREG(actual.st_mode) and actual.st_nlink==1 and key==(actual.st_dev,actual.st_ino),'LOCK_CHANGED')
   fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);identities.add(key)
  return descriptors
 except BaseException:
  for fd in reversed(descriptors):os.close(fd)
  raise
out=dict(status='FAILED',phase=SPEC['phase'],sourceCommit=SPEC['sourceCommit'],completedWrites=[],backupDispatched=False,restoreDispatched=False)
locks=[]
try:
 preservation();controls=verify_controls();audit=Path(SPEC['auditPath'])
 if SPEC['phase'] in ('preflight','publish'):
  need(not audit.exists() and not audit.is_symlink(),'PUBLICATION_ATTEMPT_EXISTS')
  # Backups are in a new audit directory. Check every destination/temp before creating it.
  for row,path,backup,staged in destinations():
   need(path.parent.resolve(strict=True)==path.parent and not path.is_symlink() and not staged.exists() and not staged.is_symlink(),'SELECTOR_PATH_ALIAS_OR_PENDING')
   if row['expected'] is None:need(not path.exists(),'EXPECTED_ABSENT_SELECTOR_EXISTS')
   else:need(file_pin(path)==row['expected'],'ORIGINAL_SELECTOR_CHANGED')
   read(row['registrationPin'])
  locks=lock_controls(controls);verify_controls();preservation()
  if SPEC['phase']=='publish':
   audit.mkdir(mode=0o700)
   for row,path,backup,staged in destinations():
    result=replace_once(path,backup,staged,row['expected'],canonical(row['value']))
    exclusive_bytes(audit/('receipt-'+str(len(out['completedWrites']))+'.private.json'),canonical(result))
    out['completedWrites'].append(str(path))
  out.update(status='PASS')
 elif SPEC['phase']=='verify':
  need(audit.is_dir() and not audit.is_symlink(),'PUBLICATION_AUDIT_REQUIRED')
  for row,path,backup,staged in destinations():
   need(file_pin(path)['sha256']==hashlib.sha256(canonical(row['value'])).hexdigest() and json.loads(path.read_bytes())==row['value'],'SELECTOR_READBACK_CHANGED')
   if row['expected'] is not None:need(all(file_pin(backup)[k]==row['expected'][k] for k in ('bytes','sha256')),'ORIGINAL_SELECTOR_NOT_PRESERVED')
  native=[]
  for row,control,owner in controls:
   code="import json,sys;from recovery_control_smallapp_native import Native;c=json.loads(sys.argv[1]);print(json.dumps(Native(c).selections(sys.argv[2])))"
   selections=json.loads(run([control['pythonPin']['path'],'-B','-c',code,canonical(row['controlConfigurationPin']).decode(),SPEC['targetConfigRef']],env=dict(os.environ,**control['environment'])))
   for ref in SPEC['sourceRefs']:
    matches=[r for r in selections['applications'] if r['sourceConfigRef']==ref]
    need(len(matches)==1 and matches[0].get('historyErrorCode') is None and matches[0].get('recoveryPointRefs') and SPEC['targetConfigRef'] in matches[0]['freshTargetConfigRefs'],'ACTUAL_NATIVE_SELECTION_UNAVAILABLE')
   native.append(dict(service=row['service'],selections=selections))
  out.update(status='PASS',selectorCount=len(SPEC['selectors']),selectorsReadBack=True,actualNativeSelectionsVerified=True,
   oldFilesPreserved=True,businessContainersUnchanged=True,fstabAndMountsUnchanged=True,controlIdentityVerified=True,nativeSelections=native)
 else:need(False,'UNKNOWN_PHASE')
 preservation();verify_controls()
except BaseException as error:out.update(status='FAILED',errorType=type(error).__name__,errorCode=str(error))
finally:
 for fd in reversed(locks):fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
print(json.dumps(out))
'''

SPUG_BODY = r'''
import sys
SPEC=json.loads(__SPEC_JSON__)
sys.path.insert(0,'/opt/intruoyi-spug')
import smallapp_entry as entry,smallapp_simple as simple,smallapp_adapter as adapter
def entry_identity():
 matches=[]
 for p in Path('/proc').glob('[0-9]*/cmdline'):
  try:args=p.read_bytes().rstrip(b'\0').split(b'\0')
  except (FileNotFoundError,ProcessLookupError):continue
  if args[:3]==[b'python3',b'-B',b'/opt/intruoyi-spug/smallapp_entry.py']:matches.append(int(p.parent.name))
 need(matches==[SPEC['observation']['entryPid']],'ENTRY_PROCESS_CHANGED')
def task_snapshot():
 entry.initialize_spug()
 from apps.schedule.models import Task
 rows=list(Task.objects.order_by('pk').values())
 return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode('utf-8')).hexdigest()
def preservation():
 entry_identity()
 for ref in SPEC['observation']['productPins']:need(file_pin(ref['path'])==ref,'PRODUCT_FILE_CHANGED')
 for ref in SPEC['observation']['connections'].values():need(file_pin(ref['path'])==ref,'ORIGINAL_CONNECTION_CHANGED')
 need(task_snapshot()==SPEC['observation']['taskSnapshotSha256'],'OLD_TASKS_CHANGED')
def destinations():
 audit=Path(SPEC['auditPath'])
 for index,row in enumerate(SPEC['writes']):
  path=Path(row['path']);yield row,path,audit/('before-'+str(index)+'.private.json'),path.with_name(path.name+'.main-program-'+SPEC['sourceCommit'][:7]+'.pending')
out=dict(status='FAILED',phase=SPEC['phase'],sourceCommit=SPEC['sourceCommit'],completedWrites=[],backupDispatched=False,restoreDispatched=False)
try:
 preservation();audit=Path(SPEC['auditPath']);need(audit.parent.resolve(strict=True)==audit.parent,'AUDIT_ALIAS')
 if SPEC['phase'] in ('preflight','publish'):
  need(not audit.exists() and not audit.is_symlink(),'PUBLICATION_ATTEMPT_EXISTS')
  for row,path,backup,staged in destinations():
   need(path.parent.resolve(strict=True)==path.parent and not path.is_symlink() and not staged.exists() and not staged.is_symlink(),'SPUG_PATH_ALIAS_OR_PENDING')
   if row['expected'] is None:need(not path.exists(),'NEW_CONNECTION_ALREADY_EXISTS')
   else:need(file_pin(path)==row['expected'],'ORIGINAL_SPUG_SETTINGS_CHANGED')
  if SPEC['phase']=='publish':
   audit.mkdir(mode=0o700)
   for row,path,backup,staged in destinations():
    result=replace_once(path,backup,staged,row['expected'],canonical(row['value']))
    exclusive_bytes(audit/('receipt-'+str(len(out['completedWrites']))+'.private.json'),canonical(result))
    out['completedWrites'].append(str(path))
  out['status']='PASS'
 elif SPEC['phase']=='verify':
  need(audit.is_dir() and not audit.is_symlink(),'PUBLICATION_AUDIT_REQUIRED')
  for row,path,backup,staged in destinations():
   need(file_pin(path)['sha256']==hashlib.sha256(canonical(row['value'])).hexdigest() and json.loads(path.read_bytes())==row['value'],'SPUG_SETTINGS_READBACK_CHANGED')
   if row['expected'] is not None:need(all(file_pin(backup)[k]==row['expected'][k] for k in ('bytes','sha256')),'SPUG_ORIGINAL_NOT_PRESERVED')
  current=entry.settings();simple_current=simple.configuration()
  need(current==SPEC['settings'] and len(current['applications'])==33 and len(current['tasks'])==3,'PRODUCT_ENTRY_READBACK_CHANGED')
  need(simple_current==next(r['value'] for r in SPEC['writes'] if r['path']==str(simple.CONFIG)),'PRODUCT_SIMPLE_READBACK_CHANGED')
  for action in ('FULL','INCREMENTAL','RESTORE'):entry.installed_task(current,action)
  binding=adapter.read_json('/run/intruoyi-spug/smallapp-bridge.private.json')
  need(adapter.HttpBridge('/run/intruoyi-spug/smallapp-bridge.private.json').fingerprint==SPEC['rootFingerprint'],'HISTORY_ROOT_FINGERPRINT_CHANGED')
  for row in SPEC['historyBindings']:
   bridge=adapter.HttpBridge('/run/intruoyi-spug/smallapp-bridge.private.json',row['ref'] if row['lane']=='sourceConnections' else None,row['ref'] if row['lane']=='targetConnections' else None)
   need(bridge.fingerprint==row['fingerprint'],'HISTORY_ROUTE_FINGERPRINT_CHANGED')
  bridge_results=[]
  for target in SPEC['targetRefs']:
   for source in SPEC['sourceRefs']:
    bridge=adapter.HttpBridge('/run/intruoyi-spug/smallapp-bridge.private.json',source,target)
    validate_product_selection(bridge.selections(),current,source,target)
    bridge_results.append(dict(sourceConfigRef=source,targetConfigRef=target))
  out.update(status='PASS',applicationCount=33,taskCount=3,productSettingsReadBack=True,
   historicalFingerprintsUnchanged=True,oldFilesPreserved=True,oldTasksUnchanged=True,productFilesUnchanged=True,
   entryReloaded=False,bridgeSelections=bridge_results)
 else:need(False,'UNKNOWN_PHASE')
 preservation()
except BaseException as error:out.update(status='FAILED',errorType=type(error).__name__,errorCode=str(error))
print(json.dumps(out))
'''

HOST_PROGRAM = embedded_helpers()+HOST_BODY
SPUG_PROGRAM = embedded_helpers()+SPUG_BODY


if __name__ == '__main__':
    args = parser().parse_args()
    try:
        result = run_request(args.task,args.private,args.inputs,apply=args.apply)
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
        code = str(error) if type(error) is ValueError and re.fullmatch('[A-Z0-9_]+',str(error)) else 'MAIN_SPUG_LOCAL_INPUTS_MISSING_OR_INVALID'
        print(json.dumps(dict(status='REFUSED',errorCode=code,applyRequested=args.apply)))
        raise SystemExit(1)
    print(json.dumps(result))
