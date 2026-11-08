"""Real tar fixtures exercise bounded legacy material preparation, never restore."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops/spug'))
from legacy_nas_materials import materialize

POINT='archive/PROD/archives/point1'


def pin(path):
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def document(path,value):
    path.write_text(json.dumps(value,sort_keys=True,separators=(',',':')),encoding='utf-8')
    path.chmod(0o600)
    return pin(path)


def fixture(tmp_path,change=None):
    source=tmp_path/'original.tar'
    members=[('private/shared.dat','file',b'alpha'),(POINT,'directory',None),
        (POINT+'/a.dat','link','source/private/shared.dat'),(POINT+'/b.dat','file',b'bravo'),
        ('private/credential','file',b'never-extract'),('python/link','symlink','../../outside')]
    if change:change(members)
    entries=[]
    for name,kind,value in members:
        row=dict(path=name,kind='file' if kind=='link' else kind,signature=[1,2,3,4,5,6])
        if row['kind']=='file':
            raw=b'alpha' if kind=='link' else value
            row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        entries.append(row)
    package=dict(schemaVersion='ProdBackupNasPackage/v1',sourceRoot='/original/source',
        operationId='backup-original',entries=entries,sourceRecaptured=False,restorePerformed=False)
    package_pin=document(tmp_path/'package-manifest.json',package)
    with tarfile.open(source,'w:') as archive:
        raw=Path(package_pin['path']).read_bytes()
        entry=tarfile.TarInfo('package-manifest.json');entry.size=len(raw)
        archive.addfile(entry,io.BytesIO(raw))
        for name,kind,value in members:
            entry=tarfile.TarInfo('source/'+name)
            if kind=='directory':entry.type=tarfile.DIRTYPE
            elif kind=='link':entry.type=tarfile.LNKTYPE;entry.linkname=value
            elif kind=='symlink':entry.type=tarfile.SYMTYPE;entry.linkname=value
            elif kind=='fifo':entry.type=tarfile.FIFOTYPE
            else:entry.size=len(value)
            archive.addfile(entry,io.BytesIO(value) if kind=='file' else None)
    receipt=dict(schemaVersion='ProdBackupNasTransferReceipt/v1',state='SUCCEEDED',
        operationId='backup-original',packageBytes=source.stat().st_size,
        packageSha256=pin(source)['sha256'],manifestSha256=package_pin['sha256'],
        allTarMembersVerified=True,independentAuthenticatedReadback=True,
        sourceRecaptured=False,restorePerformed=False)
    receipt_pin=document(tmp_path/'receipt.json',receipt)
    plan=dict(schemaVersion='LegacyNasArchiveMaterialization/v1',receiptPin=receipt_pin,
        packageManifestPin=package_pin,archivePath=str(source),originalPointRoot='/original/source/'+POINT,
        destinationRoot=str(tmp_path/'materials'),maximumMaterialBytes=1024*1024,minimumFreeBytes=0)
    return plan,receipt,package


def reset_receipt(plan,receipt):
    plan['receiptPin']=document(Path(plan['receiptPin']['path']),receipt)


def test_real_archive_materializes_only_selected_point_and_external_hardlinks(tmp_path):
    plan,_,_=fixture(tmp_path);before=pin(Path(plan['archivePath']))
    result=materialize(plan)
    root=Path(plan['destinationRoot'])
    assert result['state']=='PREPARED' and result['archiveSha256']==before['sha256']
    assert result['selectedFiles']==2 and result['selectedBytes']==10
    assert (root/POINT/'a.dat').read_bytes()==b'alpha'
    assert (root/POINT/'b.dat').read_bytes()==b'bravo'
    assert not (root/'private').exists() and not (root/'python').exists()
    assert pin(Path(plan['archivePath']))==before
    for file in (root/POINT).iterdir():
        assert file.is_file() and not file.is_symlink() and file.stat().st_nlink==1
        if os.name=='posix':assert file.stat().st_mode&0o777==0o600
    assert (root/'materialization-receipt.json').is_file()


def test_same_content_is_materialized_into_independent_files(tmp_path):
    def more(rows):rows.append((POINT+'/c.dat','link','source/private/shared.dat'))
    plan,_,_=fixture(tmp_path,more);materialize(plan)
    first=Path(plan['destinationRoot'])/POINT/'a.dat'
    second=first.with_name('c.dat')
    assert first.read_bytes()==second.read_bytes()==b'alpha'
    assert first.stat().st_ino!=second.stat().st_ino
    assert first.stat().st_nlink==second.stat().st_nlink==1


@pytest.mark.parametrize('field,value',[('state','FAILED'),('allTarMembersVerified',False),
    ('independentAuthenticatedReadback',False),('sourceRecaptured',True),('restorePerformed',True),
    ('operationId','other'),('schemaVersion','unknown')])
def test_invalid_original_receipt_is_refused_before_publication(tmp_path,field,value):
    plan,receipt,_=fixture(tmp_path);receipt[field]=value;reset_receipt(plan,receipt)
    with pytest.raises(ValueError,match='LEGACY_RECEIPT_INVALID'):materialize(plan)
    assert not Path(plan['destinationRoot']).exists()


def test_archive_digest_mismatch_is_not_published(tmp_path):
    plan,receipt,_=fixture(tmp_path);receipt['packageSha256']='0'*64;reset_receipt(plan,receipt)
    with pytest.raises(ValueError,match='LEGACY_ARCHIVE_CHANGED'):materialize(plan)
    assert not Path(plan['destinationRoot']).exists()


def test_external_package_manifest_must_match_original_receipt(tmp_path):
    plan,_,package=fixture(tmp_path);package['sourceRoot']='/another/source'
    plan['packageManifestPin']=document(Path(plan['packageManifestPin']['path']),package)
    with pytest.raises(ValueError,match='LEGACY_MANIFEST_CHANGED'):materialize(plan)
    assert not Path(plan['destinationRoot']).exists()


def test_pinned_document_mutation_is_refused(tmp_path):
    plan,_,_=fixture(tmp_path);Path(plan['receiptPin']['path']).write_bytes(b'{}')
    with pytest.raises(ValueError,match='LEGACY_PIN_CHANGED'):materialize(plan)


def test_actual_payload_tamper_is_not_accepted_with_only_matching_tar_digest(tmp_path):
    plan,receipt,_=fixture(tmp_path)
    path=Path(plan['archivePath']);raw=path.read_bytes();assert raw.count(b'bravo')==1
    path.write_bytes(raw.replace(b'bravo',b'wrong'))
    receipt['packageSha256']=pin(path)['sha256'];reset_receipt(plan,receipt)
    with pytest.raises(ValueError,match='LEGACY_CONTENT_CHANGED'):materialize(plan)
    assert not Path(plan['destinationRoot']).exists()


@pytest.mark.parametrize('kind', ['symlink','fifo'])
def test_selected_nonregular_material_is_refused(tmp_path,kind):
    def change(rows):rows.append((POINT+'/unsafe',kind,'../../outside'))
    plan,_,_=fixture(tmp_path,change)
    with pytest.raises(ValueError,match='LEGACY_SELECTED_TYPE_REFUSED'):materialize(plan)
    assert not Path(plan['destinationRoot']).exists()


@pytest.mark.parametrize('name', ['../escape','/absolute','a/../../escape','a//b','a\\b'])
def test_manifest_path_escape_or_alias_is_refused(tmp_path,name):
    def change(rows):rows.append((name,'file',b'bad'))
    plan,_,_=fixture(tmp_path,change)
    with pytest.raises(ValueError,match='LEGACY_MEMBER_PATH_INVALID'):materialize(plan)
    assert not (tmp_path/'escape').exists() and not Path(plan['destinationRoot']).exists()


def test_duplicate_manifest_members_are_refused(tmp_path):
    def change(rows):rows.append(rows[0])
    plan,_,_=fixture(tmp_path,change)
    with pytest.raises(ValueError,match='LEGACY_MEMBER_DUPLICATE'):materialize(plan)


def test_hardlink_must_reference_matching_registered_regular_content(tmp_path):
    def change(rows):rows[2]=(POINT+'/a.dat','link','source/private/credential')
    plan,_,_=fixture(tmp_path,change)
    with pytest.raises(ValueError,match='LEGACY_CONTENT_REFERENCE_INVALID'):materialize(plan)
    assert not Path(plan['destinationRoot']).exists()


def test_missing_tar_material_is_refused(tmp_path):
    plan,receipt,_=fixture(tmp_path)
    source=Path(plan['archivePath']);copy=tmp_path/'short.tar'
    with tarfile.open(source,'r:') as incoming,tarfile.open(copy,'w:') as outgoing:
        for entry in incoming:
            if entry.name.endswith('/b.dat'):continue
            outgoing.addfile(entry,incoming.extractfile(entry) if entry.isfile() else None)
    plan['archivePath']=str(copy);receipt.update(packageBytes=copy.stat().st_size,packageSha256=pin(copy)['sha256'])
    reset_receipt(plan,receipt)
    with pytest.raises(ValueError,match='LEGACY_MEMBERS_MISSING'):materialize(plan)
    assert not Path(plan['destinationRoot']).exists()


def test_capacity_limit_is_checked_before_creating_staging(tmp_path):
    plan,_,_=fixture(tmp_path);plan['maximumMaterialBytes']=1
    with pytest.raises(ValueError,match='LEGACY_MATERIAL_LIMIT_EXCEEDED'):materialize(plan)
    assert not list(tmp_path.glob('.materials-staging-*'))


def test_existing_destination_is_preserved(tmp_path):
    plan,_,_=fixture(tmp_path);root=Path(plan['destinationRoot']);root.mkdir();(root/'keep').write_bytes(b'held')
    with pytest.raises(ValueError,match='LEGACY_DESTINATION_EXISTS'):materialize(plan)
    assert (root/'keep').read_bytes()==b'held'


def test_destination_alias_is_refused(tmp_path):
    plan,_,_=fixture(tmp_path);plan['destinationRoot']=str(tmp_path/'missing'/'..'/'materials')
    with pytest.raises(ValueError,match='LEGACY_DESTINATION_INVALID'):materialize(plan)


def test_selected_point_must_be_inside_original_archive_tree(tmp_path):
    plan,_,_=fixture(tmp_path);plan['originalPointRoot']='/original/source/private'
    with pytest.raises(ValueError,match='LEGACY_POINT_ROOT_INVALID'):materialize(plan)


@pytest.mark.parametrize('extra', ['duplicate','traversal','symlink','special'])
def test_invalid_tar_header_is_refused_even_with_valid_manifest(tmp_path,extra):
    plan,receipt,_=fixture(tmp_path)
    path=Path(plan['archivePath'])
    with tarfile.open(path,'a:') as archive:
        name='source/'+POINT+'/b.dat'
        entry=tarfile.TarInfo(name if extra!='traversal' else 'source/../escape')
        if extra=='symlink':entry.type=tarfile.SYMTYPE;entry.linkname='../../outside'
        elif extra=='special':entry.type=tarfile.FIFOTYPE
        else:entry.size=5
        archive.addfile(entry,io.BytesIO(b'bravo') if extra in ('duplicate','traversal') else None)
    receipt.update(packageBytes=path.stat().st_size,packageSha256=pin(path)['sha256'])
    reset_receipt(plan,receipt)
    with pytest.raises(ValueError,match='LEGACY_MEMBER_DUPLICATE|LEGACY_MEMBER_PATH_INVALID'):
        materialize(plan)
    assert not Path(plan['destinationRoot']).exists() and not (tmp_path/'escape').exists()


def test_actual_cli_prepares_only_explicit_point(tmp_path):
    plan,_,_=fixture(tmp_path)
    plan_file=tmp_path/'plan.json';document(plan_file,plan)
    tool=Path(__file__).resolve().parents[2]/'ops/spug/legacy_nas_materials.py'
    result=subprocess.run([sys.executable,'-B',str(tool),'--plan',str(plan_file)],capture_output=True,timeout=30)
    assert result.returncode==0,result.stderr.decode('utf-8','replace')
    value=json.loads(result.stdout)
    assert value['state']=='PREPARED' and value['selectedFiles']==2 and value['restorePerformed'] is False
