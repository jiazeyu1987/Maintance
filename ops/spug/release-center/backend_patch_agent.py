"""Single-JAR switch. No migrations, data repair, configuration DML or backups.

The sole SQL writes are an owned, non-persistent MySQL GLOBAL read-only fence.
On failure it stays closed; explicit restoration owns its release. No finally
block unlocks a failed startup. Receipts contain identities, never credentials.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time
from urllib.parse import quote
from urllib.request import urlopen

from backend_patch_contract import need, validate_manifest, patch_config, PATHS, PREFIX


def write(path,value):
    temporary=path.with_suffix('.new')
    with temporary.open('w',encoding='utf-8') as stream:
        os.chmod(temporary,0o600)
        json.dump(value,stream,ensure_ascii=True)
        stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)


def fence_state(profile,remote):
    return remote.sql(profile,'SELECT @@global.read_only,@@global.super_read_only;')


def acquire_fence(profile,root,remote):
    need(fence_state(profile,remote)=='0\t0','外部数据库只读保护已启用，禁止接管或解除')
    need(not remote.sql(profile,'SHOW REPLICA STATUS;'),'复制写入线程不受 super_read_only 约束，不支持此补丁通道')
    path=root/'database-fence.json'
    need(not path.exists(),'数据库保护已登记，必须核对原任务')
    value=dict(status='acquiring',databaseId=remote.inspect(profile['database'])['Id'])
    write(path,value)
    remote.sql(profile,'SET GLOBAL super_read_only=ON;')
    need(fence_state(profile,remote)=='1\t1','数据库启动只读保护未生效')
    write(path,dict(value,status='owned'))


def release_fence(profile,root,remote):
    path=root/'database-fence.json'
    value=json.loads(path.read_text('utf-8'))
    need(value['status'] in ('owned','acquiring') and value['databaseId']==remote.inspect(profile['database'])['Id'],
         '禁止解除不属于原任务或数据库已变化的保护')
    need(fence_state(profile,remote)=='1\t1','数据库保护漂移，禁止自动开放')
    remote.sql(profile,'SET GLOBAL super_read_only=OFF; SET GLOBAL read_only=OFF;')
    need(fence_state(profile,remote)=='0\t0','未确认本任务保护已解除')
    write(path,dict(value,status='released'))


def observation(profile,a,*,online=True):
    remote=a['remote'];raw=remote.observe(profile)
    info=remote.inspect(profile['backend'])
    labels=info['Config'].get('Labels') or {}
    jar=remote.run(['docker','exec',profile['backend'],'sha256sum',PATHS['app.jar']]).decode().split()[0]
    need(re.fullmatch('[a-f0-9]{64}',jar),'无法读取实际后端 JAR 摘要')
    metadata=json.loads(remote.run(['docker','exec',profile['backend'],'cat',PATHS['release-info.json']]))
    frontend=json.loads(remote.run(['docker','exec',profile['frontend'],'cat','/usr/share/nginx/html/release-info.json']))
    tag=frontend.get('baseReleaseTag',frontend.get('releaseTag'))
    need(metadata.get('baseReleaseTag',metadata.get('releaseTag'))==tag,'前后端基础版本不一致')
    patch=labels.get(PREFIX+'tag')
    if patch:
        need(metadata.get('backendPatchTag')==patch and labels.get(PREFIX+'sha256')==jar,'实际补丁 JAR/标签/元数据不一致')
        mounts={m['Destination']:m for m in info['Mounts']}
        for name,dest in PATHS.items():
            mount=mounts.get(dest,{})
            need(mount.get('Source')==labels.get(PREFIX+'root','')+'/'+name and mount.get('RW') is False,
                 '补丁程序必须使用登记的只读挂载')
    else:
        need(not metadata.get('backendPatchTag') and not any(m['Destination'] in PATHS.values() for m in info['Mounts']),
             '发现未登记的后端程序覆盖')
    result=dict(releaseTag=tag,frontendPatchTag=frontend.get('frontendPatchTag'),frontendMetadata=frontend,
        backendPatchTag=patch,backendJarSha256=jar,backendMetadata=metadata,components=raw['components'],
        schemaSha256=raw['schemaSha256'],ledgerSha256=a['sha'](raw['migrationLedgers']),
        databaseIdentity=raw['databaseIdentity'],backendConfigSha256=a['sha'](a['runtime_config_snapshot'](info)))
    if online:
        runtime=wait_backend(profile,a,tag,False)
        with urlopen(profile['entryUrl']+'/',timeout=10) as response:
            need(response.status==200,'前端未返回 HTTP 200')
        need(all(c['running'] for c in raw['components'].values()),'程序或数据库容器未运行')
        result.update(backendHealth='UP',frontendHttpStatus=200,gxpAuditMode=runtime['gxpAuditMode'])
    return result


def validate_baseline(origins):
    need(set(origins)=={'test','prod','backup'},'必须读取三服实际补丁基线')
    first=origins['prod']
    for env,value in origins.items():
        for key in ('releaseTag','frontendPatchTag','frontendMetadata','backendPatchTag','backendJarSha256',
                    'backendMetadata','schemaSha256'):
            need(value.get(key)==first.get(key),env+': 三服程序/JAR/数据库结构不一致')
        # Migration receipts are environment history, not program identity.
        # Keep each origin intact; verify_unchanged guards its own ledger.
        need(re.fullmatch('[a-f0-9]{64}',value.get('ledgerSha256','')),
             env+': 缺少本环境迁移台账摘要')
        need(all(value['components'][r]['imageId']==first['components'][r]['imageId'] for r in ('backend','frontend')),
             env+': 三服运行镜像不一致')
    commit=first.get('backendMetadata',{}).get('sourceCommit')
    need(re.fullmatch('[a-f0-9]{40}',commit or ''),'实际后端缺少源码提交')
    need(re.fullmatch('[a-f0-9]{64}',first.get('backendJarSha256','')),'缺少实际 JAR 摘要')
    return commit


def verify_unchanged(before,after):
    for key in ('schemaSha256','ledgerSha256','databaseIdentity'):
        need(before[key]==after[key],'数据库身份/结构/迁移台账漂移: '+key)
    for role in ('database','frontend'):
        for key in ('containerId','imageId'):
            need(before['components'][role][key]==after['components'][role][key],role+' 容器被替换')
    need(before.get('frontendMetadata')==after.get('frontendMetadata'),'前端版本发生变化')


def wait_backend(profile,a,tag,maintenance):
    deadline=time.monotonic()+a['startup_timeout'](profile)
    while time.monotonic()<deadline:
        try:
            info=a['remote'].inspect(profile['backend'])
            addresses=[n['IPAddress'] for n in info['NetworkSettings']['Networks'].values() if n.get('IPAddress')]
            need(len(addresses)==1,'后端地址不明确')
            url='http://'+addresses[0]+':48081/actuator/'
            with urlopen(url+'health',timeout=5) as response:
                need(response.status==200 and json.load(response).get('status')=='UP','后端健康检查未通过')
            with urlopen(url+'release',timeout=5) as response:runtime=json.load(response)
            a['validate_release_state'](runtime,tag,maintenance)
            need(runtime.get('gxpAuditMode')==runtime.get('configuredGxpAuditMode')=='DEVELOPMENT_DISABLED',
                 'GxP 保存和运行状态必须已关闭；补丁不写配置')
            return runtime
        except Exception:
            if time.monotonic()+2>=deadline:raise
            time.sleep(2)
    raise ValueError('后端启动超时')


def replace_backend(profile,snapshot,config,retained,a):
    remote=a['remote'];name=profile['backend']
    need(not remote.inspect(name)['State']['Running'],'必须先停止后端')
    a['docker']('POST','/containers/'+quote(name)+'/rename?name='+quote(retained))
    for network in snapshot['NetworkSettings']['Networks']:
        if network not in ('host','none'):
            a['docker']('POST','/networks/'+quote(network)+'/disconnect',{'Container':snapshot['Id'],'Force':True})
    created=a['docker']('POST','/containers/create?name='+quote(name),config)
    actual=remote.inspect(created['Id'])
    need(actual['Image']==snapshot['Image'] and actual['HostConfig']['PortBindings']==snapshot['HostConfig']['PortBindings'],
         '补丁不得更换 Java 运行镜像或端口')
    old={json.dumps(m,sort_keys=True) for m in snapshot['Mounts'] if m['Destination'] not in PATHS.values()}
    new={json.dumps(m,sort_keys=True) for m in actual['Mounts'] if m['Destination'] not in PATHS.values()}
    need(old==new,'补丁改变了程序以外的挂载')
    remote.run(['docker','start',name])
    return created['Id']


def check_startup_writes(profile,a):
    # Do not return raw logs, which can contain private configuration.
    # Docker sends container stderr to the CLI stderr stream. Merge it locally
    # without ever returning log contents or shell configuration to the caller.
    import subprocess
    result=subprocess.run(['docker','logs',profile['backend']],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    need(result.returncode==0,'无法检查启动日志，禁止开放')
    logs=result.stdout
    need(not re.search(rb'super.read.only|read.only option|ERROR 1290|SQLState[^\n]*25006',logs,re.I),
         '启动程序尝试写入被只读保护拒绝；保持关闭，请恢复原程序并改用完整发布')


def execute(profile,payload,a):
    remote=a['remote'];action=payload['action'][len('backend-patch-'):]
    if action=='observe':return observation(profile,a)
    manifest=validate_manifest(payload['manifest']);tag=manifest['releaseTag']
    job=payload.get('workflowJobId','')
    need(re.fullmatch('JOB-[a-f0-9]{10}',job),'缺少持久任务身份')
    base=Path(profile['stagingRoot'])/'backend-patches';root=base/tag/job
    if action=='prepare':
        need(isinstance(payload['archive'].get('bytes'),int) and payload['archive']['bytes']>0,'缺少真实原包大小')
        base.mkdir(parents=True,exist_ok=True,mode=0o700)
        need(not base.is_symlink() and all(not p.is_symlink() for p in base.parents),'补丁暂存路径含链接')
        needed=2*payload['archive']['bytes']+1024**3
        need(shutil.disk_usage(base).free>=needed,'暂存文件系统空间不足：需要原包与解包大小及1GiB余量')
        root.mkdir(parents=True,exist_ok=False,mode=0o700)
        return {'directory':str(root),'requiredFreeBytes':needed}
    if action=='verify':
        actual=observation(profile,a)
        need(actual['backendPatchTag']==tag and actual['backendJarSha256']==manifest['files'][0]['sha256']
             and actual['backendMetadata']==manifest['metadata'],'实际后端不是当前补丁')
        verify_unchanged(manifest['baseline']['origins'][profile['environment']],actual)
        return actual
    if action=='stage':
        need(root.is_dir() and not root.is_symlink(),'补丁传输目录无效')
        a['unpack_original_package'](root,manifest,payload['archive'])
        return {'staged':True}
    if action=='restore':return restore(profile,payload,a,base,root)
    need(action=='deploy','未知后端补丁操作')
    need(json.loads((root/'manifest.json').read_text('utf-8'))==manifest,'远端补丁清单已改变')
    a['verify_files'](root,manifest['files'])
    before=observation(profile,a)
    need(before==payload['origin']==manifest['baseline']['origins'][profile['environment']], '实际起点偏离固定补丁基线')
    need(profile.get('writerInventoryConfirmed') is True and profile['backend'] in profile.get('writers',[]),
         '必须明确登记全部写者')
    need(profile['database'] not in profile['writers'],'数据库服务不能登记为待停止写者')
    for name in dict.fromkeys([profile['frontend']]+profile['writers']):
        need(remote.inspect(name)['State']['Running'],'登记写者已有停止，禁止改变未知起点状态')
    need(not remote.sql(profile,'SHOW REPLICA STATUS;'),'复制写入线程不受 super_read_only 约束，不支持此补丁通道')
    need(fence_state(profile,remote)=='0\t0','已有外部数据库保护，停止发布')
    snapshot=remote.inspect(profile['backend'])
    command=' '.join((snapshot['Config'].get('Entrypoint') or [])+(snapshot['Config'].get('Cmd') or []))
    need(snapshot['Config'].get('WorkingDir')=='/yudao-server' and '-jar app.jar' in command,
         '不支持的后端程序入口，必须使用完整发布')
    patch_config(a['clone_config'](snapshot,snapshot['Image'],True),str(root),tag,manifest['files'][0]['sha256'])
    need(not (root/'deployment.json').exists(),'部署已有回执，禁止重放')
    a['private_json'](root/'backend-origin.private.json',snapshot)
    receipt=dict(status='running',effectsStarted=True,origin=before,packageSha256=payload['archive']['sha256'],jobId=job)
    write(root/'deployment.json',receipt)
    try:
        a['stop_writers'](profile)
        acquire_fence(profile,root,remote)
        config=patch_config(a['clone_config'](snapshot,snapshot['Image'],True),str(root),tag,manifest['files'][0]['sha256'])
        replace_backend(profile,snapshot,config,profile['backend']+'-before-'+job,a)
        wait_backend(profile,a,manifest['baseReleaseTag'],True)
        check_startup_writes(profile,a)
        remote.run(['docker','stop','--time','90',profile['backend']],timeout=120)
        probe=remote.inspect(profile['backend'])
        need(probe['State']['ExitCode']!=137,'验证后端未正常停止')
        a['private_json'](root/'backend-probe.private.json',probe)
        config=patch_config(a['clone_config'](snapshot,snapshot['Image'],False),str(root),tag,manifest['files'][0]['sha256'])
        replace_backend(profile,probe,config,profile['backend']+'-probe-'+job,a)
        wait_backend(profile,a,manifest['baseReleaseTag'],False)
        check_startup_writes(profile,a)
        # docker cp works for a stopped frontend; observation must not exec it.
        after=database_program_observation(profile,a,before)
        verify_unchanged(before,after)
        release_fence(profile,root,remote)
        for name in dict.fromkeys([profile['frontend']]+profile['writers']):
            if name!=profile['backend']:remote.run(['docker','start',name])
        actual=observation(profile,a)
        verify_unchanged(before,actual)
        need(actual['backendJarSha256']==manifest['files'][0]['sha256'],'运行 JAR 摘要不一致')
        receipt.update(status='succeeded',observation=actual,databaseChanged=False)
        write(root/'deployment.json',receipt)
        return receipt
    except Exception as error:
        receipt.update(status='failed',errorType=type(error).__name__)
        write(root/'deployment.json',receipt)
        raise


def database_program_observation(profile,a,before):
    raw=a['remote'].observe(profile)
    info=a['remote'].inspect(profile['backend'])
    jar=a['remote'].run(['docker','exec',profile['backend'],'sha256sum',PATHS['app.jar']]).decode().split()[0]
    return dict(before,components=raw['components'],schemaSha256=raw['schemaSha256'],
                ledgerSha256=a['sha'](raw['migrationLedgers']),databaseIdentity=raw['databaseIdentity'],backendJarSha256=jar)


def restore(profile,payload,a,base,root):
    remote=a['remote'];original=payload.get('originalJobId','')
    need(re.fullmatch('JOB-[a-f0-9]{10}',original),'原部署任务无效')
    original_root=base/payload['manifest']['releaseTag']/original
    receipt=json.loads((original_root/'deployment.json').read_text('utf-8'))
    need(receipt['packageSha256']==payload['archive']['sha256'],'原任务包身份不一致')
    snapshot=json.loads((original_root/'backend-origin.private.json').read_text('utf-8'))
    before=receipt['origin'];names=remote.run(['docker','ps','-a','--format','{{.Names}}']).decode().splitlines()
    for role in ('database','frontend'):
        need(remote.inspect(profile[role])['Id']==before['components'][role]['containerId'],'原目标容器已变更，禁止恢复')
    root.mkdir(parents=True,exist_ok=False,mode=0o700)
    write(root/'restoration.json',{'status':'running','originalJobId':original})
    # A failed Docker create can leave the canonical backend name absent.
    # Stop only present registered writers; do not require the failed candidate
    # to have exited cleanly before restoring the unchanged original program.
    for name in dict.fromkeys([profile['frontend']]+profile['writers']):
        if name not in names:
            need(name==profile['backend'],'登记写者缺失，停止恢复')
            continue
        if remote.inspect(name)['State']['Running']:
            remote.run(['docker','stop','--time','90',name],timeout=120)
        need(not remote.inspect(name)['State']['Running'],'写者未停止，禁止恢复')
    need(remote.sql(profile,'SELECT COUNT(*) FROM information_schema.INNODB_TRX;')=='0','仍有数据库事务，停止恢复')
    fence=original_root/'database-fence.json'
    if fence.exists() and json.loads(fence.read_text('utf-8'))['status'] in ('owned','acquiring'):
        fence_root=original_root
        need(fence_state(profile,remote)=='1\t1','原任务保护状态漂移')
    else:
        acquire_fence(profile,root,remote);fence_root=root
    retained=profile['backend']+'-before-'+original
    if retained in names:
        old=remote.inspect(retained)
        need(old['Id']==snapshot['Id'] and not old['State']['Running'],'原程序恢复点已变化')
        current=remote.inspect(profile['backend']) if profile['backend'] in names else None
        if current:
            need((current['Config'].get('Labels') or {}).get(PREFIX+'tag')==payload['manifest']['releaseTag'],
                 '当前后端不属于原补丁，禁止覆盖')
            a['docker']('POST','/containers/'+quote(current['Id'])+'/rename?name='+quote(profile['backend']+'-failed-'+payload['workflowJobId']))
            for network in current['NetworkSettings']['Networks']:
                if network not in ('host','none'):
                    a['docker']('POST','/networks/'+quote(network)+'/disconnect',{'Container':current['Id'],'Force':True})
        a['docker']('POST','/containers/'+quote(old['Id'])+'/rename?name='+quote(profile['backend']))
        endpoints=a['clone_config'](snapshot,snapshot['Image']).get('NetworkingConfig',{}).get('EndpointsConfig',{})
        for network,endpoint in endpoints.items():
            if network not in old['NetworkSettings']['Networks']:
                a['docker']('POST','/networks/'+quote(network)+'/connect',{'Container':old['Id'],'EndpointConfig':endpoint})
    else:
        need(remote.inspect(profile['backend'])['Id']==snapshot['Id'],'原程序不存在，禁止猜测恢复点')
    remote.run(['docker','start',profile['backend']])
    wait_backend(profile,a,before['releaseTag'],False)
    check_startup_writes(profile,a)
    after=database_program_observation(profile,a,before)
    verify_unchanged(before,after)
    need(after['backendJarSha256']==before['backendJarSha256'],'原程序 JAR 身份不一致')
    release_fence(profile,fence_root,remote)
    for name in dict.fromkeys([profile['frontend']]+profile['writers']):
        if name!=profile['backend']:remote.run(['docker','start',name])
    actual=observation(profile,a)
    verify_unchanged(before,actual)
    result=dict(status='succeeded',originalJobId=original,observation=actual,databaseRestored=False)
    write(root/'restoration.json',result)
    return result
