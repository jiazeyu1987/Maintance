"""Run focused baseline/fixed contract tests without touching the stable executor."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

TASK = Path(__file__).parent
SOURCE = Path('C:/SpugHandoff/schema-src-20261101')
OPS = Path('C:/SpugHandoff/schema-ops-20261101/ops/spug/release-center')
STABLE = Path('C:/SpugHandoff/release/source/ops/spug/release-center')

if len(sys.argv) > 1 and sys.argv[1] == '--baseline-worker':
    sys.path.insert(0, str(STABLE))
    suite = unittest.TestSuite()
    for name in ('test_three_server_schema', 'test_direct_release'):
        spec = importlib.util.spec_from_file_location('schema_review_'+name, OPS/(name+'.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if name == 'test_three_server_schema':
            suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
        else:
            for method in ('test_different_origins_must_converge_to_the_same_tested_schema',
                           'test_direct_deployment_rejects_a_success_receipt_with_a_different_schema',
                           'test_direct_acceptance_rejects_target_own_receipt_when_source_schema_differs'):
                suite.addTest(module.DirectReleaseTest(method))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)

mode = sys.argv[1]
if mode == 'red':
    commands = [('source-red', [sys.executable,'-X','utf8','-m','unittest','discover','-s','IntRuoyiBackend/script/tests','-p','test_dcc_governance_three_environment_schema.py','-v'], SOURCE),
                ('executor-red',[sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--baseline-worker'], OPS)]
else:
    commands = [('source-green', [sys.executable,'-X','utf8','-m','unittest','discover','-s','IntRuoyiBackend/script/tests','-p','test_dcc_governance_three_environment_schema.py','-v'], SOURCE),
                ('executor-green',[sys.executable,'-X','utf8','-m','unittest','test_three_server_schema','test_direct_release','test_technical_verification','test_intruoyi_runtime','test_production_attempt_roots','test_interruption','-q'], OPS)]
report = []
for label, command, cwd in commands:
    result = subprocess.run(command,cwd=cwd,capture_output=True,encoding='utf-8',timeout=180)
    (TASK/(label+'.log')).write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    report.append(dict(label=label,exitCode=result.returncode))
    print(label+' exit='+str(result.returncode))
    print((result.stdout+'\n'+result.stderr)[-5000:])
    if (mode=='red' and result.returncode==0) or (mode!='red' and result.returncode!=0):
        raise SystemExit('Unexpected contract test outcome')
(TASK/(mode+'-contract-result.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
