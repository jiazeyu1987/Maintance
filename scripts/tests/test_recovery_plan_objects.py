"""Real local archived bytes exercise side bindings and ancestor ownership."""
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops'/'recovery'))
from recovery_engine import RecoveryError, canonical, pin, write
from recovery_plan_objects import object_index_chain


def archived_chain(tmp_path):
    scope=write(tmp_path/'scope.json',{'sourceIdentityPin':write(tmp_path/'identity.json',{'sourceFingerprint':'local-source'})})
    policy={'sourceScopePin':scope,'repositoryBindingPinsByManifestSha256':{}}
    chain=[]; prior=None; old=None
    for number in range(2):
        archive=tmp_path/str(number); metadata=archive/'.repository'; metadata.mkdir(parents=True)
        capture=write(archive/'capture.json',dict(sourceIdentity='local-source',backupId=str(number),generationId='generation',
                          commonRecoveryPoint=str(number)))
        payload=archive/'new';payload.write_bytes(b'old' if number == 0 else b'new'); new=pin(payload)
        destination=archive/'semantic-capture'/'objects'/'sha256'/new['sha256'][:2]/(new['sha256']+'.bin')
        destination.parent.mkdir(parents=True);payload.rename(destination);new=pin(destination)
        contents={new['sha256']:new}
        def version(ref, version_id, latest):
            return dict(bucket='bucket',key='key',kind='version',versionId=version_id,isLatest=latest,lastModified='2026-10-10T00:00:00Z',
                        size=ref['bytes'],etag='etag',sha256=ref['sha256'],repositoryPath='objects/sha256/'+ref['sha256'][:2]+'/'+ref['sha256']+'.bin',headers={})
        rows=[version(new,'v'+str(number),number == 0)]
        if number:
            contents[old['sha256']]=old
            rows=[dict(bucket='bucket',key='key',kind='delete-marker',versionId='deleted',isLatest=True,lastModified='2026-10-10T00:00:00Z'),
                  version(new,'v1',False),version(old,'v0',False)]
        inventory=archive/'versions.jsonl'; inventory.write_bytes(b''.join(canonical(row)+b'\n' for row in rows)); inv=pin(inventory)
        observation=dict(bucket='bucket',state='NO_MULTIPART_UPLOAD_OBSERVED',httpStatus=200,rawSha256='a'*64,rawBytes=2,
                         maxUploads=1,uploadCount=0,isTruncated=False,scope='WHOLE_BUCKET_FROM_START')
        multi=write(archive/'multipart-observations.json',dict(state='MULTIPART_EMPTY_POINT_OBSERVATIONS',before=[observation],after=[observation]))
        receipt=write(archive/'export-receipt.json',dict(buckets=['bucket'],state='S3_EXPORTED_PENDING_RESTORE_PROOF',inventoryBytes=inv['bytes'],
            inventorySha256=inv['sha256'],versionCount=len(contents),deleteMarkerCount=number,totalVersionBytes=sum(ref['bytes'] for ref in contents.values()),
            uniqueContentCount=len(contents),multipartObservationsSha256=multi['sha256']))
        payloads=[capture,new,inv,multi,receipt]; manifest=write(metadata/'manifest.json',{'unitPoint':number})
        point=dict(backupId=str(number),generationId='generation',pointType='FULL' if number == 0 else 'INCREMENTAL',manifestPin=manifest,payloadRefs=payloads)
        point_ref=write(metadata/'point.json',point)
        material=dict(sourceScopePin=scope,sourceFingerprint='local-source',recoveryPoint=str(number),objects=dict(capturePointPin=capture,inventoryPin=inv,exportReceiptPin=receipt))
        mat_ref=write(metadata/'material.json',material)
        index=dict(schemaVersion='backup-capture-object-index/v1',backupId=str(number),generationId='generation',sourceIdentity='local-source',
            recoveryPoint=str(number),pointType=point['pointType'],parentExportIndexPin=prior,inventoryPin=inv,exportReceiptPin=receipt,
            contentPins=contents,changedContentSha256=[new['sha256']],repositoryBound=True,manifestPin=manifest)
        index_ref=write(metadata/'index.json',index)
        binding=dict(schemaVersion='RecoveryRepositoryBinding/v1',backupId=str(number),generationId='generation',repositoryPointPin=point_ref,
                     manifestPin=manifest,sourceScopePin=scope,recoveryMaterialPin=mat_ref,objectContentIndexPin=index_ref)
        policy['repositoryBindingPinsByManifestSha256'][manifest['sha256']]=write(metadata/'binding.json',binding)
        chain.append((point_ref,point,material,mat_ref));prior=index_ref;old=new
    return chain,policy


