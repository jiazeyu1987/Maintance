"""Validate explicit local MAIN installation records, without remote authority."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


OLD_FILE = 'automatic-current-installations.json'
SCHEMA = 'TaskMainProgramInstallations/v1'
HOSTS = ('57', '58', '59')
ROLES = {'57': ('source', 'target'), '58': ('target',), '59': ('target',)}
TRUE_FLAGS = ('businessContainersUnchanged', 'fstabAndMountsUnchanged',
              'previousControlFilesPreserved', 'originalTargetObjectsUnchanged')
FALSE_FLAGS = ('backupDispatched', 'restoreDispatched')
CONTROLLER_KEYS = ('service', 'engine', 'pid', 'controlConfigurationPin',
                   'ownerConfigurationPin', 'sourceCommit', 'fileManifestSha256', 'fileCount')


def need(condition, reason):
    if not condition:
        raise ValueError('MAIN_INSTALLATION_' + reason)


def sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def local_name(value):
    need(type(value) is str and value.endswith('.json') and value not in ('.', '..') and
         not any(c in value for c in '/\\:') and not any(ord(c) < 32 for c in value),
         'LOCAL_FILE_INVALID')
    return value


def remote_pin(reference):
    need(type(reference) is dict and set(reference) == {'path', 'bytes', 'sha256'} and
         type(reference['path']) is str and type(reference['bytes']) is int and
         reference['bytes'] > 0 and sha(reference['sha256']), 'REMOTE_PIN_INVALID')
    path = PurePosixPath(reference['path'])
    need(path.is_absolute() and str(path) == reference['path'] and
         '..' not in path.parts and not any(ord(c) < 32 for c in reference['path']),
         'REMOTE_PATH_INVALID')
    return reference


def document(pairs):
    value = {}
    for key, item in pairs:
        need(key not in value, 'DUPLICATE_JSON_KEY')
        value[key] = item
    return value


class Records:
    def __init__(self, task):
        self.task = Path(task).resolve(strict=True)
        self.values, self.references = {}, {}

    def read(self, name, expected=None):
        name = local_name(name)
        if name not in self.values:
            path = self.task / name
            need(not path.is_symlink() and path.resolve(strict=True).parent == self.task,
                 'LOCAL_FILE_ALIAS')
            before = path.stat()
            need(0 < before.st_size <= 16 * 1024 * 1024, 'LOCAL_DOCUMENT_LIMIT')
            raw = path.read_bytes()
            after = path.stat()
            identity = lambda value: (value.st_dev, value.st_ino, value.st_size,
                                       value.st_mtime_ns, value.st_ctime_ns)
            need(identity(before) == identity(after), 'LOCAL_FILE_CHANGED')
            reference = dict(file=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            try:
                value = json.loads(raw.decode('utf-8'), object_pairs_hook=document)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError('MAIN_INSTALLATION_DOCUMENT_INVALID') from error
            need(type(value) is dict, 'DOCUMENT_OBJECT_REQUIRED')
            self.values[name], self.references[name] = value, reference
        if expected is not None:
            need(self.references[name] == expected, 'ORIGINAL_FILE_CHANGED')
        return self.values[name]

    def pinned(self, reference):
        need(type(reference) is dict and set(reference) == {'file', 'bytes', 'sha256'} and
             type(reference['bytes']) is int and reference['bytes'] > 0 and sha(reference['sha256']),
             'LOCAL_PIN_INVALID')
        return self.read(reference['file'], reference)

    def path_pins(self):
        return [dict(path=str(self.task / name), bytes=reference['bytes'], sha256=reference['sha256'])
                for name, reference in self.references.items()]


def _build(records, selected):
    reference = selected['buildPin']
    build = records.pinned(reference)
    need(reference['file'] == 'release-build-' + selected['sourceCommit'][:7] + '.json' and
         build.get('status') == 'PASS' and build.get('targetCommit') == selected['sourceCommit'] and
         build.get('allFilesShaAndCompileVerified') is True and type(build.get('fileCount')) is int and
         build['fileCount'] == 147 and sha(build.get('packageSha256')) and sha(build.get('fileManifestSha256')),
         'BUILD_NOT_PROVEN')
    packages = build.get('packages')
    need(type(packages) is list and all(type(row) is dict for row in packages), 'BUILD_PACKAGES_INVALID')
    standard = [row for row in packages if row.get('variant') == 'standard']
    need(len(standard) == 1 and all(type(standard[0].get(key)) is type(build[key]) and
         standard[0][key] == build[key] for key in ('fileCount', 'packageSha256', 'fileManifestSha256')),
         'BUILD_STANDARD_BINDING_INVALID')
    return build


def _previous(records, reference):
    old = records.pinned(reference)
    need(reference['file'] == OLD_FILE and old.get('schemaVersion') == 'TaskCurrentInstallations/v2' and
         type(old.get('targets')) is dict and set(old['targets']) == {'58', '59'},
         'PREVIOUS_SELECTION_INVALID')
    for key in ('source57', 'spug', 'catalogueInstallation', 'catalogueReadonlyObservation'):
        if key in old:
            records.pinned(old[key])
    targets = {host: records.pinned(old['targets'][host]) for host in ('58', '59')}
    for host, target in targets.items():
        need(target.get('status') == 'PASS' and target.get('host') == '172.30.30.' + host and
             type(target.get('targetConfigRef')) is str, 'PREVIOUS_TARGET_INVALID')
        remote_pin(target['currentReceiptPin'])
    return targets


def _plan(records, selected, targets):
    plan = records.pinned(selected['planPin'])
    need(selected['planPin']['file'] == 'main-program-configuration-plan-r4.json' and
         plan.get('status') == 'PLAN_ONLY_NOT_ACTIVATED' and plan.get('sourceCommit') == selected['sourceCommit'] and
         plan.get('hosts') == list(HOSTS) and type(plan.get('controllers')) is dict and
         set(plan['controllers']) == set(HOSTS) and plan.get('targetObjectsUnchanged') is True and
         plan.get('restoreDispatched') is False and plan.get('installationPerformed') is False,
         'PLAN_NOT_PROVEN')
    for key, expected in (('registrationCount', 12), ('applicationCount', 33), ('originalTaskCount', 3)):
        need(type(plan.get(key)) is int and plan[key] == expected, 'PLAN_COUNTS_INVALID')
    need(type(plan.get('programTargets')) is list and len(plan['programTargets']) == 3 and
         set(plan['programTargets']) == set(targets.values()), 'PLAN_TARGETS_INVALID')
    for host, roles in ROLES.items():
        rows = plan['controllers'][host]
        need(type(rows) is list and len(rows) == len(roles), 'PLAN_CONTROLLERS_INVALID')
        for row, role in zip(rows, roles):
            need(type(row) is dict and row.get('role') == role and type(row.get('service')) is str and
                 re.fullmatch('[A-Za-z0-9_.@-]+\\.service', row['service']) is not None and
                 type(row.get('engine')) is str and PurePosixPath(row['engine']).is_absolute() and
                 str(PurePosixPath(row['engine'])) == row['engine'] and '..' not in PurePosixPath(row['engine']).parts,
                 'PLAN_CONTROLLER_INVALID')
            remote_pin(row['controlPin']); remote_pin(row['ownerPin'])
    need(len({row['service'] for row in plan['controllers']['57']}) == 2,
         'PLAN_SERVICE_COLLISION')
    return plan


def _activation(records, reference, selected, build, plan_row, host, target_ref, previous):
    value = records.pinned(reference)
    fields = {'schemaVersion', 'status', 'role', 'host', 'sourceCommit', 'buildPin', 'planPin',
        'service', 'engine', 'pid', 'controlConfigurationPin', 'ownerConfigurationPin', 'dropinPin',
        'fileCount', 'fileManifestSha256', 'packageSha256', 'targetConfigRef', *TRUE_FLAGS, *FALSE_FLAGS}
    fields.update({'activeReceiptPin'} if host == '57' else {'previousReceiptPin', 'currentReceiptPin'})
    need(set(value) == fields and value['schemaVersion'] == 'MainProgramControlActivation/v1' and
         value['status'] == 'PASS' and value['role'] == plan_row['role'] and
         value['host'] == '172.30.30.' + host and value['sourceCommit'] == selected['sourceCommit'] and
         value['buildPin'] == selected['buildPin'] and value['planPin'] == selected['planPin'] and
         type(value['pid']) is int and value['pid'] > 0 and value['targetConfigRef'] == target_ref,
         'ACTIVATION_IDENTITY_INVALID')
    need(all(value[key] is True for key in TRUE_FLAGS) and all(value[key] is False for key in FALSE_FLAGS),
         'ACTIVATION_PRESERVATION_NOT_PROVEN')
    need(all(value[key] == plan_row[planned] for key, planned in (
        ('service', 'service'), ('engine', 'engine'), ('controlConfigurationPin', 'controlPin'),
        ('ownerConfigurationPin', 'ownerPin'))) and
        all(type(value[key]) is type(build[key]) and value[key] == build[key]
            for key in ('fileCount', 'fileManifestSha256', 'packageSha256')), 'ACTIVATION_GENERATION_CHANGED')
    remote_pin(value['dropinPin'])
    need(PurePosixPath(value['dropinPin']['path']).parent ==
         PurePosixPath('/etc/systemd/system') / (value['service'] + '.d'), 'DROPIN_SERVICE_MISMATCH')
    if host == '57':
        need(value['activeReceiptPin'] is None, 'UNEXPECTED_ACTIVE_RECEIPT')
    else:
        before, after = remote_pin(value['previousReceiptPin']), remote_pin(value['currentReceiptPin'])
        old = previous['currentReceiptPin']
        need(all(before[key] == old[key] for key in ('bytes', 'sha256')) and
             after['path'] == old['path'] and before['path'] != after['path'], 'RECEIPT_ROTATION_INVALID')
    return value


def select_main_program_installation(suffix, task, *, selection_file, private=None):
    need(suffix in HOSTS, 'HOST_REQUIRED')
    records = Records(task)
    selected = records.read(selection_file)
    if selected.get('schemaVersion') == 'TaskMainProgramInstallations/v4':
        from main_program_spug_publication_verify_only import PRIVATE, validate_publication_v4
        verified=validate_publication_v4(records,Path(PRIVATE if private is None else private),selected)
        bundle=verified['generation'];rows=bundle['controllersByHost'][suffix]
        return dict(host='172.30.30.'+suffix,suffix=suffix,sourceCommit=selected['sourceCommit'],
            currentSourceCommit=selected['sourceCommit'],currentInstallationSelectionPin=records.references[selection_file],
            controllers=[{key:row[key] for key in CONTROLLER_KEYS} for row in rows],
            targetConfigRef=bundle['targets'][suffix],activeReceiptPin=None if suffix=='57' else rows[0]['currentReceiptPin'],
            localInstallationPins=verified['inputPins'])
    if selected.get('schemaVersion') == 'TaskMainProgramInstallations/v2':
        return _select_v2(suffix,records,selected,selection_file,private)
    if selected.get('schemaVersion') == 'TaskMainProgramInstallations/v3':
        from main_program_spug_publication_continuation import PRIVATE, validate_publication_v3
        verified=validate_publication_v3(records,Path(PRIVATE if private is None else private),selected)
        bundle=verified['generation'];rows=bundle['controllersByHost'][suffix]
        return dict(host='172.30.30.'+suffix,suffix=suffix,sourceCommit=selected['sourceCommit'],
            currentSourceCommit=selected['sourceCommit'],currentInstallationSelectionPin=records.references[selection_file],
            controllers=[{key:row[key] for key in CONTROLLER_KEYS} for row in rows],
            targetConfigRef=bundle['targets'][suffix],activeReceiptPin=None if suffix=='57' else rows[0]['currentReceiptPin'],
            localInstallationPins=verified['inputPins'])
    fields = {'schemaVersion', 'sourceCommit', 'previousAutomaticSelectionPin', 'buildPin',
              'planPin', 'spugInstallationPin', 'controllersByHost'}
    need(set(selected) == fields and selected['schemaVersion'] == SCHEMA and
         type(selected['sourceCommit']) is str and re.fullmatch('[0-9a-f]{40}', selected['sourceCommit']) and
         type(selected['controllersByHost']) is dict and set(selected['controllersByHost']) == set(HOSTS),
         'SELECTION_INVALID')
    previous = _previous(records, selected['previousAutomaticSelectionPin'])
    targets = {'57': 'intruoyi-main-57-safe-restore-20261105-v2',
               **{host: value['targetConfigRef'] for host, value in previous.items()}}
    build = _build(records, selected)
    plan = _plan(records, selected, targets)
    spug = records.pinned(selected['spugInstallationPin'])
    need(set(spug) == {'schemaVersion', 'status', 'sourceCommit', 'buildPin', 'planPin',
        'applicationCount', 'taskCount', 'restoreSelectorCount', 'protectedSpugUnchanged'} and
        spug['schemaVersion'] == 'MainProgramSpugInstallation/v1' and spug['status'] == 'PASS' and
        spug['sourceCommit'] == selected['sourceCommit'] and spug['buildPin'] == selected['buildPin'] and
        spug['planPin'] == selected['planPin'] and spug['protectedSpugUnchanged'] is True and
        all(type(spug[key]) is int and spug[key] == expected for key, expected in
            (('applicationCount', 33), ('taskCount', 3), ('restoreSelectorCount', 12))), 'SPUG_NOT_PROVEN')
    activated, paths = {}, set()
    for host, roles in ROLES.items():
        references = selected['controllersByHost'][host]
        need(type(references) is list and len(references) == len(roles), 'CONTROL_SET_INVALID')
        activated[host] = []
        for index, role in enumerate(roles):
            reference = references[index]
            value = _activation(records, reference, selected, build, plan['controllers'][host][index],
                host, None if role == 'source' else targets[host], previous.get(host))
            need(reference['file'] not in paths, 'DUPLICATE_ACTIVATION')
            paths.add(reference['file']); activated[host].append(value)
    need(len({row['pid'] for row in activated['57']}) == 2, 'CONTROLLER_PID_COLLISION')
    rows = activated[suffix]
    return dict(host='172.30.30.' + suffix, suffix=suffix, sourceCommit=selected['sourceCommit'],
        currentSourceCommit=selected['sourceCommit'], currentInstallationSelectionPin=records.references[selection_file],
        controllers=[{key: row[key] for key in CONTROLLER_KEYS} for row in rows],
        targetConfigRef=targets[suffix], activeReceiptPin=None if suffix == '57' else rows[0]['currentReceiptPin'],
        localInstallationPins=records.path_pins())


def _select_v2(suffix, records, selected, selection_file, private):
    need(set(selected) == {'schemaVersion','sourceCommit','controlGenerationPin','spugInstallationPin'} and
         type(selected['sourceCommit']) is str and re.fullmatch('[0-9a-f]{40}',selected['sourceCommit']),
         'SELECTION_INVALID')
    from main_program_spug_publication import PRIVATE, validate_publication_v2
    verified = validate_publication_v2(records,Path(PRIVATE if private is None else private),selected)
    bundle = verified['generation']; rows = bundle['controllersByHost'][suffix]
    return dict(host='172.30.30.'+suffix,suffix=suffix,sourceCommit=selected['sourceCommit'],
        currentSourceCommit=selected['sourceCommit'],currentInstallationSelectionPin=records.references[selection_file],
        controllers=[{key:row[key] for key in CONTROLLER_KEYS} for row in rows],
        targetConfigRef=bundle['targets'][suffix],activeReceiptPin=None if suffix=='57' else rows[0]['currentReceiptPin'],
        localInstallationPins=verified['inputPins'])
