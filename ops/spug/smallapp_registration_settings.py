"""Consume W08's existing validator; emit public UI options, never runtime readiness."""
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
workspace = Path(__file__).resolve().parents[2]
registration_root = workspace / 'doc/tasks/20261014-backup-application-registration'
sys.path.insert(0, str(registration_root))
import registration
from smallapp_entry import settings
import smallapp_adapter as adapter


def materialize(destination):
    delivery = registration.load(registration_root / 'delivery.json')
    registration.need(delivery['localScopeComplete'] is True and delivery['validation']['passed'] is True,
                      'W08_METADATA_DELIVERY_REQUIRED')
    options, versions = [], {}
    registration.need(delivery['registrationSchema'] == 'ApplicationRegistration/v1', 'W08_SCHEMA_INVALID')
    for name in ('smallapp.registration.json', 'intruoyi.registration.json'):
        pin = delivery['artifacts'][name]
        path = Path(pin['path'])
        registration.need(path.resolve().parent == registration_root.resolve(), 'W08_PATH_OUTSIDE_OWNER')
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        registration.need(len(raw) == pin['bytes'] and sha == pin['sha256'], 'W08_DELIVERY_PIN_CHANGED')
        value = registration.validate(json.loads(raw.decode('utf-8-sig')))
        snapshot = Path(destination).parent / ('registration-' + sha + '.json')
        if snapshot.exists():
            registration.need(snapshot.read_bytes() == raw, 'OWN_REGISTRATION_SNAPSHOT_CHANGED')
        else:
            with snapshot.open('xb') as stream:
                stream.write(raw)
        options.append(dict(applicationId=value['applicationId'], displayName=value['displayName'],
            sourceConfigRef=value['sourceConfigRef'], targetConfigRefs=[t['configRef'] for t in value['allowedRestoreTargets']],
            engineSelectionRef=value['engineSelectionRef'], registrationSha256=sha))
        versions[value['applicationId']] = value['runtime']['version']
    original = registration.load(workspace / 'doc/tasks/20261010-spug-integration/smallapp-manual-tasks-20261014.json')
    tasks = {r['action']: r['taskId'] for r in original['results']}
    initial = {r['action']: r['operationId'] for r in original['results']}
    source_refs = {r['command'].split('--source-config-ref ', 1)[1].split(' ', 1)[0] for r in original['results']}
    registration.need(len(source_refs) == 1, 'ORIGINAL_SOURCE_MAPPING_CONFLICT')
    apps = [a for a in options if a['sourceConfigRef'] in source_refs]
    registration.need(len(apps) == 1, 'ORIGINAL_APPLICATION_MAPPING_REQUIRED')
    value = dict(applications=options, tasks=tasks, initialOperationIds={apps[0]['applicationId']: initial},
                 registrationVersions=versions)
    if Path(destination).exists():
        previous = adapter.read_json(destination)
        adapter.write_json(Path(destination).with_name('settings-previous-' +
            hashlib.sha256(Path(destination).read_bytes()).hexdigest() + '.json'), previous)
    adapter.write_json(destination, value)
    settings(destination)
    print(json.dumps({'applicationIds': [a['applicationId'] for a in options],
                      'actualRuntimeReadinessClaimed': False, 'tasks': tasks, 'metadataValidated': True}))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('EXPLICIT_OWN_OUTPUT_PATH_REQUIRED')
    materialize(sys.argv[1])
