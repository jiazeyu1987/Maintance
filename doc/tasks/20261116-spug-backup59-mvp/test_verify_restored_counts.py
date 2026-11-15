import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('counts',Path(__file__).with_name('verify_restored_counts.py'))
counts=importlib.util.module_from_spec(spec)
spec.loader.exec_module(counts)


class CountsContract(unittest.TestCase):
    def test_explicit_ready_target_is_required_and_scoped(self):
        target='spug-empty59-0123456789ab'
        self.assertEqual(counts.target_ref(target),target)
        for value in ('', 'spug-empty58-0123456789ab', '../old', target+'; echo bad'):
            with self.assertRaises(ValueError):counts.target_ref(value)

    def test_exact_count_comparison_and_read_only_query(self):
        expected={'infra_file':9074,'system_users':2155,'system_tenant':4,'mes_pro_work_order':19091,
                  'mes_pro_batch_record_execution':53,'mes_pro_batch_record_template':11,
                  'dcc_product_catalog':213,'erp_product':15996,'erp_kingdee_sync_run':476,
                  'infra_job_log':85151,'dcc_registration_certificate_daily_run':68}
        query=counts.count_query(expected)
        self.assertTrue(query.startswith('SELECT '))
        self.assertEqual(query.count('COUNT(*)'),11)
        self.assertNotIn('INSERT',query);self.assertNotIn('UPDATE',query)
        target='spug-empty59-0123456789ab'
        report=counts.compare(expected,expected,target)
        self.assertTrue(report['matched'])
        self.assertEqual(report['targetConfigRef'],target)
        changed=dict(expected,infra_job_log=87458)
        self.assertFalse(counts.compare(expected,changed,target)['matched'])
        with self.assertRaises(ValueError):counts.count_query(dict(expected,extra_table=1))
        with self.assertRaises(ValueError):counts.compare(expected,{},target)


if __name__=='__main__':unittest.main()
