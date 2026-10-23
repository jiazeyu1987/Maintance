"""Explicit lab capture layout; real owner byte/epoch checks retained.

Derived from the strict production byte reader, with only the approved semantic
capture and capture-input original paths added. No control/credential trees.
"""
import hashlib
import base64
import json
import os
from pathlib import Path
import re
import stat
import sys
import threading


class LabArchiveError(ValueError):
    def __init__(self,code):
        self.code=code
        super().__init__(code)


def require(ok,code):
    if not ok:raise LabArchiveError(code)


def strict_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'ARCHIVE_DUPLICATE_JSON')
            result[key]=value
        return result
    def invalid(_):raise LabArchiveError('ARCHIVE_NONFINITE_JSON')
    return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=invalid)

def digest(raw):return hashlib.sha256(raw).hexdigest()

def signature(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid, s.st_nlink,
            s.st_size, s.st_mtime_ns, s.st_ctime_ns)

class LabBackupArchiveReader:
    """Finite read session inside the still-held native owner's process.

    The actual owner supplies its current guard and keeps its claim open around
    this object. Reading and close ACKs are never capture/NAS/ownership proof.
    No arbitrary path, source write, lock acquisition, release or retry exists.
    """
    SCHEMA='release-production-backup-archive-session/v1'
    CHUNK=1048576
    CAPTURE_REQUIRED_FILES=frozenset({
        'original-release-binding.json', 'capture-recovery-inputs.json', 'semantic-capture/source-inputs.json', 'semantic-capture/supplement.json', 'semantic-capture/object-content-index.json', 'semantic-capture/multipart-observations.json', 'payload/database.sql.gz',
        'payload/original-application-images.tar', 'payload/020-sql.json',
        'payload/040-payload.json', 'payload/050-original-images.json',
        'payload/capture-content-point.json', 'payload/capture-file-inventory.json',
        'recovery-materials/index.json',
        'original-configs/config-capture-stage.json',
        *('original-configs/'+role+'.bin' for role in (
            'application-config','application-env','data-env','application-compose','data-compose'))})
    CAPTURE_PROOF_FILES=frozenset('payload/'+name for name in (
        '006-database-rejection-before.json','010-sql-started.json','011-source-data.json',
        '012-source-data-after.json','013-source-migration-ledger.json',
        '014-source-migration-ledger-after.json','015-source-data-binding.json',
        '016-source-migration-binding.json','018-database-rejection-after.json',
        'database.sql.incremental.raw','database.sql.incremental-scope.json',
        'database-log-mode.json','source-affected-data.json')) | frozenset('original-configs/'+name+'.bin' for name in (
            'application-main','application-dev','frontend-config','runtime-compose'))
    CAPTURE_DIRECTORIES=frozenset({'payload','payload/minio-physical','original-configs','semantic-capture',
        'recovery-materials'})

    @staticmethod
    def _relative(value):
        require(type(value) is str and value and '\\' not in value and
            not any(c in value for c in ':*?"<>|') and not any(ord(c)<32 for c in value) and
            all(p and p not in ('.','..') and p.rstrip(' .')==p for p in value.split('/')),
            'ARCHIVE_PATH_INVALID')
        return value

    @staticmethod
    def _stamp(info):
        return signature(info)

    @staticmethod
    def _plain(info):
        require(not stat.S_ISLNK(info.st_mode) and not (info.st_file_attributes & 0x400
            if sys.platform=='win32' else False),'ARCHIVE_REPARSE_POINT')

    def __init__(self,source_root,expected_entries,attempt_id,source_context_sha256,*,guard,
                 capture_layout=False, verify_content=True):
        require(type(source_root) is str and Path(source_root).is_absolute() and
            type(expected_entries) is dict and expected_entries and callable(guard) and
            type(capture_layout) is bool and
            all(type(v) is str and re.fullmatch('[0-9a-f]{64}',v)
                for v in (attempt_id,source_context_sha256)),'ARCHIVE_SESSION_INVALID')
        self.root=Path(source_root);self.guard=guard;self.thread=threading.get_ident()
        self.attempt=attempt_id;self.context=source_context_sha256
        self.entries=dict(expected_entries);self.pins={};self.handle_pins={};self.ancestors={}
        self.capture_layout=capture_layout;self.capture_children={}
        self.sequence=0;self.closed=False;self.failed=False
        require(self.root.resolve()==self.root,'ARCHIVE_PATH_INVALID')
        for name,value in self.entries.items():
            self._relative(name)
            require(type(value) is str and (value=='directory' or
                re.fullmatch(r'file\|(0|[1-9][0-9]*)\|[0-9a-f]{64}',value)), 'ARCHIVE_TREE_INVALID')
        if capture_layout:
            require(self.CAPTURE_REQUIRED_FILES<=self.entries.keys() and
                all(self.entries[name].startswith('file|') for name in self.CAPTURE_REQUIRED_FILES) and
                all(self.entries.get(name)=='directory' for name in self.CAPTURE_DIRECTORIES),
                'ARCHIVE_CAPTURE_TREE_REQUIRED')
            for name,value in self.entries.items():
                require((name in self.CAPTURE_REQUIRED_FILES|self.CAPTURE_PROOF_FILES and
                    value.startswith('file|')) or
                    (name in self.CAPTURE_DIRECTORIES and value=='directory') or
                    name.startswith(('payload/minio-physical/','semantic-capture/','recovery-materials/')),'ARCHIVE_CAPTURE_PATH_INVALID')
        guard()
        for path in self.root.parents:
            info=path.lstat();self._plain(info);require(stat.S_ISDIR(info.st_mode),'ARCHIVE_ROOT_INVALID')
            self.ancestors[path]=(info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid)
        root_info=self.root.lstat();self._plain(root_info);require(stat.S_ISDIR(root_info.st_mode),'ARCHIVE_ROOT_INVALID')
        self.pins['']=self._stamp(root_info)
        actual={};pending=[self.root]
        while pending:
            directory=pending.pop();guard()
            children=list(directory.iterdir())
            if capture_layout and directory in (self.root,self.root/'payload'):
                # Preserve the actual child set, including excluded live controls.
                # The original owner guard retains their private contents/authority.
                key=directory.relative_to(self.root).as_posix() if directory!=self.root else ''
                self.capture_children[key]={path.relative_to(self.root).as_posix() for path in children}
                if directory==self.root:
                    children=[path for path in children if path.name in
                        ('original-release-binding.json','capture-recovery-inputs.json','payload','original-configs','semantic-capture','recovery-materials')]
                else:
                    children=[path for path in children if path.name!='native-fence']
            for path in children:
                name=path.relative_to(self.root).as_posix();self._relative(name)
                info=path.lstat();self._plain(info);stamp=self._stamp(info);self.pins[name]=stamp
                require(name in self.entries,'ARCHIVE_TREE_CHANGED')
                if stat.S_ISDIR(info.st_mode):actual[name]='directory';pending.append(path)
                else:
                    require(stat.S_ISREG(info.st_mode) and info.st_nlink==1,'ARCHIVE_FILE_UNSAFE')
                    sha=hashlib.sha256();length=0
                    with path.open('rb') as stream:
                        held_stamp=self._stamp(os.fstat(stream.fileno()))
                        # Path and handle APIs can expose different ctime
                        # semantics. Retain BOTH complete baselines; join them
                        # by physical identity and compare each to its own API.
                        require(held_stamp[:8]==stamp[:8],'ARCHIVE_FILE_CHANGED')
                        self.handle_pins[name]=held_stamp
                        if verify_content:
                            while True:
                                guard();chunk=stream.read(self.CHUNK)
                                if not chunk:break
                                sha.update(chunk);length+=len(chunk)
                        require(self._stamp(os.fstat(stream.fileno()))==held_stamp,'ARCHIVE_FILE_CHANGED')
                    actual[name]=('file|'+str(length)+'|'+sha.hexdigest() if verify_content else
                                  'file|'+str(info.st_size)+'|'+self.entries[name].split('|')[2])
        require(actual==self.entries,'ARCHIVE_TREE_CHANGED')
        ordered=sorted(self.entries,key=lambda name:name.encode('utf-16-be'))
        self.tree_digest=hashlib.sha256(b''.join((name+'\0'+self.entries[name]+'\0').encode('utf-8')
            for name in ordered)).hexdigest()
        self.expected_children={name:set() for name,value in self.pins.items() if stat.S_ISDIR(value[2])}
        for name in self.pins:
            if name:
                parent=name.rpartition('/')[0]
                self.expected_children[parent].add(name)
        self.expected_children.update(self.capture_children)
        self._current()

    def _current(self,*,allow_closed=False):
        require(threading.get_ident()==self.thread and (allow_closed or not self.closed) and not self.failed,
                'ARCHIVE_OWNER_THREAD_INVALID')
        self.guard()
        for path,saved in self.ancestors.items():
            info=path.lstat();self._plain(info)
            require((info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid)==saved,'ARCHIVE_ROOT_CHANGED')
        for name,saved in self.pins.items():
            path=self.root/Path(name);info=path.lstat();self._plain(info)
            require(self._stamp(info)==saved,'ARCHIVE_FILE_CHANGED')
            if stat.S_ISDIR(info.st_mode):
                children={p.relative_to(self.root).as_posix() for p in path.iterdir()}
                expected=self.expected_children[name]
                require(children==expected,'ARCHIVE_TREE_CHANGED')
            else:
                with path.open('rb') as stream:
                    require(self._stamp(os.fstat(stream.fileno()))==self.handle_pins[name],'ARCHIVE_FILE_CHANGED')

    def handle(self,request_raw):
        require(not self.closed and not self.failed and threading.get_ident()==self.thread,'ARCHIVE_SESSION_RETAINED')
        try:
            require(type(request_raw) is bytes and 0<len(request_raw)<=8192,'ARCHIVE_REQUEST_INVALID')
            request=strict_json(request_raw)
            fields={'schemaVersion','attemptId','sourceContextSha256','sequence','action'}
            require(type(request) is dict and request.get('action') in ('guard','read-chunk','close') and
                set(request)==(fields|{'relativePath','offset'} if request['action']=='read-chunk' else fields) and
                request['schemaVersion']==self.SCHEMA and request['attemptId']==self.attempt and
                request['sourceContextSha256']==self.context and type(request['sequence']) is int and
                request['sequence']==self.sequence+1,'ARCHIVE_REQUEST_BINDING_INVALID')
            self.sequence=request['sequence'];self._current()
            result=dict(schemaVersion=self.SCHEMA,sequence=self.sequence,attemptId=self.attempt,
                sourceContextSha256=self.context,treeDigest=self.tree_digest,productionEvidence=False)
            if request['action']=='read-chunk':
                name=self._relative(request['relativePath']);value=self.entries.get(name)
                require(type(value) is str and value.startswith('file|') and type(request['offset']) is int and
                    0<=request['offset']<=int(value.split('|')[1]),'ARCHIVE_READ_INVALID')
                path=self.root/Path(name)
                with path.open('rb') as stream:
                    require(self._stamp(os.fstat(stream.fileno()))==self.handle_pins[name],'ARCHIVE_FILE_CHANGED')
                    stream.seek(request['offset']);chunk=stream.read(self.CHUNK)
                    require(len(chunk)==min(self.CHUNK,int(value.split('|')[1])-request['offset']) and
                        self._stamp(os.fstat(stream.fileno()))==self.handle_pins[name],'ARCHIVE_FILE_CHANGED')
                result.update(state='ARCHIVE_CHUNK_READ',relativePath=name,offset=request['offset'],
                    bytesBase64=base64.b64encode(chunk).decode('ascii'),chunkSha256=digest(chunk))
            else:result['state']='OWNER_GUARD_CURRENT' if request['action']=='guard' else 'ARCHIVE_READER_CLOSED_NOT_NAS_PROOF'
            self._current()
            if request['action']=='close':self.closed=True
            return result
        except Exception:
            self.failed=True
            raise
