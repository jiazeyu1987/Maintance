"""Validate safe remote evidence without any additional server access."""
import hashlib
import json
from pathlib import Path

task = Path(__file__).resolve().parent
evidence = task / 'remote-observation.json'
report = json.loads(evidence.read_text(encoding='utf-8'))
rows = []
for value in report['results']:
    assert value['observed'] and value['applicationLabelVerified'] and value['stableDuringObservation']
    container = value['container']
    version = value['releaseInfo']['releaseTag']
    assert value['releaseInfo']['applicationId'] == 'fenbeitong'
    assert version == container['labels']['release.version']
    assert container['state']['Running'] and not container['state']['Restarting']
    assert value['health'] == {'httpStatus': 200, 'body': {'success': True, 'status': 'ok'}}
    selected = []
    for action in ('deploy', 'verify'):
        matches = [r for r in value['receipts'] if r.get('action') == action
                   and r.get('status') == 'succeeded' and r.get('phase') == 'complete'
                   and r.get('packageSha256') == container['labels']['release.package']
                   and r.get('environment', {}).get('containerId') == container['id']
                   and r['environment']['imageId'] == container['imageId']
                   and r['environment']['releaseTag'] == version]
        assert matches, 'No complete matching ' + action + ' receipt'
        selected.append(matches[0])
    manifests = [m for m in value['matchingManifests'] if m['imageId'] == container['imageId']
                 and m['releaseTag'] == version and m['sourceSha256'] == value['releaseInfo']['sourceSha256']]
    assert manifests
    rows.append(dict(environment=value['environment'], host=value['host'], releaseTag=version,
                     sourceSha256=value['releaseInfo']['sourceSha256'], imageId=container['imageId'],
                     packageSha256=container['labels']['release.package'],
                     manifestSha256=manifests[0]['manifestSha256'], status='running', health='HTTP 200 / ok',
                     deploymentJob=selected[0]['jobId'], verificationJob=selected[1]['jobId'],
                     deployedAtUtc=selected[0]['modifiedAtUtc'], stableDuringObservation=True))
for key in ('releaseTag', 'sourceSha256', 'imageId', 'packageSha256', 'manifestSha256'):
    assert len({r[key] for r in rows}) == 1, 'Two targets differ: ' + key
summary = dict(status='OBSERVED_SAME_RELEASE_HEALTHY', collectedAtUtc=report['collectedAtUtc'],
               evidenceSha256=hashlib.sha256(evidence.read_bytes()).hexdigest(), targets=rows,
               scope='Read-only installed identity, health and existing remote receipts',
               notVerified=['Other computer local task/acceptance history',
                            'End-to-end reimbursement or external integration business behavior',
                            'Original release.tar full content checksum or recovery archive integrity'],
               remoteWrites=False, localHistoryImported=False)
(task / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
