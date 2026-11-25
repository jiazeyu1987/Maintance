"""Bind final release evidence to one immutable package; never rewrite history."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

task = Path(__file__).resolve().parent
private = Path('C:/SpugHandoff/release/private/intruoyi-fenbeitong-test-prod-20261125')
tag = '2026-11-26-01-52-12'
commit = 'eb866bbaf4ea1b1c6db93daa63e77576766c3684'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

state = read(private / 'state.private.json')
package = next(p for p in state['packages'] if p['releaseTag'] == tag)
assert package['gitCommit'] == commit
chain = []
for action in ('build-release', 'publish-test', 'mark-tested', 'promote-prod', 'accept-prod'):
    jobs = [j for j in state['jobs'] if j.get('releaseTag') == tag and j['action'] == action]
    assert len(jobs) == 1 and jobs[0]['status'] == 'succeeded', action
    chain.append({k: jobs[0].get(k) for k in ('id', 'action', 'status', 'releaseTag', 'createdAt', 'finishedAt')})

runtimes = {}
for env in ('test', 'prod'):
    path = private / (env + '-runtime-verification.json')
    value = read(path)
    assert value['status'] == 'PASS' and value['gitCommit'] == commit and value['releaseTag'] == tag
    assert value['packageSha256'] == package['packageSha256'] and value['manifestSha256'] == package['manifestSha256']
    receipts = value['databaseContractReceipts']
    assert {v['phase'] for v in receipts} == {'after-migrations', 'before-backend-open', 'before-public-open'}
    assert all(v['status'] == 'PASS' and v['releaseTag'] == tag for v in receipts)
    runtimes[env] = {k: v for k, v in value.items() if k != 'databaseContractReceipts'}
    runtimes[env]['databaseContracts'] = [{k: v[k] for k in ('phase', 'status', 'releaseTag')} for v in receipts]
    runtimes[env]['privateEvidenceSha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
assert runtimes['test']['images'] == runtimes['prod']['images']

pages = {}
for env in ('test', 'prod-maintenance', 'prod'):
    path = task / (env + '-page-acceptance.json')
    value = read(path)
    assert value['status'] in ('PASS', 'PASS_WITH_OBSERVATIONS') and not value['blockers']
    assert value['releaseTag'] == tag and value['sourceCommit'] == commit and value['packageSha256'] == package['packageSha256']
    pages[env] = dict(status=value['status'], report=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())

menus = {}
for env in ('test', 'prod'):
    current = read(private / (env + '-menus.private.json'))
    before = read(private / (env + '-menus-before-r3.private.json'))
    rows = {int(line.split('\t')[0]): line.split('\t') for line in current['menus'].splitlines()}
    assert set(rows) == {5580, 900120, 990200, 990253, 991503}
    assert rows[5580][1:8] == ['排产工单', '900120', '/mes/pro/schedule-order', 'mes/pro/scheduleorder/index', 'MesProScheduleOrder', 'mes:pro-schedule-order:query', '2']
    assert rows[900120][2:4] == ['0', '/mes/smart-scheduling']
    assert rows[991503][2:7] == ['990253', '/dcc/registration-certificate/config', 'dcc/registration-certificate/config/index', 'DccRegistrationCertificateConfig', 'dcc:registration-certificate:config:query']
    bindings = dict(line.split('\t') for line in current['roleBindings'].splitlines())
    prior_bindings = dict(line.split('\t') for line in before['roleBindings'].splitlines())
    assert all(bindings[str(i)] == prior_bindings[str(i)] for i in (5580, 991503))
    menus[env] = dict(rows=list(rows.values()), rowsBefore=[line.split('\t') for line in before['menus'].splitlines()],
        roleBindingCounts=bindings, roleBindingCountsBefore=prior_bindings,
        roleBindingDeltas={key:int(value)-int(prior_bindings[key]) for key,value in bindings.items()},
        preservedDirectMenuBindings=[5580, 991503])
assert menus['test']['rows'] == menus['prod']['rows']

report = dict(status='PASS', verifiedAt=datetime.now(timezone.utc).isoformat(), releaseTag=tag, sourceCommit=commit,
    packageSha256=package['packageSha256'], manifestSha256=package['manifestSha256'], jobChain=chain,
    targets=['test', 'prod'], runtimes=runtimes, pageAcceptance=pages, menuVerification=menus,
    scope=dict(verified=['actual frontend login', 'schedule menu and actual list response', 'Fenbeitong ticket and authenticated helper iframe', 'visible version and changelog'],
        notVerified=['voucher synchronization and accounting writes', 'workbench context initialization', 'full business E2E', 'audit server deployment']),
    knownIssues=['Pre-existing registration reminder owner/deadline configuration is missing for some tenants; no business configuration was changed.',
        'Both helpers have no saved reimbursement field mapping (GET config HTTP400, explicitly verified in each real UI); financial synchronization/accounting was not accepted.'],
    historicalAttempts=[dict(releaseTag='2026-11-25-23-53-05', status='build_failed', reason='Unregistered forward menu migration; fixed in 6a099294a0b045f59b4f3896e06c20f1486a35e3'),
        dict(releaseTag='2026-11-26-00-12-02', status='test_page_blocked', reason='Fenbeitong callback missing issuing tenant context; fixed in final source commit')])
(task / 'release-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(status=report['status'], releaseTag=tag, sourceCommit=commit, jobs=chain), ensure_ascii=False))
