"""One root Unix identity read, independently bound to actual host proc.

Internal source primitive only. No CLI, token, grant, start, OPEN or release gate.
Caller must independently bind Docker/full launch/current readonly JAR and boot.
Only the exact initial uid/gid namespace mapping is supported; no remap fallback.
"""
import json
import os
from pathlib import Path
import re
import secrets
import socket
import stat
import struct
import sys

import formal_original_launch as launch


class JvmIdentityError(RuntimeError):
    pass


def require(value, code):
    if not value:
        raise JvmIdentityError('JVM_IDENTITY_'+code)


def _remaining(deadline):
    try:
        return launch._remaining(deadline)
    except launch.LaunchObservationError:
        raise JvmIdentityError('JVM_IDENTITY_DEADLINE') from None


def _input(binding, process, instance, artifact, boot_id):
    require(type(binding) is dict and set(binding)=={'path','identity','pid','uid','gid'}, 'INPUT_INVALID')
    path=binding['path']
    require(type(path) is str and path.startswith('/') and str(Path(path))==path
            and '..' not in Path(path).parts and len(os.fsencode(path))<108, 'PATH_INVALID')
    require(type(binding['identity']) is dict and set(binding['identity'])=={'device','inode'}
            and all(type(n) is int and n>0 for n in binding['identity'].values()), 'SOCKET_BINDING_INVALID')
    require(type(binding['pid']) is int and binding['pid']>0 and all(type(binding[n]) is int
            and 0<=binding[n]<2**32-1 for n in ('uid','gid')), 'INPUT_INVALID')
    require(type(process) is dict and process.get('pid')==binding['pid'] and type(process.get('pid')) is int
            and type(process.get('startTicks')) is int and process['startTicks']>0, 'PROCESS_BINDING_INVALID')
    require(type(instance) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',instance)
            and type(artifact) is str and re.fullmatch('[0-9a-f]{64}',artifact)
            and type(boot_id) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',boot_id), 'INPUT_INVALID')


def _socket_signature(binding):
    path=Path(binding['path']); parents=[]
    for parent in (path.parent,*path.parent.parents):
        info=os.lstat(parent)
        require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0,binding['uid']) and not info.st_mode&0o022,
                'DIRECTORY_UNTRUSTED')
        parents.append((info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid))
    info=os.lstat(path)
    require(stat.S_ISSOCK(info.st_mode) and stat.S_IMODE(info.st_mode)==0o600 and info.st_nlink==1
            and (info.st_uid,info.st_gid)==(binding['uid'],binding['gid'])
            and dict(device=info.st_dev,inode=info.st_ino)==binding['identity']
            and stat.S_IMODE(os.lstat(path.parent).st_mode)==0o700, 'SOCKET_CHANGED')
    return tuple(parents),launch.NativeJarSource.signature(info)


