"""Build once from committed Java-only compatible changes; seal a single JAR."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

from executor import digest,require,stamp
from backend_patch_contract import validate_changes,validate_manifest,RUNTIME_POLICY
from build_artifact_guard import validate_source_contract,verify_backend_jar,validate_required_gxp_mode,validate_offline_cli_report,MES_PREFIX
from intruoyi_build import publish_nas,cleanup_sealed_build,archive_image_identities
from intruoyi_login import verify_login


def validate_source(executor,base,commit):
    require(re.fullmatch('[a-f0-9]{40}',commit or ''),'请选择完整源码提交')
    git=['git','-C',executor.c['repo']]
    require(executor.run(git+['rev-parse',commit+'^{commit}']).decode().strip()==commit,'源码提交不存在')
    executor.run(git+['merge-base','--is-ancestor',base['gitCommit'],commit])
    paths=executor.run(git+['diff','--name-only',base['gitCommit'],commit]).decode('utf-8').splitlines()
    validate_changes(paths)
    diff=executor.run(git+['diff','--unified=0',base['gitCommit'],commit,'--',*paths]).decode('utf-8')
    additions='\n'.join(line[1:] for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++'))
    require(not re.search(r'@(?:PostConstruct|EventListener|Scheduled)|ApplicationRunner|CommandLineRunner|InitializingBean|Flyway|Liquibase|CREATE\s+TABLE|ALTER\s+TABLE',additions,re.I),
            '补丁含启动/调度/迁移合同变更，请使用完整发布')
    validate_source_contract(executor,commit)
    return paths


def publish_original(executor,job,package):
    root=Path(package['directory'])
    require(digest(root/'manifest.json')==package['manifestSha256'] and digest(root/'release.tar')==package['packageSha256'],
            '原补丁包校验失败，禁止修改摘要后重传')
    manifest=validate_manifest(json.loads((root/'manifest.json').read_text('utf-8')))
    for item in manifest['files']:
        require(digest(root/item['name'])==item['sha256'],'原补丁成员校验失败')
    cleanup_sealed_build(executor,job)
    require(executor.c.get('nasPath'),'未配置 NAS 包存储')
    package['nasDirectory']=publish_nas(root,manifest,str(Path(executor.c['nasPath'])/'backend-patches'),executor.c.get('nasCredentialsFile'))
    if not any(p['releaseTag']==package['releaseTag'] for p in executor.state.get('backendPatches',[])):
        executor.state.setdefault('backendPatches',[]).insert(0,package)
    executor.save()


def pinned_runtime(executor,base):
    """A cloned container can use a config ID as its reference; use the manifest name."""
    runtime=dict(base['origins']['prod']['components']['backend'])
    _,manifest=executor.manifest(base['releaseTag'])
    image=manifest['images']['backend']
    require(manifest['releaseTag']==base['releaseTag'] and image['id']==runtime['imageId'],
            '基线清单运行镜像与现场不一致')
    runtime['image']=image['name']
    return runtime


def resolve_runtime(executor,runtime):
    """Bind Desktop's immutable index to the exact classic-engine config."""
    reference=runtime['image']
    local=executor.run(['docker','image','inspect','--format','{{.Id}}',reference]).decode().strip()
    require(re.fullmatch('sha256:[a-f0-9]{64}',local),'本机运行镜像身份无效')
    with tempfile.TemporaryDirectory(prefix='backend-patch-runtime-') as temporary:
        archive=Path(temporary)/'runtime.tar'
        executor.run(['docker','image','save','--output',str(archive),reference])
        require(executor.run(['docker','image','inspect','--format','{{.Id}}',reference]).decode().strip()==local,
                '本机运行镜像在核对期间改变')
        image=dict(name=reference,id=local)
        archive_image_identities(archive,{'backend':image})
        require(image['id']==runtime['imageId'],'本机运行镜像config与现场固定运行镜像不一致')
    return dict(localImageId=local,runtimeImageId=runtime['imageId'])


def verify_java(executor,job,jar,runtime):
    """Exercise the actual old runtime with the candidate JAR, no DB or network."""
    identity=resolve_runtime(executor,runtime)
    image=identity['localImageId']
    with tempfile.TemporaryDirectory(prefix='backend-patch-java-') as temporary:
        root=Path(temporary)
        binding=dict(releaseTag=job['releaseTag'],migrationId='20261023_mes_route_snapshot_legacy_summary_enforce',
                     imageId=image,operationId=job['id'],packageIdentity=digest(jar))
        command=['docker','create','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
            '--mount','type=bind,src='+str(jar.resolve())+',dst=/yudao-server/app.jar,readonly',
            '--mount','type=bind,src='+str(root)+',dst=/release-preflight',
            '--env','MES_SNAPSHOT_JDBC_URL=','--env','MES_SNAPSHOT_JDBC_USER=','--env','MES_SNAPSHOT_JDBC_PASSWORD=',
            '--entrypoint','java',image,'-Dloader.main='+MES_PREFIX.replace('/','.')+'MesRouteSnapshotMigrationCli',
            '-cp','/yudao-server/app.jar','org.springframework.boot.loader.launch.PropertiesLauncher',
            '--mode=READINESS','--report=/release-preflight/report.json']
        command+=['--'+{'releaseTag':'release-tag','migrationId':'migration-id','imageId':'image-id',
                      'operationId':'operation-id','packageIdentity':'package-identity'}[k]+'='+v for k,v in binding.items()]
        probe=executor.run(command).decode().strip()
        try:
            result=subprocess.run(['docker','start','--attach',probe],capture_output=True,timeout=60)
            report=json.loads((root/'report.json').read_text('utf-8'))
            validate_offline_cli_report(report,binding,result.returncode)
            return dict(status='passed',**identity,jarSha256=binding['packageIdentity'],network='none',databaseCredentials=False)
        finally:
            executor.run(['docker','rm','-f',probe])


