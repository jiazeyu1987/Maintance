"""An explicit target59-only continuation of the retained empty epoch stage."""
import hashlib
import json
from pathlib import Path
import stat


def epoch_directory_identity(path):
    info=Path(path).lstat()
    return [getattr(info,key) for key in ('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns')]


def epoch_stage_observation(candidate,business_snapshot,fstab_pin,protected_mounts,pid):
    def file_pin(path):
        path=Path(path);raw=path.read_bytes()
        return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    root=Path(candidate['previousCustody']['root']);generation='automatic-'+candidate['sourceCommit'][:7]
    old_owner=json.loads(Path(candidate['oldOwnerPin']['path']).read_bytes())
    old_engine=Path(old_owner['formalModuleDirectory']).parent
    epoch_root=Path(candidate['targetBackupEpochPolicy']['root'])
    absent=[Path(candidate[key]['path']) for key in ('ownerConfigurationPin','controlConfigurationPin','previousReceiptPin')]
    absent.extend(root/'configuration'/name for name in (
        generation+'-previous-unit.txt','installation-'+generation+'.json',
        'installation-audit-'+generation+'-initial','installation-audit-'+generation+'-epoch-resume-1',
        'constructor-preactivation-'+generation+'-initial','constructor-postactivation-'+generation+'-initial',
        'constructor-preactivation-'+generation+'-epoch-resume-1','constructor-postactivation-'+generation+'-epoch-resume-1'))
    absent.append(root/('target-installation.'+generation+'.tmp'))
    dropins=[]
    for base in ('/etc/systemd/system','/run/systemd/system','/usr/lib/systemd/system','/lib/systemd/system'):
        dropins.extend(file_pin(path) for path in (Path(base)/(candidate['service']+'.d')).glob('*'+generation+'*.conf'))
    original_pins=json.dumps(candidate['retainedHistoryPins'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    return dict(host=candidate['host'],targetConfigRef=candidate['targetConfigRef'],service=candidate['service'],sourceCommit=candidate['sourceCommit'],pid=pid,
        controlPin=file_pin(candidate['oldControlPin']['path']),ownerPin=file_pin(candidate['oldOwnerPin']['path']),actualReceiptPin=file_pin(root/'target-installation.json'),
        oldPackagePin=file_pin(old_engine/'package.json'),newPackagePin=file_pin(Path(candidate['engine'])/'package.json'),
        epochRoot=str(epoch_root),epochRootIdentity=epoch_directory_identity(epoch_root),epochEntries=sorted(path.name for path in epoch_root.iterdir()),
        businessSnapshot=business_snapshot,fstabPin=fstab_pin,mounts=protected_mounts,
        absentPaths={str(path):path.exists() or path.is_symlink() for path in absent},newDropins=dropins,
        retainedCount=len(candidate['retainedHistoryPins']),retainedPinsSha256=hashlib.sha256(original_pins).hexdigest())


def load_epoch_resume_proof(path):
    proof=json.loads(Path(path).read_text(encoding='utf-8'))
    refs=proof.get('localEvidencePins',[])
    if len(refs)!=3:
        raise ValueError('EPOCH_RESUME_FAILURE_PROOF_INVALID')
    for index,ref in enumerate(refs):
        raw=Path(ref['path']).read_bytes()
        if len(raw)!=ref['bytes'] or hashlib.sha256(raw).hexdigest()!=ref['sha256']:
            raise ValueError('EPOCH_RESUME_LOCAL_EVIDENCE_CHANGED')
        if index==0 and b'EPOCH_INITIALIZATION_FAILED' not in raw:
            raise ValueError('EPOCH_RESUME_FAILURE_PROOF_INVALID')
    return proof


def verify_empty_epoch_stage_resume(proof,candidate,current):
    if candidate['host']!='172.30.30.59' or candidate.get('targetBackupEpochPolicy') is None:
        raise ValueError('EPOCH_RESUME_TARGET_INVALID')
    if (proof.get('schemaVersion')!='TaskAutomatic59EmptyEpochResume/v1'
            or proof.get('originalErrorCode')!='EPOCH_INITIALIZATION_FAILED'
            or proof.get('originalInternalExceptionUnavailable') is not True
            or len(proof.get('localEvidencePins',[]))!=3):
        raise ValueError('EPOCH_RESUME_FAILURE_PROOF_INVALID')
    observation=proof['observation']
    expected={key:candidate[key] for key in ('host','targetConfigRef','service','sourceCommit')}
    expected.update(pid=candidate['oldControlPid'],controlPin=candidate['oldControlPin'],
                    ownerPin=candidate['oldOwnerPin'],actualReceiptPin=candidate['oldActiveReceiptPin'],
                    epochRoot=candidate['targetBackupEpochPolicy']['root'])
    if any(observation.get(key)!=value for key,value in expected.items()) or current!=observation:
        raise ValueError('EPOCH_RESUME_OBSERVATION_CHANGED')
    root=Path(expected['epochRoot'])
    if (not root.is_dir() or root.resolve()!=root or root.is_symlink()
            or epoch_directory_identity(root)!=observation['epochRootIdentity']
            or stat.S_IMODE(root.stat().st_mode)!=0o700 and root.drive==''
            or list(root.iterdir()) or observation['epochEntries']):
        raise ValueError('EPOCH_RESUME_ROOT_CHANGED')
    if not observation['absentPaths'] or observation['newDropins']:
        raise ValueError('EPOCH_RESUME_ACTIVATION_ALREADY_STARTED')
    for path,exists in observation['absentPaths'].items():
        candidate_path=Path(path)
        if exists or candidate_path.exists() or candidate_path.is_symlink():
            raise ValueError('EPOCH_RESUME_ACTIVATION_ALREADY_STARTED')
    return dict(status='PASS',rootIdentity=observation['epochRootIdentity'],
                originalErrorCode=proof['originalErrorCode'],localEvidencePins=proof['localEvidencePins'])
