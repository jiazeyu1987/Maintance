# 执行日志

## BDD

- BDD: Spring runner can start with its production bean definition -> Given `MesProRouteVersionSnapshotMigrationRunner` exposes a public configuration constructor and a package-private test constructor, When Spring resolves the bean, Then exactly one constructor is explicitly marked for injection and startup does not require a default constructor.
- BDD: production release role migration expands parent menus safely -> Given the migration iteratively expands required role menus, When one iteration reads the current temporary result set, Then it reads from an independent snapshot table and writes to the target temporary table without MySQL 1137 reopen risk, and cleanup removes both tables.

## RED

- RED: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py -q` -> FAIL expected because `20260814_mes_production_release_roles.sql` currently writes to and reads from `tmp_mes_production_release_required_role_menu` in one statement.
- RED: backend constructor contract test (to be added) -> FAIL expected because the public Spring constructor currently has no `@Autowired` annotation while a second constructor exists.

## 变更前阻塞证据

- Spring gate: `MesProRouteVersionSnapshotMigrationRunner.java:24`, `constructorCount=2`, `autowiredCount=0`, `noArgCount=0`.
- SQL gate: `20260814_mes_production_release_roles.sql:294` (statement beginning at the `REPEAT` block), repeated reference to `tmp_mes_production_release_required_role_menu`.

## GREEN

- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py -q --basetemp .tmp-pytest-blockers-5` -> PASS, `31 passed`; includes the actual backend migration contract test.
- GREEN: `python -X utf8 -m pytest scripts/tests/test_spring_constructor_contract.py -q --basetemp .tmp-pytest-blockers-4` -> PASS, `4 passed`.
- GREEN: `python -X utf8 ops/release/spring_constructor_contract_gate.py --source-root E:\IntRuoyi\IntRuoyiBackend` -> PASS, `status: passed`.
- GREEN: `git diff --check` on all task-owned backend, SQL, test, and task-document paths -> PASS.

## Maven 验证阻塞

- `mvn -pl yudao-module-mes -Dtest=MesProRouteVersionSnapshotMigrationCommandTest -DfailIfNoTests=false test` completed compilation of the changed runner but failed after 3:26 because concurrent source `MesStage6IdiSimulationServiceImpl.java:583` calls missing `ErpKingdeeProductionPickListItemMapper.selectPickListIdsByProductionOrderNo(String)`. This is outside the task-owned files and was not modified.
- No server, publish, backup, restore, or E2E action was executed.

## 设计与风险

- Spring change is limited to constructor injection metadata and its regression test; runtime command behavior remains unchanged.
- SQL change introduces one independent in-memory temporary snapshot table per iteration. It does not alter persistent tables or tenant data. The existing end-of-procedure cleanup will be extended to drop the snapshot table.
- No server, publish, backup, restore, or E2E action is authorized by this task.

## Current Status

ready_for_closeout; original release preflight blockers fixed, full Maven regression blocked by unrelated concurrent compile error.
