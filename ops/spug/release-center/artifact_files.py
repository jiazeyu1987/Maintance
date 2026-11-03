"""Exact manifest-owned files only. No recursive directory or volume deletion."""
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
import shutil


def require(ok, text):
    if not ok:
        raise ValueError(text)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_file(root, relative):
    root = Path(root)
    part = Path(relative)
    require(root.is_absolute() and not part.is_absolute() and part.parts and '..' not in part.parts,
            '产物路径不在登记目录内')
    target = root/part
    # Reject symlinks, junctions and reparse points throughout the path.
    for node in [target, *target.parents]:
        if node.exists() or node.is_symlink():
            info = node.lstat()
            require(not node.is_symlink() and not (getattr(info, 'st_file_attributes', 0) & 1024), '产物路径含链接或重解析点')
    require(root.resolve() in target.resolve().parents, '产物路径越界')
    return target


def file_identity(path):
    info = path.stat()
    require(stat.S_ISREG(info.st_mode), '登记产物不是普通文件')
    return dict(bytes=info.st_size, mtimeNs=info.st_mtime_ns, inode=info.st_ino)


def inventory(root, manifest, manifest_sha, archive_sha, *, archive_only=False, recovery=False, recovery_jobs=()):
    root = Path(root)
    if not root.exists():
        return []
    marker = safe_file(root, 'manifest.json')
    if not marker.is_file():
        return [dict(relative='.',kind='无法确认归属的目录',bytes=None,unmeasured=True,
                     retainedReason='目录缺少包清单，未统计内容并保留该版本产物')]
    if sha(marker) != manifest_sha:
        return [dict(relative='manifest.json',kind='身份不一致的清单（保留）',
                     retainedReason='目录清单与登记包身份不一致，保留该版本产物',unmeasured=True,**file_identity(marker))]
    expected = [('release.tar', archive_sha, '发布包')]
    if not archive_only:
        expected += [(r['name'], r['sha256'], '镜像导出') for r in manifest['files'] if r['name']=='images.tar']
        if manifest.get('kind')=='backend-patch':
            expected += [(r['name'],r['sha256'],'旧后端JAR') for r in manifest['files'] if r['name']=='app.jar']
    retained_reason = None
    retained = []
    if recovery:
        record = safe_file(root, 'recovery-record.private.json')
        if record.exists():
            value = json.loads(record.read_text('utf-8'))
            if not {'releaseTag','manifestSha256','packageSha256','resources','jobId'}<=set(value) or value['jobId'] not in recovery_jobs:
                # Read-only classification, never infer legacy ownership or permit deletion.
                retained_reason='恢复点缺少版本/任务归属信息，保留该版本产物'
                for name in ('recovery.sql', 'recovery.sql.gz'):
                    path=safe_file(root,name)
                    if path.exists():retained.append(dict(relative=name,kind='归属不完整的旧恢复点',retainedReason=retained_reason,**file_identity(path)))
            else:
                require(value['releaseTag'] == manifest['releaseTag'] and value['manifestSha256'] == manifest_sha
                        and value['packageSha256'] == archive_sha, '恢复点与登记包身份不一致')
                path = Path(value['path'])
                require(path.parent == root and path.name in ('recovery.sql', 'recovery.sql.gz'), '恢复SQL路径不一致')
                expected.append((path.name, value['sha256'], '数据库恢复点'))
                for i, resource in enumerate(value['resources']):
                    artifact = resource['artifact']
                    name = 'recovery-volume-'+str(i)+'.tar'
                    require(Path(artifact['path']) == root/name, '恢复卷路径不一致')
                    expected.append((name, artifact['sha256'], '数据卷恢复点'))
    rows = []
    seen = set()
    for relative, digest, kind in expected:
        require(relative != 'manifest.json' and relative not in seen, '包内文件与保留清单冲突')
        seen.add(relative)
        require(re.fullmatch('[a-f0-9]{64}', digest), '登记文件摘要无效')
        path = safe_file(root, relative)
        if path.exists():
            row=dict(relative=relative, sha256=digest, kind=kind, **file_identity(path))
            if retained_reason:row['retainedReason']=retained_reason
            rows.append(row)
    return rows+retained


