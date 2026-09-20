# Database Schema Evidence

## Data change goal and affected entities

- Goal: 注册证到期通知的接收角色按用户确认的业务方案收口为现有角色 `910218`，不再包含、不要求、不推断 `910231`。
- Affected entities: `infra_job.handler_param` 中 `registrationCertificateReminderDailyJob` 的 `roleIds`，以及 `mdm_role_company_scope` 中由 `dcc-reg-cert-notification-role-scope-backfill` 创建的角色公司范围。

## Database engine and migration tool

- Engine: MySQL / MariaDB 兼容执行路径。
- Migration tool: 项目 SQL 迁移文件与发布脚本按 `sql/mysql` 执行；策略门禁使用 `script/release/run-release-migration-policy-gate.py`。

## Schema, migration, fixture, seed, index, or constraint changes

- `20260818_dcc_registration_certificate_reminder.sql`：保持已执行的历史种子内容与摘要不变（历史值为 `roleIds:[910218,910231]`）；不通过改写旧迁移实现当前业务规则。
- `20260830_dcc_registration_certificate_notification_role_scope_backfill.sql`：在同一显式事务内将任务参数修正为 `roleIds:[910218]`，再基于该正式角色回填公司范围；无权限推断、无补造角色、无静默删除。
- `scripts/tests/test_dcc_notification_role_scope_mysql.py` 与应用仓对应静态/JUnit 测试分别验证历史迁移不可变和后续迁移的 `[910218]` 最终契约。

## Data safety analysis

- 不扩大通知范围：不再使用 query-current 权限作为通知接收人依据。
- 不补造业务角色：角色 `910218` 缺失时 fail-fast，迁移失败并回滚。
- 不静默删除失效角色：迁移只创建带固定 creator 的 role-company scope，不删除既有授权。
- 事务边界：`infra_job.handler_param` 更新与 `mdm_role_company_scope` 写入位于同一事务，后续失败会完整回滚。

## Safety

- 不扩大通知范围：不再使用 query-current 权限作为通知接收人依据。
- 不补造业务角色：角色 `910218` 缺失时 fail-fast，迁移失败并回滚。
- 不静默删除失效角色：迁移只创建带固定 creator 的 role-company scope，不删除既有授权。
- 事务边界：`infra_job.handler_param` 更新与 `mdm_role_company_scope` 写入位于同一事务，后续失败会完整回滚。

## Rollback or recovery plan

- 失败时由事务自动回滚 `infra_job.handler_param` 和 `mdm_role_company_scope` 写入。
- 如需人工回退已成功迁移后的数据，只允许在确认未被后续通知任务使用后删除 `creator='dcc-reg-cert-notification-role-scope-backfill'` 的新增 scope 行；不得伪造迁移台账成功状态。

## BDD scenarios

- BDD: 注册证通知角色收口为 910218 -> Given 业务确认注册证通知只发送给现有角色 `910218`，When 后续迁移修正任务参数并回填公司范围，Then 后续 SQL 必须写入 `[910218]`且不得包含或要求 `910231`，同时早期已执行 SQL 必须保持不可变。
- BDD: 通知角色修正事务回滚 -> Given `infra_job.handler_param` 只有 `actorId` 且 scope 写入后发生数据库异常，When 执行迁移，Then `infra_job.handler_param` 与 `mdm_role_company_scope` 必须一起回滚。

## RED command and expected failure

- RED: r16 测试服发布在 `20260830_dcc_registration_certificate_notification_role_scope_backfill` 触发 `ERROR 1644 Missing registration certificate notification role scope source`；原因是旧 SQL 要求 `[910218,910231]`，真实角色只有 `910218`。

## GREEN command and passing result

- GREEN: `python -X utf8 -m pytest .\scripts\tests\test_dcc_notification_role_scope_mysql.py -q` -> 5 passed。
- GREEN: `python -X utf8 -m pytest .\script\tests\test_dcc_registration_certificate_notification_role_scope_backfill_sql.py -q` -> 3 passed。
- GREEN: `mvn -pl yudao-module-dcc '-Dtest=DccRegistrationCertificateReminderSchemaTest' '-Dsurefire.failIfNoSpecifiedTests=false' test` -> 6 tests passed，BUILD SUCCESS。

## Migration verification

- `python -X utf8 script/release/run-release-migration-policy-gate.py --sql-root sql/mysql` -> `status=passed`，`migrationCount=632`。
- `rg -n "910231" ...` -> 已执行的历史提醒种子为不可变证据；当前有效的后续角色收口迁移不引用 `910231`。

## Verification

- `python -X utf8 script/release/run-release-migration-policy-gate.py --sql-root sql/mysql` -> `status=passed`，`migrationCount=632`。
- `rg -n "910231" ...` -> 历史迁移中的冻结值保留；后续有效迁移仅写入 `910218`。

## Blockers

- 未执行新 releaseTag 的真实按钮构建、测试服部署、mark-tested 或正式晋级；这些动作必须在提交同步和按钮链路前置检查通过后另行执行。
