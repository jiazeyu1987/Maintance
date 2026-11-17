"""Source policy and exact selected archive binding; no Docker or server use."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'ops/recovery'))
from recovery_engine import RecoveryError, canonical, digest, pin
from recovery_program_source import resolve_source_program, validate_source_policy


ROLES = ('backend', 'frontend', 'mysql', 'redis', 'minio')
SOURCE = 'original-59-source'


class SourceProgramTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive_root = self.root/'archives'/'original-point'
        self.metadata = self.archive_root/'.repository'
        self.metadata.mkdir(parents=True)
        self.names = {role: 'original-59-'+role for role in ROLES}
        self.images = {role: 'sha256:'+str(number+1)*64 for number, role in enumerate(ROLES)}
        self.version = self.document(self.archive_root/'images.json',
            dict(images={self.names[role]: self.images[role] for role in ROLES}))
        image_path = self.archive_root/'payload'/'original-application-images.tar'
        image_path.parent.mkdir()
        image_path.write_bytes(b'content-selection-fixture-not-a-Docker-image')
        self.archive = pin(image_path)
        self.policy = dict(schemaVersion='MainProgramSourceArchivePolicy/v1',sourceConfigRef=SOURCE,
            roleVersionBindings=[dict(role=role,versionPath=['images',self.names[role]]) for role in ROLES],
            architecture='amd64',maxArchiveBytes=8*1024*1024,maxImportBytes=9*1024*1024)
        self.owner = dict(sources={SOURCE: dict(recoveryPoints={},repositoryBindingPinsByManifestSha256={})},
                          sourceProgramArchivePolicies={SOURCE: self.policy},targets={})
        self.request = dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId='source-program-unit',
            action='RESTORE',sourceConfigRef=SOURCE,parentChainRef=None,recoveryPointRef='selected-history-point',
            targetConfigRef='registered-main')
        self.guard_calls = 0
        self.refresh()

    def document(self, path, value):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(canonical(value))
        return pin(path)

    def refresh(self, *, payloads=None, version_pins=None, point_extra=None, material_extra=None,
                binding_extra=None, manifest_extra=None):
        payloads = [self.archive] if payloads is None else payloads
        versions = [self.version] if version_pins is None else version_pins
        payloads = payloads + versions
        common = dict(backupId='original-full-point',generationId='original-generation',pointType='FULL',
            parentPointPins=[],commonRecoveryPoint='sha256:'+'d'*64,payloadRefs=payloads)
        manifest = dict(common,schemaVersion='RepositoryManifest/v1',versionPins=versions)
        manifest.update(manifest_extra or {})
        manifest_pin = self.document(self.metadata/'manifest.json',manifest)
        point = dict(common,schemaVersion='RepositoryPoint/v1',manifestPin=manifest_pin)
        point.update(point_extra or {})
        point_pin = self.document(self.metadata/'point.json',point)
        material = dict(schemaVersion='RecoveryMaterial/v1',manifestPin=manifest_pin,pointType='FULL',
            recoveryPoint=common['commonRecoveryPoint'],versionPins=versions,payloadPins=payloads)
        material.update(material_extra or {})
        material_pin = self.document(self.metadata/'material.json',material)
        binding = dict(schemaVersion='RecoveryRepositoryBinding/v1',backupId=common['backupId'],
            generationId=common['generationId'],repositoryPointPin=point_pin,manifestPin=manifest_pin,
            recoveryMaterialPin=material_pin)
        binding.update(binding_extra or {})
        binding_pin = self.document(self.metadata/'binding.json',binding)
        self.point,self.manifest,self.material,self.binding = point,manifest,material,binding
        self.point_pin,self.manifest_pin,self.material_pin,self.binding_pin = point_pin,manifest_pin,material_pin,binding_pin
        source = self.owner['sources'][SOURCE]
        source['recoveryPoints'][self.request['recoveryPointRef']] = point_pin
        source['repositoryBindingPinsByManifestSha256'] = {manifest_pin['sha256']:binding_pin}
        self.chain = [(point_pin,point,material,material_pin)]

    def guard(self):
        self.guard_calls += 1

    def resolve(self, **kwargs):
        return resolve_source_program(self.owner,self.request,self.chain,guard=self.guard,**kwargs)

    def test_exact_policy_returns_detached_value_without_owner_changes(self):
        before = deepcopy(self.owner)
        value = validate_source_policy(self.owner,SOURCE)
        self.assertEqual(self.policy,value)
        value['roleVersionBindings'][0]['versionPath'].append('mutation')
        self.assertEqual(before,self.owner)

    def test_captured_metadata_resolves_without_original_source_file(self):
        source = deepcopy(self.version)
        copied = self.archive_root/'semantic-capture'/('provided-'+hashlib.sha256(source['path'].encode('utf-8')).hexdigest()+'.bin')
        copied.parent.mkdir()
        copied.write_bytes(Path(source['path']).read_bytes())
        self.refresh(payloads=[self.archive,pin(copied)])
        # Model formal capture: original identity remains in versionPins only.
        for value,key in ((self.manifest,'payloadRefs'),(self.point,'payloadRefs'),(self.material,'payloadPins')):
            value[key] = [self.archive,pin(copied)]
        self.manifest_pin=self.document(self.metadata/'manifest.json',self.manifest)
        self.point['manifestPin']=self.manifest_pin
        self.point_pin=self.document(self.metadata/'point.json',self.point)
        self.material['manifestPin']=self.manifest_pin
        self.material_pin=self.document(self.metadata/'material.json',self.material)
        self.binding.update(manifestPin=self.manifest_pin,repositoryPointPin=self.point_pin,recoveryMaterialPin=self.material_pin)
        self.binding_pin=self.document(self.metadata/'binding.json',self.binding)
        self.owner['sources'][SOURCE]['recoveryPoints'][self.request['recoveryPointRef']]=self.point_pin
        self.owner['sources'][SOURCE]['repositoryBindingPinsByManifestSha256']={self.manifest_pin['sha256']:self.binding_pin}
        self.chain=[(self.point_pin,self.point,self.material,self.material_pin)]
        Path(source['path']).unlink()
        self.assertEqual(self.images,self.resolve()['roleImages'])
        copied.write_bytes(b'changed')
        with self.assertRaises(RecoveryError): self.resolve()

    def test_selected_point_binds_five_roles_original_pins_and_explicit_budgets(self):
        result = self.resolve()
        self.assertEqual('MainProgramSourceArchive/v1',result['schemaVersion'])
        self.assertEqual(SOURCE,result['sourceConfigRef'])
        self.assertEqual(self.request['recoveryPointRef'],result['recoveryPointRef'])
        self.assertEqual(self.point['commonRecoveryPoint'],result['recoveryPoint'])
        for key,value in dict(selectedPointPin=self.point_pin,manifestPin=self.manifest_pin,
            repositoryBindingPin=self.binding_pin,materialPin=self.material_pin,archivePin=self.archive).items():
            self.assertEqual(value,result[key])
        self.assertEqual(digest(self.policy),result['policySha256'])
        self.assertEqual(self.images,result['roleImages'])
        self.assertEqual('amd64',result['architecture'])
        self.assertEqual(self.policy['maxArchiveBytes'],result['maxArchiveBytes'])
        self.assertEqual(self.policy['maxImportBytes'],result['maxImportBytes'])
        for role in ROLES:
            self.assertEqual(dict(imageId=self.images[role],versionPin=self.version,
                versionPath=['images',self.names[role]]),result['versionBindings'][role])
        self.assertGreater(self.guard_calls,10)

    def test_result_is_not_mutable_alias_to_owner_or_chain(self):
        before = deepcopy((self.owner,self.request,self.chain))
        result = self.resolve()
        result['archivePin']['sha256']='a'*64
        result['versionBindings']['backend']['versionPath'].append('mutated')
        self.assertEqual(before,(self.owner,self.request,self.chain))

    def test_no_policy_is_explicit_error_and_never_falls_back(self):
        del self.owner['sourceProgramArchivePolicies']
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_POLICY_REQUIRED'):
            self.resolve()

    def test_selected_policy_source_reference_must_match_map_key(self):
        self.policy['sourceConfigRef']='other-source'
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_POLICY_INVALID'):
            self.resolve()

    def test_policy_requires_five_exact_unique_roles(self):
        changes = [lambda value:value['roleVersionBindings'].pop(),
            lambda value:value['roleVersionBindings'].append(deepcopy(value['roleVersionBindings'][0])),
            lambda value:value['roleVersionBindings'][0].update(role='guessed-backend'),
            lambda value:value['roleVersionBindings'][0].update(role='mysql')]
        for change in changes:
            with self.subTest(change=change):
                candidate=deepcopy(self.owner);change(candidate['sourceProgramArchivePolicies'][SOURCE])
                with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_POLICY_INVALID'):
                    validate_source_policy(candidate,SOURCE)

    def test_policy_duplicate_paths_do_not_alias_service_roles(self):
        self.policy['roleVersionBindings'][0]['versionPath']=self.policy['roleVersionBindings'][1]['versionPath']
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_POLICY_INVALID'):
            self.resolve()

    def test_invalid_policy_fields_fail_before_reader_access(self):
        variations = [('schemaVersion','unknown/v1'),('architecture',''),('architecture',True),
            ('maxArchiveBytes',0),('maxArchiveBytes',True),('maxImportBytes',-1),('maxImportBytes',2**63),
            ('maxImportBytes',1.5),('extra','unapproved')]
        for key,value in variations:
            with self.subTest(key=key,value=value):
                owner=deepcopy(self.owner);owner['sourceProgramArchivePolicies'][SOURCE][key]=value
                with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_POLICY_INVALID'):
                    resolve_source_program(owner,self.request,self.chain,guard=self.guard,
                        reader=lambda reference:self.fail('must not read invalid policy'))

    def test_invalid_binding_path_types_and_empty_paths_are_rejected(self):
        for path in ([],(),['images',True],['images',-1],['images',None],[''],['images','a\n']):
            with self.subTest(path=path):
                owner=deepcopy(self.owner)
                owner['sourceProgramArchivePolicies'][SOURCE]['roleVersionBindings'][0]['versionPath']=path
                with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_POLICY_INVALID'):
                    validate_source_policy(owner,SOURCE)

    def test_policy_for_unknown_source_is_not_accepted(self):
        self.owner['sourceProgramArchivePolicies']['unknown']=deepcopy(self.policy)
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_POLICIES_INVALID'):
            self.resolve()

    def test_missing_selected_policy_is_not_other_source_policy(self):
        self.owner['sourceProgramArchivePolicies']={}
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_POLICY_REQUIRED'):
            self.resolve()

    def test_request_must_be_restore_and_bind_a_recovery_point(self):
        for key,value in (('action','FULL'),('recoveryPointRef',None),('targetConfigRef',None)):
            with self.subTest(key=key):
                request=dict(self.request,**{key:value})
                with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_REQUEST_INVALID'):
                    resolve_source_program(self.owner,request,self.chain,guard=self.guard)

    def test_selected_chain_cannot_substitute_another_point(self):
        altered=dict(self.point_pin,path=str(self.root/'another-point.json'))
        self.chain[-1]=(altered,self.point,self.material,self.material_pin)
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_POINT_MISMATCH'):
            self.resolve()

    def test_empty_chain_is_rejected(self):
        self.chain=[]
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_CHAIN_INVALID'):
            self.resolve()

    def test_forged_selected_point_value_is_not_accepted_from_memory(self):
        self.chain[-1]=(self.point_pin,dict(self.point,backupId='forged'),self.material,self.material_pin)
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_POINT_MISMATCH'):
            self.resolve()

    def test_forged_selected_material_value_is_not_accepted_from_memory(self):
        self.chain[-1]=(self.point_pin,self.point,dict(self.material,recoveryPoint='forged'),self.material_pin)
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_MATERIAL_MISMATCH'):
            self.resolve()

    def test_material_pin_must_be_original_repository_binding_pin(self):
        other=self.document(self.metadata/'other-material.json',self.material)
        self.chain[-1]=(self.point_pin,self.point,self.material,other)
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_MATERIAL_MISMATCH'):
            self.resolve()

    def test_repository_binding_cannot_name_another_point(self):
        self.refresh(binding_extra=dict(repositoryPointPin=dict(self.point_pin,sha256='f'*64)))
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_BINDING_MISMATCH'):
            self.resolve()

    def test_manifest_identity_and_payload_must_equal_selected_point(self):
        self.refresh(manifest_extra=dict(backupId='other-backup'))
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_MANIFEST_MISMATCH'):
            self.resolve()

    def test_material_versions_cannot_substitute_different_originals(self):
        other=self.document(self.root/'other-images.json',dict(images={}))
        self.refresh(material_extra=dict(versionPins=[other]))
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_MATERIAL_MISMATCH'):
            self.resolve()

    def test_material_payloads_cannot_hide_archive_selection(self):
        self.refresh(material_extra=dict(payloadPins=[]))
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_MATERIAL_MISMATCH'):
            self.resolve()

    def test_missing_tar_does_not_take_parent_point_archive(self):
        self.refresh(payloads=[])
        self.chain.insert(0,(self.point_pin,dict(self.point,payloadRefs=[self.archive]),self.material,self.material_pin))
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_ARCHIVE_REQUIRED'):
            self.resolve()

    def test_duplicate_tar_pin_is_rejected_even_when_identical(self):
        self.refresh(payloads=[self.archive,self.archive])
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_ARCHIVE_REQUIRED'):
            self.resolve()

    def test_other_point_same_filename_is_not_an_archive_candidate(self):
        other=dict(self.archive,path=str(self.root/'archives'/'other-point'/'payload'/'original-application-images.tar'))
        self.refresh(payloads=[other])
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_ARCHIVE_REQUIRED'):
            self.resolve()

    def test_decoy_same_filename_cannot_coexist_as_second_candidate(self):
        other=dict(self.archive,path=str(self.archive_root/'decoy'/'original-application-images.tar'))
        self.refresh(payloads=[self.archive,other])
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_ARCHIVE_REQUIRED'):
            self.resolve()

    def test_archive_pin_over_budget_is_rejected_without_reading_binary_as_json(self):
        self.policy['maxArchiveBytes']=self.archive['bytes']-1
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_ARCHIVE_LIMIT_EXCEEDED'):
            self.resolve()

    def test_public_document_reader_handles_original_point_larger_than_private_4mib(self):
        self.refresh(point_extra=dict(originalMetadataPadding='x'*(4*1024*1024+1)))
        self.assertGreater(self.point_pin['bytes'],4*1024*1024)
        result=self.resolve()
        self.assertEqual(self.point_pin,result['selectedPointPin'])

    def test_original_pin_sha_or_bytes_change_is_not_ignored_by_lightweight_reader(self):
        Path(self.version['path']).write_bytes(canonical(dict(images={})))
        # STANDARD check_pin rejects the changed original before the source
        # wrapper; lightweight readers reach the wrapper's equivalent check.
        with self.assertRaisesRegex(RecoveryError,r'^(?:PIN_CHANGED|SOURCE_PROGRAM_ORIGINAL_PIN_CHANGED)$'):
            self.resolve()

    def test_original_duplicate_json_keys_are_rejected(self):
        path=Path(self.version['path']);path.write_bytes(b'{"images":{},"images":{}}')
        self.version=pin(path);self.refresh()
        with self.assertRaisesRegex(RecoveryError,'DUPLICATE_JSON_KEY'):
            self.resolve()

    def test_old_names_require_explicit_path_without_current_name_guessing(self):
        self.policy['roleVersionBindings'][0]['versionPath']=['images','current-backend']
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_IMAGE_BINDING_MISMATCH'):
            self.resolve()

    def test_duplicate_version_matches_are_rejected_even_for_same_image_ids(self):
        self.refresh(version_pins=[self.version,self.version])
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_IMAGE_BINDING_MISMATCH'):
            self.resolve()

    def test_original_reader_receives_public_pins_and_guard_wraps_each_read(self):
        calls=[]
        def read(reference):
            before=self.guard_calls
            raw=Path(reference['path']).read_bytes()
            self.assertEqual(reference['bytes'],len(raw))
            self.assertEqual(reference['sha256'],hashlib.sha256(raw).hexdigest())
            calls.append((deepcopy(reference),before))
            return json.loads(raw)
        result=self.resolve(reader=read)
        self.assertEqual(self.images,result['roleImages'])
        self.assertEqual({self.point_pin['path'],self.manifest_pin['path'],self.material_pin['path'],
            self.binding_pin['path'],self.version['path']},{item[0]['path'] for item in calls})
        self.assertEqual(5,len(calls))
        self.assertTrue(all(after[1]>before[1] for before,after in zip(calls,calls[1:])))

    def test_reader_error_and_lost_guard_are_propagated(self):
        def read(reference):
            raise RecoveryError('ORIGINAL_NAS_LEASE_LOST')
        with self.assertRaisesRegex(RecoveryError,'ORIGINAL_NAS_LEASE_LOST'):
            self.resolve(reader=read)
        def lost():
            raise RecoveryError('ORIGINAL_DEADLINE_EXPIRED')
        with self.assertRaisesRegex(RecoveryError,'ORIGINAL_DEADLINE_EXPIRED'):
            resolve_source_program(self.owner,self.request,self.chain,guard=lost)

    def test_resolver_does_not_dispatch_docker_or_use_private_generation_reader(self):
        with patch('subprocess.run',side_effect=AssertionError('unexpected Docker process')), \
             patch('subprocess.Popen',side_effect=AssertionError('unexpected Docker process')), \
             patch('recovery_program_generation.document',side_effect=AssertionError('private reader')):
            self.assertEqual(self.images,self.resolve()['roleImages'])

    def test_non_callable_guard_or_reader_is_rejected(self):
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_GUARD_INVALID'):
            resolve_source_program(self.owner,self.request,self.chain,guard=None)
        with self.assertRaisesRegex(RecoveryError,'SOURCE_PROGRAM_READER_INVALID'):
            self.resolve(reader=True)


if __name__=='__main__':
    unittest.main()
