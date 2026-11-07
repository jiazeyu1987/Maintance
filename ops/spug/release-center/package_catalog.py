"""Read-only NAS metadata catalogue. No payload hashing, restore or publication."""
from collections import deque
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import threading
import time

KINDS = {'FULL': 'backup-full', 'INCREMENTAL': 'backup-incremental',
         'frontend-patch': 'frontend-patch', 'backend-patch': 'backend-patch'}
STATE_KINDS = {'packages': 'release-full', 'frontendPatches': 'frontend-patch', 'backendPatches': 'backend-patch'}
MAX_METADATA = 64 * 1024 * 1024
MAX_DIRECTORIES = 20000
SHANGHAI = dt.timezone(dt.timedelta(hours=8))


def timestamp(value):
    if not isinstance(value, str): return None
    try:
        parsed = (dt.datetime.strptime(value, '%Y-%m-%d-%H-%M-%S').replace(tzinfo=SHANGHAI)
                  if re.fullmatch(r'\d{4}(?:-\d{2}){5}', value) else dt.datetime.fromisoformat(value.replace('Z', '+00:00')))
        if parsed.tzinfo is None: return None
        return parsed.astimezone(dt.timezone.utc).isoformat()
    except ValueError:
        return None


def native_path(path):
    """Use explicit Win32 long paths, including UNC, without changing archive identity."""
    path = Path(path).absolute()
    if os.name != 'nt' or str(path).startswith('\\\\?\\'): return path
    return Path('\\\\?\\UNC\\'+str(path)[2:] if str(path).startswith('\\\\') else '\\\\?\\'+str(path))


def metadata_bytes(path):
    path = native_path(path)
    if path.resolve() != path.absolute(): raise ValueError('METADATA_LINK_REFUSED')
    if path.stat().st_size > MAX_METADATA: raise ValueError('METADATA_TOO_LARGE')
    with path.open('rb') as stream: raw = stream.read(MAX_METADATA+1)
    if len(raw) > MAX_METADATA: raise ValueError('METADATA_TOO_LARGE')
    return raw


def read_json(path):
    raw = metadata_bytes(path)
    value = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(value, dict): raise ValueError('METADATA_OBJECT_REQUIRED')
    return value, hashlib.sha256(raw).hexdigest()


def pinned_metadata(folder, relative, pin):
    if (not isinstance(pin,dict) or type(pin.get('bytes')) is not int or
            not 0 <= pin['bytes'] <= MAX_METADATA or
            not isinstance(pin.get('sha256'),str) or not re.fullmatch('[a-f0-9]{64}',pin['sha256'])):
        raise ValueError('BACKUP_VERSION_PIN_INVALID')
    raw = metadata_bytes(folder/relative)
    if len(raw) != pin['bytes'] or hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise ValueError('BACKUP_VERSION_PIN_MISMATCH')
    return json.loads(raw.decode('utf-8-sig'))


def payload_pin(manifest, relative):
    matches = [p for p in manifest['payloadRefs'] if isinstance(p.get('path'),str) and p['path'].endswith('/'+relative)]
    if len(matches) != 1: raise ValueError('BACKUP_VERSION_COPY_NOT_PINNED')
    return matches[0]


