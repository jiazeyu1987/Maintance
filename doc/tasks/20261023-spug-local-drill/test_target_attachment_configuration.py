"""Configuration contract tests using the inspected rehearsal Nginx rules."""
import importlib.util,unittest
from pathlib import Path
path=Path(__file__).with_name('intruoyi57-prepare-safe-target.remote.py')
spec=importlib.util.spec_from_file_location('target_prepare',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
MATCHES=(b'http://127.0.0.1:9000/yudao/',b'http://172.30.30.57:9000/yudao/')
RULES=b'\n'.join(b'sub_filter "'+url+b'" "http://127.0.0.1:18322/yudao/";' for url in MATCHES*2)
CONFIG=RULES+b'\nlocation /yudao/ { proxy_pass http://172.28.151.33:9000; }\n'
class AttachmentConfiguration(unittest.TestCase):
    def test_output_uses_same_origin_and_preserves_source_matches(self):
        result=module.normalize_attachment_route(CONFIG,'172.28.151.33')
        self.assertNotIn(b':18322',result)
        self.assertEqual(result.count(b'"/yudao/"'),4)
        for url in MATCHES:self.assertEqual(result.count(url),2)
        self.assertIn(b'proxy_pass http://172.28.151.33:9000;',result)
    def test_already_normalized_is_unchanged(self):
        raw=CONFIG.replace(b'"http://127.0.0.1:18322/yudao/"',b'"/yudao/"')
        self.assertEqual(module.normalize_attachment_route(raw,'172.28.151.33'),raw)
    def test_wrong_minio_fails(self):
        with self.assertRaisesRegex(ValueError,'TARGET_MINIO_ROUTE_MISSING'):
            module.normalize_attachment_route(CONFIG,'172.28.199.33')
    def test_missing_rule_fails(self):
        with self.assertRaisesRegex(ValueError,'ATTACHMENT_REWRITE_CONTRACT'):
            module.normalize_attachment_route(CONFIG.replace(RULES.splitlines()[0],b'',1),'172.28.151.33')
    def test_mixed_old_and_relative_rules_fail(self):
        raw=CONFIG.replace(b'"http://127.0.0.1:18322/yudao/"',b'"/yudao/"',1)
        with self.assertRaisesRegex(ValueError,'ATTACHMENT_REWRITE_CONTRACT'):
            module.normalize_attachment_route(raw,'172.28.151.33')
if __name__=='__main__':unittest.main()
