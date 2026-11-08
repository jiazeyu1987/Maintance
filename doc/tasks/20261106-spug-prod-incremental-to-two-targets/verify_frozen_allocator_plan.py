"""Verify the real frozen 885-table proofs without mutating any server."""
import json
import sys
from common import TASK, PRIVATE, now, write

sys.path.insert(0, str(TASK.parents[2] / 'ops/backup_engine/formal'))
from formal_schema_evidence import frozen_auto_increment_plan, compare_schema
from formal_snapshot_linux import FormalSnapshotError

value = json.loads((PRIVATE / 'restore-368-schema-comparison.private.json').read_text(encoding='utf8'))
source, target = value['expectedSchema'], value['actualSchema']
plan = frozen_auto_increment_plan(source, target)
assert plan == [dict(table='mes_kingdee_production_order_sync_record', column='id',
    before=30376, after=30384,
    sql='ALTER TABLE `mes_kingdee_production_order_sync_record` AUTO_INCREMENT = 30384;')]
try:
    compare_schema(source, target)
except FormalSnapshotError as error:
    assert error.code == 'FORMAL_SCHEMA_MISMATCH'
else:raise AssertionError('STRICT_COMPARISON_WAS_WEAKENED')
report = dict(status='PASS', observedAt=now(), sourceSchemaSha256=source['schemaSha256'],
    targetSchemaSha256=target['schemaSha256'], actualFrozenTableCount=len(source['catalog']['TABLES']),
    exactPlan=plan, actualMutations=0, strictComparisonStillRejectsOriginalMismatch=True)
write(TASK / 'allocator-real-frozen-plan.json', report);print(json.dumps(report))