def backup_program_version(folder, manifest):
    """Only archived, bounded metadata can identify the backed-up program."""
    pins = manifest.get('versionPins',[])
    if not isinstance(pins,list) or len(pins)>32: raise ValueError('BACKUP_VERSION_PIN_INVALID')
    relative = 'recovery-materials/container-inspects.bin'
    runtime_present = native_path(folder/relative).is_file()
    # Old archives can have only tagged image snapshots. A digest-to-version
    # binding additionally requires both metadata files to match manifest pins.
    runtime_pins = [p for p in manifest['payloadRefs'] if isinstance(p.get('path'),str) and p['path'].endswith('/'+relative)]
    if runtime_pins and not runtime_present: raise ValueError('BACKUP_VERSION_RUNTIME_MISSING')
    value = (pinned_metadata(folder,relative,payload_pin(manifest,relative)) if runtime_pins else
             json.loads(metadata_bytes(folder/relative).decode('utf-8-sig')) if runtime_present else [])
    entries = list(value.items()) if isinstance(value,dict) else list(enumerate(value)) if isinstance(value,list) else []
    images = {}; versions = set()
    for key, entry in entries:
        if not isinstance(entry,dict): continue
        config = entry.get('Config',{})
        if not isinstance(config,dict): raise ValueError('BACKUP_VERSION_RUNTIME_INVALID')
        configured = config.get('Image','')
        match = re.search(r':(\d{4}(?:-\d{2}){5})$',configured) if isinstance(configured,str) else None
        if match: versions.add(match[1])
        name = entry.get('Name',key)
        if isinstance(name,str): images[name.lstrip('/')] = {v for v in (configured,entry.get('Image')) if isinstance(v,str)}
    for pin in pins:
        if not isinstance(pin,dict) or not isinstance(pin.get('path'),str): raise ValueError('BACKUP_VERSION_PIN_INVALID')
        # Formal capture makes a deterministic immutable copy of each supplied
        # version document. Never open the original external/private path.
        relative = 'semantic-capture/provided-'+hashlib.sha256(pin['path'].encode('utf-8')).hexdigest()+'.bin'
        copy_pin = payload_pin(manifest,relative)
        if any(copy_pin.get(k)!=pin.get(k) for k in ('bytes','sha256')):
            raise ValueError('BACKUP_VERSION_PIN_MISMATCH')
        document = pinned_metadata(folder,relative,pin)
        tag = document.get('releaseTag') if isinstance(document,dict) else None
        bound = document.get('images') if isinstance(document,dict) else None
        if isinstance(tag,str) and re.fullmatch(r'sha256:[a-f0-9]{64}',tag): continue
        if not isinstance(tag,str): raise ValueError('BACKUP_PROGRAM_VERSION_INVALID')
        tag = tag.rsplit(':',1)[-1]
        if (not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}',tag) or
                (re.fullmatch(r'\d{4}(?:-\d{2}){5}',tag) and not timestamp(tag))):
            raise ValueError('BACKUP_PROGRAM_VERSION_INVALID')
        if runtime_present and (not runtime_pins or not isinstance(bound,dict) or not bound or
                any(not isinstance(name,str) or not isinstance(image,str) or image not in images.get(name.lstrip('/'),set())
                    for name,image in bound.items())):
            raise ValueError('BACKUP_VERSION_RUNTIME_MISMATCH')
        versions.add(tag)
    if len(versions)>1: raise ValueError('BACKUP_PROGRAM_VERSION_CONFLICT')
    basis = ('archive-version-pin+runtime-images' if runtime_present else 'archive-version-pin') if pins else 'archive-image-tag'
    return (next(iter(versions)),basis) if versions else (None,'unrecorded')


def base_row(folder, category):
    return dict(packageId=folder.name, kind='unknown', application='unknown', time=None,
                timeBasis='unknown', servers=[], serverEvidence='unknown', version=None,
                sizeBytes=None, sizeBasis='unknown', status='unknown', manifestSha256=None,
                nasPaths=[str(folder)], registered=False, integrityState=None,
                verification='metadata-only', restoreVerified=False, issues=[], category=category)


def namespace(row, folder, targets):
    """Namespace labels are provenance hints, never a live server observation."""
    names = [s.lower() for s in folder.parts]
    hosts = {str(v.get('host')) for v in targets.values() if isinstance(v, dict) and v.get('host')}
    matches = set()
    for host in hosts:
        suffix = host.rsplit('.', 1)[-1]
        if any(s in (suffix, 'prod'+suffix, 'backup'+suffix, 'test'+suffix) for s in names): matches.add(host)
    if not matches:
        matches = {s for s in names if re.fullmatch(r'\d{2,3}', s)}
    row['servers'] = sorted(matches)
    if matches: row['serverEvidence'] = 'nas-namespace'
    if any('intruoyi' in s or s in ('prod57', 'backup59', 'test58') for s in names): row['application'] = 'intruoyi'
    elif any('smallapp' in s for s in names): row['application'] = 'smallapp'


