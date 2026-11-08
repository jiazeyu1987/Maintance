"""Registration planning is isolated from live installation and restore."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ops/spug'))
from restore_target_registration import plan


class RegistrationPlan(unittest.TestCase):
    def fixture(self):
        servers=['172.30.30.57','172.30.30.58','172.30.30.59']
        targets=[]
        for server in servers:
            ref='main-'+server.rsplit('.',1)[1]
            target=dict(sourceConfigRef='source-A',mainApplication={'schemaVersion':'RegisteredMainApplication/v1'},
                replacement={'schemaVersion':'RegisteredApplicationReplacement/v2'},resourceBudget={'explicit':'unit'})
            owner=dict(schemaVersion='RecoveryMinimalConfiguration/v1',targets={ref:target},
                sources={'source-A':{'archiveCatalogue':{'schemaVersion':'RecoveryArchiveCatalogue/v1'}}})
            targets.append(dict(server=server,targetConfigRef=ref,ownerConfiguration=owner,
                controlConfiguration=dict(programPins={'recovery':'safe-program'},sourceConfigurations={'source-A':'repository'},
                    restoreConfigurations={},registryRoot='/private/registry'),configurationRoot='/private/configuration',
                engineVariant='standard',bridgeFile=ref+'.json',bridgeConfiguration=dict(sourceConfigRefs=[],targetConfigRefs=[]),
                progressBinding=dict(server=server,progressRoot='/private/restore',pythonPath='/usr/bin/python3',sshTransport={}),
                preflightEvidencePin={'real-observation-required':'unit-planning-only'}))
        return dict(schemaVersion='SpugMainRestoreRegistrationInputs/v1',sourceConfigRef='source-A',applicationId='app-A',
            simpleSettings=dict(servers=[{'value':s} for s in servers],bindings=[dict(applicationId='app-A',selectable=True,
                mode='safe',overwriteTargetServers={},targetServers={'172.30.30.57':'old-fresh'})]),
            entrySettings=dict(applications=[dict(applicationId='app-A',sourceConfigRef='source-A',targetConfigRefs=['old-target'])]),
            bridgeSettings=dict(targetConnections={'old-target':'old-bridge.json'}),
            registration=dict(applicationId='app-A',sourceConfigRef='source-A',allowedRestoreTargets=[{'configRef':'old-target'}]),
            targets=targets)

    def test_all_three_routes_and_display_bindings_share_registered_identity(self):
        value=self.fixture();before=deepcopy(value);result=plan(value)
        self.assertEqual(value,before)
        self.assertEqual(result['state'],'PLAN_ONLY')
        self.assertEqual(len(result['simpleSettings']['bindings'][0]['overwriteTargetServers']),3)
        self.assertEqual(result['bridgeSettings']['targetConnections']['old-target'],'old-bridge.json')
        for target in result['targets']:
            ref=target['targetConfigRef']
            self.assertEqual(target['controlConfiguration']['restoreConfigurations']['source-A'][ref],
                target['recoveryConfigurationPin'])
            self.assertIn(ref,result['entrySettings']['applications'][0]['targetConfigRefs'])
            self.assertIn(ref,target['bridgeConfiguration']['targetConfigRefs'])
            self.assertIs(target['bridgeConfiguration']['selectedTargetPreflight'],True)
            self.assertIn(ref,result['simpleSettings']['bindings'][0]['restoreProgressBindings'])

    def test_cannot_enable_fast_engine_fresh_target_or_static_point_template(self):
        mutations=[lambda t:t.update(engineVariant='lightweight'),
                   lambda t:t['ownerConfiguration']['targets'][t['targetConfigRef']].pop('mainApplication'),
                   lambda t:t['ownerConfiguration']['sources']['source-A'].pop('archiveCatalogue'),
                   lambda t:t['ownerConfiguration']['targets'][t['targetConfigRef']].pop('resourceBudget')]
        for mutation in mutations:
            value=self.fixture();mutation(value['targets'][0])
            with self.assertRaises(ValueError):plan(value)

    def test_one_server_duplicate_or_unregistered_server_is_refused(self):
        value=self.fixture();value['targets'].pop()
        with self.assertRaisesRegex(ValueError,'THREE_DISTINCT'):plan(value)

    def test_versioned_retained_main_target_keeps_all_three_routes(self):
        value=self.fixture();target=value['targets'][0];ref=target['targetConfigRef']
        target['ownerConfiguration']['targets'][ref]['mainApplication']['schemaVersion']='RegisteredMainApplication/v2'
        result=plan(value)
        self.assertEqual(result['targets'][0]['recoveryConfiguration']['targets'][ref]['mainApplication']['schemaVersion'],
            'RegisteredMainApplication/v2')
        self.assertEqual(len(result['simpleSettings']['bindings'][0]['overwriteTargetServers']),3)
        value=self.fixture();value['targets'][0]['server']='10.0.0.1'
        with self.assertRaisesRegex(ValueError,'THREE_DISTINCT'):plan(value)

    def test_historical_scope_catalogue_and_explicit_archive_only_source_keep_three_targets(self):
        value=self.fixture()
        for target in value['targets']:
            target['ownerConfiguration']['sources']['source-A']['archiveCatalogue']['schemaVersion']='RecoveryArchiveCatalogue/v2'
            target['controlConfiguration']['sourceConfigurations']={}
            target['controlConfiguration']['archiveRestoreCatalogues']={'source-A':dict(
                path='/private/archive-admission.json',bytes=100,sha256='a'*64)}
        result=plan(value)
        self.assertEqual(len(result['simpleSettings']['bindings'][0]['overwriteTargetServers']),3)
        for target in result['targets']:
            self.assertEqual(target['controlConfiguration']['sourceConfigurations'],{})
            self.assertIn('source-A',target['controlConfiguration']['archiveRestoreCatalogues'])

    def test_archive_only_registration_requires_an_explicit_pinned_admission(self):
        for invalid in (None, {}, {'path':'relative','bytes':100,'sha256':'a'*64},
                        {'path':'/private/archive.json','bytes':100,'sha256':'invalid'}):
            value=self.fixture()
            target=value['targets'][0]
            target['controlConfiguration']['sourceConfigurations']={}
            target['controlConfiguration']['archiveRestoreCatalogues']={'source-A':invalid}
            with self.subTest(pin=invalid), self.assertRaisesRegex(ValueError,'SOURCE_CONFIGURATION_REQUIRED_ON_DESTINATION'):
                plan(value)

    def test_explicit_catalogue_route_can_register_retired_safe_source_without_enabling_capture_choice(self):
        value=self.fixture();value['simpleSettings']['bindings'][0]['selectable']=False
        value['simpleSettings']['catalogueRestoreBindings']={'historical-point':'app-A'}
        result=plan(value)
        self.assertFalse(result['simpleSettings']['bindings'][0]['selectable'])
        self.assertEqual(result['simpleSettings']['catalogueRestoreBindings'],{'historical-point':'app-A'})
        self.assertEqual(len(result['simpleSettings']['bindings'][0]['overwriteTargetServers']),3)

    def test_retired_source_without_valid_explicit_catalogue_route_remains_unselectable(self):
        for routes in ({},{'point':'another-app'},{'../point':'app-A'},['app-A']):
            value=self.fixture();value['simpleSettings']['bindings'][0]['selectable']=False
            value['simpleSettings']['catalogueRestoreBindings']=routes
            with self.subTest(routes=routes), self.assertRaises(ValueError):plan(value)


if __name__=='__main__':unittest.main()
