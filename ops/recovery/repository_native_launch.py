"""Controlled native launch and strict SSH argv construction. No remote retries."""
import argparse
import os
from pathlib import PurePosixPath
import shlex
import sys

from repository_records import (Configuration, document, exact, pin_file, read_pin,
                                require, signed_pin)
from repository_native_lab import LAB_ROOT, contained, execution_host, private


def ssh_argv(profile_pin, authority_pins, configuration_pin, request_pin, context_pin, trust_pin, output):
    """W05 may launch this exact argv; a disconnect never proves remote exit."""
    profile=signed_pin(profile_pin,authority_pins)
    exact(profile,'schemaVersion host port user sshPin knownHostsPin credentialRef remoteExecutionHostPin remoteDispatcherPin remoteWorkingDirectory allowedLabRoot connectionTimeoutSeconds',
        'RepositorySshLaunchProfile/v1')
    require(profile['host']=='172.30.30.59' and type(profile['port']) is int and 1<=profile['port']<=65535 and
        profile['user']=='root' and profile['allowedLabRoot']==LAB_ROOT and
        type(profile['connectionTimeoutSeconds']) is int and 0<profile['connectionTimeoutSeconds']<=60,
        'REPOSITORY_SSH_SCOPE_INVALID')
    for key in ('sshPin','knownHostsPin','credentialRef'):read_pin(profile[key],32*1024*1024)
    known=read_pin(profile['knownHostsPin']).decode('ascii').splitlines()
    require(any(line.split() and line.split()[0] in (profile['host'],f"[{profile['host']}]:{profile['port']}")
        for line in known if not line.startswith('#')), 'REPOSITORY_SSH_KNOWN_HOST_REQUIRED')
    credential=document(read_pin(profile['credentialRef']))
    exact(credential,'schemaVersion privateKeyPin','RepositorySshCredentialReference/v1')
    read_pin(credential['privateKeyPin'],65536)
    host=document(read_pin(profile['remoteExecutionHostPin']))
    require(host['schemaVersion']=='RepositoryNativeExecutionHost/v1' and
        host['hostOs']=='Linux' and host['uid']==host['gid']==0 and
        host['dispatcherPin']==profile['remoteDispatcherPin'] and
        host['workingDirectory']==profile['remoteWorkingDirectory'], 'REPOSITORY_SSH_REMOTE_HOST_CHANGED')
    def remote_path(path):
        path=PurePosixPath(path)
        require(path.is_absolute() and '..' not in path.parts and
            (str(path)==LAB_ROOT or PurePosixPath(LAB_ROOT) in path.parents), 'REPOSITORY_SSH_REMOTE_PATH_INVALID')
        return str(path)
    args=[remote_path(host['pythonPin']['path']),'-B',remote_path(profile['remoteDispatcherPin']['path'])]
    for name,pin in (('configuration',configuration_pin),('request',request_pin),('context',context_pin),('trust',trust_pin)):
        read_pin(pin,128*1024*1024)
        args+=['--'+name,remote_path(pin['path']),'--'+name+'-sha256',pin['sha256']]
    args+=['--output',remote_path(output)]
    return [profile['sshPin']['path'],'-T','-p',str(profile['port']),'-o','BatchMode=yes',
        '-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+profile['knownHostsPin']['path'],
        '-o','IdentitiesOnly=yes','-o','ConnectTimeout='+str(profile['connectionTimeoutSeconds']),
        '-i',credential['privateKeyPin']['path'],profile['user']+'@'+profile['host'],shlex.join(args)]


def main():
    require(sys.platform.startswith('linux') and os.geteuid()==os.getegid()==0,
            'REPOSITORY_NATIVE_LINUX_ROOT_REQUIRED')
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('configuration','configuration-sha256','request','request-sha256','context','context-sha256','trust','trust-sha256','output'):
        parser.add_argument('--'+key,required=True)
    args=parser.parse_args()
    pins={}
    for key in ('configuration','request','context','trust'):
        path=private(getattr(args,key));pins[key]=pin_file(path)
        require(pins[key]['sha256']==getattr(args,key+'_sha256'),'REPOSITORY_NATIVE_LAUNCH_INPUT_CHANGED')
    private(contained(args.output).parent,directory=True)
    for prefix in ('INTRUOYI_REPOSITORY_LAB_CONTEXT_','INTRUOYI_BACKUP_LAB_CONTEXT_'):
        os.environ[prefix+'PATH']=pins['context']['path'];os.environ[prefix+'SHA256']=pins['context']['sha256']
    os.environ['INTRUOYI_REPOSITORY_CONFIG_PATH']=pins['configuration']['path']
    os.environ['INTRUOYI_REPOSITORY_CONFIG_SHA256']=pins['configuration']['sha256']
    os.environ['INTRUOYI_BACKUP_LAB_TRUST_PATH']=pins['trust']['path']
    os.environ['INTRUOYI_BACKUP_LAB_TRUST_SHA256']=pins['trust']['sha256']
    config=Configuration(pins['configuration'])
    require(config.native_lab,'REPOSITORY_NATIVE_SERVICE_REQUIRED')
    host=execution_host(config.value['executionHostPin'],config.value['authorityKeyPins'])
    require(host['dispatcherPin']==pin_file(__file__),'REPOSITORY_NATIVE_DISPATCHER_NOT_SELECTED')
    from repository_cli import execute
    return execute(pins['request']['path'],args.output)


if __name__=='__main__':
    try:sys.exit(main())
    except Exception as error:
        from repository_records import RepositoryError
        print(error.code if isinstance(error,RepositoryError) else 'REPOSITORY_NATIVE_LAUNCH_'+type(error).__name__.upper(),file=sys.stderr)
        sys.exit(2 if isinstance(error,RepositoryError) and error.unknown else 1)
