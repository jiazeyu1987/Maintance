"""Explicit target adoption without rewriting failed deployment evidence."""


def superseding_test_deployment(state, failed):
    """Prove a login-only historical incident was followed by verified deployment.

    This does not accept the old release or mutate its failed result. Unknown
    effects, migration failures and failures on other targets remain blocking.
    """
    if not (failed.get('action') == 'publish-test' and failed.get('target') == 'test'
            and failed.get('status') == 'failed' and failed.get('currentStep') == 'technical-login'
            and failed.get('finishedAt')):
        return None
    if any(call.get('env') != 'test' for call in failed.get('remoteOperations', [])):
        return None

    def bound_proof(job, status, checks):
        packages = [p for p in state.get('packages', []) if p.get('releaseTag') == job.get('releaseTag')]
        if len(packages) != 1:
            return False
        package = packages[0]
        proof = job.get('technicalVerification', {})
        deployment = package.get('outcomes', {}).get('test', {}).get('deployment', {})
        return (proof.get('jobId') == job.get('id') and proof.get('env') == 'test'
                and proof.get('releaseTag') == job.get('releaseTag')
                and proof.get('packageSha256') == package.get('packageSha256')
                and bool(package.get('packageSha256')) and proof.get('status') == status
                and deployment.get('status') == 'succeeded' and deployment.get('jobId') == job.get('id')
                and all(proof.get('checks', {}).get(key, {}).get('status') == value for key, value in checks.items()))

    if not bound_proof(failed, 'failed', dict(version='passed', upgrade='passed', login='failed')):
        return None
    for later in state.get('jobs', []):
        if (later.get('action') == 'publish-test' and later.get('target') == 'test'
                and later.get('status') == 'succeeded' and later.get('finishedAt')
                and later.get('createdAt', '') > failed['finishedAt']
                and bound_proof(later, 'passed', dict(version='passed', upgrade='passed', login='passed'))):
            return dict(failedJobId=failed['id'], supersedingJobId=later['id'],
                        releaseTag=later['releaseTag'], packageSha256=later['technicalVerification']['packageSha256'])
    return None


def registration_targets(payload):
    if 'target' not in payload:
        return ('test', 'prod', 'backup')
    target = payload['target']
    if target not in ('test', 'prod', 'backup'):
        raise ValueError('Explicit registration target must be test, prod or backup')
    return (target,)


def validate_registered_takeover(original, registered, jobs, observed):
    def require(value, message):
        if not value:
            raise ValueError(message)

    require(original.get('action') == 'publish-test' and original.get('target') == 'test'
            and original.get('status') == 'failed' and not original.get('effectsStarted')
            and not original.get('resolution') and original.get('currentStep') == 'check-target-origin',
            'Only a failed test origin check without effects can adopt a registered origin')
    calls = original.get('remoteOperations', [])
    require(calls and all(c.get('action') == 'observe' and c.get('env') == 'test' for c in calls),
            'Original remote calls must contain only test observations')
    registration = next((j for j in jobs if j['id'] == registered.get('registrationJobId')), None)
    require(registration and registration.get('action') == 'register-targets'
            and registration.get('status') == 'succeeded'
            and registration.get('createdAt', '') > original.get('createdAt', '')
            and 'test' in registration.get('result', {}).get('targets', {}),
            'A later successful test registration is required')
    require(observed.get('fingerprint') and observed['fingerprint'] == registered.get('fingerprint')
            and observed.get('maintenance') is False
            and observed.get('readOnly') == dict(read_only=False, super_read_only=False),
            'Registered test origin changed or remains protected')
    return dict(registrationJobId=registration['id'], previousFingerprint=original.get('originFingerprint'),
                registeredFingerprint=observed['fingerprint'])
