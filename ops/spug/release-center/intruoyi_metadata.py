"""Explicit restoration of omitted metadata for a proved historical package.

This repairs a running historical deployment, not the original immutable image.
New builds must still read release-info.json back from their built images.
"""
import json
from pathlib import Path
import re
import shlex
import subprocess

from executor import digest, require
from intruoyi_build import archive_image_identities


def reference(config):
    folder = Path(config['packageDirectory'])
    manifest = json.loads((folder/'manifest.json').read_bytes())
    require(digest(folder/'manifest.json') == config['manifestSha256'], 'Historical manifest changed')
    require(digest(folder/'images.tar') == manifest['packageSha256'], 'Historical image archive changed')
    require(re.fullmatch('[a-f0-9]{40}', manifest['sourceCommit']), 'Exact historical source commit required')
    images = {role:dict(name='intruoyi-'+role+':'+manifest['releaseTag'], id=manifest[role+'Image'])
              for role in ('frontend','backend')}
    archive_image_identities(folder/'images.tar', images)
    repository = Path(config['sourceRepository']).resolve(strict=True)
    proc = subprocess.run(['git','-c','safe.directory='+repository.as_posix(),'-C',str(repository),
                           'show','-s','--format=%s',manifest['sourceCommit']],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(proc.returncode == 0, 'Historical source commit is unavailable')
    info = {key:manifest[key] for key in ('releaseTag','sourceCommit','builtAt')}
    info['changeSet'] = {'gitChanges':[manifest['sourceCommit'][:12]+' '+proc.stdout.decode('utf-8').strip()]}
    return manifest, images, info


AGENT = r'''
import hashlib,json,subprocess,urllib.request
from pathlib import Path
def run(args):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if result.returncode: raise ValueError('Metadata operation failed: '+args[0]+' exit='+str(result.returncode))
    return result.stdout
def inspect(name): return json.loads(run(['docker','inspect',name]))[0]
def stable(c):
    result={key:c[key] for key in ('Id','Image','Config','HostConfig','Mounts')}
    result['Mounts']=sorted(result['Mounts'],key=lambda mount:(mount['Destination'],mount['Source'],mount['Type']))
    return result
def check():
    root=Path(payload['directory'])
    if json.loads((root/'manifest.json').read_bytes())!=payload['manifest']:
        raise ValueError('Deployed historical manifest differs')
    before={role:inspect(payload['profile'][role]) for role in ('backend','frontend')}
    for role,c in before.items():
        if c['Image']!=payload['images'][role]['id'] or c['Config']['Image']!=payload['images'][role]['name'] or not c['State']['Running']:
            raise ValueError(role+': running image does not match original archive')
    metadata=run(['docker','exec',payload['profile']['frontend'],'sh','-c',
        'if test -f /usr/share/nginx/html/release-info.json; then cat /usr/share/nginx/html/release-info.json; else printf MISSING; fi'])
    if metadata!=b'MISSING' and json.loads(metadata)!=payload['info']:
        raise ValueError('Existing version metadata conflicts; no overwrite')
    return root,before,metadata==b'MISSING'
try:
    root,before,missing=check()
    if payload['apply']:
        supplement=root/'metadata-repair-20261021'
        supplement.mkdir(mode=0o700,exist_ok=True)
        path=supplement/'release-info.json'
        content=json.dumps(payload['info'],ensure_ascii=False,indent=2).encode('utf-8')
        if path.exists() and path.read_bytes()!=content: raise ValueError('Saved metadata differs')
        path.write_bytes(content)
        path.chmod(0o644)
        if missing:
            run(['docker','cp',str(path),payload['profile']['frontend']+':/usr/share/nginx/html/release-info.json'])
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(payload['profile']['entryUrl'].rstrip('/')+'/release-info.json',timeout=20) as response:
            if response.status!=200 or response.headers.get_content_type()!='application/json' or json.load(response)!=payload['info']:
                raise ValueError('Published metadata HTTP identity differs')
        for role,c in before.items():
            current=inspect(payload['profile'][role])
            if stable(current)!=stable(c) or current['State']['StartedAt']!=c['State']['StartedAt'] or not current['State']['Running']:
                raise ValueError('Runtime container identity/configuration changed')
        if json.loads((root/'manifest.json').read_bytes())!=payload['manifest']: raise ValueError('Historical manifest changed')
    print(json.dumps({'ok':True,'result':{'releaseTag':payload['info']['releaseTag'],
        'sourceCommit':payload['info']['sourceCommit'],'neededRepair':missing,'applied':payload['apply'],
        'persistedInImage':False,'containerIdentityUnchanged':True}}))
except Exception as error:
    print(json.dumps({'ok':False,'error':str(error)}))
'''


def remote(runtime, env, directory, manifest, images, info, apply=False):
    profile = runtime.profile(env)
    payload = dict(profile={k:profile[k] for k in ('frontend','backend','entryUrl')},
                   directory=directory,manifest=manifest,images=images,info=info,apply=apply)
    source = 'payload='+repr(payload)+'\n'+AGENT
    result = subprocess.run(['ssh',*runtime.ssh_options(),'root@'+profile['host'],shlex.quote(profile['python'])+' -'],
                            input=source.encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
    require(result.returncode == 0, env+': metadata transport failed; exit='+str(result.returncode))
    value = json.loads(result.stdout)
    require(value.get('ok') is True, env+': '+value.get('error','Metadata restoration refused'))
    return value['result']


def restore(executor, job):
    config = executor.c['metadataRepair']
    manifest, images, info = reference(config)
    origins = {}
    # All origins are proved before the first file is written.
    for env in ('test','prod','backup'):
        executor.step(job,'verify-historical-package-'+env)
        origins[env] = executor.runtime.observe(env)
        require(origins[env]['backendHealth']['status']=='UP' and origins[env]['frontendHttpStatus']==200,
                env+': healthy original deployment required')
        remote(executor.runtime,env,config['directories'][env],manifest,images,info)
    job['originEvidence'] = {env:{key:value[key] for key in ('images','schemaSha256','ledgerSha256','runtimeConfigSha256')}
                             for env,value in origins.items()}
    job['result'] = {}
    executor.save()
    for env in ('test','prod','backup'):
        executor.step(job,'restore-version-metadata-'+env,effects=True)
        value = remote(executor.runtime,env,config['directories'][env],manifest,images,info,apply=True)
        after = executor.runtime.observe(env)
        for key in ('images','schemaSha256','ledgerSha256','runtimeConfigSha256'):
            require(after[key] == origins[env][key], env+': metadata repair changed '+key)
        require(after['releaseTag']==info['releaseTag'], env+': version read-back failed')
        job['result'][env] = value
        executor.save()
    executor.log(job,'Historical static metadata restored. Original images/package unchanged; not a new release or acceptance.')