def build(executor,job):
    base=executor.backend_baseline(job['payload']['baselineId'])
    commit=job['payload']['commit'];changes=validate_source(executor,base,commit)
    for env in ('test','prod','backup'):
        require(executor.backend_call(job,env,'observe')==base['origins'][env],env+': 现场基线已改变')
    c=executor.c
    require(c.get('gxpConfigurationSourceUrl'),'请配置 GxP 来源地址及真实登录凭据')
    evidence=verify_login(c,c['gxpConfigurationSourceUrl'],executor.root/'technical-evidence'/job['id']/'source-configuration',
                          dict(jobId=job['id'],gitCommit=commit),read_gxp_mode=True)
    validate_required_gxp_mode(c,evidence['gxpAuditMode'])
    require(evidence['gxpAuditMode']=='DEVELOPMENT_DISABLED','本地 GxP 必须已关闭，补丁不会写入配置')
    job['gxpConfigurationEvidence']=evidence
    tag=stamp();root=executor.root/'backend-patches'/tag
    root.mkdir(parents=True,exist_ok=False)
    worktree=Path(c['buildWorktreeRoot'])/tag
    job.update(releaseTag=tag,buildDirectory=str(root),buildWorktree=str(worktree));executor.save()
    executor.step(job,'freeze-backend-source')
    executor.run(['git','-c','core.autocrlf=false','-C',c['repo'],'worktree','add','--detach',str(worktree),commit],timeout=900)
    require(not executor.run(['git','-C',str(worktree),'status','--porcelain']).strip(),'补丁源码工作副本不干净')
    mvn=shutil.which('mvn.cmd' if os.name=='nt' else 'mvn')
    require(mvn,'未找到 Maven')
    executor.step(job,'compile-backend-jar-only')
    executor.run([mvn,'-B','-ntp','-f',str(worktree/'IntRuoyiBackend/pom.xml'),'-pl','yudao-server','-am',
                  '-DskipTests','clean','package'],timeout=5400)
    require(not executor.run(['git','-C',str(worktree),'status','--porcelain']).strip(),'编译修改了固定源码')
    shutil.copyfile(worktree/'IntRuoyiBackend/yudao-server/target/yudao-server-exec.jar',root/'app.jar')
    proof=verify_backend_jar(root/'app.jar');job['backendArtifactContract']=proof
    executor.step(job,'verify-jar-with-pinned-runtime-offline')
    job['backendJavaCompatibility']=verify_java(executor,job,root/'app.jar',pinned_runtime(executor,base))
    metadata=dict(releaseTag=base['releaseTag'],baseReleaseTag=base['releaseTag'],backendPatchTag=tag,
                  sourceCommit=commit,backendJarSha256=proof['jarSha256'])
    (root/'release-info.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),'utf-8')
    manifest=dict(applicationId='intruoyi',kind='backend-patch',releaseTag=tag,baseReleaseTag=base['releaseTag'],
                  baseGitCommit=base['gitCommit'],gitCommit=commit,databasePolicy=RUNTIME_POLICY,
                  releaseSettings={'gxpAuditMode':'DEVELOPMENT_DISABLED'},metadata=metadata,baseline=base,
                  changedFiles=changes,compatibilityReview=job['payload']['note'],
                  files=[dict(name=name,sha256=digest(root/name)) for name in ('app.jar','release-info.json')])
    validate_manifest(manifest)
    (root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')
    with tarfile.open(root/'release.tar','w') as archive:
        for name in ('manifest.json','app.jar','release-info.json'):archive.add(root/name,arcname=name)
    package=dict(releaseTag=tag,baseReleaseTag=base['releaseTag'],gitCommit=commit,directory=str(root),
                 manifestSha256=digest(root/'manifest.json'),packageSha256=digest(root/'release.tar'),
                 jarSha256=proof['jarSha256'],jarBytes=(root/'app.jar').stat().st_size,
                 stage='built',deployments={},accepted={})
    job['sealedPackage']=package;executor.save()
    executor.step(job,'publish-original-backend-patch-to-nas')
    publish_original(executor,job,package)
    executor.log(job,'单 JAR 补丁已封包；没有构建镜像、前端或数据库制品，也未部署服务器。')