def backup_row(folder, targets):
    row = base_row(folder, 'backup'); namespace(row, folder, targets)
    manifest, sha = read_json(folder/'.repository/manifest.json')
    if manifest.get('schemaVersion') != 'RepositoryManifest/v1': raise ValueError('BACKUP_SCHEMA_UNKNOWN')
    row.update(packageId=manifest['backupId'], kind=KINDS.get(manifest.get('pointType'), 'unknown'),
               time=timestamp(manifest.get('createdAt')), timeBasis='archive-manifest', manifestSha256=sha,
               status='unpublished')
    refs = manifest.get('payloadRefs', [])
    if not isinstance(refs, list) or any(not isinstance(p,dict) or type(p.get('bytes')) is not int or p['bytes']<0 for p in refs):
        raise ValueError('BACKUP_PAYLOAD_SIZE_INVALID')
    row.update(sizeBytes=sum(p['bytes'] for p in refs), sizeBasis='manifest-payload-bytes')
    point_path = folder/'.repository/point.json'
    if point_path.exists():
        point, _ = read_json(point_path)
        if (point.get('schemaVersion') != 'RepositoryPoint/v1' or point.get('pointType') != manifest.get('pointType') or
                point.get('backupId') != row['packageId'] or point.get('manifestPin', {}).get('sha256') != sha):
            row.update(status='invalid', issues=['BACKUP_POINT_MANIFEST_MISMATCH'])
        else:
            row.update(status='indexed', integrityState=point.get('integrityState'),
                       archivePointPublished=True, restoreAdmission=point.get('blockedReason'))
    try:
        row['version'], row['versionBasis'] = backup_program_version(folder,manifest)
        row['versionStatus'] = 'recorded' if row['version'] else 'unrecorded'
    except (OSError,ValueError,KeyError,TypeError) as exc:
        code = str(exc) if isinstance(exc,ValueError) and re.fullmatch('[A-Z_]+',str(exc)) else 'BACKUP_VERSION_METADATA_UNREADABLE'
        row.update(version=None,versionBasis='invalid',versionStatus='conflict' if code=='BACKUP_PROGRAM_VERSION_CONFLICT' else 'invalid',
                   issues=row['issues']+[code])
    return row


