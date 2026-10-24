"""A new backup attempt remains bound to the accepted production original."""
from executor import require
from pathlib import PurePosixPath


def bind_attempt_roots(executor, job):
    """A retry keeps old recovery files untouched and owns a new staging root."""
    if 'runtimeStagingRoots' in job:
        return
    roots = {}
    original_id = job.get('originalDeploymentJobId') or job.get('originalTaskId') or job.get('payload', {}).get('jobId')
    original = next((j for j in executor.state['jobs'] if j['id'] == original_id), None)
    if original:
        roots.update(original.get('runtimeStagingRoots', {}))
    else:
        package = next((p for p in executor.state['packages'] if p['releaseTag'] == job.get('releaseTag')), None)
        for env in ('test', 'rehearsal', 'prod', 'backup'):
            deployment = (package or {}).get('outcomes', {}).get(env, {}).get('deployment', {})
            owner = next((j for j in executor.state['jobs'] if j['id'] == deployment.get('jobId')), {})
            roots.update(owner.get('runtimeStagingRoots', {}))
    if job['action'] == 'promote-backup' and job.get('payload', {}).get('retryOf'):
        roots['backup'] = str(PurePosixPath(executor.c['targets']['backup']['stagingRoot']) / 'attempts' / job['id'])
    job['runtimeStagingRoots'] = roots
    executor.save()


def validate_retry(executor, package, original_id):
    original = next((j for j in executor.state['jobs'] if j['id'] == original_id), None)
    require(original and original['action'] == 'promote-backup' and original.get('target') == 'backup'
            and original['releaseTag'] == package['releaseTag'] and original['status'] in ('failed', 'interrupted'),
            'Select the original failed backup deployment for this immutable package')
    require(original.get('resolution'), 'Inspect/reconcile or restore the original backup task before retry')
    require(package['stage'] in ('prod-accepted', 'backup-restored'),
            'Backup is installed or awaiting acceptance; do not redeploy it')
    if original.get('effectsStarted'):
        require(original['resolution']['decision'] == 'restored'
                and package.get('outcomes', {}).get('backup', {}).get('recovery', {}).get('status') == 'accepted',
                'Partial backup deployment requires verified recovery and recovery acceptance first')
    require(executor.state['environments']['prod']['releaseTag'] == package['releaseTag']
            and package.get('outcomes', {}).get('prod', {}).get('acceptance', {}).get('status') == 'passed'
            and executor.state['environments']['prod'].get('maintenance') is False,
            'Only the currently accepted open production package can be retried on backup')


def available(state, package):
    for job in state['jobs']:
        if (job['action'] == 'promote-backup' and job.get('target') == 'backup'
                and job.get('releaseTag') == package['releaseTag'] and job['status'] in ('failed', 'interrupted')
                and job.get('resolution') and package['stage'] in ('prod-accepted', 'backup-restored')):
            return job['id']
    return None
