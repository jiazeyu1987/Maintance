"""Distinguish retired, restored candidates from immutable execution history."""


def requires_candidate_history(package, state):
    tag = package['releaseTag']
    if package.get('abandoned') is not True or package.get('baseline'):
        return True
    if any(env.get('releaseTag') == tag for env in state['environments'].values()):
        return True
    jobs = {job['id']: job for job in state['jobs']}
    deployments = [job for job in jobs.values() if job.get('releaseTag') == tag
                   and job.get('action') in ('publish-test', 'promote-prod', 'promote-backup')
                   and job.get('effectsStarted')]
    if not deployments:
        return True
    for original in deployments:
        resolution = original.get('resolution', {})
        acceptance = jobs.get(resolution.get('jobId'), {})
        result = acceptance.get('result', {})
        receipt = result.get('receipt', {})
        if (original.get('status') not in ('failed', 'interrupted', 'succeeded')
                or resolution.get('decision') != 'restored'
                or acceptance.get('action') != 'accept-recovery'
                or acceptance.get('status') != 'succeeded'
                or acceptance.get('releaseTag') != tag
                or acceptance.get('target') != original.get('target')
                or acceptance.get('originalDeploymentJobId') != original['id']
                or result.get('maintenance') is not False
                or receipt.get('phase') != 'opened'
                or receipt.get('originalJobId') != original['id']):
            return True
    return False
