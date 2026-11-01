"""Run the ordinary executor's complete local unit/boundary suite."""
import json
from pathlib import Path
import sys
import unittest

root=Path('C:/SpugHandoff/schema-ops-20261101/ops/spug/release-center')
sys.path.insert(0,str(root))
excluded={'test_manage_executor_service':'User explicitly excludes Windows service installation; win32api is not installed'}
names=[p.stem for p in sorted(root.glob('test_*.py')) if p.stem not in excluded]
result=unittest.TextTestRunner(verbosity=0).run(unittest.TestLoader().loadTestsFromNames(names))
report=dict(status='PASS' if result.wasSuccessful() else 'FAIL',testsRun=result.testsRun,
            failures=len(result.failures),errors=len(result.errors),
            skipped=[dict(test=str(t),reason=r) for t,r in result.skipped],outOfScopeModules=excluded,
            scope='Local ordinary-executor unit/boundary suite; no live server operations')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
sys.exit(0 if result.wasSuccessful() else 1)
