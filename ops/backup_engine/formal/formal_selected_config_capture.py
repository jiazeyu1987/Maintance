"""Five private original byte copies; no authority, full author or CLI.

Expected identities come from the trusted normal source binding. Repeated
readback is integrity evidence, never proof of continuous host exclusion.
"""
import hashlib
import os
from pathlib import Path
import re
import stat
import threading

from formal_boot_state import _absolute, _directory, _directory_unchanged, _read_secure, _signature
from formal_snapshot_linux import (FormalSnapshotError, require, current_owner_guard,
    safe_file, _canonical_bytes, _sync_directory)

FILES={'application-config':'config/application-instance.yaml','application-env':'.env',
       'data-env':'config/data.env','application-compose':'docker-compose.yml','data-compose':'data-compose.json'}
FIELDS={'path','bytes','sha256','fileSystemId','inode','mtimeNs','ctimeNs'}
CODE='FORMAL_SELECTED_CONFIG_CAPTURE_INVALID'


def observe_selected_config_originals(source_root, *, guard):
    """Independently read fixed original files, before capture or approval.

    The returned map is an observation, not an installation approval. Its
    retained check uses the same owner and reopens every original byte.
    """
    current_owner_guard(guard,code='FORMAL_SELECTED_CONFIG_OWNER_REQUIRED')
    require(os.name=='posix' and os.geteuid()==0,CODE)
    pid=os.getpid();thread=threading.get_ident()
    try:
        source=_absolute(str(source_root))
        with _directory(source,no_atime=True) as (_,source_identity), \
                _directory(source/'config',no_atime=True) as (_,config_identity):
            require(stat.S_IMODE(source.stat().st_mode)==0o700 and
                stat.S_IMODE((source/'config').stat().st_mode)==0o700,CODE)
            held={};observed={};sealed=None
            def current():
                require(os.getpid()==pid and threading.get_ident()==thread,
                    'FORMAL_SELECTED_CONFIG_OWNER_CHANGED')
                current_owner_guard(guard,code='FORMAL_SELECTED_CONFIG_OWNER_REQUIRED')
                _directory_unchanged(source,source_identity)
                _directory_unchanged(source/'config',config_identity)
                if sealed is not None:
                    require(_canonical_bytes(observed)==sealed,'FORMAL_SELECTED_CONFIG_DESCRIPTOR_CHANGED')
            for role,relative in FILES.items():
                current();path=source/relative
                raw,identity=_read_secure(path,0o600,1048576,no_atime=True)
                held[role]=(raw,identity)
                observed[role]=dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                    fileSystemId=identity[0],inode=identity[1],mtimeNs=identity[7],ctimeNs=identity[8])
                require(all(type(observed[role][key]) is int and observed[role][key]>0
                    for key in ('fileSystemId','inode','mtimeNs','ctimeNs')),CODE)
                current()
            sealed=_canonical_bytes(observed)
            require(len(sealed)<=16384,'FORMAL_SELECTED_CONFIG_DESCRIPTOR_LIMIT')
            def retained():
                current()
                for role,relative in FILES.items():
                    current()
                    require(_read_secure(source/relative,0o600,1048576,no_atime=True)==held[role],
                        'FORMAL_SELECTED_CONFIG_SOURCE_CHANGED')
                    current()
                # Guard reads are external observations: terminal identity
                # checks close the gap after the last such callback.
                for role,relative in FILES.items():
                    require(_signature((source/relative).lstat())==held[role][1],
                        'FORMAL_SELECTED_CONFIG_SOURCE_CHANGED')
                _directory_unchanged(source,source_identity)
                _directory_unchanged(source/'config',config_identity)
            retained()
            return observed,retained
    except OSError:
        raise FormalSnapshotError('FORMAL_SELECTED_CONFIG_OBSERVATION_IO_FAILED') from None


