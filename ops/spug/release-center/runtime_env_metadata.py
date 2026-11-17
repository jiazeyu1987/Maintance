"""Align legacy compose metadata after a verified Spug deployment, without restarting it.

The running digest and immutable manifest remain authoritative. This command only
updates IMAGE_TAG after both images and the deployment's technical record agree.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import stat
import subprocess
import sys


class MetadataBlocked(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise MetadataBlocked(message)


def aligned_bytes(raw, expected, tag):
    require(re.fullmatch(r'20\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}', tag), 'Invalid release tag')
    lines=raw.splitlines(keepends=True)
    indices=[i for i,line in enumerate(lines) if line.startswith(b'IMAGE_TAG=')]
    require(len(indices)==1, 'Exactly one IMAGE_TAG line is required')
    index=indices[0]; line=lines[index]; content=line.rstrip(b'\r\n')
    require(content==('IMAGE_TAG='+expected).encode('ascii'), 'IMAGE_TAG changed since inspection')
    lines[index]=('IMAGE_TAG='+tag).encode('ascii')+line[len(content):]
    return b''.join(lines)


def validate_image(container, image, expected):
    require(container['State']['Running'] is True, 'Application container is stopped')
    require(container['Image']==image['Id']==expected['id'], 'Running image differs from immutable package')
    require(expected['name'] in image.get('RepoTags',[]), 'Release image tag is missing')


def remote_align(payload):
    import fcntl
    lock_path=Path(payload['operationRoot'])/'runtime-operation.lock'
    require(lock_path.is_file() and not lock_path.is_symlink(),'Registered operation lock is missing or is a symlink')
    with lock_path.open('r+b') as mutation_lock:
        fcntl.flock(mutation_lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        return _remote_align_locked(payload)


def _remote_align_locked(payload):
    import fcntl
    def inspect(arguments):
        result=subprocess.run(['docker',*arguments],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        require(result.returncode==0, 'Docker inspection failed')
        return json.loads(result.stdout)[0]
    for role in ('backend','frontend'):
        validate_image(inspect(['inspect',payload['containers'][role]]),
                       inspect(['image','inspect',payload['images'][role]['name']]),payload['images'][role])
    path=Path(payload['envFile'])
    require(path.is_file() and not path.is_symlink(), 'Runtime env file is missing or is a symlink')
    with path.open('rb') as stream:
        fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
        raw=stream.read(); original_stat=os.fstat(stream.fileno())
        updated=aligned_bytes(raw,payload['expectedCurrentTag'],payload['releaseTag'])
        report={'releaseTag':payload['releaseTag'],'beforeSha256':hashlib.sha256(raw).hexdigest(),
                'afterSha256':hashlib.sha256(updated).hexdigest(),'imagesVerified':True,
                'businessRestarted':False,'applied':False}
        if payload['apply']:
            evidence=Path(payload['evidenceRoot'])
            evidence.mkdir(parents=True,mode=0o700,exist_ok=False)
            backup=evidence/'runtime.env.before'
            descriptor=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(descriptor,'wb') as original:original.write(raw);original.flush();os.fsync(original.fileno())
            temporary=path.with_name('.env.spug-'+payload['releaseTag'])
            descriptor=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,stat.S_IMODE(original_stat.st_mode))
            with os.fdopen(descriptor,'wb') as output:
                output.write(updated);output.flush();os.fsync(output.fileno())
                os.fchmod(output.fileno(),stat.S_IMODE(original_stat.st_mode))
                os.fchown(output.fileno(),original_stat.st_uid,original_stat.st_gid)
            require(path.stat().st_ino==original_stat.st_ino and path.read_bytes()==raw,'Runtime env changed concurrently')
            os.replace(temporary,path)
            require(path.read_bytes()==updated,'Runtime env readback differs')
            report['applied']=True
        return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True)
    parser.add_argument('--environment',choices=['test','prod','backup'],required=True)
    parser.add_argument('--release-tag',required=True)
    parser.add_argument('--expected-current-tag',required=True)
    parser.add_argument('--env-file',required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    config=json.loads(Path(args.config).read_text(encoding='utf-8-sig'))
    root=Path(config['stateDir']);uri=(root/'state.sqlite3').resolve().as_uri()+'?mode=ro'
    with sqlite3.connect(uri,uri=True) as connection:
        state=json.loads(connection.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
    candidates=[p for p in state['packages'] if p['releaseTag']==args.release_tag]
    require(len(candidates)==1,'Immutable package is not uniquely registered')
    package=candidates[0]
    technical=package.get('outcomes',{}).get(args.environment,{}).get('technical',{})
    require(technical.get('status')=='passed' and technical.get('releaseTag')==args.release_tag
            and technical.get('packageSha256')==package['packageSha256'],'Same-package technical verification is required')
    require(all(technical.get('checks',{}).get(k,{}).get('status')=='passed' for k in ['version','upgrade','login']),
            'Version, upgrade and real login checks must pass')
    require(state['environments'][args.environment]['releaseTag']==args.release_tag,'Registered target version differs')
    require(not any(j['status']=='running' or (j['status']=='interrupted' and not j.get('resolution') and not j.get('reconciledBy')) for j in state['jobs']),'A task is running or interrupted')
    path=Path(package['directory'])/'manifest.json';raw=path.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==package['manifestSha256'],'Manifest digest differs')
    manifest=json.loads(raw)
    require(manifest['releaseTag']==manifest['IMAGE_TAG']==args.release_tag,'Manifest version differs')
    profile=config['targets'][args.environment]
    require(re.fullmatch(r'[A-Za-z0-9.-]+',profile['host']),'Invalid target host')
    require(args.env_file.startswith('/') and '..' not in Path(args.env_file).parts,'Explicit absolute runtime env path required')
    payload={'containers':{k:profile[k] for k in ['backend','frontend']},'images':manifest['images'],
             'releaseTag':args.release_tag,'expectedCurrentTag':args.expected_current_tag,'envFile':args.env_file,
             'operationRoot':profile['stagingRoot'],
             'evidenceRoot':profile['stagingRoot']+'/configuration/env-metadata-'+args.release_tag,'apply':args.apply}
    code='scope={"__name__":"runtime_env_metadata_remote"}\nexec(compile('+repr(Path(__file__).read_text(encoding='utf-8'))+',"runtime_env_metadata.py","exec"),scope)\n'
    code+='try:\n print(json.dumps(scope["remote_align"]('+repr(payload)+')))\nexcept Exception as error:\n print(json.dumps({"blocked":type(error).__name__}));sys.exit(1)\n'
    code='import json,sys\n'+code
    command=['ssh','-F','NUL' if os.name=='nt' else '/dev/null','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
             '-o','ConnectTimeout=10','-i',config['sshIdentityFile'],'-o','IdentitiesOnly=yes',
             '-o','UserKnownHostsFile='+config['sshKnownHostsFile'],'root@'+profile['host'],shlex.quote(profile['python'])+' -']
    result=subprocess.run(command,input=code.encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
    require(result.returncode==0,'Remote metadata verification or alignment was blocked; no success is inferred')
    report=json.loads(result.stdout);report['environment']=args.environment
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    try:main()
    except MetadataBlocked as error:
        print('BLOCKED: '+str(error),file=sys.stderr);sys.exit(2)
    except Exception as error:
        print('BLOCKED: '+type(error).__name__,file=sys.stderr);sys.exit(2)
