"""Pure report-contract tests, without executing control queries or SSH."""
import ast
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_stable_controls as stable


def report_literals():
    tree=ast.parse(stable.CURRENT_SCRIPT)
    call=tree.body[-1].value.args[0].args[0]
    assert isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id=='dict'
    return {kw.arg:ast.literal_eval(kw.value) for kw in call.keywords if isinstance(kw.value,ast.Constant)}


def test_remote_report_distinguishes_business_actions_and_control_query_audit():
    report=report_literals()
    assert 'serverWrites' not in report
    assert report['businessMutationDispatched'] is False
    assert report['controlApiQueriesPerformed'] is True
    assert report['queryAuditWritesMayOccur'] is True


@pytest.mark.parametrize('corruption', [None,'legacy','business','queries','audit'])
def test_report_validator_rejects_wrong_or_old_semantics(corruption):
    report=dict(status='PASS',businessMutationDispatched=False,controlApiQueriesPerformed=True,queryAuditWritesMayOccur=True)
    if corruption=='legacy':report=dict(status='PASS',serverWrites=False)
    if corruption=='business':report['businessMutationDispatched']=True
    if corruption=='queries':report['controlApiQueriesPerformed']=False
    if corruption=='audit':report['queryAuditWritesMayOccur']=False
    if corruption is None:stable.verify_control_query_effects(report)
    else:
        with pytest.raises(AssertionError):stable.verify_control_query_effects(report)


def test_final_closeout_consumes_corrected_contract():
    source=Path(__file__).with_name('verify_closeout.py').read_text(encoding='utf-8')
    assert "current['serverWrites']" not in source
    assert 'verify_control_query_effects(current)' in source
