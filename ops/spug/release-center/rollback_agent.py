"""Production application rollback; never restores or changes business databases.

Loaded beside the frozen release runtime. Private configurations stay on target.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import quote


def config_files(info):
    result = {}
    for mount in info['Mounts']:
        path = Path(mount['Source'])
        if mount['Type'] == 'bind' and path.is_file():
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            result[str(path)] = digest.hexdigest()
    return result


def snapshot_path(profile, tag):
    if not re.fullmatch(r'\d{4}(-\d{2}){5}', tag):
        raise ValueError('Invalid rollback releaseTag')
    return Path(profile['stagingRoot']) / 'rollback-snapshots' / (tag + '.private.json')


def capture(agent, profile, tag, origin):
    path = snapshot_path(profile, tag)
    snapshot = {'targetReleaseTag': tag, 'origin': origin, 'containers': {}, 'configFiles': {}}
    for role in ('frontend', 'backend'):
        info = agent.remote.inspect(profile[role])
        agent.require(info['State']['Running'] and info['Image'] == origin['images'][role],
                      'Stable source container differs before snapshot')
        snapshot['containers'][role] = info
        snapshot['configFiles'].update(config_files(info))
    if path.exists():
        saved = json.loads(path.read_text(encoding='utf-8'))
        agent.require(saved['targetReleaseTag'] == tag and
                      saved['origin']['fingerprint'] == origin['fingerprint'] and
                      saved['origin']['images'] == origin['images'] and
                      saved['origin']['releaseTag'] == origin['releaseTag'],
                      'Existing rollback snapshot origin differs; inspect original operation')
        agent.require(set(saved['containers']) == {'frontend', 'backend'} and
                      saved['configFiles'] == snapshot['configFiles'],
                      'Existing rollback snapshot configuration differs')
        for role, current in snapshot['containers'].items():
            original = saved['containers'][role]
            agent.require(all(current[key] == original[key]
                              for key in ('Id', 'Image', 'Config', 'HostConfig')) and
                          sorted(current['Mounts'], key=lambda item: item['Destination']) ==
                          sorted(original['Mounts'], key=lambda item: item['Destination']),
                          'Existing rollback snapshot container differs')
        # A pre-effect retry preserves the original recovery evidence byte for byte.
    else:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        agent.private_json(path, snapshot)
    return {'snapshotSha256': agent.file_sha(path), 'originReleaseTag': origin['releaseTag'],
            'configFileCount': len(snapshot['configFiles'])}


def inspect_snapshot(agent, profile, tag, origin):
    path = snapshot_path(profile, tag)
    if not path.is_file():
        return {'ready': False, 'blockers': ['缺少发布前配置文件摘要快照，不能授权回滚'], 'snapshotSha256': None}
    saved = json.loads(path.read_text())
    agent.require(saved['origin']['fingerprint'] == origin['fingerprint'], 'Rollback snapshot origin differs')
    agent.require(set(saved['containers']) == {'frontend', 'backend'}, 'Incomplete rollback container snapshot')
    blockers = []
    for name, expected in saved['configFiles'].items():
        if not Path(name).is_file() or agent.file_sha(Path(name)) != expected:
            blockers.append('原版本挂载配置文件已改变，必须恢复并验证原配置')
    ids = {}
    for role, original in saved['containers'].items():
        current = agent.remote.inspect(original['Id'])
        ids[role] = current['Id']
        if current['State']['Running']:
            blockers.append('原版本容器仍在运行，不能执行回滚切换')
        if current['Image'] != origin['images'][role] or current['Config'] != original['Config'] or current['HostConfig'] != original['HostConfig']:
            blockers.append('原版本容器镜像或配置已漂移')
    return {'ready': not blockers, 'blockers': blockers, 'snapshotSha256': agent.file_sha(path), 'containerIds': ids}


def execute(agent, profile, plan, job_id):
    agent.require(profile['host'] == '172.30.30.57' and profile['environment'] == 'prod', 'Production target identity differs')
    agent.require(re.fullmatch(r'JOB-[a-f0-9]{10}', job_id), 'Invalid operation identity')
    agent.require(set(profile['writers']) == {profile['backend']}, 'Additional writers require an explicit rollback adapter')
    current = agent.observe(profile)
    agent.require(current['fingerprint'] == plan['currentFingerprint'], 'Production changed after rollback preview')
    agent.require(current['schemaSha256'] == plan['origin']['schemaSha256'] and
                  current['ledgerSha256'] == plan['origin']['ledgerSha256'],
                  'Database differs from stable origin; application-only rollback forbidden')
    proof = inspect_snapshot(agent, profile, plan['currentReleaseTag'], plan['origin'])
    agent.require(proof['ready'] and proof['snapshotSha256'] == plan['snapshotSha256'], 'Rollback configuration proof changed')
    saved = json.loads(snapshot_path(profile, plan['currentReleaseTag']).read_text())
    operation = Path(profile['stagingRoot']) / 'rollback-operations' / job_id
    operation.mkdir(mode=0o700, parents=True, exist_ok=False)
    agent.private_json(operation / 'plan.private.json', plan)
    # The same writer-drain contract as deployment; it never issues database writes.
    agent.check_fence(profile)
    agent.stop_writers(profile)
    stopped = agent.observe(profile)
    agent.require(stopped['schemaSha256'] == current['schemaSha256'] and stopped['ledgerSha256'] == current['ledgerSha256'],
                  'Database changed during writer drain; leave applications stopped')
    final_proof = inspect_snapshot(agent, profile, plan['currentReleaseTag'], plan['origin'])
    agent.require(final_proof['ready'] and final_proof['snapshotSha256'] == plan['snapshotSha256'],
                  'Rollback configuration changed during writer drain; leave applications stopped')
    for role in ('frontend', 'backend'):
        original = saved['containers'][role]
        name = profile[role]
        failed = agent.remote.inspect(name)
        agent.private_json(operation / (role + '-failed.private.json'), failed)
        agent.docker('POST', '/containers/' + quote(name) + '/rename?name=' + quote(name + '-failed-' + job_id))
        for network in failed['NetworkSettings']['Networks']:
            if network not in ('host', 'none'):
                agent.docker('POST', '/networks/' + quote(network) + '/disconnect', {'Container': failed['Id'], 'Force': True})
        agent.docker('POST', '/containers/' + original['Id'] + '/rename?name=' + quote(name))
        for network, endpoint in original['NetworkSettings']['Networks'].items():
            if network in ('host', 'none'):
                continue
            config = {}
            if network != 'bridge':
                if endpoint.get('IPAMConfig'):
                    config['IPAMConfig'] = copy.deepcopy(endpoint['IPAMConfig'])
                elif endpoint.get('IPAddress'):
                    config['IPAMConfig'] = {'IPv4Address': endpoint['IPAddress']}
                if endpoint.get('Aliases'):
                    config['Aliases'] = endpoint['Aliases']
            agent.docker('POST', '/networks/' + quote(network) + '/connect', {'Container': original['Id'], 'EndpointConfig': config})
    for role in ('backend', 'frontend'):
        agent.docker('POST', '/containers/' + quote(profile[role]) + '/start')
    health = agent.health(profile, plan['targetReleaseTag'], False)
    actual = agent.observe(profile)
    agent.require(actual['images'] == plan['origin']['images'] and actual['releaseTag'] == plan['targetReleaseTag'] and
                  actual['schemaSha256'] == current['schemaSha256'] and actual['ledgerSha256'] == current['ledgerSha256'],
                  'Rollback verification failed; do not claim restored')
    agent.private_json(operation / 'result.private.json', {'observation': actual, 'health': health})
    return actual