def verify_selected_config_originals(source_root, expected_originals, destination, result, *, guard):
    """Return the receipt and a pure identity recheck of this actual readback."""
    current_owner_guard(guard,code='FORMAL_SELECTED_CONFIG_OWNER_REQUIRED')
    require(os.name=='posix' and os.geteuid()==0,CODE)
    try:
        source=_absolute(str(source_root));target=_absolute(str(destination))
        expected_raw=_canonical_bytes(expected_originals);result_raw=_canonical_bytes(result)
        require(type(expected_originals) is dict and set(expected_originals)==set(FILES),CODE)
        require(source!=target and source not in target.parents and target not in source.parents,CODE)
        rows={}
        for role,relative in FILES.items():
            value=expected_originals[role]
            require(type(value) is dict and set(value)==FIELDS and value['path']==str(source/relative) and
                type(value['bytes']) is int and 0<value['bytes']<=1048576 and
                type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}',value['sha256']) and
                all(type(value[key]) is int and value[key]>0 for key in ('fileSystemId','inode','mtimeNs','ctimeNs')),CODE)
            rows[role]=dict(source=value,copyPath=role+'.bin',copySha256=value['sha256'],copyBytes=value['bytes'])
        require(result_raw==_canonical_bytes(dict(state='SELECTED_CONFIG_ORIGINALS_CAPTURED_PENDING_FULL_PROTECTION',
            originals=rows,originalObservationSha256=hashlib.sha256(expected_raw).hexdigest(),
            fullCaptureVerified=False,continuousHostExclusionVerified=False,productionEvidence=False)),CODE)
        with _directory(source,no_atime=True) as (_,source_identity), \
                _directory(source/'config',no_atime=True) as (_,config_identity), \
                _directory(target,no_atime=True) as (_,target_identity):
            require(stat.S_IMODE(source.stat().st_mode)==0o700 and stat.S_IMODE((source/'config').stat().st_mode)==0o700 and
                    stat.S_IMODE(target.stat().st_mode)==0o700,CODE)
            names={role+'.bin' for role in FILES}|{'config-capture-stage.json'}
            def current():
                current_owner_guard(guard,code='FORMAL_SELECTED_CONFIG_OWNER_REQUIRED')
                require(_canonical_bytes(expected_originals)==expected_raw and _canonical_bytes(result)==result_raw,CODE)
                _directory_unchanged(source,source_identity);_directory_unchanged(target,target_identity)
                _directory_unchanged(source/'config',config_identity)
                observed=set()
                for path in target.iterdir():
                    observed.add(path.name);require(len(observed)<=len(names),CODE)
                require(observed==names,'FORMAL_SELECTED_CONFIG_COPY_CHANGED')
            def secure(path):return _read_secure(path,0o600,1048576,no_atime=True)
            current();receipt=secure(target/'config-capture-stage.json')
            require(receipt[0]==result_raw,'FORMAL_SELECTED_CONFIG_COPY_CHANGED')
            held={}
            for role,relative in FILES.items():
                current();path=source/relative;original=secure(path);info=path.stat()
                observed=dict(path=str(path),bytes=len(original[0]),sha256=hashlib.sha256(original[0]).hexdigest(),
                    fileSystemId=info.st_dev,inode=info.st_ino,mtimeNs=info.st_mtime_ns,ctimeNs=info.st_ctime_ns)
                require(observed==expected_originals[role],'FORMAL_SELECTED_CONFIG_SOURCE_CHANGED')
                copied=secure(target/(role+'.bin'));require(copied[0]==original[0],'FORMAL_SELECTED_CONFIG_COPY_CHANGED')
                held[role]=(original,copied);current()
            for role,relative in FILES.items():
                current();original,copied=held[role]
                require(secure(source/relative)==original,'FORMAL_SELECTED_CONFIG_SOURCE_CHANGED')
                require(secure(target/(role+'.bin'))==copied,'FORMAL_SELECTED_CONFIG_COPY_CHANGED')
            current();require(secure(target/'config-capture-stage.json')==receipt,'FORMAL_SELECTED_CONFIG_COPY_CHANGED');current()
            # The owner may still read its pinned inputs. Reuse the identities
            # from these content reads after that observer has finished, without
            # another content read or owner callback opening the same gap.
            file_identities=tuple((source/relative,held[role][0][1],
                target/(role+'.bin'),held[role][1][1]) for role,relative in FILES.items())
            receipt_identity=receipt[1];expected_names=frozenset(names)
            def identity_check():
                try:
                    for original_path,original_identity,copy_path,copy_identity in file_identities:
                        require(_signature(original_path.lstat())==original_identity,
                            'FORMAL_SELECTED_CONFIG_SOURCE_CHANGED')
                        require(_signature(copy_path.lstat())==copy_identity,
                            'FORMAL_SELECTED_CONFIG_COPY_CHANGED')
                    require(_signature((target/'config-capture-stage.json').lstat())==receipt_identity,
                        'FORMAL_SELECTED_CONFIG_COPY_CHANGED')
                    require(frozenset(path.name for path in target.iterdir())==expected_names,
                        'FORMAL_SELECTED_CONFIG_COPY_CHANGED')
                    _directory_unchanged(source,source_identity);_directory_unchanged(source/'config',config_identity)
                    _directory_unchanged(target,target_identity)
                except (OSError,ValueError,TypeError,KeyError,AttributeError,RecursionError):
                    raise FormalSnapshotError('FORMAL_SELECTED_CONFIG_READBACK_FAILED') from None
            identity_check()
            return dict(configReceiptSha256=hashlib.sha256(receipt[0]).hexdigest(),productionEvidence=False),identity_check
    except (OSError,ValueError,TypeError,KeyError,AttributeError,RecursionError):
        raise FormalSnapshotError('FORMAL_SELECTED_CONFIG_READBACK_FAILED') from None


