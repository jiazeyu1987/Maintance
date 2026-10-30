"""Validate/import an offline IntRuoyi handoff on a different Windows PC."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tarfile


def run(args, **kw):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw).stdout


def verify(root):
    manifest = json.loads((root/'integrity.json').read_text('utf-8'))
    for name, digest in manifest['files'].items():
        file = (root/name).resolve()
        if not file.is_relative_to(root.resolve()):
            raise ValueError('Manifest path escapes package')
        with file.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != digest:
            raise ValueError('Package checksum mismatch: '+name)
    with closing(sqlite3.connect('file:'+str(root/'private/state.snapshot.sqlite3')+'?mode=ro',uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('State database integrity failure')
        state = json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
    if any(j['status'] in ('running','queued') for j in state['jobs']):
        raise ValueError('Snapshot contains active jobs')
    print(json.dumps({'verifiedFiles':len(manifest['files']),'packages':len(state['packages'])}))


def replace_paths(value, pairs):
    if isinstance(value,dict):
        return {k:replace_paths(v,pairs) for k,v in value.items()}
    if isinstance(value,list):
        return [replace_paths(v,pairs) for v in value]
    if isinstance(value,str):
        for old,new in pairs:
            for variant in (old,old.replace('\\','/'),old.replace('/','\\')):
                if value == variant or value.startswith(variant+'/') or value.startswith(variant+'\\'):
                    return new+value[len(variant):].replace('\\','/')
    return value


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--package',required=True)
    p.add_argument('--destination')
    p.add_argument('--verify-only',action='store_true')
    p.add_argument('--source-stopped',action='store_true')
    p.add_argument('--playwright-cli')
    p.add_argument('--staging-only',action='store_true')
    p.add_argument('--project',default='intruoyi-spug')
    p.add_argument('--web-port',type=int,default=18080)
    p.add_argument('--executor-port',type=int,default=18112)
    p.add_argument('--git-proxy')
    a=p.parse_args()
    package=Path(a.package).resolve()
    verify(package)
    if a.verify_only:
        return
    if not a.destination or not (a.source_stopped or a.staging_only) or not a.playwright_cli:
        raise ValueError('Import requires destination, playwright-cli and explicit source-stopped handoff')
    if a.staging_only and (a.project=='intruoyi-spug' or a.web_port==18080 or a.executor_port==18112):
        raise ValueError('Staging verification requires separate project and ports')
    if os.name!='nt':
        raise ValueError('This package targets Windows')
    tools={name:shutil.which(name) for name in ('docker','git','ssh','java','mvn.cmd','pnpm.cmd','node')}
    if not all(tools.values()) or not Path(a.playwright_cli).is_file():
        raise ValueError('Install Docker, Git, OpenSSH, Java 21, Maven, pnpm, Node and Playwright CLI first')
    run(['docker','info'])
    if run(['docker','ps','-aq','--filter','label=com.docker.compose.project='+a.project]).strip():
        raise ValueError('Existing intruoyi-spug installation: refusing overwrite')
    dest=Path(a.destination).resolve()
    dest.mkdir(exist_ok=False)
    shutil.copytree(package/'source',dest/'source')
    shutil.copytree(package/'portable',dest/'source/ops/spug/portable',dirs_exist_ok=True)
    bootstrap=dest/'source/ops/spug/smallapp_bootstrap.sh'
    text=bootstrap.read_text(encoding='utf-8')
    guard='python3 -B /opt/intruoyi-spug/portable/disable_legacy_workers.py\n'
    if guard not in text:
        text=text.replace('set -eu\n','set -eu\n'+guard)
    if guard not in text:
        raise ValueError('Expected Spug bootstrap entry not found')
    bootstrap.write_text(text,encoding='utf-8',newline='\n')
    shutil.copytree(package/'private',dest/'private')
    state=dest/'state';state.mkdir()
    with tarfile.open(package/'release-state.tar.gz') as archive:
        archive.extractall(state, filter='data')
    included=json.loads((package/'included-versions.json').read_text('utf-8'))
    for tag in included:
        folder=state/'packages'/tag
        with tarfile.open(folder/'release.tar') as archive:
            archive.extractall(folder,filter='data')
    shutil.copyfile(package/'private/state.snapshot.sqlite3',state/'state.sqlite3')
    c=json.loads((dest/'private/executor.original.private.json').read_text('utf-8-sig'))
    repo=dest/'repository'
    revision=json.loads((package/'source-revision.json').read_text('utf-8'))
    run(['git','init',str(repo)])
    run(['git','-C',str(repo),'config','--local','core.longpaths','true'])
    run(['git','-C',str(repo),'remote','add','origin',revision['origin']])
    if a.git_proxy:
        run(['git','-C',str(repo),'config','--local','http.https://github.com.proxy',a.git_proxy])
    run(['git','-C',str(repo),'fetch','--depth=1','origin',revision['commit']])
    run(['git','-C',str(repo),'checkout','-b','portable-release','FETCH_HEAD'])
    if run(['git','-C',str(repo),'rev-parse','HEAD']).decode().strip()!=revision['commit']:
        raise ValueError('Downloaded Git commit differs from the handoff revision')
    pairs=[(c['stateDir'],state.as_posix()),(c['repo'],repo.as_posix()),
           (c['buildWorktreeRoot'],(dest/'build').as_posix())]
    c=replace_paths(c,pairs)
    c.pop('metadataRepair',None)  # Already initialized; original first-install artifact is not portable.
    c['pythonExecutable']=sys.executable
    c['executionMode']='portable-console'
    c['port']=a.executor_port
    c['sshIdentityFile']=(dest/'private/sshIdentityFile').as_posix()
    c['sshKnownHostsFile']=(dest/'private/sshKnownHostsFile').as_posix()
    c['nasCredentialsFile']=(dest/'private/nasCredentialsFile.json').as_posix()
    c['loginVerification'].update(nodePath=tools['node'],cliPath=str(Path(a.playwright_cli).resolve()),
                                  credentialsFile=(dest/'private/loginCredentials.json').as_posix())
    (dest/'build').mkdir()
    (dest/'executor.private.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
    with closing(sqlite3.connect(state/'state.sqlite3')) as db:
        payload=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
        for record in payload['packages']:
            record['portableLocalOmission']=record['releaseTag'] not in included
        db.execute('UPDATE release_state SET payload=? WHERE id=1',
                   (json.dumps(replace_paths(payload,pairs),ensure_ascii=False),))
        db.commit()
    # Only the new copied key is changed. Do not change the source/user key ACL.
    identity=run(['whoami']).decode().strip()
    run(['icacls',c['sshIdentityFile'],'/inheritance:r'])
    run(['icacls',c['sshIdentityFile'],'/grant:r',identity+':F'])
    run(['docker','load','-i',str(package/'docker-images.tar')])
    compose=dest/'source/ops/spug/compose.yaml'
    text=compose.read_text('utf-8').replace(
        'openspug/spug-service@sha256:872a01100211e3083c6b2e53f2317a488cf48d5956c7c7470b98822cab2fc392',
        'intruoyi-spug-portable:20261030')
    text=text.replace('127.0.0.1:18080:80','127.0.0.1:'+str(a.web_port)+':80')
    text=text.replace('mariadb@sha256:456709ab146585d6189da05669b84384518baecd83670c9e5221f8c20a47cf1e','intruoyi-spug-portable-db:20261030')
    compose.write_text(text,encoding='utf-8')
    env=(dest/'private/compose.env')
    env.write_text((package/'private/compose.env').read_text('utf-8')+'\nSPUG_PRIVATE_DIR='+str(dest/'private').replace('\\','/')+'\n',encoding='utf-8')
    command=['docker','compose','-p',a.project,'--env-file',str(env),'-f',str(compose)]
    run(command+['up','-d','--wait','db'])
    # Initial MariaDB bootstrap can answer ping before the named database exists.
    ready='for i in $(seq 1 60); do MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot spug -e "SELECT 1" >/dev/null 2>&1 && exit 0; sleep 1; done; exit 1'
    run(command+['exec','-T','db','sh','-c',ready])
    with (package/'private/spug.sql').open('rb') as stream:
        run(command+['exec','-T','db','sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot spug'],stdin=stream)
    for filename,directory in [('spug-data.tar.gz','/data/spug'),('spug-records.tar.gz','/var/lib/intruoyi-spug')]:
        with (package/filename).open('rb') as stream:
            run(command+['run','--rm','-T','--no-deps','--entrypoint','tar','spug','xzf','-','-C',directory],stdin=stream)
    # Keep the original registrations for evidence; disable apps whose executors were not migrated.
    script=r'''import json,re,shutil
from pathlib import Path
p=Path('/var/lib/intruoyi-spug/release-center-bridge.private.json')
c=json.loads(p.read_text())
p.with_suffix('.original.json').write_text(json.dumps(c))
c['defaultApplication']='intruoyi'
c['origin']=ORIGIN
for app in c['applications']:
 if app['id']=='intruoyi':
  app['executorUrl']=EXECUTOR
  app['repo']=REPOSITORY
 else:
  app.update(status='pending',blockers=['本次资料包仅迁移 IntRuoyi，尚未迁移此应用执行器'])
  app.pop('executorUrl',None);app.pop('bridgeKey',None)
p.write_text(json.dumps(c))
nginx=Path('/etc/nginx/nginx.conf').read_text()
locations=re.findall(r'include\s+(/var/lib/intruoyi-spug/releases/[^;]+/locations.conf);',nginx)
if len(locations)!=1:raise RuntimeError('Unique release-center nginx include required')
location=Path(locations[0]).read_text()
aliases=re.findall(r'alias\s+(/var/lib/intruoyi-spug/releases/[^;]+/ui/);',location)
if len(aliases)!=1:raise RuntimeError('Unique release-center UI directory required')
shutil.copyfile('/opt/intruoyi-spug/release-center/ui/app.js',str(Path(aliases[0])/'app.js'))
'''
    script=script.replace('ORIGIN',repr('http://127.0.0.1:'+str(a.web_port))).replace('EXECUTOR',repr('http://host.docker.internal:'+str(a.executor_port))).replace('REPOSITORY',repr(str(repo)))
    run(command+['run','--rm','-T','--no-deps','--entrypoint','python3','spug','-c',script])
    run(command+['up','-d','spug'])
    if a.staging_only:
        (dest/'STAGING_ONLY').write_text('Import verification only; do not start a publishing executor.',encoding='utf-8')
    print(json.dumps({'installed':str(dest),'start':'Run start.ps1 with the destination path','remoteServersChanged':False}))


if __name__=='__main__':
    main()
