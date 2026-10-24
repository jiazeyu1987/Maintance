"""Normal deployment ordering, independent of explicit task recovery."""
import datetime
import re


DEPLOYMENT_TARGETS = {'publish-test': 'test', 'promote-prod': 'prod', 'promote-backup': 'backup'}
TARGET_NAMES = {'test': '测试服', 'prod': '正式服', 'backup': '备用服'}


def release_order(tag):
    if not isinstance(tag, str) or not re.fullmatch(r'\d{4}(?:-\d{2}){5}', tag):
        raise ValueError('版本号必须为北京时间 yyyy-MM-dd-HH-mm-ss')
    return datetime.datetime.strptime(tag, '%Y-%m-%d-%H-%M-%S')


def deployment_block(action, package, environments):
    """Return a user-visible reason; missing/invalid ordering evidence blocks."""
    if action not in DEPLOYMENT_TARGETS:
        return None
    if package.get('artifactsPruned'):
        return 'ARTIFACTS_RETIRED：该包产物已退役清理，禁止重新发布，请构建新包。'
    env = DEPLOYMENT_TARGETS[action]
    tag = package.get('releaseTag')
    current = environments.get(env, {}).get('releaseTag')
    try:
        candidate_order, current_order = release_order(tag), release_order(current)
    except ValueError:
        return f'RELEASE_ORDER_UNKNOWN：候选包或{TARGET_NAMES[env]}版本缺失/无效，请先核对版本登记。'
    if candidate_order < current_order:
        return f'STALE_RELEASE：候选包 {tag} 早于{TARGET_NAMES[env]}当前版本 {current}，禁止普通发布覆盖新版本。'
    if candidate_order == current_order:
        return f'RELEASE_ALREADY_DEPLOYED：{TARGET_NAMES[env]}已运行 {tag}；请查看原任务，不要新建重复发布。'
    if env == 'backup':
        production = environments.get('prod', {})
        if production.get('releaseTag') != tag:
            return f'PRODUCTION_PACKAGE_CHANGED：备用只能发布正式当前包 {production.get("releaseTag") or "未登记"}，不能发布所选包 {tag}。'
        if production.get('maintenance') is not False or production.get('maintenanceUnknown'):
            return 'PRODUCTION_NOT_OPEN：正式服尚未确认开放业务，不能发布备用服。'
        if package.get('outcomes', {}).get('prod', {}).get('acceptance', {}).get('status') != 'passed':
            return 'PRODUCTION_NOT_ACCEPTED：所选包尚未通过正式业务验收，不能发布备用服。'
    return None


def deployment_blocks(state):
    return {package['releaseTag']: {
        action: reason for action in DEPLOYMENT_TARGETS
        if (reason := deployment_block(action, package, state['environments']))
    } for package in state['packages']}