def remove_file(root, row):
    require(not row.get('retainedReason'), '归属不完整的产物禁止删除')
    path = safe_file(root, row['relative'])
    require(path.exists() and file_identity(path) == {k:row[k] for k in ('bytes','mtimeNs','inode')}, '文件自预览后发生变化，请重新扫描')
    require(sha(path) == row['sha256'], '产物摘要与原包/恢复记录不同，未删除')
    path.unlink()
    require(not path.exists(), '文件删除未完成')


def docker(args):
    p = subprocess.run(['docker', *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    require(p.returncode == 0, 'Docker 产物检查或清理失败（退出码 '+str(p.returncode)+'）')
    return p.stdout


def docker_inventory():
    images = {}
    for line in docker(['image','ls','--no-trunc','--format','{{json .}}']).decode().splitlines():
        row = json.loads(line)
        if row['Repository'] != '<none>' and row['Tag'] != '<none>':
            images[row['Repository']+':'+row['Tag']] = row['ID']
    ids = docker(['ps','-aq']).decode().split()
    containers = json.loads(docker(['inspect', *ids])) if ids else []
    used = {row['Image'] for row in containers}
    mounts=[m['Source'] for row in containers for m in row.get('Mounts',[]) if m.get('Source')]
    return images, used, mounts


def mounted(path, mounts):
    return any(Path(source)==path or Path(source) in path.parents for source in mounts)


def remove_image(reference, identity):
    images, used, _ = docker_inventory()
    require(images.get(reference) == identity and identity not in used, '镜像身份改变或正被容器引用，未删除')
    # Only the manifest-owned tag. Never --force, image IDs, system prune or volumes.
    docker(['image','rm','--',reference])


def remote(profile, payload):
    if payload['action'] == 'artifact-auto-clean':
        return automatic_cleanup(profile, payload)
    base = Path(profile['stagingRoot'])
    require(base.is_absolute() and base.is_dir(), '登记发布暂存目录不存在')
    entries = payload['entries']
    rows = []
    for entry in entries:
        tag = entry['manifest']['releaseTag']
        require(re.fullmatch(r'\d{4}(-\d{2}){5}', tag), '版本号无效')
        attempt = entry.get('attempt')
        if attempt:
            require(re.fullmatch('JOB-[a-f0-9]{10}', attempt), '备用补发目录无效')
        root = base/'attempts'/attempt/tag if attempt else base/tag
        files = inventory(root, entry['manifest'], entry['manifestSha256'], entry['packageSha256'], recovery=True,recovery_jobs=entry.get('ownerJobIds',[]))
        rows.append(dict(releaseTag=tag, root=str(root), files=files))
    images, used, mounts = docker_inventory()
    if payload['action'] == 'artifact-inventory':
        return dict(directories=rows, images=images, usedImages=sorted(used),usedMounts=mounts)
    actual=docker(['inspect','--format','{{.Image}}',profile['backend'],profile['frontend']]).decode().splitlines()
    require(actual==[payload['expectedImages'][role] for role in ('backend','frontend')], '目标实际版本在清理前发生变化，已停止')
    item = payload['item']
    if item['kind'] == 'image':
        # The controller selects an exact manifest image reference; enforce again here.
        allowed = {(v['name'],v['id']) for e in entries for v in e['manifest']['images'].values()}
        require((item['reference'],item['imageId']) in allowed, '镜像不属于登记清单')
        remove_image(item['reference'], item['imageId'])
    else:
        matches = [r for r in rows if r['root']==item['root'] and r['releaseTag']==item['releaseTag']]
        require(len(matches)==1 and item['file'] in matches[0]['files'], '文件不在本次真实扫描清单内')
        require(not mounted(Path(matches[0]['root'])/item['file']['relative'],mounts),'容器已挂载该产物，未删除')
        remove_file(matches[0]['root'],item['file'])
    return {'removed':True}


def same_device(base, path):
    return base.stat().st_dev == path.stat().st_dev


def assert_cleanup_idle(base, payload):
    from operation_journal import process_identity
    receipts = safe_file(base, '.operations')
    if not receipts.exists():
        return
    for path in receipts.glob('OP-*.json'):
        path = safe_file(base, str(path.relative_to(base)))
        receipt = json.loads(path.read_text('utf-8'))
        if receipt.get('operationId') == payload.get('operationId'):
            continue
        require(not (receipt.get('status') == 'running' and receipt.get('processStart') and
                process_identity(receipt['pid']) == receipt['processStart']),
                '远端仍有活动执行器，停止自动清理')


def verify_cleanup_runtime(profile, payload):
    actual = json.loads(docker(['inspect', profile['backend'], profile['frontend']]))
    require([r['Image'] for r in actual] == [payload['expectedImages'][r] for r in ('backend','frontend')]
            and all(r['State']['Running'] for r in actual), '当前容器已改变或未运行，停止自动清理')
    metadata = json.loads(docker(['exec', profile['frontend'], 'cat', '/usr/share/nginx/html/release-info.json']))
    require(metadata.get('baseReleaseTag', metadata.get('releaseTag')) == payload['currentReleaseTag']
            and metadata.get('frontendPatchTag') == payload.get('currentPatchTag'),
            '当前页面版本已改变，停止自动清理')
    backend=actual[0]
    labels=backend['Config'].get('Labels') or {}
    require(labels.get('intruoyi.backend-patch.tag')==payload.get('currentBackendPatchTag'),
            '当前后端补丁已改变，停止清理')
    if payload.get('currentBackendPatchTag'):
        jar=docker(['exec',profile['backend'],'sha256sum','/yudao-server/app.jar']).decode().split()[0]
        require(jar==labels.get('intruoyi.backend-patch.sha256')==payload.get('currentBackendJarSha256'),
                '当前后端 JAR 身份已改变，停止清理')


def cleanup_root(base, entry):
    tag = entry['manifest']['releaseTag']
    require(re.fullmatch(r'\d{4}(-\d{2}){5}', tag), '旧包版本号无效')
    if entry.get('kind') in ('frontend-patch','backend-patch'):
        owner = entry.get('deploymentJobId', '')
        require(re.fullmatch('JOB-[a-f0-9]{10}', owner), '旧补丁任务号无效')
        relative = entry['kind']+'es/'+tag+'/'+owner
    elif entry.get('attempt'):
        owner = entry['attempt']
        require(re.fullmatch('JOB-[a-f0-9]{10}', owner), '旧重试任务号无效')
        relative = 'attempts/'+owner+'/'+tag
    else:
        relative = tag
    return safe_file(base, relative)


def automatic_cleanup(profile, payload):
    """No discovery/recursive removal. Only exact, SHA-bound retired payloads.

    The common operation journal lock serializes this with other remote work.
    Current/recovery resources are protected. Retired exact Docker identities
    and resolved failed material are planned before any deletion.
    """
    base = Path(profile['stagingRoot'])
    require(not (base == Path('/mnt/nas') or Path('/mnt/nas') in base.parents), '禁止自动清理NAS')
    require(base.is_absolute() and base.is_dir() and base != Path('/') and len(base.parts) >= 3, '发布暂存根无效')
    safe_file(base, '.cleanup')  # Check all base ancestors before any access.
    owner = payload.get('workflowJobId', '')
    require(re.fullmatch('JOB-[a-f0-9]{10}', owner), '清理任务号无效')
    roots = [(entry, cleanup_root(base, entry)) for entry in payload['entries']]
    verify_cleanup_runtime(profile, payload)
    assert_cleanup_idle(base, payload)
    report = dict(status='running', removed=[], retained=[], bytes=0)
    report['freeBytesBefore']=shutil.disk_usage(base).free
    report_path = safe_file(base, '.cleanup/'+owner+'.json')
    report_path.parent.mkdir(mode=0o700, exist_ok=True)
    # Preserve a previous attempt's per-file evidence when resuming this job.
    if report_path.exists():
        previous = json.loads(report_path.read_text('utf-8'))
        report['previousAttempt'] = previous
    def save_report():
        from operation_journal import write
        write(report_path, report)
    save_report()
    try:
        if 'resourceEntries' in payload:
            import runtime_resource_cleanup as resources
            plan=resources.plan(profile,payload)
            report['plan']=plan
            report['retained'].extend(plan['retained'])
            report['imageSpaceNote']='镜像层可共享；不将镜像逻辑大小计为实际释放空间'
            save_report()  # The concrete sanitized resource plan precedes effects.
            def pending(kind,row):
                verify_cleanup_runtime(profile,payload)
                assert_cleanup_idle(base,payload)
                report['pendingDeletion']=dict(kind=kind,resource=row)
                save_report()
            def removed(kind,row):
                report['removed'].append(dict(kind=kind,**row))
                report.pop('pendingDeletion',None)
                save_report()
            for row in plan['containers']:
                pending('container',row)
                resources.remove_container(row)
                removed('container',row)
            for row in plan['images']:
                pending('image',row)
                if resources.remove_image(row,plan['protectedImages']):removed('image',row)
                else:report.pop('pendingDeletion',None);save_report()
            for row in plan['files']:
                pending('file',row)
                path=Path(row['root'])/row['relative']
                require(not mounted(path,docker_inventory()[2]),'已核销失败资料出现挂载引用')
                require(same_device(Path(row['root']),path) and path.stat().st_nlink==1,'失败资料设备/链接身份改变')
                remove_file(row['root'],row)
                report['bytes']+=row['bytes']
                removed('file',row)
            for row in plan['directories']:
                pending('directory',row)
                resources.remove_directory(row)
                removed('directory',row)
        held = (set(payload['protectedTags']) | {payload['currentReleaseTag'], payload.get('currentPatchTag')}
                | set(report.get('plan',{}).get('blockedReleaseTags',[])))
        for entry, root in roots:
            tag = entry['manifest']['releaseTag']
            if tag in held or (entry.get('kind') not in ('frontend-patch','backend-patch') and tag >= payload['currentReleaseTag']):
                report['retained'].append(dict(releaseTag=tag, reason='当前版本、恢复点、演练或未结束任务引用'))
                continue
            # A patch cannot be retired merely because its wall-clock tag is
            # older than a full build; only explicitly retired controller entries.
            rows = inventory(root, entry['manifest'], entry['manifestSha256'], entry['packageSha256'],
                             recovery=entry.get('kind') not in ('frontend-patch','backend-patch'), recovery_jobs=entry.get('ownerJobIds', []))
            if (entry.get('kind') not in ('frontend-patch','backend-patch') and root.exists()
                    and not safe_file(root, 'recovery-record.private.json').exists()
                    and any(root.glob('recovery*'))):
                report['retained'].append(dict(releaseTag=tag, reason='恢复资料缺少归属记录，保留整组载荷'))
                continue
            for row in rows:
                if row.get('retainedReason') or row.get('unmeasured'):
                    report['retained'].append(dict(releaseTag=tag, file=row['relative'],
                        reason=row.get('retainedReason', '资料归属无法确认')))
                    continue
                path = safe_file(root, row['relative'])
                _, _, mounts = docker_inventory()
                if mounted(path, mounts):
                    report['retained'].append(dict(releaseTag=tag, file=row['relative'], reason='容器挂载引用'))
                    continue
                verify_cleanup_runtime(profile, payload)
                assert_cleanup_idle(base, payload)
                require(same_device(base, path), '产物跨文件系统，停止自动清理')
                require(path.stat().st_nlink == 1, '产物存在硬链接，停止自动清理')
                report['pendingDeletion'] = dict(releaseTag=tag, relative=str(path.relative_to(base)), sha256=row['sha256'])
                save_report()
                remove_file(root, row)
                report['removed'].append(dict(kind='file',releaseTag=tag, relative=str(path.relative_to(base)), bytes=row['bytes']))
                report['bytes'] += row['bytes']
                report.pop('pendingDeletion')
                save_report()
        report['status'] = 'succeeded'
    except Exception as error:
        report.update(status='failed', error=str(error))
    report['freeBytesAfter']=shutil.disk_usage(base).free
    report['freeBytesDelta']=report['freeBytesAfter']-report['freeBytesBefore']
    save_report()
    return report
