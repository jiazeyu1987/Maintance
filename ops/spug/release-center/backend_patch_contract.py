"""Pure contracts shared by builder, remote agent and full-release transition."""
import copy
import re


def need(value, message):
    if not value:
        raise ValueError(message)


PREFIX = 'intruoyi.backend-patch.'
PATHS = {'app.jar': '/yudao-server/app.jar', 'release-info.json': '/yudao-server/release-info.json'}


def validate_manifest(value):
    need(value.get('applicationId') == 'intruoyi' and value.get('kind') == 'backend-patch', '不是后端 JAR 补丁')
    need(not any(k in value for k in ('migrations','sql','images','data','hooks','executionPlans')), '后端补丁禁止数据库迁移、数据、钩子和镜像')
    need(value.get('databasePolicy') == 'no-migrations-readonly-startup-v1', '缺少数据库禁止修改合同')
    for key in ('releaseTag','baseReleaseTag'):
        need(re.fullmatch(r'\d{4}(-\d{2}){5}',value.get(key,'')), '补丁版本无效')
    for key in ('gitCommit','baseGitCommit'):
        need(re.fullmatch('[a-f0-9]{40}',value.get(key,'')), '源码提交无效')
    files=value.get('files',[])
    need([f.get('name') for f in files]==list(PATHS), '补丁仅允许依次排列的 app.jar 和版本元数据')
    need(all(re.fullmatch('[a-f0-9]{64}',f.get('sha256','')) for f in files),'补丁文件摘要无效')
    need(value.get('releaseSettings',{}).get('gxpAuditMode')=='DEVELOPMENT_DISABLED','后端补丁要求 GxP 已关闭，不能通过补丁修改配置')
    return value


def validate_changes(paths):
    need(paths,'没有后端代码变更')
    for path in paths:
        allowed=(path.startswith('IntRuoyiBackend/') and '/src/' in path and path.endswith('.java')
                 and ('/main/java/' in path or '/test/java/' in path))
        need(allowed and not any(s in path.lower() for s in ('/dataobject/','migration','initializer','configuration.java',
             'applicationrunner','commandlinerunner','/tracer/config/release','/script/')),
             '补丁仅允许兼容的 Java 修复；数据库、配置、依赖和启动合同变更请使用完整发布: '+path)
    return paths


def full_release_config(config):
    """Remove only the two proven patch-owned binds; never reset secrets/data mounts."""
    labels=config.get('Labels') or {}
    root=labels.get(PREFIX+'root')
    binds=config.get('HostConfig',{}).get('Binds') or []
    def covers(dest):
        return any(p==dest or p.startswith(dest.rstrip('/')+'/') for p in PATHS.values())
    program=[b for b in binds if len(b.split(':'))>=2 and covers(b.split(':')[1])]
    need(not any(covers(m.get('Target','?')) for m in config.get('HostConfig',{}).get('Mounts',[])),
         '不支持的程序 Mounts 覆盖')
    if not root:
        need(not program,'未知后端程序挂载，不能用新镜像覆盖身份')
        return config
    expected={root+'/'+name+':'+dest+':ro' for name,dest in PATHS.items()}
    need(set(program)==expected and len(program)==2,'后端补丁挂载归属不一致')
    need(not any(m.get('Target') in PATHS.values() for m in config['HostConfig'].get('Mounts',[])), '程序使用不支持的 Mounts 配置')
    config['HostConfig']['Binds']=[b for b in binds if b not in expected]
    if config.get('Volumes'):
        config['Volumes']={k:v for k,v in config['Volumes'].items() if k not in PATHS.values()}
    config['Labels']={k:v for k,v in labels.items() if not k.startswith(PREFIX)}
    return config


def patch_config(original_config, root, tag, sha):
    config=full_release_config(copy.deepcopy(original_config))
    config['HostConfig']['Binds']=(config['HostConfig'].get('Binds') or [])+[
        root+'/'+name+':'+dest+':ro' for name,dest in PATHS.items()]
    config['Labels']=dict(config.get('Labels') or {}, **{PREFIX+'root':root,PREFIX+'tag':tag,PREFIX+'sha256':sha})
    return config
