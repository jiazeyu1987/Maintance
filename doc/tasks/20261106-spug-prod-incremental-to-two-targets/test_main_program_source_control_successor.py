"""Source-only preparation against captured configuration and real release bytes."""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path

import unittest

TASK=Path(__file__).resolve().parent
PRIVATE=Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')


def originals():
    base=json.loads((PRIVATE/'source-upgrade-base-installation-20261111-r2.private.json').read_text(encoding='utf-8'))
    row=base['generation']['selections']['57']['controllers'][0]
    docs=base['generation']['privatePlan']['documentsByHost']['57']
    def document(pin):
        return next(x['value'] for x in docs if x['pin']==pin)
    old=base['generation']['build']
    new=json.loads((TASK/'release-build-ddba4c6.json').read_text(encoding='utf-8'))
    return dict(previous=row,control=document(row['controlConfigurationPin']),owner=document(row['ownerConfigurationPin']),
        previous_build=old,build=new,previous_package_raw=Path(old['variants']['standard']['packagePin']['path']).read_bytes(),
        package_raw=Path(new['variants']['standard']['packagePin']['path']).read_bytes())


def subject():
    return importlib.import_module('main_program_source_control_successor')


def check_actual_packages_make_only_bound_source_candidate(originals):
    result=subject().prepare_candidate(**deepcopy(originals))
    row=result['controller']
    assert row['status']=='BOUND' and row['pid'] is None
    assert row['service']==originals['previous']['service']
    assert row['sourceCommit']==originals['build']['targetCommit']
    assert set(result['changedFiles'])==subject().CHANGED_FILES
    assert result['control']['sourceEpochPolicies']==originals['control']['sourceEpochPolicies']
    assert result['control']['sourceProgramPolicies']==originals['control']['sourceProgramPolicies']
    for key in ('ledgerRoot','registryRoot','listenAddress','listenPort','authCredentialRef','engineSelectionRef'):
        assert result['control'][key]==originals['control'][key]


def check_new_owner_is_exactly_bound_and_all_program_paths_move(originals):
    result=subject().prepare_candidate(**deepcopy(originals));row=result['controller']
    for kind,key in (('owner','ownerConfigurationPin'),('control','controlConfigurationPin')):
        raw=subject().canonical(result[kind]);pin=row[key]
        assert pin['bytes']==len(raw) and pin['sha256']==hashlib.sha256(raw).hexdigest()
    assert result['control']['sourceConfigurations']=={subject().SOURCE:row['ownerConfigurationPin']}
    assert originals['previous']['engine'] not in json.dumps(result['control'])
    assert originals['previous']['engine'] not in json.dumps(result['owner'])
    assert result['owner']['sources'][subject().SOURCE]['configurationPath']==originals['owner']['sources'][subject().SOURCE]['configurationPath']


def check_changed_original_configuration_rejected(originals,field):
    args=deepcopy(originals);key='control' if field=='controlConfigurationPin' else 'owner'
    args[key]['schemaVersion']='unapproved'
    with unittest.TestCase().assertRaisesRegex(ValueError,'ORIGINAL_CONFIGURATION_CHANGED'):
        subject().prepare_candidate(**args)


def check_changed_package_bytes_rejected(originals):
    args=deepcopy(originals);args['package_raw']+=b'changed'
    with unittest.TestCase().assertRaisesRegex(ValueError,'PACKAGE_BUILD_CHANGED'):
        subject().prepare_candidate(**args)


def check_unapproved_candidate_engine_rejected(originals,engine):
    with unittest.TestCase().assertRaisesRegex(ValueError,'ENGINE_SCOPE_INVALID'):
        subject().prepare_candidate(**deepcopy(originals),engine=engine)


def check_third_file_and_changed_capture_program_rejected(originals):
    before={'control/recovery_control_smallapp.py':b'a','control/recovery_control_smallapp_native.py':b'b','formal/capture.py':b'c'}
    after=dict(before);after.update({name:b'new-'+raw for name,raw in before.items()})
    with unittest.TestCase().assertRaisesRegex(ValueError,'PACKAGE_SCOPE_CHANGED'):
        subject().validate_delta(before,after)


def check_originals_not_mutated(originals):
    args=deepcopy(originals);subject().prepare_candidate(**args)
    assert args==originals


def check_changed_source_owner_binding_rejected(originals):
    args=deepcopy(originals)
    args['previous']['ownerConfigurationPin']['sha256']='0'*64
    with unittest.TestCase().assertRaisesRegex(ValueError,'ORIGINAL_CONFIGURATION_CHANGED'):
        subject().prepare_candidate(**args)


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=originals()

    def test_actual_packages(self):check_actual_packages_make_only_bound_source_candidate(self.data)
    def test_owner_binding_and_program_paths(self):check_new_owner_is_exactly_bound_and_all_program_paths_move(self.data)
    def test_original_control_changed(self):check_changed_original_configuration_rejected(self.data,'controlConfigurationPin')
    def test_original_owner_changed(self):check_changed_original_configuration_rejected(self.data,'ownerConfigurationPin')
    def test_package_changed(self):check_changed_package_bytes_rejected(self.data)
    def test_engine_elsewhere(self):check_unapproved_candidate_engine_rejected(self.data,'/tmp/elsewhere')
    def test_engine_relative(self):check_unapproved_candidate_engine_rejected(self.data,'relative/engine')
    def test_engine_parent_alias(self):check_unapproved_candidate_engine_rejected(self.data,'/var/lib/../new-engine')
    def test_third_changed_file(self):check_third_file_and_changed_capture_program_rejected(self.data)
    def test_originals_unchanged(self):check_originals_not_mutated(self.data)
    def test_owner_pin_changed(self):check_changed_source_owner_binding_rejected(self.data)


if __name__=='__main__':unittest.main()
