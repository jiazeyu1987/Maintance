"""Immutable frontend-only build pinned to an installed full release."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import tarfile

from executor import digest, require, stamp
from intruoyi_build import archive_image_identities, install_frontend, publish_nas


def validate_source(executor, base, commit):
    require(re.fullmatch('[0-9a-f]{40}', commit or ''), '请选择完整源码提交')
    require(executor.run(['git','-C',executor.c['repo'],'rev-parse',commit+'^{commit}']).decode().strip()==commit,
            '源码提交不存在')
    changes=executor.run(['git','-C',executor.c['repo'],'diff','--name-only',base['gitCommit'],commit]).decode().splitlines()
    require(changes and all(p.startswith('IntRuoyiFronted/') for p in changes),
            '前端补丁只能包含 IntRuoyiFronted 变更；后端及数据库变更请使用完整发布')
    return changes


def build(executor, job):
    base,base_manifest=executor.manifest(job['payload']['baseReleaseTag'])
    commit=job['payload'].get('commit')
    changes=validate_source(executor,base,commit)
    tag=stamp()
    folder=executor.root/'frontend-patches'/tag
    folder.mkdir(parents=True,exist_ok=False)
    worktree=Path(executor.c['buildWorktreeRoot'])/('frontend-'+tag)
    job.update(releaseTag=tag,buildDirectory=str(folder),buildWorktree=str(worktree))
    executor.step(job,'freeze-frontend-source')
    executor.run(['git','-C',executor.c['repo'],'worktree','add','--detach','--no-checkout',str(worktree),commit])
    executor.run(['git','-C',str(worktree),'sparse-checkout','set','IntRuoyiFronted'])
    executor.run(['git','-c','core.autocrlf=false','-C',str(worktree),'checkout',commit],timeout=900)
    require(not executor.run(['git','-C',str(worktree),'status','--porcelain']).strip(),'补丁构建源码不干净')
    frontend=worktree/'IntRuoyiFronted'
    pnpm=shutil.which('pnpm.cmd' if os.name=='nt' else 'pnpm')
    require(pnpm,'未找到 pnpm')
    executor.step(job,'install-frontend-dependencies')
    install_frontend(executor,job,pnpm,frontend)
    executor.step(job,'compile-frontend-only')
    env=dict(os.environ,NODE_OPTIONS='--max-old-space-size=8192',VITE_BASE_URL='',VITE_BASE_PATH='/',VITE_OUT_DIR='dist-intruoyi-test')
    executor.run(['node','node_modules/vite/bin/vite.js','build','--mode','prod'],cwd=frontend,env=env,timeout=2700)
    metadata=dict(releaseTag=tag,baseReleaseTag=base['releaseTag'],frontendPatchTag=tag,
                  sourceCommit=commit,builtAt=dt.datetime.now(dt.timezone.utc).isoformat())
    dist=frontend/'dist-intruoyi-test'
    (dist/'release-info.json').write_text(json.dumps(metadata,ensure_ascii=False),'utf-8')
    require(not executor.run(['git','-C',str(worktree),'status','--porcelain']).strip(),'编译修改了固定源码')
    context=folder/'build-context'
    shutil.copytree(dist,context/'frontend')
    runtime=executor.c['localRuntimeImages']['frontend']
    base_id=executor.run(['docker','image','inspect','--format','{{.Id}}',runtime]).decode().strip()
    require(re.fullmatch('sha256:[a-f0-9]{64}',base_id),'前端运行镜像身份无效')
    pinned='intruoyi-frontend-base:'+base_id.split(':')[1]
    executor.run(['docker','tag',base_id,pinned])
    dockerfile=context/'Dockerfile'
    dockerfile.write_text('FROM '+pinned+'\nRUN rm -rf /usr/share/nginx/html/*\nCOPY frontend/ /usr/share/nginx/html/\n','utf-8')
    name='intruoyi-frontend-patch:'+tag
    executor.step(job,'build-frontend-image')
    executor.run(['docker','build','--pull=false','-t',name,str(context)],timeout=1200)
    image=dict(name=name,id=executor.run(['docker','image','inspect','--format','{{.Id}}',name]).decode().strip())
    container=executor.run(['docker','create','--network','none',name]).decode().strip()
    try:
        executor.run(['docker','cp',container+':/usr/share/nginx/html/release-info.json',str(folder/'release-info.json')])
        require(json.loads((folder/'release-info.json').read_text('utf-8'))==metadata,'前端镜像内版本信息不一致')
    finally:
        executor.run(['docker','rm',container])
    executor.step(job,'seal-frontend-package')
    executor.run(['docker','save','-o',str(folder/'images.tar'),name],timeout=1200)
    archive_image_identities(folder/'images.tar',{'frontend':image})
    files=[dict(name=n,sha256=digest(folder/n)) for n in ('images.tar','release-info.json')]
    manifest=dict(applicationId='intruoyi',kind='frontend-patch',releaseTag=tag,baseReleaseTag=base['releaseTag'],
                  baseGitCommit=base['gitCommit'],gitCommit=commit,backendImageId=base_manifest['images']['backend']['id'],
                  images={'frontend':image},metadata=metadata,changedFiles=changes,files=files)
    (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')
    with tarfile.open(folder/'release.tar','w') as archive:
        for n in ['manifest.json']+[f['name'] for f in files]:archive.add(folder/n,arcname=n)
    package=dict(releaseTag=tag,baseReleaseTag=base['releaseTag'],gitCommit=commit,directory=str(folder),
                 manifestSha256=digest(folder/'manifest.json'),packageSha256=digest(folder/'release.tar'),
                 imageId=image['id'],stage='built',deployments={},accepted={})
    require(executor.c.get('nasPath'),'未配置 NAS 包存储')
    executor.step(job,'publish-patch-to-nas')
    package['nasDirectory']=publish_nas(folder,manifest,str(Path(executor.c['nasPath'])/'frontend-patches'),executor.c.get('nasCredentialsFile'))
    executor.state.setdefault('frontendPatches',[]).insert(0,package)
    executor.save()
    executor.log(job,'前端补丁封包完成；未编译后端，未执行 SQL，未部署任何服务器。')
