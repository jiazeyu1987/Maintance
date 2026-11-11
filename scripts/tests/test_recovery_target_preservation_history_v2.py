"""Offline v2 negative originals; an actual tmpfs observation is NOT CIFS proof.

No successful view observation, producer success, clear grant or historical
restore is synthesized. The positive historical view awaits the real facility.
"""
from copy import deepcopy
import os
from pathlib import Path
import stat

import pytest

from test_recovery_target_preservation_template import (
    publication_case,capture_protocol,case,restore_case,register_v2,original_context,derive)
from test_recovery_target_preservation_view import _ORIGINAL_PARSE_MOUNTINFO,_ORIGINAL_VISIBLE_MOUNT
from recovery_engine import pinned_json,write,utc
from recovery_program_evidence import _Reader
from repository_records import RepositoryError
import recovery_target_preservation as preservation


@pytest.mark.parametrize('problem,code',[
    ('non-cifs','PRESERVATION_WRITE_VIEW_CIFS_REQUIRED'),
    ('derivation-operation','PRESERVATION_READBACK_DERIVATION_CHANGED'),
    ('derived-root','PRESERVATION_READBACK_DERIVATION_CHANGED'),
    ('observation-operation','PRESERVATION_WRITE_VIEW_EVIDENCE_CHANGED'),
])
def test_offline_admission_rejects_wrong_binding_or_real_non_cifs_fact(publication_case,monkeypatch,problem,code):
    h=register_v2(publication_case,monkeypatch)
    with original_context(h) as (native,ctx):
        result=derive(h,native)
        raw=Path('/proc/self/mountinfo').read_text(encoding='utf-8')
        observed=_ORIGINAL_VISIBLE_MOUNT(str(h.repository),_ORIGINAL_PARSE_MOUNTINFO(raw))
        assert observed['filesystem']!='cifs'
        fd=os.open(h.repository,os.O_PATH|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:info=os.fstat(fd)
        finally:os.close(fd)
        value=dict(schemaVersion='MainTargetPreservationWriteViewObservation/v1',
            operationId=h.request['operationId'],targetConfigRef='target57',
            repositoryConfigurationPin=h.v2_repository_pin,executionBindingPin=ctx._binding,
            mountIdentity=observed,rootIdentity=dict(device=info.st_dev,inode=info.st_ino,
                mode=stat.S_IMODE(info.st_mode),uid=info.st_uid,gid=info.st_gid),
            mountInfoLine=next(line for line in raw.splitlines() if line.split(' ',1)[0]==str(observed['mountId'])),
            observedAt=utc())
        if problem=='observation-operation':value['operationId']='another-operation'
        view_pin=write(h.root/'target-preservation'/'write-view.json',value)
        derivation=pinned_json(result['derivationPin'])
        if problem=='derivation-operation':derivation['operationId']='another-operation'
        elif problem=='derived-root':
            config=pinned_json(result['configurationPin']);config['recordRoot']=str(h.case['root']/'wrong-records')
            derivation['configurationPin']=write(Path(result['configurationPin']['path']),config)
        if problem in ('derivation-operation','derived-root'):
            result['derivationPin']=write(Path(result['derivationPin']['path']),derivation)
        reader=_Reader(lambda:None,(ctx._root,ctx._claim))
        with pytest.raises(RepositoryError,match=code):
            preservation._read_v2_admission(reader,policy_pin=h.v2_policy_pin,
                policy=pinned_json(h.v2_policy_pin),repository=pinned_json(h.v2_repository_pin),
                request=deepcopy(h.request),root=ctx._root,binding_pin=ctx._binding,
                derivation_pin=result['derivationPin'],view_pin=view_pin)
        assert not (h.repository/'.repository-control').exists()