def _native_peer(binding, process, boot_id, deadline):
    require(launch.process_snapshot(binding['pid'],deadline=deadline)==process, 'PROCESS_CHANGED')
    directory=os.open('/proc/'+str(binding['pid']),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        def read(name, limit):
            _remaining(deadline)
            fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
            try:
                require(stat.S_ISREG(os.fstat(fd).st_mode),'PROC_UNAVAILABLE')
                raw=os.read(fd,limit+1)
                require(0<len(raw)<=limit and not os.read(fd,1),'PROC_UNAVAILABLE')
                return raw.decode('ascii',errors='strict')
            finally:
                os.close(fd)
        for name in ('uid_map','gid_map'):
            rows=[tuple(int(v) for v in line.split()) for line in read(name,256).splitlines()]
            require(rows==[(0,0,4294967295)],'INITIAL_UID_GID_MAPPING_REQUIRED')
        fields={}
        for line in read('status',16384).splitlines():
            if ':' in line:
                key,value=line.split(':',1);require(key not in fields,'PROC_UNAVAILABLE');fields[key]=value.split()
        require(len(fields['Uid'])==4 and all(int(v)==binding['uid'] for v in fields['Uid'])
                and len(fields['Gid'])==4 and all(int(v)==binding['gid'] for v in fields['Gid']), 'PEER_CHANGED')
        pids=[int(v) for v in fields['NSpid']]
        require(pids and pids[0]==binding['pid'] and all(v>0 for v in pids), 'PEER_CHANGED')
        pid_ns=os.readlink('ns/pid',dir_fd=directory); mount_ns=os.readlink('ns/mnt',dir_fd=directory)
        require(launch._boot(deadline)==boot_id and launch._sha(os.fsencode(pid_ns))==process['ns_pidSha256']
                and launch._sha(os.fsencode(mount_ns))==process['ns_mntSha256'], 'PEER_CHANGED')
        result=dict(pid=pids[-1],startTicks=process['startTicks'],hostBootId=boot_id,
                    pidNamespace=pid_ns,mountNamespace=mount_ns)
    finally:
        os.close(directory)
    require(launch.process_snapshot(binding['pid'],deadline=deadline)==process, 'PROCESS_CHANGED')
    _remaining(deadline)
    return result


def _response(raw, nonce, native, instance, artifact):
    try:
        value=json.loads(raw.decode('utf-8',errors='strict'),object_pairs_hook=launch._pairs,parse_constant=launch._nonfinite)
    except (ValueError,UnicodeError,RecursionError,launch.LaunchObservationError):
        raise JvmIdentityError('JVM_IDENTITY_RESPONSE_INVALID') from None
    require(type(value) is dict and set(value)=={'schemaVersion','nonce','identity','codeSourceArtifactBound',
            'readOnlyObservation','admissionChanged','loadedAtStartupBytesProven','fullIdentity','fullDrain','releaseReady'}
            and value['schemaVersion']=='formal-maintenance-identity-response/v1' and value['nonce']==nonce,
            'RESPONSE_INVALID')
    require(value['codeSourceArtifactBound'] is True and value['readOnlyObservation'] is True
            and all(value[n] is False for n in ('admissionChanged','loadedAtStartupBytesProven','fullIdentity','fullDrain','releaseReady')),
            'RESPONSE_INVALID')
    identity=value['identity']
    require(type(identity) is dict and set(identity)==set(native)|{'jvmInstanceId','instanceId','artifactSha256','fullIdentity'}
            and identity['fullIdentity'] is False and identity['instanceId']==instance and identity['artifactSha256']==artifact
            and type(identity['jvmInstanceId']) is str
            and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',identity['jvmInstanceId'])
            and all(identity[n]==v and type(identity[n]) is type(v) for n,v in native.items()), 'RESPONSE_INVALID')
    return value


def observe_jvm_identity(binding, process, instance, artifact, boot_id, *, deadline):
    """One root connection and nonce; no retry, startup confirmation or state write."""
    require(sys.platform=='linux' and os.getuid()==os.geteuid()==0 and os.getgid()==os.getegid()==0, 'LINUX_ROOT_REQUIRED')
    _input(binding,process,instance,artifact,boot_id);require(0<_remaining(deadline)<=60,'DEADLINE_INVALID')
    try:
        signature=_socket_signature(binding);native=_native_peer(binding,process,boot_id,deadline)
        nonce=secrets.token_hex(16)
        payload=launch._canonical(dict(schemaVersion='formal-maintenance-identity/v1',action='READ_IDENTITY',nonce=nonce))
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
            connection.settimeout(_remaining(deadline));connection.connect(binding['path'])
            require(struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                    ==(binding['pid'],binding['uid'],binding['gid']), 'PEER_CHANGED')
            require(_socket_signature(binding)==signature,'SOCKET_CHANGED')
            connection.settimeout(_remaining(deadline));connection.sendall(struct.pack('!I',len(payload))+payload)
            def take(count):
                raw=b''
                while len(raw)<count:
                    connection.settimeout(_remaining(deadline));chunk=connection.recv(count-len(raw))
                    require(bool(chunk),'FRAME_INCOMPLETE');raw+=chunk
                return raw
            count=struct.unpack('!I',take(4))[0];require(0<count<=8192,'FRAME_INVALID')
            result=_response(take(count),nonce,native,instance,artifact)
            require(struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                    ==(binding['pid'],binding['uid'],binding['gid']), 'PEER_CHANGED')
        require(_native_peer(binding,process,boot_id,deadline)==native,'PEER_CHANGED')
        require(_socket_signature(binding)==signature,'SOCKET_CHANGED');_remaining(deadline)
        result['peerPid']=binding['pid']
        return result
    except (OSError,ValueError,UnicodeError,KeyError,IndexError,launch.LaunchObservationError):
        raise JvmIdentityError('JVM_IDENTITY_SOURCE_UNAVAILABLE') from None


def require_new_jvm(previous, current):
    """Finite matching of already observed facts, never an action or attestation.

    A UUID can change when a Control is recreated in the same JVM. Actual start
    ticks must increase on the same boot; namespace PID=1 and host PID reuse are
    valid only with this process distinction. Caller still owns both provenances.
    """
    require(type(previous) is dict and type(current) is dict,'NEW_PROCESS_INPUT_INVALID')
    for value in (previous,current):
        identity=value.get('identity')
        require(type(identity) is dict and type(value.get('peerPid')) is int and value['peerPid']>0,
                'NEW_PROCESS_INPUT_INVALID')
        native={n:identity.get(n) for n in ('pid','startTicks','hostBootId','pidNamespace','mountNamespace')}
        require(all(type(native[n]) is int and native[n]>0 for n in ('pid','startTicks'))
                and type(native['hostBootId']) is str
                and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',native['hostBootId'])
                and all(type(native[n]) is str and re.fullmatch(prefix+r':\[[0-9]+\]',native[n])
                        for n,prefix in (('pidNamespace','pid'),('mountNamespace','mnt'))), 'NEW_PROCESS_INPUT_INVALID')
        instance=identity.get('instanceId');artifact=identity.get('artifactSha256')
        require(type(instance) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',instance)
                and type(artifact) is str and re.fullmatch('[0-9a-f]{64}',artifact)
                and type(value.get('nonce')) is str and re.fullmatch('[0-9a-f]{32}',value['nonce']), 'NEW_PROCESS_INPUT_INVALID')
        wire={n:v for n,v in value.items() if n!='peerPid'}
        _response(launch._canonical(wire),value['nonce'],native,instance,artifact)
    old=previous['identity'];new=current['identity']
    require(all(old[n]==new[n] for n in ('hostBootId','instanceId','artifactSha256'))
            and old['jvmInstanceId']!=new['jvmInstanceId'] and new['startTicks']>old['startTicks'], 'NEW_PROCESS_REQUIRED')
    return dict(newProcessIdentityMatched=True,coldStartConfirmed=False,fullDrain=False,releaseReady=False,
                productionEvidence=False,serviceActionsPerformed=False)