def release_row(folder, targets):
    manifest, sha = read_json(folder/'manifest.json')
    row = base_row(folder, 'release')
    kind = manifest.get('kind')
    if not manifest.get('releaseTag') or not manifest.get('applicationId'): raise ValueError('RELEASE_IDENTITY_MISSING')
    row.update(packageId=manifest['releaseTag'], version=manifest['releaseTag'], application=manifest['applicationId'],
               kind=KINDS.get(kind, 'release-full' if kind is None else 'unknown'),
               time=timestamp(manifest.get('metadata',{}).get('builtAt')) or timestamp(manifest['releaseTag']),
               timeBasis='build-metadata' if manifest.get('metadata',{}).get('builtAt') else 'release-tag',
               manifestSha256=sha, status='indexed', baseVersion=manifest.get('baseReleaseTag'))
    sizes = []; missing = []; directories = {}
    with os.scandir(folder) as listing:
        directories[folder] = {os.path.normcase(e.name): e for e in listing}
    archive = directories[folder].get(os.path.normcase('release.tar'))
    archive_size = None
    if archive is not None:
        info = archive.stat(follow_symlinks=False)
        if archive.is_symlink() or getattr(info,'st_file_attributes',0) & 0x400 or not stat.S_ISREG(info.st_mode):
            raise ValueError('PACKAGE_FILE_PATH_UNSAFE')
        archive_size = info.st_size
    files = manifest.get('files')
    if not isinstance(files,list) or not files: row.update(status='incomplete', issues=['RELEASE_FILES_NOT_RECORDED']); return row
    for item in files:
        name = item.get('name','') if isinstance(item,dict) else ''
        relative = PurePosixPath(name.replace('\\','/'))
        if not name or not relative.parts or relative.is_absolute() or '..' in relative.parts or ':' in name:
            raise ValueError('PACKAGE_FILE_PATH_UNSAFE')
        # NAS publication stores the sealed release.tar and manifest only.
        # Inner members are deliberately not read or extracted by this list.
        if archive_size is not None: continue
        # SMB directory enumeration already carries file attributes and size on
        # Windows. Inspect each parent once, refusing reparse points, instead of
        # resolving and opening every migration/payload file over the network.
        parent = folder
        try:
            for index, part in enumerate(relative.parts):
                if parent not in directories:
                    with os.scandir(parent) as listing:
                        directories[parent] = {os.path.normcase(e.name): e for e in listing}
                entry = directories[parent].get(os.path.normcase(part))
                if entry is None: raise FileNotFoundError(name)
                info = entry.stat(follow_symlinks=False)
                if entry.is_symlink() or getattr(info,'st_file_attributes',0) & 0x400:
                    raise ValueError('PACKAGE_FILE_PATH_UNSAFE')
                if index < len(relative.parts)-1:
                    if not stat.S_ISDIR(info.st_mode): raise FileNotFoundError(name)
                    parent = Path(entry.path)
                else:
                    if not stat.S_ISREG(info.st_mode): raise ValueError('PACKAGE_FILE_PATH_UNSAFE')
                    sizes.append(info.st_size)
        except FileNotFoundError: missing.append(name)
    row.update(sizeBytes=archive_size if archive_size is not None else sum(sizes),
               sizeBasis='sealed-archive-stat' if archive_size is not None else 'manifest-files-stat')
    if missing: row.update(status='incomplete',issues=['PACKAGE_FILES_MISSING'],missingFileCount=len(missing))
    return row


def legacy_backup_row(folder, targets):
    receipt, sha = read_json(folder/'backup.complete.json')
    if receipt.get('schemaVersion') != 'ProdBackupNasTransferReceipt/v1': raise ValueError('BACKUP_SCHEMA_UNKNOWN')
    row = base_row(folder,'backup'); namespace(row,folder,targets)
    row.update(packageId=receipt.get('operationId',folder.name),kind='backup-full',
               time=timestamp(receipt.get('completedAt')),timeBasis='archive-receipt',manifestSha256=sha,
               integrityState=receipt.get('state'),status='indexed')
    # The file name is fixed by this receipt contract. Do not follow a path from metadata.
    path=folder/'backup.tar'
    if path.is_file():row.update(sizeBytes=path.stat().st_size,sizeBasis='archive-file-stat')
    else:row.update(status='incomplete',issues=['PACKAGE_FILES_MISSING'])
    return row


