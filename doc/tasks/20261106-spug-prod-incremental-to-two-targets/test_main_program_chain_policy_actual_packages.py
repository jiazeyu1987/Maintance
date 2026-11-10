"""The approved policy cases against ONE explicit, already frozen package.

Run only through run_main_program_chain_policy_verification. No builder fixture
is used. The boundary scenarios call the original reviewed assertions.
"""
import hashlib
import importlib
import os
from pathlib import Path
import sys

import pytest

from main_program_chain_policy_evidence import MODULES, VARIANTS, archive_files, need

ROOT = Path(__file__).resolve().parents[3]
MODE = os.environ.get('CHAIN_POLICY_VARIANT')
need(MODE in VARIANTS and os.environ.get('CHAIN_POLICY_PACKAGE_ROOT') and
     os.environ.get('CHAIN_POLICY_PACKAGE_ARCHIVE'),'ACTUAL_PACKAGE_SELECTION_REQUIRED')
ENGINE = Path(os.environ['CHAIN_POLICY_PACKAGE_ROOT']).resolve()
ARCHIVE = Path(os.environ['CHAIN_POLICY_PACKAGE_ARCHIVE']).resolve()
ORIGINAL = ARCHIVE.read_bytes()
MEMBERS = archive_files(ORIGINAL,package=True)
need(len(MEMBERS) == VARIANTS[MODE],'ACTUAL_PACKAGE_MEMBER_COUNT')
for name,raw in MEMBERS.items():need((ENGINE/name).read_bytes() == raw,'ACTUAL_PACKAGE_EXTRACT_CHANGED')
sys.path[:0] = [str(ENGINE/p) for p in ('common','control','formal')]
for name in ('repository_records','repository_minimal','recovery_control_smallapp_native','recovery_control_incremental_plan'):
    module = importlib.import_module(name)
    need(Path(module.__file__).resolve().is_relative_to(ENGINE),'ACTUAL_PACKAGE_MODULE_SHADOWED')

# The original module's builder fixture remains unregistered here. Its real
# metadata planner scenarios retain the same assertions and explicit boundaries.
sys.path.append(str(ROOT/'scripts/tests'))
policy = importlib.import_module('test_incremental_chain_policy_admission')
for name,value in vars(policy).items():
    if name.startswith('test_') and callable(value) and name not in (
            'test_actual_packaged_constructor_and_publish_stop_before_capture',
            'test_standard_package_retains_the_original_final_age_check'):
        globals()[name] = value


@pytest.fixture(scope='module')
def selected_package(tmp_path_factory):
    folder = tmp_path_factory.mktemp('explicit-frozen-package')
    destination = folder/('backup-restore-'+MODE+'.tgz')
    with destination.open('xb') as output:output.write(ORIGINAL)
    assert hashlib.sha256(destination.read_bytes()).digest() == hashlib.sha256(ORIGINAL).digest()
    return folder


@pytest.mark.parametrize('scenario',['expired','at-limit','future','invalid-policy','valid','next-at-limit',
                                     'during-preflight','during-config','full'])
def test_exact_frozen_constructor_and_publish(scenario,selected_package,tmp_path):
    policy.test_actual_packaged_constructor_and_publish_stop_before_capture(MODE,scenario,selected_package,tmp_path)


def test_selected_mode_keeps_its_reviewed_payload_contract(selected_package):
    if MODE == 'standard':policy.test_standard_package_retains_the_original_final_age_check(selected_package)
    else:
        # LIGHTWEIGHT deliberately omits full payload verification; preserving
        # that contract cannot be claimed from STANDARD's AST.
        import repository_minimal
        assert Path(repository_minimal.__file__).resolve() == ENGINE/'common/repository_minimal.py'
    for member in MODULES:
        module = sys.modules[Path(member).stem]
        assert Path(module.__file__).resolve() == ENGINE/member
        assert Path(module.__file__).read_bytes() == MEMBERS[member]
