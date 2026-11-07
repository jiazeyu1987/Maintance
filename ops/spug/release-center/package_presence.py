"""On-demand file existence only: approved catalogue rows, metadata and file attributes."""
import datetime as dt
import os
from pathlib import Path, PurePosixPath
import stat

from package_catalog import native_path, read_json

MAX_FILES=200000
MAX_DIRECTORIES=20000


def relative_name(value):
    if not isinstance(value,str) or not value or '\\' in value or ':' in value:
        raise ValueError('PACKAGE_FILE_PATH_UNSAFE')
    path=PurePosixPath(value)
    if path.is_absolute() or not path.parts or '..' in path.parts:
        raise ValueError('PACKAGE_FILE_PATH_UNSAFE')
    return path.as_posix()


def declared_files(row,folder):
    if row.get('timeBasis')=='archive-manifest':
        manifest,sha=read_json(folder/'.repository/manifest.json')
        if sha!=row['manifestSha256']:raise ValueError('CATALOG_MANIFEST_CHANGED')
        if manifest.get('schemaVersion')!='RepositoryManifest/v1':raise ValueError('PACKAGE_CONTRACT_UNKNOWN')
        origin=PurePosixPath(manifest.get('payloadTreePin',{}).get('path',''))
        if not origin.is_absolute() or '..' in origin.parts or origin.parts[-2:]!=('.repository','payload-tree.json'):
            raise ValueError('PACKAGE_FILE_PATH_UNSAFE')
        files=['.repository/manifest.json','.repository/payload-tree.json']
        if row.get('archivePointPublished'):files.append('.repository/point.json')
        refs=manifest.get('payloadRefs')
        if not isinstance(refs,list) or not refs:raise ValueError('PACKAGE_FILES_NOT_RECORDED')
        for ref in refs:
            if not isinstance(ref,dict) or not isinstance(ref.get('path'),str):raise ValueError('PACKAGE_FILE_PATH_UNSAFE')
            source=PurePosixPath(ref['path'])
            try:relative=source.relative_to(origin.parent.parent).as_posix()
            except ValueError:raise ValueError('PACKAGE_FILE_PATH_UNSAFE') from None
            files.append(relative_name(relative))
    elif row.get('timeBasis')=='archive-receipt':
        _,sha=read_json(folder/'backup.complete.json')
        if sha!=row['manifestSha256']:raise ValueError('CATALOG_MANIFEST_CHANGED')
        files=['backup.complete.json','backup.tar']
    elif row.get('category')=='release':
        manifest,sha=read_json(folder/'manifest.json')
        if sha!=row['manifestSha256']:raise ValueError('CATALOG_MANIFEST_CHANGED')
        files=['manifest.json']
        if row.get('sizeBasis')=='sealed-archive-stat':files.append('release.tar')
        else:
            refs=manifest.get('files')
            if not isinstance(refs,list) or not refs:raise ValueError('PACKAGE_FILES_NOT_RECORDED')
            files.extend(relative_name(ref.get('name') if isinstance(ref,dict) else None) for ref in refs)
    else:raise ValueError('PACKAGE_CONTRACT_UNKNOWN')
    files=list(dict.fromkeys(files))
    if len(files)>MAX_FILES:raise ValueError('PACKAGE_FILE_LIMIT')
    return files


class FileIndex:
    """Enumerate each referenced directory once; never open a payload file."""
    def __init__(self,folder):
        self.folder=native_path(folder);self.directories={}

    def contains(self,name):
        parts=PurePosixPath(relative_name(name)).parts;parent=self.folder
        for index,part in enumerate(parts):
            if parent not in self.directories:
                if len(self.directories)>=MAX_DIRECTORIES:raise ValueError('PACKAGE_DIRECTORY_LIMIT')
                try:
                    with os.scandir(parent) as listing:self.directories[parent]={os.path.normcase(e.name):e for e in listing}
                except FileNotFoundError:self.directories[parent]={}
            entry=self.directories[parent].get(os.path.normcase(part))
            if entry is None:return False
            info=entry.stat(follow_symlinks=False)
            if entry.is_symlink() or getattr(info,'st_file_attributes',0)&0x400:raise ValueError('PACKAGE_FILE_PATH_UNSAFE')
            if index==len(parts)-1:
                if not stat.S_ISREG(info.st_mode):raise ValueError('PACKAGE_FILE_TYPE_INVALID')
                return True
            if not stat.S_ISDIR(info.st_mode):raise ValueError('PACKAGE_FILE_TYPE_INVALID')
            parent=Path(entry.path)
        return False


def check_copy(row,path,roots):
    result=dict(path=str(path),status='error',existingFiles=0,missingFileCount=0,missingFiles=[])
    folder=Path(path)
    approved=next((Path(r['path']) for r in roots if r.get('category')==row.get('category') and
                   folder.is_absolute() and folder.is_relative_to(Path(r['path']))),None)
    if approved is None:return dict(result,code='PACKAGE_PATH_NOT_APPROVED')
    try:
        root=native_path(approved)
        try:info=root.stat()
        except OSError:return dict(result,status='unavailable',code='CATALOG_SOURCE_UNAVAILABLE')
        if not stat.S_ISDIR(info.st_mode):return dict(result,status='unavailable',code='CATALOG_SOURCE_UNAVAILABLE')
        current=native_path(folder)
        if current.resolve()!=current.absolute():raise ValueError('PACKAGE_FILE_PATH_UNSAFE')
        try:info=current.stat()
        except FileNotFoundError:return dict(result,status='missing',code='PACKAGE_DIRECTORY_MISSING',missingFileCount=1,missingFiles=['包目录'])
        if not stat.S_ISDIR(info.st_mode):raise ValueError('PACKAGE_FILE_TYPE_INVALID')
        if not row.get('manifestSha256'):raise ValueError('PACKAGE_CONTRACT_UNKNOWN')
        try:files=declared_files(row,current)
        except FileNotFoundError:return dict(result,status='missing',code='PACKAGE_MANIFEST_MISSING',missingFileCount=1,missingFiles=['包清单文件'])
        index=FileIndex(current)
        for name in files:
            if index.contains(name):result['existingFiles']+=1
            else:
                result['missingFileCount']+=1
                if len(result['missingFiles'])<10:result['missingFiles'].append(name)
        return dict(result,status='missing' if result['missingFileCount'] else 'exists',requiredFiles=len(files))
    except ValueError as exc:
        code=str(exc)
        return dict(result,status='changed' if code=='CATALOG_MANIFEST_CHANGED' else 'unsupported' if code=='PACKAGE_CONTRACT_UNKNOWN' else 'error',code=code)
    except OSError:return dict(result,status='unavailable',code='PACKAGE_FILES_UNREADABLE')
    except (TypeError,KeyError):return dict(result,status='error',code='PACKAGE_METADATA_INVALID')


def verify_package(row,roots):
    copies=[check_copy(row,path,roots) for path in row.get('nasPaths',[])]
    status=next((state for state in ('error','unavailable','changed','unsupported','missing') if any(c['status']==state for c in copies)),'exists' if copies else 'error')
    return dict(schemaVersion='PackagePresence/v1',status=status,checkedAt=dt.datetime.now(dt.timezone.utc).isoformat(),
                checkKey=row.get('checkKey'),existingFiles=sum(c['existingFiles'] for c in copies),
                missingFileCount=sum(c['missingFileCount'] for c in copies),copies=copies,
                verification='file-existence-only',payloadContentVerified=False,restoreVerified=False)
