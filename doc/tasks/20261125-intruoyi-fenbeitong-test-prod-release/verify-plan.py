import json
import sys
from pathlib import Path
BASE=Path('C:/SpugHandoff/release')
ROOT=BASE/'registration-config-release-fix-20261126'
MAINT=BASE/'intruoyi-fenbeitong-release-20261125'
sys.path[:0]=[str(MAINT/'ops/spug/release-center'),str(MAINT)]
from intruoyi_build import migration_inputs,target_input_plan
MID='20261125_registration_certificate_config_menu_parent'
migrations,references,artifacts=migration_inputs(ROOT)
item=next(entry for entry in migrations if entry['migrationId']==MID)
assert item['type']=='menu'
assert item['targetPreflight']['readOnly'] is True
assert item['targetPreflight']['reference'] in artifacts
state=json.loads((BASE/'private/intruoyi-fenbeitong-test-prod-20261125/state.private.json').read_text(encoding='utf-8'))
plans={env:target_input_plan(migrations,state['environments'][env]['ledgerRecords'],env) for env in ('test','prod')}
report=dict(status='PASS',migration=MID,migrations=len(migrations),artifacts=len(artifacts),readonlyPreflight=item['targetPreflight'],plans=plans)
(BASE/'private/intruoyi-fenbeitong-test-prod-20261125/migration-input-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='plans'},ensure_ascii=False))
