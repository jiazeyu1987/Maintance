"""Frontend replacement and explicit restoration. Never executes database commands."""
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import quote
from urllib.request import urlopen


def write(path,value):
    temporary=path.with_suffix('.new')
    with temporary.open('w',encoding='utf-8') as stream:
        os.chmod(temporary,0o600)
        json.dump(value,stream,ensure_ascii=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary,path)


def observation(profile,a):
    remote=a['remote']
    components={}
    for role in ('frontend','backend','database'):
        value=remote.inspect(profile[role])
        a['require'](value['State']['Running'],role+' 容器未运行')
        components[role]=dict(containerId=value['Id'],imageId=value['Image'],startedAt=value['State']['StartedAt'])
        if role=='backend':
            addresses=[entry['IPAddress'] for entry in value['NetworkSettings']['Networks'].values() if entry.get('IPAddress')]
            a['require'](len(addresses)==1,'后端健康检查地址不明确')
            with urlopen('http://'+addresses[0]+':48081/actuator/health',timeout=10) as response:
                a['require'](response.status==200 and json.load(response).get('status')=='UP','后端健康检查未通过')
    metadata=json.loads(remote.run(['docker','exec',profile['frontend'],'cat','/usr/share/nginx/html/release-info.json']))
    a['require'](isinstance(metadata.get('releaseTag'),str),'前端缺少版本信息')
    with urlopen(profile['entryUrl']+'/',timeout=10) as response:
        a['require'](response.status==200,'前端未返回 HTTP 200')
    return dict(releaseTag=metadata.get('baseReleaseTag',metadata['releaseTag']),
                frontendPatchTag=metadata.get('frontendPatchTag'),metadata=metadata,components=components,frontendHttpStatus=200,backendHealth='UP')


def validate_origin(actual,expected,manifest,a):
    a['require'](actual==expected,'目标前端或后端起点已改变，请重新核对')
    a['require'](actual['releaseTag']==manifest['baseReleaseTag'],'目标主版本不适用本补丁')
    a['require'](actual['components']['backend']['imageId']==manifest['backendImageId'],'后端镜像不在补丁适用范围')
    a['require'](actual.get('frontendPatchTag')!=manifest['releaseTag'],'目标已安装同一补丁')
    a['require'](not actual.get('frontendPatchTag') or actual['frontendPatchTag']<manifest['releaseTag'],'目标补丁版本更新，禁止覆盖')


def check_untouched(before,after,a):
    a['require'](all(before['components'][role]==after['components'][role] for role in ('backend','database')),
                 '后端或数据库容器发生了外部变更；不能确认本次补丁')