def scan_root(root, targets):
    path=Path(root['path']); category=root['category']; rows=[]; errors=[]; count=0
    if category not in ('backup','release') or not path.is_absolute(): raise ValueError('CATALOG_ROOT_INVALID')
    queue=deque([(path,0)])
    while queue:
        folder,depth=queue.popleft();count+=1
        if count>MAX_DIRECTORIES:
            errors.append(dict(path=str(path),code='DIRECTORY_SCAN_LIMIT'));break
        try:
            if folder.resolve() != folder.absolute(): raise ValueError('SYMLINK_ROOT_REFUSED')
            with os.scandir(folder) as listing: entries=list(listing)
            names={e.name for e in entries}
            candidate=None
            if '.repository' in names:candidate='backup'
            elif 'backup.complete.json' in names:candidate='legacy'
            elif 'manifest.json' in names:candidate='release'
            elif folder.parent.name=='archives':candidate='unknown'
            if candidate:
                try:
                    row=(backup_row(folder,targets) if candidate=='backup' else legacy_backup_row(folder,targets)
                         if candidate=='legacy' else release_row(folder,targets) if candidate=='release' else base_row(folder,category))
                except (OSError,ValueError,KeyError,TypeError) as exc:
                    row=base_row(folder,category);namespace(row,folder,targets)
                    row.update(status='invalid',issues=[str(exc) if isinstance(exc,ValueError) and re.fullmatch('[A-Z_]+',str(exc)) else 'PACKAGE_METADATA_UNREADABLE'])
                rows.append(row);continue
            for entry in entries:
                if entry.is_symlink():
                    errors.append(dict(path=entry.path,code='SYMLINK_SKIPPED'));continue
                if entry.is_dir(follow_symlinks=False) and not entry.name.startswith('.'):
                    if entry.name in ('payload','semantic-capture','recovery-materials','original-configs','verification'):continue
                    if depth>=12:errors.append(dict(path=entry.path,code='DIRECTORY_DEPTH_LIMIT'))
                    else:queue.append((Path(entry.path),depth+1))
        except (OSError,ValueError) as exc:
            errors.append(dict(path=str(folder),code='SOURCE_UNAVAILABLE' if isinstance(exc,OSError) else str(exc)))
    return rows,dict(path=str(path),category=category,status='error' if errors else 'ok',
                     scannedDirectories=count,packageCount=len(rows)),errors


def scan_catalog(roots, state, targets=None):
    targets=targets or {};items=[];sources=[];errors=[];seen=set()
    for root in roots:
        key=os.path.normcase(os.path.abspath(root['path']))
        if key in seen:continue
        seen.add(key)
        rows,source,failures=scan_root(root,targets);items+=rows;sources.append(source);errors+=failures
    by_path={os.path.normcase(os.path.abspath(path)):row for row in items for path in row['nasPaths']}
    for field,kind in STATE_KINDS.items():
        for record in state.get(field,[]):
            path=record.get('nasDirectory')
            if not path:continue
            key=os.path.normcase(os.path.abspath(path));row=by_path.get(key)
            if row is None:
                # Keep registered missing copies visible, but never inspect a path outside configured roots.
                if not any(Path(path).is_relative_to(Path(r['path'])) for r in roots):continue
                row=base_row(Path(path),'release')
                row.update(packageId=record['releaseTag'],kind=kind,application=record.get('applicationId','intruoyi'),
                           version=record['releaseTag'],time=timestamp(record['releaseTag']),timeBasis='release-tag',
                           status='unavailable' if any(s['status']=='error' and Path(path).is_relative_to(Path(s['path'])) for s in sources) else 'missing')
                items.append(row);by_path[key]=row
            row['registered']=True
            if row['manifestSha256'] and record.get('manifestSha256') and row['manifestSha256']!=record['manifestSha256']:
                row.update(status='conflict',issues=row['issues']+['REGISTERED_MANIFEST_MISMATCH'])
            environments=set(record.get('outcomes',{})) | set(record.get('deployments',{}))
            row['servers']=sorted(set(row['servers'])|{targets[e]['host'] for e in environments if e in targets and isinstance(targets[e],dict) and targets[e].get('host')})
            if row['servers']:row['serverEvidence']='release-history'
            row['releaseStage']=record.get('stage')
    grouped={}
    for row in items:
        key=(row['application'],row['kind'],row['packageId'],row['nasPaths'][0] if row['kind']=='unknown' else '')
        if key not in grouped:grouped[key]=row;continue
        prior=grouped[key]
        if row['manifestSha256']!=prior['manifestSha256']:
            prior.update(status='conflict',issues=sorted(set(prior['issues']+['DUPLICATE_ID_DIFFERENT_MANIFEST'])))
        prior['nasPaths']=sorted(set(prior['nasPaths']+row['nasPaths']))
        prior['registered']|=row['registered'];prior['servers']=sorted(set(prior['servers']+row['servers']))
    rows=sorted(grouped.values(),key=lambda r:(r['time'] or '',r['packageId']),reverse=True)
    for row in rows:
        row['checkKey']=hashlib.sha256(json.dumps([row['category'],row['packageId'],row['nasPaths'],row['manifestSha256']],sort_keys=True).encode('utf-8')).hexdigest()
    return dict(schemaVersion='PackageCatalog/v1',observedAt=dt.datetime.now(dt.timezone.utc).isoformat(),
                complete=not errors,items=rows,sources=sources,errors=errors,
                verification='metadata-only',payloadContentVerified=False)


