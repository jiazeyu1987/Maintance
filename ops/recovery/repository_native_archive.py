"""Lab archive binding using the unchanged strict production byte reader."""
import hashlib
import importlib.util
import os
from pathlib import Path
import threading

_reader = None


def open_production_backup_archive_for_claim(claim,source_root,expected_entries,attempt_id,
        source_context_sha256,*,release_binding_raw,source_context_raw,installed_context_raw,guard,
        capture_layout=False,capture_recovery=None):
    global _reader
    import formal_boot_state as boot
    import formal_snapshot_linux as snapshot
    from formal_backup_lab import current_authority,validate_original_binding
    from formal_normal_owner import require,strict_document,canonical
    authority=current_authority();authority.check()
    require(type(claim) is snapshot.FormalMaintenanceClaim and callable(guard) and capture_layout is True and
        source_root==str(claim.root) and type(capture_recovery) is tuple and len(capture_recovery)==2 and
        capture_recovery[1] is guard, 'BACKUP_LAB_ARCHIVE_ORIGINAL_REQUIRED')
    validate_original_binding(release_binding_raw,authority,claim)
    require(source_context_raw==authority.read(authority.context['sourceIdentityPin']) and
        installed_context_raw==authority.read(authority.context['executionHostPin']) and
        hashlib.sha256(source_context_raw).hexdigest()==source_context_sha256 and
        len(attempt_id)==64 and all(c in '0123456789abcdef' for c in attempt_id),
        'BACKUP_LAB_ARCHIVE_BINDING_CHANGED')
    recovery=capture_recovery[0]
    require(type(recovery) is dict and recovery.get('state')=='A_ORIGINAL_CAPTURE_AND_RECOVERY_COMPLETED_PENDING_NAS' and
        recovery['sharedCapture']['capturedArchiveEntries'] is expected_entries and
        recovery['sharedCapture']['state']=='A_SHARED_CAPTURED_AND_ORIGINAL_SERVICES_RESTORED_PENDING_REMAINING_OWNER' and
        recovery['originalParticipants']['state']=='ORIGINAL_PARTICIPANTS_RESTORED_INGRESS_RELEASED_PENDING_NAS' and
        all(value.get(key) is False for value in (recovery,recovery['sharedCapture'],recovery['originalParticipants'])
            for key in ('productionEvidence','fullRunnerCompleted','releaseReady','claimReleased')) and
        recovery['nasArchiveVerified'] is False and recovery['originalParticipants']['nasArchiveVerified'] is False,
        'BACKUP_LAB_ARCHIVE_RECOVERY_UNPROVEN')
    helper=Path(__file__).absolute().parent.parent/'release/release_production_backup_input.py'
    approved=[p for p in authority.installation['filePins'] if p['path']==str(helper)]
    require(len(approved)==1,'BACKUP_LAB_ARCHIVE_READER_NOT_INSTALLED')
    raw=authority.read(approved[0])
    if _reader is None:
        spec=importlib.util.spec_from_file_location('repository_lab_approved_byte_reader',helper)
        require(spec is not None and spec.loader is not None,'BACKUP_LAB_ARCHIVE_READER_NOT_INSTALLED')
        _reader=importlib.util.module_from_spec(spec)
        exec(compile(raw,str(helper),'exec'),_reader.__dict__)
        lab_helper=Path(__file__).with_name('repository_native_archive_reader.py')
        lab_approved=[p for p in authority.installation['filePins'] if p['path']==str(lab_helper)]
        require(len(lab_approved)==1,'BACKUP_LAB_ARCHIVE_LAYOUT_NOT_INSTALLED')
        lab_spec=importlib.util.spec_from_file_location('repository_explicit_lab_byte_reader',lab_helper)
        require(lab_spec is not None and lab_spec.loader is not None,'BACKUP_LAB_ARCHIVE_LAYOUT_NOT_INSTALLED')
        lab_module=importlib.util.module_from_spec(lab_spec)
        exec(compile(authority.read(lab_approved[0]),str(lab_helper),'exec'),lab_module.__dict__)
        _reader.ProductionBackupArchiveReader=lab_module.LabBackupArchiveReader
    held=(os.getpid(),threading.get_ident(),claim._fd,boot._signature(os.fstat(claim._fd)),claim._plan)
    release_path=Path(claim.root)/'original-release-binding.json'
    pair=boot._read_secure(release_path,0o600,16384,no_atime=True)
    require(pair[0]==release_binding_raw,'BACKUP_LAB_ARCHIVE_BINDING_CHANGED')
    def checked():
        guard();authority.check();claim.assert_owned()
        require((os.getpid(),threading.get_ident(),claim._fd,boot._signature(os.fstat(claim._fd)),claim._plan)==held and
            not any(e['step']=='released' for e in claim.events) and
            boot._read_secure(release_path,0o600,16384,no_atime=True)==pair and
            boot._signature(release_path.lstat())==pair[1], 'BACKUP_LAB_ARCHIVE_OWNER_CHANGED')
    checked()
    reader=_reader.ProductionBackupArchiveReader(source_root,expected_entries,attempt_id,
        source_context_sha256,guard=checked,capture_layout=True)
    checked();return reader


def serve_production_backup_archive(reader,request_fd,response_fd,*,deadline,idle_seconds=60):
    from formal_normal_owner import require
    require(_reader is not None and type(reader) is _reader.ProductionBackupArchiveReader,
        'BACKUP_LAB_ARCHIVE_READER_NOT_INSTALLED')
    return _reader.serve_production_backup_archive(reader,request_fd,response_fd,deadline=deadline,idle_seconds=idle_seconds)
