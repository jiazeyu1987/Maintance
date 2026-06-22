# Bug Regression Evidence

## Bug

- 问题：维护仓 `ops/release/release_sql_contract_gate.py` 会把合法 SQL 的 `ON DUPLICATE KEY UPDATE ... VALUES(...)` 更新子句误识别为新的 `system_menu` 插入元组，导致 `build-release` 在本机 SQL 预检阶段误报 `system_menu.id must be an integer literal ... -> \`name\``。
- 期望行为：SQL 预检只解析真正 `INSERT INTO system_menu ... VALUES (...)` 的顶层插入元组；更新子句里的 `VALUES(...)` 不能再被当成额外插入记录。

## Expected

- 维护仓 release SQL 预检只解析真正的 `system_menu` 插入元组。
- 合法 `ON DUPLICATE KEY UPDATE ... VALUES(...)` 菜单 SQL 必须直接通过本机预检。
- 页面 `build-release` 不应再因为 `20260520_system_nas_management_menu.sql` 的更新子句被误报失败。

## Reproduction

- 真实页面路径：运行控制台 `build-release(v11)`，operation `op-2026-06-22T034606591995400Z-87264c6d-8e7b-4b5f-801f-e8b6e91e555f`
- 本地复现命令：`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q`

## Root Cause

- 旧实现的 `_extract_value_tuples()` 会扫描 `values_text` 中所有括号对。
- 当 SQL 含 `ON DUPLICATE KEY UPDATE \`name\` = VALUES(\`name\`)` 时，更新子句里的 `VALUES(\`name\`)` 也被当成新的插入元组。
- 后续 `_parse_menu_id()` 读取到的是 `` `name` ``，于是抛出“`system_menu.id must be an integer literal`”误报。

## Regression Test

- 新增测试：`scripts/tests/test_release_sql_preflight_gate.py::test_release_sql_contract_gate_allows_on_duplicate_key_update_values_clause`
- 覆盖场景：单条合法 `system_menu` 插入语句带 `ON DUPLICATE KEY UPDATE ... VALUES(...)` 更新子句时，预检应直接通过。

## RED:

- `RED: python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q -> FAIL, test_release_sql_contract_gate_allows_on_duplicate_key_update_values_clause 因 \`name\` 被误当作 system_menu.id 而失败`

## GREEN:

- `GREEN: python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q -> PASS`
- `GREEN: python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\ops\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro\sql\mysql -> PASS`

## Verification

- 风险范围：仅影响维护仓本机 SQL 预检，对业务 SQL 内容与远端数据库没有写入副作用。
- 回归范围：`system_menu` 重复 ID 检查继续保留；合法 `ON DUPLICATE KEY UPDATE` 菜单 SQL 恢复可通过；`build-release` 可以重新回到真实页面链路。

## Blockers

- 后续仍需回真实页面以新标签 `release-20260621-page-full-flow-mainmerge-v12` 重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
