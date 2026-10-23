"""Bind an explicitly supplied verified deployment to own Spug read-only tasks. No release writes."""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path
from release_adapter import BINDINGS, CONTEXT_FIELDS, check_context, validate_selection

parser = argparse.ArgumentParser()
parser.add_argument('--evidence', type=Path, required=True)
parser.add_argument('--workflow', required=True)
parser.add_argument('--operation', required=True)
args = parser.parse_args()
private = Path('E:/Int/CacheData/IntRuoyi/spug-integration-20261010')
output = Path('doc/tasks/20261010-spug-integration')
evidence = json.loads(args.evidence.read_text(encoding='utf-8-sig'))
assert evidence['workflowId'] == args.workflow and evidence['operationId'] == args.operation
assert evidence['status'] == 'REAL_FRONTEND_TO_TEST_DEPLOYMENT_AND_FRESH_RUNTIME_PASS'
assert evidence['backend']['health']['status'] == 'UP' and evidence['frontend']['health']['httpStatus'] == 200
config = json.loads((private / 'backend.private.json').read_text(encoding='utf-8-sig'))
assert config['publishEnabled'] is False and config['productionPaused'] is True
probe = subprocess.run(['docker', 'exec', 'intruoyi-spug-spug-1', 'python3',
                        '/opt/intruoyi-spug/readonly_probe.py', '--workflow', args.workflow, '--context'],
                       capture_output=True, encoding='utf-8', timeout=65, check=True)
data = json.loads(probe.stdout)
assert data['authenticated'] and data['operationsQueryPassed'] and not data.get('error')
assert all(r['method'] == 'GET' or r['path'] == '/system/auth/login' for r in data['requests'])
record = data['workflowReads'][0]
assert record['result'] == 'READ'
assert all(record[k] == evidence[k] for k in ('workflowId', 'releaseTag', 'packageDigest', 'manifestDigest'))
matches = [op for op in data['boundOperations'] if op['operationId'] == args.operation]
assert len(matches) == 1
operation = matches[0]
assert operation['status'] == 'succeeded' and operation['action'] == 'publish-test' and operation['environment'] == 'test'
assert all(operation['parameters'][k] == evidence[k] for k in ('releaseTag', 'packageDigest', 'manifestDigest'))
context = data['creationContext']
selection = {k: record[k] for k in BINDINGS}
selection.update(observedTestOperationId=args.operation,
                 admission={k: context[k] for k in CONTEXT_FIELDS},
                 **{k: operation['parameters'][k] for k in
                    ('testTargetProfileId', 'testTargetFingerprint', 'testDeploymentBindingDigest')})
validate_selection(selection)
check_context(context, selection)
assert all(selection[k] == context[k] for k in ('testTargetProfileId', 'testTargetFingerprint', 'testDeploymentBindingDigest'))
path = private / 'candidate.private.json'
previous = path.read_bytes()
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
archive = private / ('candidate-before-live-entry-' + stamp + '.json')
with archive.open('xb') as stream:
    stream.write(previous)
temporary = private / ('candidate-' + stamp + '.tmp')
with temporary.open('x', encoding='utf-8') as stream:
    json.dump(selection, stream, ensure_ascii=False, indent=2)
    stream.flush()
    os.fsync(stream.fileno())
os.replace(temporary, path)
assert json.loads(path.read_text(encoding='utf-8')) == selection
data.update(explicitBindingConfigured=True, configurationOnly=True, previousSelectionArchived=True,
            successEvidenceSha256=hashlib.sha256(args.evidence.read_bytes()).hexdigest(),
            deploymentSubmitted=False, publishEnabled=False, productionPaused=True)
(output / 'live-backend-binding-20261012.json').write_text(
    json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('Explicit successful original operation configured and verified; failed workflow remains unchanged; no release POST.')
