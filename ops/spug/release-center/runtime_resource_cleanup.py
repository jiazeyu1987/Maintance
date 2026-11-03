"""Plan exact retired resources from bound deployment/recovery evidence.

No age/name-only discovery, container stop, image force or volume removal.
Private inspect data stays in memory; plans contain identity digests only.
"""
import hashlib
import json
from pathlib import Path
import re
import stat

import artifact_files as files

require=files.require


def containers():
    ids=files.docker(['ps','-aq','--no-trunc']).decode().split()
    # --size scans unrelated writable layers; identity does not need that scan.
    return json.loads(files.docker(['inspect',*ids])) if ids else []


def fingerprint(value):
    # Runtime network endpoints, timestamps and names change on retirement.
    value={key:value.get(key) for key in ('Id','Image','Config','HostConfig','Mounts')}
    # Docker builds Mounts from a map; array order is not configuration identity.
    # Preserve all mount fields and the order of genuinely ordered Config lists.
    if isinstance(value['Mounts'],list):
        value['Mounts']=sorted(value['Mounts'],key=lambda m:json.dumps(m,sort_keys=True,separators=(',',':')))
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def stopped(value):
    state=value['State']
    return not any(state.get(key) for key in ('Running','Paused','Restarting'))


def read(root,name):
    path=files.safe_file(root,name)
    if not path.exists():return None
    require(path.is_file() and path.stat().st_nlink==1,'清理依据不是独立普通文件')
    return json.loads(path.read_text('utf-8'))


def file_row(root,path,digest=None,kind='已核销失败资料'):
    path=files.safe_file(root,str(path.relative_to(root)))
    require(files.same_device(root,path) and path.stat().st_nlink==1,'恢复资料跨设备或存在硬链接')
    identity=files.file_identity(path)
    digest=digest or files.sha(path)
    require(files.sha(path)==digest,'恢复资料摘要发生变化')
    return dict(root=str(root),relative=str(path.relative_to(root)),sha256=digest,kind=kind,**identity)


def tree_rows(root,mounts):
    """Freeze every exact file; unlink/rmdir later never recursively follows paths."""
    require(root.is_absolute() and root!=Path('/') and len(root.parts)>=3
            and not (root==Path('/mnt/nas') or Path('/mnt/nas') in root.parents),'失败现场路径无效或属于NAS')
    files.safe_file(root,'.cleanup-check')
    require(root.is_dir(),'失败现场目录不存在')
    require(not any(Path(m)==root or root in Path(m).parents or Path(m) in root.parents for m in mounts),
            '失败现场或其子目录仍被容器挂载')
    result=[];directories=[]
    for path in sorted(root.rglob('*')):
        files.safe_file(root,str(path.relative_to(root)))
        require(files.same_device(root,path),'失败现场跨设备')
        require(not files.mounted(path,mounts) and str(path) not in mounts,'失败现场仍被容器挂载')
        mode=path.lstat().st_mode
        if stat.S_ISDIR(mode):directories.append(path)
        else:
            require(stat.S_ISREG(mode),'失败现场包含特殊文件')
            result.append(file_row(root,path))
    require(not files.mounted(root,mounts),'失败现场根仍被容器挂载')
    directories.append(root)
    return result,[dict(root=str(root),relative=str(p.relative_to(root)),inode=p.stat().st_ino)
                   for p in sorted(directories,key=lambda p:len(p.parts),reverse=True)]


