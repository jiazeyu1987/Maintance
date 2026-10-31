"""Explicit, non-destructive handover of a completed isolation registration."""
from copy import deepcopy
from pathlib import PurePosixPath

from intruoyi_runtime import rehearsal_profile, require
from intruoyi_rehearsal_agent import rehearsal_endpoints, rehearsal_gateway_name


def retention_matches(config, environment):
    binding = config.get('rehearsalRetention', {})
    return bool(environment and binding.get('fingerprint')
                and environment.get('fingerprint') == binding['fingerprint']
                and environment.get('releaseTag') == binding.get('releaseTag'))


def registered_rehearsal_profile(config, environment):
    """Keep a registered isolation bound to its resources across config changes."""
    source = environment.get('sourceEnvironment')
    profile = environment.get('resourceProfile')
    if profile is None and retention_matches(config, environment):
        profile = config['rehearsalRetention'].get('profile')
        require(isinstance(profile, dict), 'Retained rehearsal resource profile required')
    if profile is None:
        profile = rehearsal_profile(config, source)
    require(profile.get('sourceEnvironment') == source, 'Registered rehearsal source differs')
    for key in ('host','entryUrl'):
        require(not environment.get(key) or profile.get(key) == environment[key],
                'Registered rehearsal resource profile differs: '+key)
    return deepcopy(profile)


def disjoint_profiles(previous, candidate):
    if previous['host'] != candidate['host']:
        return
    def names(profile):
        values = {profile[key] for key in
                  ('frontend','backend','database','redis','minio','acceptanceFrontend','network')}
        values.add(rehearsal_gateway_name(profile))
        values.update(profile[key]+'-data' for key in ('database','redis','minio'))
        return values
    require(not names(previous) & names(candidate), 'Retained rehearsal resource names overlap')
    old_ports = {item['port'] for item in rehearsal_endpoints(previous).values()}
    new_ports = {item['port'] for item in rehearsal_endpoints(candidate).values()}
    require(not old_ports & new_ports, 'Retained rehearsal ports overlap')
    old_root, new_root = (PurePosixPath(p['stagingRoot']) for p in (previous,candidate))
    require(old_root.is_absolute() and new_root.is_absolute()
            and '..' not in old_root.parts and '..' not in new_root.parts,
            'Absolute non-traversing rehearsal staging roots required')
    require(old_root != new_root and old_root not in new_root.parents and new_root not in old_root.parents,
            'Retained rehearsal staging roots overlap')


def retention_record(state, config, candidate, observation, job_id, time):
    """Validate first; return a snapshot without changing state or remote resources."""
    environment = state['environments']['rehearsal']
    require(retention_matches(config, environment), 'Explicit matching rehearsal retention binding required')
    binding = config['rehearsalRetention']
    packages = [p for p in state['packages'] if p['releaseTag'] == binding['releaseTag']]
    require(len(packages) == 1 and packages[0].get('stage') == 'completed',
            'Only a completed package rehearsal can be retained for handover')
    package = packages[0]
    records = [r for r in package.get('rehearsals', []) if r.get('id') == binding.get('rehearsalId')]
    require(len(records) == 1 and package.get('activeRehearsal') == binding.get('rehearsalId'),
            'Retention must identify the completed active rehearsal')
    record = records[0]
    require(record.get('status') == 'passed' and record.get('source') == 'prod'
            and record.get('technical', {}).get('status') == 'passed'
            and record.get('packageSha256') == package['packageSha256'],
            'Passed same-package production rehearsal evidence required for retention')
    for key in ('fingerprint','releaseTag','images','schemaSha256','ledgerSha256'):
        require(environment.get(key) and observation.get(key) == environment[key],
                'Retained rehearsal runtime differs: '+key)
    require(observation.get('backendHealth', {}).get('status') == 'UP'
            and observation.get('frontendHttpStatus') == 200, 'Retained rehearsal runtime is not healthy')
    previous = registered_rehearsal_profile(config, environment)
    disjoint_profiles(previous, candidate)
    require(not any(item.get('rehearsalId') == record['id']
                    and item.get('releaseTag') == package['releaseTag']
                    for item in state.get('retainedRehearsals', [])), 'Rehearsal already retained')
    return deepcopy(dict(rehearsalId=record['id'],releaseTag=package['releaseTag'],
                         packageSha256=package['packageSha256'],environment=environment,
                         profile=previous,observation=observation,retainedBy=job_id,
                         retainedAt=time,remoteResourcesPreserved=True))
