"""Two bounded read-only samples of one approved v6 boot attempt.

No ownership, locking, action replay, journal write or durability confirmation.
Matching samples are not a proof that a paused/concurrent writer does not exist.
"""
import hashlib
import os
from pathlib import Path
import re
import stat
import time

import formal_boot_state as boot
import formal_snapshot_linux as snapshot
from formal_filesystem_watchdog import require_native_runtime
from formal_s3_export import _strict_json
from formal_snapshot_linux import FormalSnapshotError,require


def _read_at(fd,name,mode,limit,*,optional=False,allow_empty=False):
    try:return boot._read_at(fd,name,mode,limit,no_atime=True,allow_empty=allow_empty)
    except FileNotFoundError:
        require(optional,'FORMAL_BOOT_OBSERVATION_FILE_MISSING')
        return None


def _private(path):
    path=boot._absolute(str(path))
    with boot._directory(path.parent,no_atime=True) as (fd,parents):
        result=_read_at(fd,path.name,0o600,16384)
        boot._directory_unchanged(path.parent,parents)
        return result,parents


def _lock_metadata(fd,name,*,optional=False):
    try:info=os.stat(name,dir_fd=fd,follow_symlinks=False)
    except FileNotFoundError:
        require(optional,'FORMAL_BOOT_OBSERVATION_FILE_MISSING')
        return None
    require(stat.S_ISREG(info.st_mode) and info.st_uid==0 and info.st_nlink==1 and
            stat.S_IMODE(info.st_mode)==0o600,'FORMAL_BOOT_LOCK_UNTRUSTED')
    return boot._signature(info)


def _sample(request,request_path):
    snapshot.observation_timeout(1)
    result={'approval':_private(request_path)}
    root=boot._absolute(request['claimRoot']);target=boot._absolute(request['bootBinding']['path'])
    prefix='boot-'+request['bootBinding']['role']
    with boot._directory(root,no_atime=True) as (fd,parents):
        require(stat.S_IMODE(os.fstat(fd).st_mode)==0o700,'FORMAL_BOOT_DIRECTORY_UNTRUSTED')
        result['claimParents']=parents
        result['ownershipLock']=_lock_metadata(fd,'ownership.lock')
        result['binding']=_read_at(fd,'binding.json',0o600,16384)
        names=[];count=0
        with os.scandir(fd) as entries:
            for entry in entries:
                snapshot.observation_timeout(1);count+=1
                require(count<=256,'FORMAL_BOOT_DIRECTORY_LIMIT')
                if entry.name.startswith('event-'):
                    names.append(entry.name)
                    require(len(names)<=len(snapshot.FormalMaintenanceClaim._steps),
                            'FORMAL_MAINTENANCE_JOURNAL_INVALID')
        names.sort()
        result['events']={}
        for name in names:
            snapshot.observation_timeout(1)
            result['events'][name]=_read_at(fd,name,0o600,16384)
        result['originals']={name:_read_at(fd,name,0o600,16384) for name in sorted(boot.ORIGINALS)}
        result['saved']=_read_at(fd,prefix+'-original-open.json',0o600,4096,optional=True)
        boot._directory_unchanged(root,parents)
    with boot._directory(target.parent,no_atime=True) as (fd,parents):
        result['targetParents']=parents
        result['writerLock']=_lock_metadata(fd,target.name+'.writer.lock',optional=True)
        result['target']=_read_at(fd,target.name,0o644,4096,optional=True,allow_empty=True)
        request_sha=boot._sha(result['approval'][0][0])
        result['pending']=_read_at(fd,'.boot-close-'+request_sha+'.pending',0o644,4096,optional=True,allow_empty=True)
        boot._directory_unchanged(target.parent,parents)
    result['hostBootId']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    snapshot.observation_timeout(1)
    return result


def _fact(value):
    if value is None:return {'exists':False,'sha256':None,'identity':None}
    raw,identity=value
    return {'exists':True,'sha256':boot._sha(raw),'identity':{'device':identity[0],'inode':identity[1]}}


