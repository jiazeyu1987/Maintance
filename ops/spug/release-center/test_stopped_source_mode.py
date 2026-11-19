import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from pathlib import Path
import route_import_correction as correction
import intruoyi_runtime_agent as agent
from intruoyi_runtime import RuntimeBlocked


class StoppedSourceModeTests(unittest.TestCase):
    def test_normal_source_keeps_real_login_and_does_not_read_database(self):
        executor=SimpleNamespace(c={'gxpConfigurationSourceUrl':'http://prod',
            'targets':{'prod':{'entryUrl':'http://prod'}}},state={'environments':{'prod':{}},'jobs':[]},
            root=Path('evidence'),runtime=Mock())
        reader=Mock(return_value={'gxpAuditMode':'FORMAL'})
        result=correction.capture_source_mode(executor,{'id':'JOB-build'},'a'*40,reader)
        self.assertEqual(result,{'gxpAuditMode':'FORMAL'})
        reader.assert_called_once()
        executor.runtime.observe.assert_not_called()

    def test_unknown_maintenance_incident_cannot_fall_back_to_a_new_source(self):
        executor=SimpleNamespace(c={'gxpConfigurationSourceUrl':'http://prod',
            'targets':{'prod':{'entryUrl':'http://prod'}}},state={'environments':{'prod':{'maintenanceUnknown':True}},'jobs':[]},
            root=Path('evidence'),runtime=Mock())
        reader=Mock()
        with self.assertRaisesRegex(RuntimeBlocked,'reviewed failed production'):
            correction.capture_source_mode(executor,{'id':'JOB-build'},'a'*40,reader)
        reader.assert_not_called()

    def test_stopped_source_is_bound_to_original_incident_and_saved_mode(self):
        original=dict(id='JOB-882bad6add',action='promote-prod',target='prod',status='failed',
            effectsStarted=True,error='Route snapshot READINESS blocked: 148',releaseTag='2026-11-19-15-03-12',
            workflowPolicy={'productionRecovery':'external'},remoteOperations=[dict(env='prod',action='deploy',operationId='OP-original')],
            runtimeStagingRoots={'prod':'/release/attempts/JOB-882bad6add'},originState={'fingerprint':'original'},
            migrationPlan={'items':[dict(migrationId='m1',sha256='a'*64,action='APPLY')]})
        manifest=dict(migrations=[],releaseSettings={'gxpAuditMode':'FORMAL'})
        executor=SimpleNamespace(c={'gxpConfigurationSourceUrl':'http://prod',
            'targets':{'prod':{'entryUrl':'http://prod'}}},
            state={'environments':{'prod':{'maintenanceUnknown':True}},'jobs':[original]},
            root=Path('evidence'),runtime=Mock(),manifest=Mock(return_value=({'manifestSha256':'b'*64},manifest)),
            runtime_manifest=Mock(return_value=manifest))
        executor.runtime.observe.return_value={'ledgerRecords':[]}
        evidence=dict(gxpAuditMode='FORMAL',source='verified-stopped-origin-database',authenticated=False,runtimeModeVerified=False)
        executor.runtime.call.return_value=evidence
        reader=Mock()
        result=correction.capture_source_mode(executor,{'id':'JOB-build'},'c'*40,reader)
        self.assertEqual(result['originalJobId'],original['id'])
        self.assertFalse(result['runtimeModeVerified'])
        self.assertEqual(executor.runtime.call.call_args.args,('prod','read-stopped-gxp'))
        self.assertEqual(executor.runtime.call.call_args.kwargs['incident']['origin'],original['originState'])
        reader.assert_not_called()
        for change in ({'gxpAuditMode':'DEVELOPMENT_DISABLED'},{'authenticated':True},{'runtimeModeVerified':True}):
            executor.runtime.call.return_value=dict(evidence,**change)
            with self.assertRaisesRegex(RuntimeBlocked,'Stopped saved GxP setting differs'):
                correction.capture_source_mode(executor,{'id':'JOB-build'},'c'*40,reader)

    def test_remote_saved_setting_requires_verified_origin_and_one_visible_value(self):
        profile={'environment':'prod'}
        payload=dict(action='read-stopped-gxp',profile=profile,manifest={},incident={'originalJobId':'JOB-original'})
        with patch.object(agent,'inspect_stopped_origin',return_value={'fingerprint':'physical'}) as origin, \
                patch.object(agent.remote,'sql',side_effect=['infra_config','config_key\ttext\nvalue\ttext\ntype\tint\nvisible\tbit\ndeleted\tbit','FORMAL\t1\t1']) as sql:
            result=agent.dispatch(payload)
            self.assertEqual(result['gxpAuditMode'],'FORMAL')
            self.assertFalse(result['authenticated'])
            self.assertFalse(result['runtimeModeVerified'])
            origin.assert_called_once_with(profile,{},payload['incident'],require_repair=False)
            self.assertTrue(all(call.args[1].startswith(('SHOW ','DESCRIBE ','SELECT ')) for call in sql.call_args_list))
        for value in ('','FORMAL\t1\t0','FORMAL\t2\t1','FORMAL\t1\t1\nFORMAL\t1\t1','UNKNOWN\t1\t1'):
            with self.subTest(value=value), patch.object(agent,'inspect_stopped_origin',return_value={'fingerprint':'physical'}), \
                    patch.object(agent.remote,'sql',side_effect=['infra_config','config_key\ttext\nvalue\ttext\ntype\tint\nvisible\tbit\ndeleted\tbit',value]), \
                    self.assertRaises(RuntimeBlocked):
                agent.dispatch(payload)
