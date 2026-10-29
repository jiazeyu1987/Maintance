"""Explicit local-source snapshot input for the standalone Node assistant."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

from executor import digest, require, stamp

ROOT_FILES = ('server.js', 'package.json', 'package-lock.json')
SOURCE_DIRS = ('backend/src', 'frontend/src')
EXTENSIONS = {'.js', '.mjs', '.json', '.html', '.css', '.svg', '.png', '.jpg', '.jpeg', '.woff', '.woff2', '.ico'}


def source_files(root):
    root = Path(root).resolve(strict=True)
    files = [root / name for name in ROOT_FILES]
    for name in SOURCE_DIRS:
        directory = root / name
        require(directory.is_dir() and not directory.is_symlink(), '缺少源码目录或目录为链接：' + name)
        files.extend(p for p in directory.rglob('*') if p.is_file())
    result = {}
    for path in sorted(files):
        relative = path.relative_to(root).as_posix()
        require(path.is_file() and not path.is_symlink() and root in path.resolve().parents,
                '源码不是独立的普通文件：' + relative)
        require(not any(p.is_symlink() for p in path.parents if p != root), '源码目录不能包含链接')
        require(path.suffix.lower() in EXTENSIONS and not path.name.startswith('.'),
                '未声明的源码文件类型：' + relative)
        result[relative] = digest(path)
    require('frontend/src/index.html' in result, '缺少前端 index.html')
    package = json.loads((root / 'package.json').read_text('utf-8'))
    require(package.get('name') == 'fenbeitong-kingdee-expense-reimbursement', '不是已登记的分贝通项目')
    require(not package.get('dependencies'), '发现新的运行依赖，需要先完善构建契约')
    return result


def source_identity(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def exported_image_id(path, tag):
    """Use Docker config identity, not Desktop's OCI index identity."""
    with tarfile.open(path, 'r:') as archive:
        entries = json.load(archive.extractfile('manifest.json'))
        require(len(entries) == 1 and entries[0]['RepoTags'] == [tag], '镜像导出不是唯一目标镜像')
        config = archive.extractfile(entries[0]['Config']).read()
        return 'sha256:' + hashlib.sha256(config).hexdigest()


def build(executor, job):
    root = Path(executor.c['repo'])
    files = source_files(root)
    identity = source_identity(files)
    require(job['payload'].get('sourceSha256') == identity, '源码已变化，请刷新源码快照后重新构建')
    tag = stamp()
    folder = executor.root / 'packages' / tag
    folder.mkdir(parents=True, exist_ok=False)
    context = folder / 'source'
    context.mkdir()
    executor.step(job, 'freeze-source')
    for relative, sha in files.items():
        destination = context / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, destination)
        require(digest(destination) == sha, '源码在冻结过程中改变：' + relative)
    require(source_files(root) == files, '源码在冻结过程中发生增删改，请重新构建')
    metadata = dict(applicationId='fenbeitong', releaseTag=tag, sourceKind='local-snapshot', sourceSha256=identity)
    (context / 'release-info.json').write_text(json.dumps(metadata), 'utf-8')
    image_base = executor.c['nodeImage']
    base = json.loads(executor.run(['docker', 'image', 'inspect', image_base]))[0]
    require(base['Os'] == 'linux' and base['Architecture'] == 'amd64', '需要已准备的 Linux amd64 Node 镜像')
    # BuildKit interprets a bare sha256 ID as a registry name. Use the explicitly
    # prepared local reference, disable pulling and verify it has not changed.
    dockerfile = ('FROM ' + image_base + '\nWORKDIR /app\nCOPY . /app/\n'
                  'RUN node --check server.js && node -e "require(\'node:sqlite\')"\n'
                  'ENV NODE_ENV=production\nEXPOSE 18734\nCMD ["node", "server.js"]\n')
    (context / 'Dockerfile').write_text(dockerfile, 'utf-8')
    image_tag = 'fenbeitong-assistant:' + tag
    executor.step(job, 'build-image')
    executor.run(['docker', 'build', '--pull=false', '-t', image_tag, str(context)], timeout=900)
    require(json.loads(executor.run(['docker', 'image', 'inspect', image_base]))[0]['Id'] == base['Id'],
            '构建期间 Node 基础镜像身份发生变化')
    image_id = json.loads(executor.run(['docker', 'image', 'inspect', image_tag]))[0]['Id']
    readback = json.loads(executor.run(['docker', 'run', '--rm', '--network', 'none', image_id,
                                      'node', '-e', 'console.log(JSON.stringify(require("./release-info.json")))']))
    require(readback == metadata, '镜像中的版本身份与源码快照不一致')
    executor.step(job, 'verify-isolated-startup')
    smoke_name = 'fenbeitong-build-' + job['id'].lower()
    executor.run(['docker', 'run', '-d', '--name', smoke_name, '--network', 'none',
                  '-e', 'APP_DATA_DIR=/data', '-e', 'FENBEITONG_MODE=real', '-e', 'KINGDEE_MODE=real',
                  '-e', 'SCHEDULER_ENABLED=false', '-e', 'PAYMENT_STATUS_SYNC_ENABLED=false',
                  '-e', 'FENBEITONG_ASSISTANT_TICKET_VALIDATE_URL=http://127.0.0.1:48081/admin-api/system/auth/fenbeitong-assistant-ticket/validate', image_id])
    try:
        check = ('let n=0;const t=setInterval(async()=>{try{const r=await fetch("http://127.0.0.1:18734/api/health");'
                 'const b=await r.json();if(r.ok&&b.success===true&&b.status==="ok"){clearInterval(t);process.exit(0)}}'
                 'catch(e){}if(++n>=25){clearInterval(t);process.exit(1)}},200);')
        executor.run(['docker', 'exec', smoke_name, 'node', '-e', check], timeout=15)
    finally:
        executor.run(['docker', 'rm', '-f', smoke_name], timeout=30)
    executor.step(job, 'export-package')
    executor.run(['docker', 'save', '-o', str(folder / 'image.tar'), image_tag], timeout=900)
    runtime_image_id = exported_image_id(folder / 'image.tar', image_tag)
    manifest = dict(metadata, image=image_tag, imageId=runtime_image_id, buildImageId=image_id, nodeBaseImageId=base['Id'],
                    sourceFiles=files, files=[dict(name='image.tar', sha256=digest(folder / 'image.tar'))])
    (folder / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), 'utf-8')
    with tarfile.open(folder / 'release.tar', 'w') as archive:
        for name in ('manifest.json', 'image.tar'):
            archive.add(folder / name, arcname=name)
    package = dict(metadata, directory=str(folder), manifestSha256=digest(folder / 'manifest.json'),
                   packageSha256=digest(folder / 'release.tar'), imageId=runtime_image_id, stage='built',
                   createdAt=stamp(), outcomes={}, buildJobId=job['id'])
    executor.state['packages'].insert(0, package)
    job['releaseTag'] = tag
    executor.save()
    executor.log(job, '完整程序镜像已封包；未包含本机配置、凭据或业务数据。')