def execute(profile,payload,a):
    import fcntl
    require,remote=a['require'],a['remote']
    action=payload['action'][len('frontend-patch-'):]
    if action=='observe':return observation(profile,a)
    manifest=payload['manifest']
    tag=manifest['releaseTag']
    require(manifest.get('kind')=='frontend-patch' and manifest.get('applicationId')=='intruoyi'
            and set(manifest['images'])=={'frontend'},'只能使用前端补丁包')
    require(re.fullmatch(r'\d{4}(-\d{2}){5}',tag),'补丁版本号无效')
    job=payload.get('workflowJobId')
    require(re.fullmatch(r'JOB-[a-f0-9]{10}',job or ''),'缺少任务编号')
    base=Path(profile['stagingRoot'])/'frontend-patches'
    base.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (base/'release.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        root=base/tag/job
        if action=='stage':
            front=remote.inspect(profile['frontend'])
            require(not any(m['Destination']=='/usr/share/nginx/html' or m['Destination'].startswith('/usr/share/nginx/html/') for m in front['Mounts']),
                    '前端静态目录由挂载覆盖，不能使用镜像补丁')
            require(root.is_dir() and not root.is_symlink(),'补丁传输目录不存在')
            a['unpack_original_package'](root,manifest,payload['archive'])
            remote.run(['docker','load','-i',str(root/'images.tar')],timeout=300)
            image=manifest['images']['frontend']
            require(json.loads(remote.run(['docker','image','inspect',image['name']]))[0]['Id']==image['id'],'补丁镜像不一致')
            return dict(staged=True,directory=str(root))
        if action=='verify':
            actual=observation(profile,a)
            require(actual['metadata']==manifest['metadata'] and actual['components']['frontend']['imageId']==manifest['images']['frontend']['id'],
                    '实际前端不是本补丁，不能验收')
            require(actual['components']['backend']['imageId']==manifest['backendImageId'],'实际后端不符合补丁基础版本')
            return actual
        if action=='restore':
            original=payload['originalJobId']
            require(re.fullmatch(r'JOB-[a-f0-9]{10}',original or ''),'原部署任务编号无效')
            original_root=base/tag/original
            receipt=json.loads((original_root/'deployment.json').read_text('utf-8'))
            require(receipt['packageSha256']==payload['archive']['sha256'],'原部署包身份不一致')
            require(receipt.get('effectsStarted'),'原任务尚未停止前端，无需恢复')
            snapshot=json.loads((original_root/'frontend-origin.private.json').read_text('utf-8'))
            before=receipt['origin']
            for role in ('backend','database'):
                current=remote.inspect(profile[role])
                require(current['Id']==before['components'][role]['containerId'] and current['Image']==before['components'][role]['imageId'],
                        '后端或数据库已变更，禁止恢复不匹配起点')
            names=remote.run(['docker','ps','-a','--format','{{.Names}}']).decode().splitlines()
            retained=profile['frontend']+'-before-'+original
            if retained not in names:
                current=remote.inspect(profile['frontend'])
                require(current['Id']==snapshot['Id'] and current['Image']==snapshot['Image'],'原前端恢复点不存在且当前身份不同')
                if not current['State']['Running']:remote.run(['docker','start',profile['frontend']])
                actual=wait(profile,before['metadata'],before['components']['frontend']['imageId'],a)
                check_untouched(before,actual,a)
                return dict(status='succeeded',originalJobId=original,observation=actual)
            old=remote.inspect(retained)
            require(old['Id']==snapshot['Id'] and not old['State']['Running'],'原前端恢复点身份变化')
            root.mkdir(parents=True,exist_ok=False,mode=0o700)
            write(root/'restoration.json',dict(status='running',originalJobId=original,packageSha256=payload['archive']['sha256']))
            if profile['frontend'] in names:
                current=remote.inspect(profile['frontend'])
                require(current['Image']==manifest['images']['frontend']['id'],'当前前端不是原任务候选，禁止覆盖')
                if current['State']['Running']:remote.run(['docker','stop',profile['frontend']])
                a['docker']('POST','/containers/'+quote(current['Id'])+'/rename?name='+quote(profile['frontend']+'-failed-'+job))
                for network in current['NetworkSettings']['Networks']:
                    if network not in ('host','none'):
                        a['docker']('POST','/networks/'+quote(network)+'/disconnect',{'Container':current['Id'],'Force':True})
            a['docker']('POST','/containers/'+quote(old['Id'])+'/rename?name='+quote(profile['frontend']))
            endpoints=a['clone_config'](snapshot,snapshot['Image']).get('NetworkingConfig',{}).get('EndpointsConfig',{})
            for network,endpoint in endpoints.items():
                if network not in old['NetworkSettings']['Networks']:
                    a['docker']('POST','/networks/'+quote(network)+'/connect',{'Container':old['Id'],'EndpointConfig':endpoint})
            remote.run(['docker','start',profile['frontend']])
            actual=wait(profile,before['metadata'],before['components']['frontend']['imageId'],a)
            check_untouched(before,actual,a)
            result=dict(status='succeeded',originalJobId=original,observation=actual)
            write(root/'restoration.json',result)
            return result
        require(action=='deploy','未知前端补丁操作')
        require((root/'manifest.json').is_file(),'尚未校验补丁包')
        require(json.loads((root/'manifest.json').read_text('utf-8'))==manifest,'远端补丁清单已改变')
        a['verify_files'](root,manifest['files'])
        before=observation(profile,a)
        validate_origin(before,payload['origin'],manifest,a)
        path=root/'deployment.json'
        require(not path.exists(),'原部署已登记，请核对原任务，禁止重复执行')
        a['private_json'](root/'frontend-origin.private.json',remote.inspect(profile['frontend']))
        receipt=dict(status='running',effectsStarted=True,origin=before,packageSha256=payload['archive']['sha256'])
        write(path,receipt)
        try:
            remote.run(['docker','stop',profile['frontend']])
            a['replace'](profile,root,'frontend',manifest['images']['frontend']['id'],job)
            remote.run(['docker','start',profile['frontend']])
            actual=wait(profile,manifest['metadata'],manifest['images']['frontend']['id'],a)
            check_untouched(before,actual,a)
            receipt.update(status='succeeded',observation=actual)
            write(path,receipt)
            return receipt
        except Exception as error:
            receipt.update(status='failed',errorType=type(error).__name__)
            write(path,receipt)
            raise


def wait(profile,metadata,image,a):
    for attempt in range(30):
        try:
            actual=observation(profile,a)
        except Exception:
            if attempt==29:raise
            time.sleep(1)
            continue
        a['require'](actual['metadata']==metadata and actual['components']['frontend']['imageId']==image,'前端镜像或版本身份不一致')
        return actual
    raise RuntimeError('前端未就绪')