def rewrite_final_index(chain,policy,change):
    from recovery_engine import pinned_json
    binding_ref=policy['repositoryBindingPinsByManifestSha256'][chain[-1][1]['manifestPin']['sha256']]
    binding=pinned_json(binding_ref);index=pinned_json(binding['objectContentIndexPin']);change(index)
    binding['objectContentIndexPin']=write(binding['objectContentIndexPin']['path'],index)
    policy['repositoryBindingPinsByManifestSha256'][chain[-1][1]['manifestPin']['sha256']]=write(binding_ref['path'],binding)


def test_parent_content_and_complete_history_are_consumed_without_recopied_archive(tmp_path):
    chain,policy=archived_chain(tmp_path);indexed=object_index_chain(chain,policy)
    final=indexed[-1]; rows=final[4][('bucket','key')]
    assert [row['versionId'] for row in rows] == ['deleted','v1','v0']
    ancestor=indexed[0][2]['contentPins'];sha=next(iter(ancestor))
    assert final[2]['contentPins'][sha] == ancestor[sha]
    assert not (tmp_path/'1'/'semantic-capture'/'objects'/'sha256'/sha[:2]/(sha+'.bin')).exists()


def test_same_bytes_from_unowned_path_do_not_replace_parent_pin(tmp_path):
    chain,policy=archived_chain(tmp_path)
    indexed=object_index_chain(chain,policy);sha,ref=next(iter(indexed[0][2]['contentPins'].items()))
    other=tmp_path/'unowned';other.write_bytes(Path(ref['path']).read_bytes())
    rewrite_final_index(chain,policy,lambda index:index['contentPins'].update({sha:pin(other)}))
    with pytest.raises(RecoveryError,match='OBJECT_INDEX_PARENT_CONTENT_OWNERSHIP_INVALID'):object_index_chain(chain,policy)


def test_tampered_ancestor_bytes_block_whole_chain(tmp_path):
    chain,policy=archived_chain(tmp_path);indexed=object_index_chain(chain,policy)
    ref=next(iter(indexed[0][2]['contentPins'].values()));Path(ref['path']).write_bytes(b'bad')
    with pytest.raises(RecoveryError,match='PIN_CHANGED'):object_index_chain(chain,policy)


def test_wrong_parent_index_is_rejected(tmp_path):
    chain,policy=archived_chain(tmp_path);rewrite_final_index(chain,policy,lambda index:index.update(parentExportIndexPin=None))
    with pytest.raises(RecoveryError,match='OBJECT_INDEX_PARENT_MISMATCH'):object_index_chain(chain,policy)


def test_binding_is_mandatory_and_frozen_field_set(tmp_path):
    chain,policy=archived_chain(tmp_path);bad=copy.deepcopy(policy);bad.pop('repositoryBindingPinsByManifestSha256')
    with pytest.raises(RecoveryError,match='RECOVERY_REPOSITORY_BINDING_REQUIRED'):object_index_chain(chain,bad)
    from recovery_engine import pinned_json
    ref=policy['repositoryBindingPinsByManifestSha256'][chain[0][1]['manifestPin']['sha256']]
    policy['repositoryBindingPinsByManifestSha256'][chain[0][1]['manifestPin']['sha256']]=write(ref['path'],dict(pinned_json(ref),extra='forbidden'))
    with pytest.raises(RecoveryError,match='RECOVERY_REPOSITORY_BINDING_INVALID'):object_index_chain(chain,policy)


def test_current_w03_binder_source_identity_must_match_material_and_scope(tmp_path):
    chain,policy=archived_chain(tmp_path)
    rewrite_final_index(chain,policy,lambda index:index.update(sourceIdentity='another-source'))
    with pytest.raises(RecoveryError,match='OBJECT_INDEX_REPOSITORY_SOURCE_MISMATCH'):object_index_chain(chain,policy)
