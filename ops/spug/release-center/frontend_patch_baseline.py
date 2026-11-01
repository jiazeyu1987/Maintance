"""Explicit live frontend baselines, independent of full-release package history."""
import re

from executor import require

ENVS = ('test', 'prod', 'backup')


def target_binding(profile):
    return {key: profile[key] for key in ('host', 'environment', 'entryUrl', 'frontend', 'backend', 'database')}


def validate_observations(origins):
    require(set(origins) == set(ENVS), '补丁基线必须完整读取三服')
    for env, origin in origins.items():
        require(re.fullmatch(r'\d{4}(-\d{2}){5}', origin.get('releaseTag', '')), env + ': 当前主版本无效')
        require(re.fullmatch(r'[a-f0-9]{40}', origin.get('metadata', {}).get('sourceCommit', '')),
                env + ': 实际前端缺少有效源码提交，无法确定补丁源码起点')
        for role in ('frontend', 'backend', 'database'):
            component = origin.get('components', {}).get(role, {})
            require(re.fullmatch(r'sha256:[a-f0-9]{64}', component.get('imageId', ''))
                    and component.get('containerId') and component.get('startedAt'),
                    env + ': ' + role + ' 实际容器身份不完整')
        require(origin.get('backendHealth') == 'UP' and origin.get('frontendHttpStatus') == 200,
                env + ': 当前程序未通过健康检查')
    first = origins['prod']
    for env in ENVS:
        origin = origins[env]
        require(all(origin.get(key) == first.get(key) for key in ('releaseTag', 'frontendPatchTag', 'metadata'))
                and all(origin['components'][role]['imageId'] == first['components'][role]['imageId']
                        for role in ('frontend', 'backend')),
                '三服当前程序版本、源码或镜像不一致，请先明确统一补丁起点')
    return first['metadata']['sourceCommit']


def build_base(executor, payload):
    """The caller explicitly selects a live baseline OR an existing package."""
    baseline_id = payload.get('baselineId')
    require(not (baseline_id and payload.get('baseReleaseTag')), '不能同时选择现场基线和历史包基线')
    if baseline_id:
        rows = [b for b in executor.state.get('frontendPatchBaselines', []) if b['id'] == baseline_id]
        require(len(rows) == 1, '现场补丁基线不存在，请先读取并登记三服当前基线')
        baseline = rows[0]
        validate_observations(baseline['origins'])
        return dict(releaseTag=baseline['releaseTag'], gitCommit=baseline['gitCommit']), {
            'backendImageId': baseline['origins']['prod']['components']['backend']['imageId'],
            'observedBaseline': baseline}
    require(payload.get('baseReleaseTag'), '请明确选择补丁基线')
    base, manifest = executor.manifest(payload['baseReleaseTag'])
    return base, {'backendImageId': manifest['images']['backend']['id']}


def validate_live_origin(executor, baseline, env, actual):
    require(target_binding(executor.runtime.profile(env)) == baseline['targets'][env],
            env + ': 目标服务器配置已改变，请重新登记补丁基线')
    require(actual == baseline['origins'][env],
            env + ': 当前容器、镜像或版本已偏离登记的补丁基线，请重新核对')