def plan(profile,payload):
    base=Path(profile['stagingRoot']);actual=containers();by_id={c['Id']:c for c in actual}
    held=set(payload['protectedTags'])|{payload['currentReleaseTag'],payload.get('currentPatchTag')}
    result=dict(containers=[],images=[],files=[],directories=[],retained=[],protectedImages=[],protectedContainers=[])
    protected_images=set(payload.get('protectedImageIds',[]))|set(payload['expectedImages'].values())
    protected_ids={c['Id'] for c in actual if c['Name'].lstrip('/') in
                   (profile['backend'],profile['frontend'],profile.get('database'),profile.get('redis'),profile.get('minio'))}
    candidates=[];image_rows=[];seen=set();blocked=set()
    mounts=[m['Source'] for c in actual for m in c.get('Mounts',[]) if m.get('Source')]

    def retain(kind,identity,reason):
        result['retained'].append(dict(kind=kind,identity=identity,reason=reason))

    def snapshot(value,names,tag,protect=False):
        if not value:return
        if protect:
            protected_ids.add(value['Id']);protected_images.add(value['Image'])
        candidates.append(dict(id=value['Id'],imageId=value['Image'],names=names,
                               fingerprint=fingerprint(value),releaseTag=tag))

    for entry in payload.get('resourceEntries',[]):
        root=files.cleanup_root(base,entry);tag=entry['manifest']['releaseTag']
        if not root.exists():continue
        marker=files.safe_file(root,'manifest.json')
        require(marker.is_file() and files.sha(marker)==entry['manifestSha256'], '资源清理清单身份不一致')
        require(json.loads(marker.read_text('utf-8'))==entry['manifest'],'资源清单内容不一致')
        boundary=(payload.get('currentPatchTag') or payload['currentReleaseTag']) if entry.get('kind')=='frontend-patch' else (
            payload.get('currentBackendPatchTag') or payload['currentReleaseTag']) if entry.get('kind')=='backend-patch' else payload['currentReleaseTag']
        protected=tag in held or tag>=boundary
        for image in entry['manifest'].get('images',{}).values():
            require(re.fullmatch(r'[A-Za-z0-9._:/-]+',image['name']) and
                    re.fullmatch(r'sha256:[a-f0-9]{64}',image['id']),'镜像登记身份无效')
            image_rows.append(dict(reference=image['name'],imageId=image['id'],releaseTag=tag))
            if protected:protected_images.add(image['id'])
        originals=read(root,'recovery-containers.private.json') or {}
        if protected:
            for value in originals.values():
                protected_ids.add(value['Id']);protected_images.add(value['Image'])
        if entry.get('kind')=='frontend-patch':
            origin=read(root,'frontend-origin.private.json')
            snapshot(origin,[profile['frontend']+'-before-'+entry['deploymentJobId']],tag,protected)
        elif entry.get('kind')=='backend-patch':
            original=read(root,'backend-origin.private.json')
            snapshot(original,[profile['backend']+'-before-'+entry['deploymentJobId']],tag,protected)
            if entry.get('acceptedDeployment'):
                snapshot(read(root,'backend-probe.private.json'),[profile['backend']+'-probe-'+entry['deploymentJobId']],tag,False)
        else:
            for role in ('backend','frontend'):
                name=profile[role]
                snapshot(read(root,role+'-before-initial.private.json'),[name+'-before-'+tag],tag,protected)
            # A fully accepted release no longer needs the intermediate
            # maintenance-mode backend. Its original stable checkpoint is held.
            if entry.get('acceptedDeployment'):
                snapshot(read(root,'backend-before-reopen.private.json'),
                         [profile['backend']+'-before-'+tag+'-maintenance'],tag,tag>boundary)
        for binding in entry.get('resolvedRecoveries',[]):
            if protected:
                retain('recovery',binding['recoveryJobId'],'当前或恢复/演练引用');continue
            folder=files.safe_file(root,'recovery-'+binding['recoveryJobId'])
            receipt=read(folder,'receipt.private.json')
            require(receipt and receipt.get('jobId')==binding['recoveryJobId']
                    and receipt.get('originalJobId')==binding['originalJobId'] in entry['ownerJobIds']
                    and receipt.get('releaseTag')==tag and receipt.get('packageSha256')==entry['packageSha256']
                    and receipt.get('status')=='succeeded' and receipt.get('phase')=='opened'
                    and receipt.get('openingStatus')=='succeeded'
                    and receipt.get('openingJobId')==binding['openingJobId'],
                    '恢复验收/原任务核销依据不一致')
            for journal in ('backend-replacement.private.json','backend-opening-replacement.private.json','frontend-replacement.private.json'):
                replacement=read(folder,journal)
                if not replacement:continue
                identity=replacement['retainedId'];value=by_id.get(identity)
                if value:
                    role='frontend' if journal.startswith('frontend') else 'backend'
                    suffix=binding['openingJobId'] if '-opening-' in journal else binding['recoveryJobId']
                    require(value['Image']==replacement['retainedImage'],'失败容器镜像身份变化')
                    snapshot(value,[profile[role]+'-failed-'+suffix],tag)
            failed=receipt.get('failedDatabase')
            if failed:
                path=Path(failed['path'])
                require(path.parent.parent==folder and re.fullmatch(r'failed-database-\d+',path.parent.name)
                        and path.name in ('recovery.sql','recovery.sql.gz'),'失败数据库路径越界')
                if path.exists():result['files'].append(dict(releaseTag=tag,**file_row(base,path,failed['sha256'])))
            record=read(root,'recovery-record.private.json') or {}
            resources=record.get('resources',[])
            for retained_path in receipt.get('retainedData',[]):
                retained=Path(retained_path)
                matched=[r for r in resources if retained==Path(r['mount']['Source']).with_name(
                    Path(r['mount']['Source']).name+'.failed-'+binding['recoveryJobId'])]
                require(len(matched)==1,'失败数据目录不属于登记恢复资源')
                source=Path(matched[0]['mount']['Source'])
                resource=matched[0]
                service=next((c for c in actual if c['Name'].lstrip('/')==profile.get(resource['role'])),None)
                require(resource['role'] in ('redis','minio') and service and any(
                    m.get('Source')==str(source) and m.get('Destination')==resource['mount']['Destination']
                    for m in service.get('Mounts',[])), '失败目录不对应当前登记数据服务挂载')
                journal=read(source.parent,source.name+'.restore-'+binding['recoveryJobId']+'.json')
                if not (journal and journal.get('phase')=='complete' and journal.get('attemptId')==binding['recoveryJobId']
                        and journal.get('source')==str(source.resolve())
                        and journal.get('archiveSha256')==matched[0]['artifact']['sha256']):
                    blocked.add(tag)
                    retain('recovery',binding['recoveryJobId'],'恢复日志/归档绑定不一致，保留整组版本及恢复依赖')
                    for value in originals.values():
                        protected_ids.add(value['Id']);protected_images.add(value['Image'])
                    continue
                if retained.exists():
                    rows,dirs=tree_rows(retained,mounts)
                    for row in rows+dirs:row['releaseTag']=tag
                    result['files']+=rows;result['directories']+=dirs

    result['blockedReleaseTags']=sorted(blocked)
    result['files']=[r for r in result['files'] if r['releaseTag'] not in blocked]
    result['directories']=[r for r in result['directories'] if r['releaseTag'] not in blocked]
    for candidate in candidates:
        if candidate['releaseTag'] in blocked:
            protected_ids.add(candidate['id']);protected_images.add(candidate['imageId'])
    protected_images.update(row['imageId'] for row in image_rows if row['releaseTag'] in blocked)

    for candidate in candidates:
        identity=candidate['id'];value=by_id.get(identity)
        if identity in seen:continue
        seen.add(identity)
        if not value:continue
        reason=None
        if identity in protected_ids:reason='当前版本或最近有效恢复点引用'
        elif not stopped(value):reason='容器仍运行或重启中'
        elif value['Name'].lstrip('/') not in candidate['names']:reason='容器名称与归属证据不同'
        elif value['Image']!=candidate['imageId'] or fingerprint(value)!=candidate['fingerprint']:reason='容器配置或镜像已改变'
        if reason:retain('container',identity,reason)
        else:
            result['containers'].append(dict(id=identity,name=value['Name'].lstrip('/'),imageId=value['Image'],
                fingerprint=candidate['fingerprint'],releaseTag=candidate['releaseTag'],bytes=None))
    selected={c['id'] for c in result['containers']}
    for value in actual:
        if value['Id'] not in selected and not any(r['identity']==value['Id'] for r in result['retained']):
            retain('container',value['Id'],'当前/其他任务容器或缺少已登记退役证据')
    used={c['Image'] for c in actual if c['Id'] not in selected}
    for image in image_rows:
        if image['reference'] in {r['reference'] for r in result['images']}:continue
        if image['imageId'] in protected_images or image['imageId'] in used:
            retain('image',image['reference'],'当前/恢复点或其他容器引用')
        else:result['images'].append(image)
    result['protectedImages']=sorted(protected_images);result['protectedContainers']=sorted(protected_ids)
    return result


def remove_container(row):
    current=next((c for c in containers() if c['Id']==row['id']),None)
    require(current and stopped(current) and current['Name'].lstrip('/')==row['name']
            and current['Image']==row['imageId'] and fingerprint(current)==row['fingerprint'],
            '旧容器身份/配置/运行状态改变，未删除')
    files.docker(['rm','--',row['id']])
    require(row['id'] not in files.docker(['ps','-aq','--no-trunc']).decode().split(),'容器删除未完成')


def remove_directory(row):
    root=Path(row['root']);path=root if row['relative']=='.' else files.safe_file(root,row['relative'])
    files.safe_file(root,'.cleanup-check')
    require(path.is_dir() and path.stat().st_ino==row['inode'] and files.same_device(root,path),'失败目录身份改变')
    require(not files.mounted(path,files.docker_inventory()[2]),'失败目录已被挂载')
    path.rmdir()  # Empty only. Unexpected files stop deletion.


def remove_image(row,protected):
    images,used,_=files.docker_inventory()
    if row['reference'] not in images:return False
    require(images[row['reference']]==row['imageId'] and row['imageId'] not in used
            and row['imageId'] not in protected,'镜像身份改变或存在容器/恢复引用')
    files.docker(['image','rm','--',row['reference']])
    return True