def capture_selected_config_originals(source_root, expected_originals, destination, *, guard):
    """Internal owner supplies original observation and currently held guard."""
    from formal_capture_budget import active_budget
    output_budget=active_budget.get()
    def current():current_owner_guard(guard,code='FORMAL_SELECTED_CONFIG_OWNER_REQUIRED')
    current();require(os.name=='posix' and os.geteuid()==0,CODE)
    try:
        source=_absolute(str(source_root));target=_absolute(str(destination))
        expected_raw=_canonical_bytes(expected_originals)
        require(type(expected_originals) is dict and set(expected_originals)==set(FILES),CODE)
        require(source!=target and source not in target.parents and target not in source.parents,CODE)
        for role,relative in FILES.items():
            value=expected_originals[role]
            require(type(value) is dict and set(value)==FIELDS and value['path']==str(source/relative) and
                type(value['bytes']) is int and 0<value['bytes']<=1048576 and
                type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}',value['sha256']) and
                all(type(value[key]) is int and value[key]>0 for key in ('fileSystemId','inode','mtimeNs','ctimeNs')),CODE)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,RecursionError):
        raise FormalSnapshotError(CODE) from None
    def secure(path):
        try:return _read_secure(path,0o600,1048576,no_atime=True)
        except OSError:raise FormalSnapshotError('FORMAL_SELECTED_CONFIG_FILE_UNAVAILABLE') from None
    held={}
    def read(role):
        current();require(_canonical_bytes(expected_originals)==expected_raw,CODE)
        path=source/FILES[role];raw,identity=secure(path)
        info=path.stat()
        observed=dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
            fileSystemId=info.st_dev,inode=info.st_ino,mtimeNs=info.st_mtime_ns,ctimeNs=info.st_ctime_ns)
        require(observed==expected_originals[role], 'FORMAL_SELECTED_CONFIG_SOURCE_CHANGED')
        current();require(secure(path)==(raw,identity),
            'FORMAL_SELECTED_CONFIG_SOURCE_CHANGED')
        require(role not in held or held[role]==(raw,identity),'FORMAL_SELECTED_CONFIG_SOURCE_CHANGED')
        held[role]=(raw,identity);return raw
    with _directory(source,no_atime=True) as (_,source_identity):
        require(stat.S_IMODE(source.stat().st_mode)==0o700 and stat.S_IMODE((source/'config').stat().st_mode)==0o700,CODE)
        for role in FILES:read(role)
        current();_directory_unchanged(source,source_identity)
        with _directory(target.parent,no_atime=True) as (_,parent_identity):
            safe_file(target);current()
            if output_budget is None:target.mkdir(mode=0o700)
            else:output_budget.mkdir(target)
            _sync_directory(target.parent)
            _directory_unchanged(target.parent,parent_identity)
        with _directory(target,no_atime=True) as (directory,target_identity):
            def record(name,raw):
                _directory_unchanged(target,target_identity)
                if output_budget is not None:
                    with output_budget.open(target/name,'config' if name.endswith('.bin') else 'proof') as output:
                        output.write(raw);output.flush()
                else:
                    descriptor=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=directory)
                    try:
                        offset=0
                        while offset<len(raw):
                            written=os.write(descriptor,raw[offset:]);require(written>0,CODE);offset+=written
                        os.fsync(descriptor)
                    finally:os.close(descriptor)
                os.fsync(directory)
                saved=secure(target/name)
                require(saved[0]==raw,'FORMAL_SELECTED_CONFIG_COPY_CHANGED');return saved
            try:
                copies={};rows={}
                for role in FILES:
                    current();content=read(role);name=role+'.bin';copies[name]=record(name,content)
                    current();rows[role]=dict(source=expected_originals[role],copyPath=name,
                        copySha256=hashlib.sha256(content).hexdigest(),copyBytes=len(content))
                def readback():
                    current();_directory_unchanged(source,source_identity);_directory_unchanged(target,target_identity)
                    for role in FILES:read(role)
                    for name,value in copies.items():
                        current();require(secure(target/name)==value,
                            'FORMAL_SELECTED_CONFIG_COPY_CHANGED')
                    current();_directory_unchanged(source,source_identity);_directory_unchanged(target,target_identity)
                readback()
                result=dict(state='SELECTED_CONFIG_ORIGINALS_CAPTURED_PENDING_FULL_PROTECTION',originals=rows,
                    originalObservationSha256=hashlib.sha256(expected_raw).hexdigest(),
                    fullCaptureVerified=False,continuousHostExclusionVerified=False,productionEvidence=False)
                record('config-capture-stage.json',_canonical_bytes(result));readback();return result
            except Exception as error:
                code=getattr(error,'code','FORMAL_SELECTED_CONFIG_CAPTURE_FAILED')
                if not (type(code) is str and re.fullmatch('FORMAL_[A-Z_]+',code)):code='FORMAL_SELECTED_CONFIG_CAPTURE_FAILED'
                try:record('config-capture-failed.json',_canonical_bytes(dict(state='FAILED_RETAINED',code=code,productionEvidence=False)))
                except Exception:error.evidenceWriteUncertain=True
                raise
