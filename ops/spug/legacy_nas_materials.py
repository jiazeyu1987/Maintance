"""Prepare one original archive point from a pinned legacy NAS package.

No restore, path rewriting, extractall, symlink or hardlink output. A destination
is published only after the complete tar digest and every selected file's
independent readback match the original transfer receipt and package manifest.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile
import tempfile


def need(value, code):
    if not value:
        raise ValueError(code)


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def identity(info):
    # Windows path stat retains creation-time ctime semantics while handle
    # fstat can report change time. Use their explicit common birth-time field;
    # Linux retains the stronger change-time check. Content always has a SHA.
    time_identity=info.st_birthtime_ns if os.name=='nt' else info.st_ctime_ns
    return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,time_identity)


def relative(value):
    need(type(value) is str and value and '\\' not in value and '\x00' not in value and
         not value.startswith('/') and all(part not in ('','.','..') for part in value.split('/')),
         'LEGACY_MEMBER_PATH_INVALID')
    return PurePosixPath(value)


def original_path(value,code):
    need(type(value) is str and value.startswith('/') and '\\' not in value and '\x00' not in value and
         str(PurePosixPath(value))==value and '..' not in PurePosixPath(value).parts,code)
    return PurePosixPath(value)


def open_original(path):
    path=Path(path)
    need(path.is_absolute() and path.resolve()==path and not path.is_symlink(),'LEGACY_INPUT_PATH_INVALID')
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    stream=os.fdopen(fd,'rb')
    try:
        before=os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_nlink==1,'LEGACY_INPUT_TYPE_INVALID')
        need(identity(path.lstat())==identity(before),'LEGACY_INPUT_CHANGED')
        return stream,before
    except BaseException:
        stream.close()
        raise


def pinned_document(pin,limit):
    need(type(pin) is dict and set(pin)=={'path','bytes','sha256'} and
         type(pin['bytes']) is int and 0<=pin['bytes']<=limit and
         type(pin['sha256']) is str and re.fullmatch('[0-9a-f]{64}',pin['sha256']), 'LEGACY_PIN_INVALID')
    with open_original(pin['path'])[0] as stream:
        before=os.fstat(stream.fileno());raw=stream.read(limit+1)
        need(len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'LEGACY_PIN_CHANGED')
        need(identity(before)==identity(os.fstat(stream.fileno()))==identity(Path(pin['path']).lstat()),'LEGACY_INPUT_CHANGED')
    return json.loads(raw),raw


class HashReader:
    def __init__(self,stream):
        self.stream=stream
        self.digest=hashlib.sha256()
        self.count=0

    def read(self,size=-1):
        raw=self.stream.read(size)
        self.digest.update(raw)
        self.count+=len(raw)
        return raw


def write_file(path,stream,size,digest):
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
    actual=hashlib.sha256();count=0
    with os.fdopen(descriptor,'wb') as output:
        while True:
            raw=stream.read(min(1024*1024,size-count+1))
            if not raw:break
            count+=len(raw)
            need(count<=size,'LEGACY_CONTENT_CHANGED')
            actual.update(raw);output.write(raw)
        output.flush();os.fsync(output.fileno())
    need(count==size and actual.hexdigest()==digest,'LEGACY_CONTENT_CHANGED')


def file_digest(path):
    with open_original(path)[0] as stream:
        before=os.fstat(stream.fileno());digest=hashlib.sha256()
        while raw:=stream.read(1024*1024):digest.update(raw)
        need(identity(before)==identity(os.fstat(stream.fileno()))==identity(Path(path).lstat()),'LEGACY_OUTPUT_CHANGED')
    return digest.hexdigest()


def materialize(plan):
    fields={'schemaVersion','receiptPin','packageManifestPin','archivePath','originalPointRoot',
            'destinationRoot','maximumMaterialBytes','minimumFreeBytes'}
    need(type(plan) is dict and set(plan)==fields and plan['schemaVersion']=='LegacyNasArchiveMaterialization/v1',
         'LEGACY_PLAN_INVALID')
    need(type(plan['maximumMaterialBytes']) is int and 0<plan['maximumMaterialBytes']<=1024**4 and
         type(plan['minimumFreeBytes']) is int and 0<=plan['minimumFreeBytes']<=1024**4,'LEGACY_PLAN_LIMIT_INVALID')
    receipt,_=pinned_document(plan['receiptPin'],65536)
    package,package_raw=pinned_document(plan['packageManifestPin'],64*1024*1024)
    need(receipt.get('schemaVersion')=='ProdBackupNasTransferReceipt/v1' and receipt.get('state')=='SUCCEEDED' and
         receipt.get('allTarMembersVerified') is True and receipt.get('independentAuthenticatedReadback') is True and
         receipt.get('sourceRecaptured') is False and receipt.get('restorePerformed') is False and
         package.get('schemaVersion')=='ProdBackupNasPackage/v1' and
         receipt.get('operationId')==package.get('operationId') and
         type(receipt.get('packageBytes')) is int and receipt['packageBytes']>0 and
         type(receipt.get('packageSha256')) is str and re.fullmatch('[0-9a-f]{64}',receipt['packageSha256']),
         'LEGACY_RECEIPT_INVALID')
    need(plan['packageManifestPin']['sha256']==receipt.get('manifestSha256'),'LEGACY_MANIFEST_CHANGED')
    source_root=original_path(package.get('sourceRoot'),'LEGACY_SOURCE_ROOT_INVALID')
    point=original_path(plan['originalPointRoot'],'LEGACY_POINT_ROOT_INVALID')
    need(point.is_relative_to(source_root),'LEGACY_POINT_ROOT_INVALID')
    point=point.relative_to(source_root)
    need(len(point.parts)==4 and point.parts[0]=='archive' and point.parts[2]=='archives' and
         all(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}',item) for item in point.parts),'LEGACY_POINT_ROOT_INVALID')
    entries=package.get('entries')
    need(type(entries) is list and 1<=len(entries)<=200000,'LEGACY_MANIFEST_LIMIT_INVALID')
    registered={};selected={}
    for item in entries:
        need(type(item) is dict,'LEGACY_MANIFEST_ENTRY_INVALID')
        name=relative(item.get('path'));text=str(name)
        need(text not in registered,'LEGACY_MEMBER_DUPLICATE')
        chosen=name==point or name.is_relative_to(point)
        if chosen:need(item.get('kind') in ('file','directory'),'LEGACY_SELECTED_TYPE_REFUSED')
        need(item.get('kind') in ('file','directory','symlink'),'LEGACY_MEMBER_TYPE_REFUSED')
        if item['kind']=='file':
            need(type(item.get('bytes')) is int and item['bytes']>=0 and type(item.get('sha256')) is str and
                 re.fullmatch('[0-9a-f]{64}',item['sha256']),'LEGACY_MANIFEST_ENTRY_INVALID')
            if chosen:selected[text]=item
        registered[text]=item
    need(selected,'LEGACY_SELECTED_FILES_MISSING')
    selected_bytes=sum(row['bytes'] for row in selected.values())
    need(selected_bytes<=plan['maximumMaterialBytes'],'LEGACY_MATERIAL_LIMIT_EXCEEDED')
    destination=Path(plan['destinationRoot'])
    need(destination.is_absolute() and destination.resolve()==destination and destination.parent.is_dir() and
         destination.parent.resolve()==destination.parent and destination!=destination.parent,'LEGACY_DESTINATION_INVALID')
    need(not destination.exists() and not destination.is_symlink(),'LEGACY_DESTINATION_EXISTS')
    for pin in (plan['receiptPin'],plan['packageManifestPin']):
        need(not Path(pin['path']).is_relative_to(destination),'LEGACY_DESTINATION_INVALID')
    archive_path=Path(plan['archivePath'])
    need(not archive_path.is_relative_to(destination),'LEGACY_DESTINATION_INVALID')
    need(shutil.disk_usage(destination.parent).free>=selected_bytes+plan['minimumFreeBytes'],'LEGACY_SPACE_INSUFFICIENT')
    wanted={}
    for name,item in selected.items():wanted.setdefault((item['bytes'],item['sha256']),[]).append(name)
    with open_original(archive_path)[0] as stream:
        before=os.fstat(stream.fileno())
        need(before.st_size==receipt['packageBytes'],'LEGACY_ARCHIVE_CHANGED')
        staging=Path(tempfile.mkdtemp(prefix='.'+destination.name+'-staging-',dir=destination.parent))
        staging.chmod(0o700)
        reader=HashReader(stream);seen=set();written=set();package_seen=False
        with tarfile.open(fileobj=reader,mode='r|') as archive:
            for member in archive:
                member_path=relative(member.name.rstrip('/') if member.isdir() else member.name)
                if str(member_path)=='package-manifest.json':
                    need(not package_seen and member.isfile() and member.size==len(package_raw),'LEGACY_MANIFEST_CHANGED')
                    need(archive.extractfile(member).read(len(package_raw)+1)==package_raw,'LEGACY_MANIFEST_CHANGED')
                    package_seen=True;continue
                need(member_path.parts[0]==source_root.name,'LEGACY_MEMBER_PATH_INVALID')
                if len(member_path.parts)==1:
                    need(member.isdir() and str(member_path) not in seen,'LEGACY_MEMBER_TYPE_REFUSED')
                    seen.add(str(member_path));continue
                name=str(member_path.relative_to(source_root.name))
                need(name not in seen,'LEGACY_MEMBER_DUPLICATE');seen.add(name)
                need(name in registered,'LEGACY_UNREGISTERED_MEMBER')
                item=registered[name]
                if item['kind']=='directory':need(member.isdir(),'LEGACY_MEMBER_TYPE_REFUSED');continue
                if item['kind']=='symlink':need(member.issym(),'LEGACY_MEMBER_TYPE_REFUSED');continue
                need(member.isfile() or member.islnk(),'LEGACY_MEMBER_TYPE_REFUSED')
                key=(item['bytes'],item['sha256'])
                if member.islnk():
                    link=relative(member.linkname)
                    need(link.parts[0]==source_root.name and len(link.parts)>1,'LEGACY_CONTENT_REFERENCE_INVALID')
                    referent=registered.get(str(link.relative_to(source_root.name)))
                    need(type(referent) is dict and referent['kind']=='file' and
                         (referent['bytes'],referent['sha256'])==key,'LEGACY_CONTENT_REFERENCE_INVALID')
                else:
                    need(member.size==item['bytes'],'LEGACY_CONTENT_CHANGED')
                    if key in wanted and key not in written:
                        names=wanted[key];first=staging/names[0]
                        write_file(first,archive.extractfile(member),*key)
                        for name in names[1:]:
                            with first.open('rb') as incoming:write_file(staging/name,incoming,*key)
                        written.add(key)
        # Stream mode can prefetch padding; include every remaining byte as well.
        while reader.read(1024*1024):pass
        need(reader.count==receipt['packageBytes'] and reader.digest.hexdigest()==receipt['packageSha256'],'LEGACY_ARCHIVE_CHANGED')
        need(identity(before)==identity(os.fstat(stream.fileno()))==identity(archive_path.lstat()) and
             archive_path.resolve()==archive_path,'LEGACY_INPUT_CHANGED')
        need(package_seen and set(registered)<=seen and set(wanted)==written,'LEGACY_MEMBERS_MISSING')
    for name,item in selected.items():
        path=staging/name
        need(path.stat().st_size==item['bytes'] and file_digest(path)==item['sha256'],'LEGACY_OUTPUT_CHANGED')
    result=dict(schemaVersion='LegacyNasArchiveMaterializationReceipt/v1',state='PREPARED',
        operationId=receipt['operationId'],archiveSha256=reader.digest.hexdigest(),
        originalReceiptPin=plan['receiptPin'],originalPackageManifestPin=plan['packageManifestPin'],
        originalPointRoot=plan['originalPointRoot'],destinationRoot=str(destination),
        selectedFiles=len(selected),selectedBytes=selected_bytes,independentOutputReadback=True,
        sourceArchiveUnchanged=True,originalPinsRewritten=False,restorePerformed=False,
        completedAt=datetime.datetime.now(datetime.timezone.utc).isoformat())
    with (staging/'materialization-receipt.json').open('xb') as output:
        output.write(canonical(result));output.flush();os.fsync(output.fileno())
    need(not destination.exists() and not destination.is_symlink(),'LEGACY_DESTINATION_EXISTS')
    staging.rename(destination)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True)
    args=parser.parse_args()
    result=materialize(json.loads(Path(args.plan).read_text(encoding='utf-8')))
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
