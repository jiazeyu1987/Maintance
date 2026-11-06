"""The same-host source view must be protected by the actual MAIN workflow."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from test_main_retained_authentication import contract
import recovery_main_target as main


def protected(case,tmp_path):
    mount=dict(mountId=2,parentId=1,device='0:1',root='/',mountPoint='/archive-view',
        filesystem='cifs',source='//nas/share',options=['rw','relatime'],superOptions=['rw'])
    case.target['mainApplication']['archiveMountProtection']=dict(schemaVersion='RegisteredArchiveViewProtection/v1',
        mountIdentity=mount,mountProgramPin=dict(path='/usr/bin/mount',bytes=100,sha256='1'*64))
    case.target['dataPaths']=['/target-data']
    case.target['replacement']['stateRoot']=str(tmp_path)
    case.native.source=dict(archiveRoots=['/archive-view/backups/archives'])
    case.native.original=dict(operationId='archive-test')
    case.native.command=lambda *args,**kwargs: None
    return mount


def test_explicit_main_contract_supports_an_independent_same_host_archive_view(contract,tmp_path):
    protected(contract,tmp_path);main.validate(contract.target)
    assert main.archive_view(contract.native) is not None


@pytest.mark.parametrize('change',['source','data','company-share'])
def test_archive_view_cannot_protect_an_unrelated_or_business_mount(contract,tmp_path,change):
    mount=protected(contract,tmp_path)
    if change=='source':contract.native.source['archiveRoots']=['/other/archives']
    elif change=='data':contract.target['dataPaths']=['/archive-view/data']
    else:mount['mountPoint']='/mnt/nas'
    with pytest.raises(Exception,match='ARCHIVE_VIEW_'):main.archive_view(contract.native)


def test_archive_protection_is_installed_before_publication_and_released_after_native_success(contract,tmp_path):
    protected(contract,tmp_path);calls=[]
    archive=SimpleNamespace(install=lambda:calls.append('archive-ro'),release=lambda:calls.append('archive-rw') or {'pin':'archive'})
    ports=SimpleNamespace(install=lambda:calls.append('ports-on'),release=lambda:calls.append('ports-off') or {'pin':'ports'})
    cls=main.guarded_type(object)
    scheduler=SimpleNamespace(release=lambda:calls.append('scheduler-original') or {'pin':'scheduler'})
    with patch.object(main,'archive_view',return_value=archive),patch.object(main,'published_fence',return_value=ports), \
            patch.object(main,'mysql_scheduler',return_value=scheduler):
        cls.replacement_write_fence(contract.native)
        assert calls==['archive-ro','ports-on']
        receipt=cls.replacement_finish(contract.native)
        assert calls==['archive-ro','ports-on','archive-rw','ports-off','scheduler-original']
        assert receipt['archiveViewReleasePin']=={'pin':'archive'}
