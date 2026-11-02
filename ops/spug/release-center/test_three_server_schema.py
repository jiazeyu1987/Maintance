import unittest
from intruoyi_runtime import RuntimeBlocked, validate_expected_schema
from test_direct_release import POLICY


class ThreeServerSchemaContractTest(unittest.TestCase):
    def test_formal_direct_targets_require_the_verified_source_schema(self):
        for environment in ('prod','backup'):
            policy=dict(POLICY,targetEnvironment=environment,recoveryMode='external' if environment=='prod' else 'checkpoint')
            with self.subTest(environment=environment), self.assertRaisesRegex(RuntimeBlocked,'schema'):
                validate_expected_schema(environment,None,policy)
            validate_expected_schema(environment,'a'*64,policy)

    def test_test_target_can_establish_the_reference_schema(self):
        validate_expected_schema('test',None,dict(POLICY,targetEnvironment='test',recoveryMode='checkpoint'))
