"""Exact manifest-owned files only. No recursive directory or volume deletion."""
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess


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