def _interpret(sample,request,approved):
    plan=snapshot._canonical_bytes(request['claimBinding'])
    require(sample['binding'][0]==plan,'FORMAL_MAINTENANCE_BINDING_CHANGED')
    events=snapshot._parse_maintenance_events(plan,((n,v[0]) for n,v in sample['events'].items()),
                                             snapshot.FormalMaintenanceClaim._steps)
    originals=[e for e in events if e['step']=='maintenance-originals-bound']
    require(len(originals)==1 and set(originals[0]['details'])=={'originalFileSha256'} and
            type(originals[0]['details']['originalFileSha256']) is dict and
            set(originals[0]['details']['originalFileSha256'])==boot.ORIGINALS,'FORMAL_BOOT_ORIGINALS_REQUIRED')
    for name,expected in originals[0]['details']['originalFileSha256'].items():
        require(type(expected) is str and re.fullmatch('[a-f0-9]{64}',expected) and
                boot._sha(sample['originals'][name][0])==expected,'FORMAL_BOOT_ORIGINALS_CHANGED')
    selected=request['bootBinding'];prefix='boot-'+selected['role']
    selected_events=[e for e in events if e['step'].startswith(prefix+'-')]
    steps=[prefix+'-bound',prefix+'-close-intent',prefix+'-closed']
    require([e['step'] for e in selected_events]==steps[:len(selected_events)],'FORMAL_BOOT_EVENT_ORDER_INVALID')
    require(not selected_events or sample['saved'] is not None,'FORMAL_BOOT_SAVED_ORIGINAL_INVALID')
    if sample['saved'] is not None:
        raw=sample['saved'][0]
        require(boot._sha(raw)==selected['originalOpenSha256'],'FORMAL_BOOT_SAVED_ORIGINAL_INVALID')
        require(boot._sha(boot._closed_bytes(raw,selected))==selected['closedSha256'],'FORMAL_BOOT_SAVED_ORIGINAL_INVALID')
    details={'requestSha256':approved,'path':selected['path'],'hostBootId':request['hostBootId'],
             'binding':selected,'savedOriginalSha256':selected['originalOpenSha256']}
    published=None
    for event in selected_events:
        expected=details
        if event['step']==steps[2]:
            published=event['details'].get('publishedIdentity')
            require(type(published) is dict and set(published)=={'device','inode'} and
                    all(type(v) is int and v>0 for v in published.values()),'FORMAL_BOOT_EVENT_BINDING_INVALID')
            expected=dict(details,publishedIdentity=published)
        require(event['details']==expected,'FORMAL_BOOT_EVENT_BINDING_INVALID')
        require(event['sequence']>originals[0]['sequence'],'FORMAL_BOOT_EVENT_ORDER_INVALID')
    target=_fact(sample['target']);saved=_fact(sample['saved']);pending=_fact(sample['pending'])
    target['matches']='MISSING' if not target['exists'] else ('ORIGINAL_OPEN' if target['sha256']==selected['originalOpenSha256']
                         else 'EXPECTED_CLOSED' if target['sha256']==selected['closedSha256'] else 'OTHER')
    if target['matches']=='ORIGINAL_OPEN':
        require(boot._sha(boot._closed_bytes(sample['target'][0],selected))==selected['closedSha256'],
                'FORMAL_BOOT_BINDING_CHANGED')
    pending['matchesExpectedClosed']=pending['exists'] and pending['sha256']==selected['closedSha256']
    require(re.fullmatch('[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}',sample['hostBootId']),
            'FORMAL_BOOT_HOST_INVALID')
    tail=plan if not events else list(sample['events'].values())[-1][0]
    return {'state':'BOOT_STATE_OBSERVED_ONLY','requestSha256':approved,'operationId':selected['epoch'],
            'role':selected['role'],'instanceId':selected['instanceId'],
            'transition':('NOT_RECORDED','BOUND_RECORDED','INTENT_RECORDED','CLOSED_RECORDED')[len(selected_events)],
            'journalCount':len(events),'journalTailSha256':hashlib.sha256(tail).hexdigest(),
            'roleEventSequences':[e['sequence'] for e in selected_events],
            'target':target,'savedOriginal':saved,'pending':pending,
            'recordedIdentityMatchesCurrent':None if published is None else published==target['identity'],
            'expectedHostBootId':request['hostBootId'],'observedHostBootId':sample['hostBootId'],
            'hostBootIdMatches':sample['hostBootId']==request['hostBootId'],
            'durableClosedConfirmed':False,'liveAdmissionClosed':False,'operatorPermissionVerified':False,
            'applicationIdentityVerified':False,'productionEvidence':False,'releaseReady':False,
            'serviceActionsPerformed':False,'claimReleased':False,'writerExitConfirmed':False,
            'ownershipAcquired':False,'lockHeldObserved':False}


def observe_approved_boot_state(request_path,expected_sha256):
    require_native_runtime();require(os.geteuid()==0,'FORMAL_BOOT_ROOT_REQUIRED')
    require(type(expected_sha256) is str and re.fullmatch('[a-f0-9]{64}',expected_sha256),'FORMAL_BOOT_APPROVAL_REQUIRED')
    token=None
    try:
        approval=_private(request_path)
        raw=approval[0][0]
        require(boot._sha(raw)==expected_sha256,'FORMAL_BOOT_APPROVAL_CHANGED')
        request=_strict_json(raw);boot._validate_request(request)
        token=snapshot.observation_deadline.set(time.monotonic()+snapshot.observation_timeout(request['totalSeconds']))
        first=_sample(request,request_path)
        second=_sample(request,request_path)
        require(first==second and second['approval']==approval,'FORMAL_BOOT_OBSERVATION_CHANGED')
        result=_interpret(second,request,expected_sha256)
        snapshot.observation_timeout(1)
        return result
    except RecursionError:raise FormalSnapshotError('FORMAL_BOOT_OBSERVATION_PARSE_FAILED') from None
    except OSError:raise FormalSnapshotError('FORMAL_BOOT_OBSERVATION_IO_FAILED') from None
    finally:
        if token is not None:snapshot.observation_deadline.reset(token)