class CatalogCache:
    """One bounded background scan; HTTP never waits on an unavailable SMB server."""
    def __init__(self, executor):
        self.executor=executor;self.lock=threading.Lock();self.value=None;self.running=False;self.finished=0;self.checks={}

    def verify(self,key,force=False):
        with self.lock:
            row=next((r for r in (self.value or {}).get('items',[]) if r.get('checkKey')==key),None)
            if row is None:return 404,dict(error='清单项目已变化或尚未读取，请刷新包清单。')
            result=self.checks.get(key)
            if result is not None and (not force or result['status']=='running'):return 200,dict(result)
            if sum(v['status']=='running' for v in self.checks.values())>=2:
                return 429,dict(error='已有两个包正在检查，请稍后再试。')
            for old in list(self.checks):
                if len(self.checks)<256:break
                if self.checks[old]['status']!='running':del self.checks[old]
            result=dict(schemaVersion='PackagePresence/v1',status='running',checkKey=key,verification='file-existence-only',payloadContentVerified=False)
            self.checks[key]=result
            threading.Thread(target=self.check_files,args=(key,dict(row)),daemon=True,name='readonly-package-presence').start()
            return 200,dict(result)

    def check_files(self,key,row):
        from package_presence import verify_package
        try:result=verify_package(row,self.executor.c.get('packageCatalogRoots',[]))
        except Exception:result=dict(schemaVersion='PackagePresence/v1',status='error',checkKey=key,code='PACKAGE_CHECK_FAILED',verification='file-existence-only',payloadContentVerified=False)
        with self.lock:self.checks[key]=result

    def get(self, force=False):
        with self.lock:
            if not self.running and (force or self.value is None or time.monotonic()-self.finished>60):
                self.running=True
                threading.Thread(target=self.scan,daemon=True,name='readonly-package-catalog').start()
            return dict(self.value or dict(schemaVersion='PackageCatalog/v1',items=[],sources=[],errors=[],
                        complete=False,observedAt=None,verification='metadata-only',payloadContentVerified=False),refreshing=self.running)

    def scan(self):
        try:
            from nas_connection import connect_nas
            config=self.executor.c;roots=config.get('packageCatalogRoots')
            if not isinstance(roots,list) or not roots:raise ValueError('CATALOG_ROOTS_NOT_CONFIGURED')
            connect_nas(config['nasPath'],config.get('nasCredentialsFile'))
            state=self.executor.snapshot()
            value=scan_catalog(roots,state,config.get('targets',{}))
        except Exception as exc:
            code=str(exc) if isinstance(exc,ValueError) and re.fullmatch('[A-Z_]+',str(exc)) else 'CATALOG_SOURCE_READ_FAILED'
            value=dict(schemaVersion='PackageCatalog/v1',items=[],sources=[],errors=[dict(code=code)],complete=False,
                       observedAt=dt.datetime.now(dt.timezone.utc).isoformat(),verification='metadata-only',payloadContentVerified=False)
        with self.lock:self.value=value;self.running=False;self.finished=time.monotonic()
