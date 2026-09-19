# Bug Regression Evidence

## Bug Summary

r43 测试服 `deploy-release` 在执行 `20260908_system_signature_password_t1.sql` 时失败：迁移要求同一租户内所有 `canonical_username` 永久唯一，但测试服存在已删除历史账号与当前账号规范化用户名重复。

## Expected Behavior

电子签名登录账号唯一约束应保护未删除账号的登录身份唯一性，同时保留已删除账号的审计记录。未删除账号重复时必须 fail fast；仅已删除账号造成的历史重复不应阻断迁移。

## Reproduction

- `deploy-release` releaseTag：`release-20260911-verified-branch-app-r260908c-r43`
- 失败点：`20260908_system_signature_password_t1.sql`
- 失败结果：`ERROR 1644 (45000): system_users contains duplicate tenant canonical username values`
- 只读诊断：`ALL_DUP_GROUPS=2`，`ACTIVE_DUP_GROUPS=0`

## Root Cause

r43 迁移直接对 `(tenant_id, canonical_username)` 建永久唯一键，且重复检查未排除 `deleted=1` 的历史账号。该约束把审计保留数据当作当前登录身份冲突处理，导致真实测试库阻断。

## Regression Test

- 更新 `IntRuoyiBackend/script/tests/test_system_signature_password_t1_contract.py`，要求迁移包含 `active_canonical_username` generated column、未删除账号重复检查、以及 `(tenant_id, active_canonical_username)` 唯一键。
- 更新 H2 测试结构 `IntRuoyiBackend/yudao-module-system/src/test/resources/sql/create_tables.sql`，保持测试 schema 与迁移约束一致。

## RED

`deploy-release-test-r43-system-signature-active-duplicate` -> FAIL。真实测试库存在历史删除账号重复，r43 迁移错误阻断。

## GREEN

- `python -X utf8 -m pytest script\tests\test_system_signature_password_t1_contract.py -q` -> `10 passed`
- `python -X utf8 ops\release\run-release-migration-policy-gate.py --sql-root <app>\IntRuoyiBackend\sql\mysql --file-prefix sql/mysql --output <task>\r44-signature-t1-active-migration-policy.json` -> `status=passed migrationCount=607`
- `python -X utf8 -m pytest script\tests\test_mes_process_pool_device_selection_mode_sql.py -q` -> `3 passed`
- `git diff --check` on the three changed files -> PASS

## Risk And Scope

Scope is limited to the electronic-signature T1 user schema migration and matching tests. It does not merge accounts, delete users, change tenant data, skip migration state, or downgrade failure behavior. Active duplicate users still block the migration.

## Blockers

None after application commit `713c64112d7b626a2ba71788fd36cc32d686addc`; next release must rebuild with a new releaseTag r44.
