"""Preserve original history while admitting one bound native query audit.

Used only before the installation's final, strictly immutable history baseline.
It neither dispatches operations nor changes historical files.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat


def _history_need(value, code):
    if not value:
        raise ValueError(code)


def _history_identity(info):
    return [info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_uid, info.st_gid, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def _history_same_handle(handle, path):
    # This Windows runtime exposes creation time from lstat and change time
    # from fstat as st_ctime. POSIX deployment compares all fields exactly.
    length=8 if os.name=='nt' else 9
    return _history_identity(handle)[:length]==_history_identity(path)[:length]


def _history_pin(path):
    path=Path(path);before=path.lstat()
    _history_need(path.resolve()==path and stat.S_ISREG(before.st_mode) and before.st_nlink==1,
                  'HISTORY_FILE_INVALID')
    digest=hashlib.sha256();size=0
    with path.open('rb') as stream:
        _history_need(_history_same_handle(os.fstat(stream.fileno()),before),'HISTORY_RACE')
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            digest.update(chunk);size+=len(chunk)
        _history_need(_history_same_handle(os.fstat(stream.fileno()),before),'HISTORY_RACE')
    _history_need(_history_identity(path.lstat())==_history_identity(before),'HISTORY_RACE')
    return dict(path=str(path),bytes=size,sha256=digest.hexdigest())


def history_snapshot(scopes,*,baseline=None):
    values={}
    for scope in sorted(map(Path,scopes)):
        _history_need(scope.is_dir() and scope.resolve()==scope,'HISTORY_SCOPE_INVALID')
        for path in [scope,*sorted(scope.rglob('*'))]:
            info=path.lstat()
            _history_need(not stat.S_ISLNK(info.st_mode) and path.resolve()==path,'HISTORY_LINK_REJECTED')
            _history_need(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode),'HISTORY_ENTRY_INVALID')
            previous=None if baseline is None else baseline.get(str(path))
            if stat.S_ISREG(info.st_mode) and previous is not None:
                _history_need(previous['kind']=='file' and previous['identity']==_history_identity(info),'HISTORY_ORIGINAL_CHANGED')
                reference=previous['pin']
            else:reference=None if stat.S_ISDIR(info.st_mode) else _history_pin(path)
            values[str(path)]=dict(kind='directory' if stat.S_ISDIR(info.st_mode) else 'file',identity=_history_identity(info),pin=reference)
    return values


def verify_saved_snapshot(rows,scopes):
    """Reuse saved content pins only while every original filesystem identity holds."""
    paths={}
    for scope in sorted(map(Path,scopes)):
        _history_need(scope.is_dir() and scope.resolve()==scope,'SAVED_HISTORY_SCOPE_INVALID')
        for path in [scope,*sorted(scope.rglob('*'))]:
            paths[str(path)]=path
    _history_need(rows and set(paths)==set(rows),'SAVED_HISTORY_ENTRY_SET_CHANGED')
    for text,path in paths.items():
        info=path.lstat();row=rows[text]
        _history_need(path.resolve()==path and _history_identity(info)==row['identity'],'SAVED_HISTORY_IDENTITY_CHANGED')
        _history_need((row['kind']=='file' and stat.S_ISREG(info.st_mode)) or
                      (row['kind']=='directory' and stat.S_ISDIR(info.st_mode)),'SAVED_HISTORY_KIND_CHANGED')
        if row['kind']=='file':
            _history_need(row['pin']['path']==text and row['pin']['bytes']==info.st_size and
                re.fullmatch('[0-9a-f]{64}',row['pin']['sha256']) is not None,'SAVED_HISTORY_PIN_INVALID')
    return dict(originalEntries=len(rows),contentPinsReusedFromStableIdentity=True,payloadContentReopened=False)


def verify_query_append(before,after,ledger_root,source_ref):
    ledger_root=Path(ledger_root)
    _history_need(before and str(ledger_root) in before,'HISTORY_BEFORE_REQUIRED')
    _history_need(set(before)<=set(after),'HISTORY_ORIGINAL_REMOVED')
    added=set(after)-set(before);parents=set();query_pins=[]
    for text in sorted(added):
        path=Path(text)
        _history_need(after[text]['kind']=='file' and path.parent.name=='queries' and path.parent.parent.parent==ledger_root
            and re.fullmatch('[0-9a-f]{32}\\.json',path.name) is not None and str(path.parent) in before,'HISTORY_APPEND_PATH')
        parents.add(str(path.parent));operation=path.parent.parent
        request_path=operation/'request.json'
        _history_need(str(request_path) in before and before[str(request_path)]==after[str(request_path)],'HISTORY_ORIGINAL_CHANGED')
        request=json.loads(request_path.read_bytes());record=json.loads(path.read_bytes())
        _history_need(set(record)=={'operationId','requestSha256','ownerResultPin','resolutionPins','resourceReleaseError','ownerActualExitCode','result','observedAt'},'HISTORY_QUERY_BINDING')
        digest=hashlib.sha256(json.dumps(request,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        result=record['result']
        _history_need(request['operationId']==operation.name==record['operationId'] and request['sourceConfigRef']==source_ref
            and record['requestSha256']==digest and isinstance(result,dict)
            and result.get('schemaVersion')=='SmallAppBackupUiResult/v1' and result.get('operationId')==operation.name
            and result.get('action')==request['action'] and result.get('state') in ('SUCCEEDED','FAILED'), 'HISTORY_QUERY_BINDING')
        references=[record['ownerResultPin'],*record['resolutionPins']]
        _history_need(all(isinstance(ref,dict) and set(ref)=={'path','bytes','sha256'} and _history_pin(ref['path'])==ref for ref in references),'HISTORY_QUERY_PIN')
        selected_path=operation/'selection.json'
        _history_need(str(selected_path) in before and before[str(selected_path)]==after[str(selected_path)],'HISTORY_QUERY_OWNER_BINDING')
        selected=json.loads(selected_path.read_bytes())
        owner_pin=selected['ownerConfigurationPin']
        _history_need(_history_pin(owner_pin['path'])==owner_pin,'HISTORY_QUERY_OWNER_BINDING')
        owner_config=json.loads(Path(owner_pin['path']).read_bytes())
        if request['action']=='RESTORE':
            _history_need(owner_config.get('schemaVersion')=='RecoveryMinimalConfiguration/v1','HISTORY_QUERY_OWNER_BINDING')
            owner_root=Path(owner_config['operationsRoot'])/operation.name
        else:
            _history_need(owner_config.get('schemaVersion')=='RepositoryMinimumConfiguration/v1','HISTORY_QUERY_OWNER_BINDING')
            owner_root=Path(owner_config['operationRoot'])/hashlib.sha256(operation.name.encode()).hexdigest()
        _history_need(Path(record['ownerResultPin']['path'])==owner_root/'result.json','HISTORY_QUERY_OWNER_BINDING')
        owner=json.loads(Path(record['ownerResultPin']['path']).read_bytes())
        _history_need(owner.get('operationId')==owner.get('requestId')==operation.name and owner.get('action')==request['action']
            and owner.get('actualExitCode')==record['ownerActualExitCode'] and owner.get('state') in ('SUCCEEDED','FAILED_RETAINED','TERMINAL_UNKNOWN'), 'HISTORY_QUERY_BINDING')
        query_pins.append(after[text]['pin'])
    for text,original in before.items():
        current=after[text]
        if text in parents:
            _history_need(original['kind']==current['kind']=='directory' and original['identity'][:6]==current['identity'][:6], 'HISTORY_DIRECTORY_CHANGED')
        else:
            _history_need(original==current,'HISTORY_ORIGINAL_CHANGED')
    return dict(schemaVersion='TaskSourceIdleQueryAudit/v1',sourceConfigRef=source_ref,
        queryPins=query_pins,originalEntryCount=len(before),originalFilesPreserved=True)
