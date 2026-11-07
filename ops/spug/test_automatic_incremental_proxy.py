"""Proxy admission budgets must enclose the automatic entry's bounded work."""
from pathlib import Path
import re
import unittest


class AutomaticProxyContract(unittest.TestCase):
    def test_automatic_routes_keep_auth_and_fit_between_entry_and_browser_budgets(self):
        text = Path(__file__).with_name('smallapp-entry.locations.conf').read_text(encoding='utf-8')
        for route in ('incremental-plan', 'automatic-incremental'):
            with self.subTest(route=route):
                match = re.search(r'location\s+=\s+/backup-entry-api/' + route + r'\s*\{([^{}]*)\}', text)
                self.assertIsNotNone(match, 'automatic route still inherits the 30-second generic limit')
                block = match.group(1)
                limit = int(re.search(r'proxy_read_timeout\s+(\d+)s;', block).group(1))
                self.assertGreater(limit, 40 + 10)  # plan transport + selection admission
                self.assertLess(limit, 60)  # browser receives a definite proxy response first
                self.assertIn('proxy_set_header X-Token $http_x_token;', block)
                self.assertIn('proxy_set_header Origin $http_origin;', block)
                self.assertIn('access_log off;', block)
                self.assertIn('rewrite ^/backup-entry-api(.*) $1 break;', block)
                self.assertIn('proxy_pass http://127.0.0.1:18081;', block)
        ordinary = re.search(r'location\s+\^~\s+/backup-entry-api/\s*\{([^{}]*)\}', text).group(1)
        self.assertIn('proxy_read_timeout 30s;', ordinary)


if __name__ == '__main__':
    unittest.main()
