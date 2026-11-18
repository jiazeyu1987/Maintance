"""Explicit target adoption without rewriting failed deployment evidence."""


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
