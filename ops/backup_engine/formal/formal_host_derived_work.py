"""Read fixed systemd-v1 related work sources; no drain or exclusion attestation.

Missing or changed known processes remain unresolved. Empty cgroups describe
only this finite observation, not business completion or future writer control.
No command line, environment, signal, action, alternate hierarchy or CLI.
"""
import hashlib
import os
from pathlib import Path
import re
import stat
import time

import formal_boot_state as boot
import formal_host_admission as host
import formal_snapshot_linux as snapshot
from formal_filesystem_watchdog import require_native_runtime
from formal_snapshot_linux import FormalSnapshotError,require

UNITS=('crond.service',*host.ASSOCIATED)
UNIT_PROPERTIES=(('Unit','Id'),('Unit','LoadState'),('Unit','ActiveState'),
    ('Unit','SubState'),('Unit','Job'),('Unit','InvocationID'),
    ('Service','MainPID'),('Service','ControlPID'),('Service','ControlGroup'))
PSEUDO_FILES={'stat','status','cgroup','mountinfo','boot_id','cgroup.procs'}
MAX_DIRECTORIES=128
MAX_PROCESSES=256


def _need(ok,code):require(ok,'FORMAL_HOST_'+code)
def _sha(raw):return hashlib.sha256(raw).hexdigest()
def _time(deadline):_need(time.monotonic()<deadline,'DERIVED_DEADLINE')
def _identity(info):return (info.st_dev,info.st_ino,info.st_uid,info.st_gid,info.st_mode)


def _path(value):
    _need(type(value) is str and value.startswith('/') and '\0' not in value and
        str(Path(value))==value and all(part not in ('.','..') for part in value.split('/')[1:]),
        'DERIVED_BINDING_INVALID')
    return value


