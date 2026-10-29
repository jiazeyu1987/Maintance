"""Package mode is explicit, immutable and checked against the running process."""
import unittest
from unittest.mock import patch

from intruoyi_runtime import (
    RuntimeBlocked, gxp_release_mode, gxp_migration_sql, validate_gxp_runtime,
)


class GxpReleaseModeTest(unittest.TestCase):
    def test_only_explicit_server_modes_are_accepted(self):
        for mode in ('FORMAL', 'DEVELOPMENT_DISABLED'):
            manifest = {'releaseSettings': {'gxpAuditMode': mode}}
            self.assertEqual(gxp_release_mode(manifest), mode)
            sql = gxp_migration_sql(manifest,
                {'migrationId': '20261026_gxp_audit_mode_config'}, 'SELECT 1;')
            self.assertEqual(sql, "SET @intruoyi_gxp_audit_initial_mode='" + mode + "';\nSELECT 1;")
        for mode in (None, '', 'LOCAL_POLICY', "FORMAL';DROP TABLE infra_config;--"):
            with self.assertRaises(RuntimeBlocked):
                gxp_release_mode({'releaseSettings': {'gxpAuditMode': mode}})
        with self.assertRaises(RuntimeBlocked):
            gxp_release_mode({})

    def test_unrelated_migration_is_not_rewritten(self):
        self.assertEqual(gxp_migration_sql({}, {'migrationId': 'other'}, 'SELECT 1;'), 'SELECT 1;')

    def test_persisted_setting_alone_does_not_prove_runtime_mode(self):
        mode = 'DEVELOPMENT_DISABLED'
        validate_gxp_runtime({'gxpAuditMode': mode, 'configuredGxpAuditMode': mode}, mode)
        for state in ({'configuredGxpAuditMode': mode},
                      {'gxpAuditMode': 'FORMAL', 'configuredGxpAuditMode': mode},
                      {'gxpAuditMode': mode, 'configuredGxpAuditMode': 'FORMAL'}):
            with self.assertRaises(RuntimeBlocked):
                validate_gxp_runtime(state, mode)

    def test_persistence_checks_schema_and_reads_back_exact_mode(self):
        from intruoyi_runtime_agent import persist_gxp_release_mode
        columns = '\n'.join(('config_key', 'value', 'type', 'visible', 'deleted', 'updater', 'update_time'))
        manifest = {'releaseSettings': {'gxpAuditMode': 'DEVELOPMENT_DISABLED'}}
        # Transport unit test only; real database/restart acceptance remains separate.
        with patch('intruoyi_runtime_agent.remote.sql', side_effect=[
                'infra_config', columns, 'FORMAL\t1\t1', '', 'DEVELOPMENT_DISABLED\t1\t1']) as sql:
            persist_gxp_release_mode({}, manifest)
        update = sql.call_args_list[3].args[1]
        self.assertIn("SET value='DEVELOPMENT_DISABLED'", update)
        self.assertIn("AND BINARY value<>'DEVELOPMENT_DISABLED'", update)
        for invalid in ('', 'FORMAL\t1\t1\nFORMAL\t1\t1', 'FORMAL\t1\t0', 'INVALID\t1\t1'):
            with patch('intruoyi_runtime_agent.remote.sql', side_effect=['infra_config', columns, invalid]) as sql:
                with self.assertRaises(RuntimeBlocked):
                    persist_gxp_release_mode({}, manifest)
                self.assertFalse(any('UPDATE ' in call.args[1] for call in sql.call_args_list))
        with patch('intruoyi_runtime_agent.remote.sql', side_effect=[
                'infra_config', columns, 'FORMAL\t1\t1', '', 'FORMAL\t1\t1']):
            with self.assertRaises(RuntimeBlocked):
                persist_gxp_release_mode({}, manifest)


if __name__ == '__main__':
    unittest.main()
