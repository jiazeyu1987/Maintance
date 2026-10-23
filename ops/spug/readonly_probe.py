"""Explicit diagnostic reads of named workflows; never select or publish a candidate."""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from release_adapter import Client, CONFIG, PREFIX, Refused, read_json

parser = argparse.ArgumentParser()
parser.add_argument('--config', type=Path, default=CONFIG)
parser.add_argument('--workflow', action='append', required=True)
parser.add_argument('--context', action='store_true')
args = parser.parse_args()
config = read_json(args.config)
assert config['publishEnabled'] is False and config['productionPaused'] is True
client = Client(config)
result = dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              backend=config['baseUrl'], diagnosticOnly=True, candidateChanged=False, deploymentSubmitted=False)
try:
    client.login()
    result['authenticated'] = True
    result['workflowReads'] = []
    for workflow in args.workflow:
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,160}', workflow):
            raise Refused('EXPLICIT_WORKFLOW_REQUIRED')
        try:
            data = client.call(PREFIX + workflow)
            keys = ('workflowId', 'releaseTag', 'state', 'stateVersion', 'packageDigest',
                    'manifestDigest', 'applicationCommit', 'frontendCommit', 'operationId', 'failedStage', 'errorCode',
                    'evidenceRefs', 'testTargetProfileId', 'testTargetFingerprint', 'testDeploymentBindingDigest')
            result['workflowReads'].append(dict(requestedWorkflow=workflow, result='READ',
                                                **{k: data.get(k) for k in keys}))
        except Refused as error:
            result['workflowReads'].append(dict(requestedWorkflow=workflow, result='REFUSED', reason=str(error)))
    operations = client.call('/infra/runtime-control/operations')
    if not isinstance(operations, list):
        raise Refused('OPERATION_RESPONSE_INVALID')
    result['operationsQueryPassed'] = True
    result['boundOperations'] = []
    for op in operations:
        if op.get('releaseWorkflowId') not in args.workflow:
            continue
        value = {k: op.get(k) for k in ('operationId', 'releaseWorkflowId', 'environment', 'action', 'status',
                                       'requestedAt', 'startedAt', 'finishedAt', 'phase', 'errorCode')}
        value['parameters'] = {k: (op.get('parameters') or {}).get(k) for k in
                               ('releaseTag', 'packageDigest', 'manifestDigest', 'testTargetProfileId',
                                'testTargetFingerprint', 'testDeploymentBindingDigest')}
        result['boundOperations'].append(value)
    if args.context:
        context = client.call('/infra/runtime-control/release-workflows/creation-context')
        keys = ('sourceSelectionId', 'expectedSelectionDigest', 'applicationCommit', 'frontendCommit',
                'existingPackageBindingSha256', 'executorPublisherSha256', 'testTargetProfileId',
                'testTargetFingerprint', 'testDeploymentBindingDigest')
        result['creationContext'] = {k: context.get(k) for k in keys}
except Refused as error:
    result['error'] = str(error)
result['requests'] = client.requests
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(2 if 'error' in result else 0)