def _validate(binding,expected_sha256):
    _need(type(binding) is dict and set(binding)=={'schemaVersion','hierarchy','bootId','hierarchyId',
        'mount','units','knownProcesses'} and binding['schemaVersion']=='formal-host-derived-source/v1',
        'DERIVED_BINDING_INVALID')
    _need(binding['hierarchy']=='systemd-v1','HIERARCHY_UNSUPPORTED')
    _need(type(expected_sha256) is str and re.fullmatch('[0-9a-f]{64}',expected_sha256) and
        _sha(snapshot._canonical_bytes(binding))==expected_sha256,'DERIVED_BINDING_CHANGED')
    _need(type(binding['bootId']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',binding['bootId']) and
        type(binding['hierarchyId']) is int and 0<binding['hierarchyId']<2**31,'DERIVED_BINDING_INVALID')
    mount=binding['mount']
    _need(type(mount) is dict and set(mount)=={'mountId','device','root','target','namespace'} and
        type(mount['mountId']) is int and 0<mount['mountId']<2**31 and type(mount['device']) is str and
        re.fullmatch('(0|[1-9][0-9]*):(0|[1-9][0-9]*)',mount['device']) and type(mount['namespace']) is str and
        re.fullmatch(r'mnt:\[[1-9][0-9]*\]',mount['namespace']),'DERIVED_BINDING_INVALID')
    _path(mount['root']);_path(mount['target'])
    _need(type(binding['units']) is dict and set(binding['units'])==set(UNITS),'DERIVED_BINDING_INVALID')
    paths=[]
    for item in binding['units'].values():
        _need(type(item) is dict and set(item)=={'cgroupPath'} and type(item['cgroupPath']) is str,
              'DERIVED_BINDING_INVALID')
        if item['cgroupPath']:
            _path(item['cgroupPath']);paths.append(item['cgroupPath'])
            _need(item['cgroupPath']!='/' and (mount['root']=='/' or
                item['cgroupPath'].startswith(mount['root']+'/')),'DERIVED_BINDING_INVALID')
    _need(len(paths)==len(set(paths)) and all(not a.startswith(b+'/') for a in paths for b in paths if a!=b),
          'DERIVED_BINDING_INVALID')
    known=binding['knownProcesses']
    _need(type(known) is list and len(known)<=MAX_PROCESSES,'DERIVED_BINDING_INVALID')
    for row in known:
        _need(type(row) is dict and set(row)=={'pid','startTicks'} and
            all(type(row[k]) is int and 0<row[k]<2**63 for k in row),'DERIVED_BINDING_INVALID')
    _need(len(known)==len({row['pid'] for row in known}),'DERIVED_BINDING_INVALID')


def _read(directory,name,limit,deadline):
    _need(name in PSEUDO_FILES,'DERIVED_SOURCE_INVALID');_time(deadline)
    fd=None
    try:
        fd=os.open(name,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory)
        before=os.fstat(fd)
        _need(stat.S_ISREG(before.st_mode),'DERIVED_SOURCE_INVALID')
        parts=[];size=0
        while True:
            _time(deadline);part=os.read(fd,min(65536,limit-size+1))
            if not part:break
            size+=len(part);_need(size<=limit,'DERIVED_SOURCE_LIMIT');parts.append(part)
        _need(_identity(os.fstat(fd))==_identity(before) and
            _identity(os.stat(name,dir_fd=directory,follow_symlinks=False))==_identity(before),
            'DERIVED_SOURCE_CHANGED')
        _time(deadline);return b''.join(parts)
    except OSError:raise FormalSnapshotError('FORMAL_HOST_DERIVED_SOURCE_UNAVAILABLE') from None
    finally:
        if fd is not None:os.close(fd)


def _namespace(directory,name):
    fd=None
    try:
        fd=os.open('ns',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory)
        _need(stat.S_ISLNK(os.stat(name,dir_fd=fd,follow_symlinks=False).st_mode),'DERIVED_SOURCE_INVALID')
        value=os.readlink(name,dir_fd=fd)
        _need(re.fullmatch(('mnt' if name=='mnt' else 'pid')+r':\[[1-9][0-9]*\]',value),
              'DERIVED_SOURCE_INVALID')
        return value
    except OSError:raise FormalSnapshotError('FORMAL_HOST_PROCESS_UNAVAILABLE') from None
    finally:
        if fd is not None:os.close(fd)


def _stat_identity(pid,raw):
    text=raw.decode('ascii',errors='strict');end=text.rfind(') ')
    _need(end>0 and text.startswith(str(pid)+' ('),'PROCESS_SOURCE_INVALID')
    fields=text[end+2:].split()
    _need(len(fields)>=20 and fields[1].isdigit() and fields[19].isdigit() and
        len(fields[0])==1 and fields[0] not in ('Z','X','x'),'PROCESS_SOURCE_INVALID')
    return dict(pid=pid,parentPid=int(fields[1]),startTicks=int(fields[19]),state=fields[0])


def _groups(raw):
    rows=[];ids=set()
    for line in raw.decode('utf-8',errors='strict').splitlines():
        fields=line.split(':',2)
        _need(len(fields)==3 and re.fullmatch('0|[1-9][0-9]*',fields[0]),'PROCESS_SOURCE_INVALID')
        hierarchy=int(fields[0]);controllers=fields[1].split(',') if fields[1] else []
        _need(hierarchy not in ids and len(controllers)==len(set(controllers)) and
            all(re.fullmatch('[A-Za-z0-9_=.-]+',v) for v in controllers),'PROCESS_SOURCE_INVALID')
        ids.add(hierarchy);_path(fields[2])
        rows.append(dict(hierarchyId=hierarchy,controllers=sorted(controllers),path=fields[2]))
    _need(0<len(rows)<=64,'PROCESS_SOURCE_INVALID')
    return sorted(rows,key=lambda row:row['hierarchyId'])


def _process(proc_fd,pid,deadline):
    directory=None
    try:
        directory=os.open(str(pid),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=proc_fd)
        before_dir=_identity(os.fstat(directory));before=_stat_identity(pid,_read(directory,'stat',8192,deadline))
        status=_read(directory,'status',65536,deadline).decode('utf-8',errors='strict')
        for key in ('Pid','Tgid'):
            values=re.findall(r'^'+key+r':\s*([0-9]+)$',status,re.M)
            _need(len(values)==1 and int(values[0])==pid,'PROCESS_SOURCE_INVALID')
        groups=_groups(_read(directory,'cgroup',65536,deadline))
        mounts=_read(directory,'mountinfo',1048576,deadline)
        _mounts(mounts)
        result=dict(before,cgroups=groups,mountinfoSha256=_sha(mounts),
            mountNamespace=_namespace(directory,'mnt'),pidNamespace=_namespace(directory,'pid'),
            directoryIdentity=list(before_dir))
        _need(before==_stat_identity(pid,_read(directory,'stat',8192,deadline)) and
            before_dir==_identity(os.fstat(directory)) and
            before_dir==_identity(os.stat(str(pid),dir_fd=proc_fd,follow_symlinks=False)),
            'PROCESS_IDENTITY_CHANGED')
        _time(deadline);return result
    except OSError:raise FormalSnapshotError('FORMAL_HOST_PROCESS_UNAVAILABLE') from None
    finally:
        if directory is not None:os.close(directory)


def _unescape(value):
    _need(re.search(r'\\(?!040|011|012|134)',value) is None,'MOUNT_SOURCE_INVALID')
    return re.sub(r'\\(040|011|012|134)',lambda m:chr(int(m[1],8)),value)


def _mounts(raw):
    rows=[];ids=set()
    for line in raw.decode('utf-8',errors='strict').splitlines():
        fields=line.split(' ')
        _need(fields.count('-')==1,'MOUNT_SOURCE_INVALID');end=fields.index('-')
        _need(end>=6 and len(fields)==end+4 and fields[0].isdigit() and fields[1].isdigit() and
            re.fullmatch('[0-9]+:[0-9]+',fields[2]) and all(fields),'MOUNT_SOURCE_INVALID')
        mid=int(fields[0]);_need(mid>0 and mid not in ids,'MOUNT_SOURCE_INVALID');ids.add(mid)
        root=_unescape(fields[3]);target=_unescape(fields[4]);_path(root);_path(target)
        rows.append(dict(mountId=mid,device=fields[2],root=root,target=target,
            fstype=fields[end+1],superOptions=sorted(fields[end+3].split(','))))
        _need(len(rows)<=4096,'DERIVED_SOURCE_LIMIT')
    _need(bool(rows),'MOUNT_SOURCE_INVALID');return rows


def _unit(native,unit,deadline):
    result={};encoded=''.join(c if c.isascii() and c.isalnum() else '_%02x'%ord(c) for c in unit)
    for interface,key in UNIT_PROPERTIES:
        _time(deadline)
        raw=native._bus_run(['--system','--no-pager','get-property','org.freedesktop.systemd1',
            '/org/freedesktop/systemd1/unit/'+encoded,'org.freedesktop.systemd1.'+interface,key],deadline)
        _need(type(raw) is bytes and len(raw)<=16384,'UNIT_SOURCE_INVALID')
        if key in ('MainPID','ControlPID'):
            match=re.fullmatch(rb'u (0|[1-9][0-9]*)\n',raw)
            _need(match is not None and int(match[1])<2**32,'UNIT_SOURCE_INVALID');result[key]=int(match[1])
        elif key=='Job':
            match=re.fullmatch(rb'\(uo\) (0|[1-9][0-9]*) "(/[A-Za-z0-9_/]*)"\n',raw)
            _need(match is not None and int(match[1])<2**32,'UNIT_SOURCE_INVALID')
            job=int(match[1]);path=match[2]
            _need(path==(b'/' if job==0 else b'/org/freedesktop/systemd1/job/'+str(job).encode()),
                  'UNIT_SOURCE_INVALID')
            result[key]=job
        elif key=='InvocationID':
            words=raw.split()
            _need(len(words)==18 and words[:2]==[b'ay',b'16'] and
                all(w.isdigit() and 0<=int(w)<=255 for w in words[2:]),'UNIT_SOURCE_INVALID')
            result[key]=bytes(int(w) for w in words[2:]).hex()
        else:
            match=re.fullmatch(rb's "([A-Za-z0-9_./@:-]*)"\n',raw)
            _need(match is not None,'UNIT_SOURCE_INVALID');result[key]=match[1].decode('ascii')
    _need(result['Id']==unit and result['LoadState'] in ('loaded','masked') and
        result['ActiveState'] in ('active','inactive','activating','deactivating','failed') and
        bool(result['SubState']),'UNIT_SOURCE_INVALID')
    if result['ControlGroup']:_path(result['ControlGroup'])
    _time(deadline);return result


def _tree(path,mount,deadline,directory_limit):
    directories=[];pids=set();pending=[path]
    _need(directory_limit>0,'DERIVED_SOURCE_LIMIT')
    while pending:
        _time(deadline);current=pending.pop()
        with boot._directory(current) as (fd,identity):
            info=os.fstat(fd)
            _need(str(os.major(info.st_dev))+':'+str(os.minor(info.st_dev))==mount['device'],
                  'MOUNT_BINDING_CHANGED')
            raw=_read(fd,'cgroup.procs',65536,deadline)
            words=raw.splitlines()
            _need(all(re.fullmatch(rb'[1-9][0-9]*',w) and int(w)<2**31 for w in words),
                  'PROCESS_SOURCE_INVALID')
            members=sorted(set(map(int,words)));pids.update(members)
            names=os.listdir(fd);_need(len(names)<=512,'DERIVED_SOURCE_LIMIT')
            children=[]
            for name in sorted(names):
                item=os.stat(name,dir_fd=fd,follow_symlinks=False)
                _need(not stat.S_ISLNK(item.st_mode),'DERIVED_SOURCE_INVALID')
                if stat.S_ISDIR(item.st_mode):children.append(current/name)
            directories.append(dict(path=str(current),identity=[list(v) for v in identity],members=members))
            boot._directory_unchanged(current,identity)
            pending.extend(reversed(children))
            _need(len(directories)+len(pending)<=directory_limit and len(pids)<=MAX_PROCESSES,
                  'DERIVED_SOURCE_LIMIT')
    return directories,pids


def _sample(native,binding,proc,deadline,*,allow_bound_process_absence=False):
    with boot._directory(proc/'sys/kernel/random') as (fd,_):
        _need(_read(fd,'boot_id',128,deadline)==(binding['bootId']+'\n').encode(),'DERIVED_BINDING_CHANGED')
    units={u:_unit(native,u,deadline) for u in UNITS}
    mount=binding['mount']
    with boot._directory(proc) as (proc_fd,proc_identity):
        observer=None
        try:
            observer=os.open(str(os.getpid()),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=proc_fd)
            _need(_namespace(observer,'mnt')==mount['namespace'],'MOUNT_BINDING_CHANGED')
            rows=_mounts(_read(observer,'mountinfo',1048576,deadline))
            selected=[r for r in rows if r['target']==mount['target']]
            _need(len(selected)==1 and all(selected[0][k]==mount[k] for k in ('mountId','device','root','target')) and
                selected[0]['fstype']=='cgroup' and 'name=systemd' in selected[0]['superOptions'] and
                not any(r['target'].startswith(mount['target']+'/') for r in rows),'MOUNT_BINDING_CHANGED')
        finally:
            if observer is not None:os.close(observer)
        directories=[];members=set();paths=[]
        for unit in UNITS:
            path=binding['units'][unit]['cgroupPath'];actual=units[unit]['ControlGroup']
            _need(not actual or actual==path,'PROCESS_SCOPE_CHANGED')
            if path:
                paths.append(path)
                relative=path[len(mount['root']):].lstrip('/') if mount['root']!='/' else path.lstrip('/')
                tree,found=_tree(Path(mount['target'])/relative,mount,deadline,MAX_DIRECTORIES-len(directories))
                directories.extend(tree);members.update(found)
        _need(len(members)<=MAX_PROCESSES,'DERIVED_SOURCE_LIMIT')
        known={row['pid']:row['startTicks'] for row in binding['knownProcesses']}
        _need(len(members|set(known))<=MAX_PROCESSES,'DERIVED_SOURCE_LIMIT')
        processes=[];absent=[]
        for pid in sorted(members|set(known)):
            if allow_bound_process_absence and pid in known and pid not in members:
                # Only native ENOENT of the bound PID directory is absence.
                # A live/reused/migrated PID, permissions or broken content must
                # continue through strict source validation or fail explicitly.
                try:os.stat(str(pid),dir_fd=proc_fd,follow_symlinks=False)
                except FileNotFoundError:
                    absent.append(dict(pid=pid,startTicks=known[pid]));continue
            row=_process(proc_fd,pid,deadline)
            if pid in known:_need(row['startTicks']==known[pid],'PROCESS_IDENTITY_CHANGED')
            group=[g for g in row['cgroups'] if g['hierarchyId']==binding['hierarchyId'] and g['controllers']==['name=systemd']]
            _need(len(group)==1 and any(group[0]['path']==p or group[0]['path'].startswith(p+'/') for p in paths) and
                pid in members,'PROCESS_SCOPE_CHANGED')
            processes.append(row)
        for unit,row in units.items():
            for pid in (row['MainPID'],row['ControlPID']):
                if pid:
                    path=binding['units'][unit]['cgroupPath']
                    process=next((item for item in processes if item['pid']==pid),None)
                    group=[] if process is None else [g for g in process['cgroups'] if
                        g['hierarchyId']==binding['hierarchyId'] and g['controllers']==['name=systemd']]
                    _need(bool(path) and row['ControlGroup']==path and pid in members and len(group)==1 and
                        (group[0]['path']==path or group[0]['path'].startswith(path+'/')),
                        'PROCESS_SCOPE_CHANGED')
        boot._directory_unchanged(proc,proc_identity)
    _time(deadline)
    result=dict(units=units,directories=directories,processes=processes,mount=mount)
    if allow_bound_process_absence:result['boundProcessesAbsent']=absent
    return result


def observe_related_work(native,binding,expected_sha256,*,guard,deadline,proc_directory,require_idle,
                         allow_bound_process_absence=False):
    _need(callable(guard),'DERIVED_GUARD_REQUIRED')
    return _observe_related_work(native,binding,expected_sha256,guard=guard,deadline=deadline,
        proc_directory=proc_directory,require_idle=require_idle,allow_bound_process_absence=allow_bound_process_absence)


def observe_related_work_native(native,binding,expected_sha256,*,deadline,proc_directory,require_idle,
                                allow_bound_process_absence=False):
    """Final native tail: no caller callback or private source content read."""
    return _observe_related_work(native,binding,expected_sha256,guard=None,deadline=deadline,
        proc_directory=proc_directory,require_idle=require_idle,allow_bound_process_absence=allow_bound_process_absence)


def _observe_related_work(native,binding,expected_sha256,*,guard,deadline,proc_directory,require_idle,
                          allow_bound_process_absence=False):
    require_native_runtime();_need(type(require_idle) is bool,'DERIVED_GUARD_REQUIRED')
    _need(type(allow_bound_process_absence) is bool and
        (not allow_bound_process_absence or require_idle), 'DERIVED_ABSENCE_REQUIRES_IDLE')
    _validate(binding,expected_sha256)
    outer=snapshot.observation_deadline.get()
    if outer is not None:deadline=min(deadline,outer)
    _time(deadline);proc=boot._absolute(str(proc_directory));original=snapshot._canonical_bytes(binding)
    try:
        if guard is not None:guard()
        _time(deadline)
        _need(snapshot._canonical_bytes(binding)==original,'DERIVED_BINDING_CHANGED')
        first=_sample(native,binding,proc,deadline,allow_bound_process_absence=allow_bound_process_absence)
        if guard is not None:guard()
        _time(deadline)
        _need(snapshot._canonical_bytes(binding)==original,'DERIVED_BINDING_CHANGED')
        second=_sample(native,binding,proc,deadline,allow_bound_process_absence=allow_bound_process_absence)
        _need(first==second,'DERIVED_SOURCE_CHANGED')
        idle=not second['processes'] and all(row['ActiveState']=='inactive' and row['SubState']=='dead' and
            row['MainPID']==row['ControlPID']==row['Job']==0 for row in second['units'].values())
        _need(not require_idle or idle,'DERIVED_WORK_PENDING')
        _time(deadline)
        return dict(schemaVersion='formal-selected-host-work-observation/v1',bindingSha256=expected_sha256,
            sourceSha256=_sha(snapshot._canonical_bytes(second)),selectedScopeIdleObserved=idle,
            **second,knownProcessesObserved=len(binding['knownProcesses']),fullHostFence=False,
            fullDrain=False,releaseReady=False,productionEvidence=False,serviceActionsPerformed=False,
            coverage='Fixed selected systemd-v1 cgroup process sources only; not all writers or durable business terminals.')
    except (OSError,ValueError,UnicodeError):
        raise FormalSnapshotError('FORMAL_HOST_DERIVED_SOURCE_UNAVAILABLE') from None
