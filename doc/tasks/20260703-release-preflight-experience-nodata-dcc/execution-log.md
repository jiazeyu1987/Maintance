# 20260703 release-preflight-experience-nodata-dcc execution log

## 请求

- 用户请求：帮我沉淀成前置经验，防止后面继续犯错。

## 经验预检

- GREEN: experience-preflight -> PASS，已读取 `docs/experience-index.md`，命中 `docs/release-build-preflight-lessons.md` 与 `docs/release-agent-checklist.md`。

## BDD

- BDD: 发布前置经验可命中 -> Given 后续发布任务按经验索引检索 `code-only`、DCC `lifecycle_stage`、远端 MySQL 或 `runtime-control.local.yaml`，When Agent 执行发布预检，Then 必须命中本次沉淀的发布前置经验并在发布前完成对应门禁。
- BDD: 发布执行清单可阻塞重复错误 -> Given 后续执行不带数据测试服发布，When 检查发布执行清单，Then 清单必须明确要求校验 schema/required SQL、全表 `NOT NULL` 空值、远端 MySQL 查询方式、runtime-control 配置恢复和 no-data manifest。

## TDD / 验证记录

- GREEN: existing-experience-read -> PASS，`docs/experience-index.md` 已包含 no-data、DCC lifecycle_stage、远端 MySQL、runtime-control 关键词路由。
- GREEN: existing-preflight-read -> PASS，`docs/release-build-preflight-lessons.md` 已包含 `2026-07-03 不带数据测试服发布前置门禁`。
- GREEN: git diff --check -> PASS。
- GREEN: document-keyword-gate -> PASS，已确认经验索引、前置经验、发布执行清单和任务文档包含本次关键门禁。

## 完成记录

- 已沉淀前置经验：
  - 不带数据发布仍必须检查 schema、required SQL、migration 和约束变更。
  - DCC `lifecycle_stage` 改 `NOT NULL` 前必须全表查空值，包含 `deleted=1` 历史归档行。
  - 远端 MySQL 查询必须使用真实业务库和容器内密码变量，避免多层引号误判。
  - `runtime-control.local.yaml` 指向临时 worktree 后必须恢复稳定主路径并做健康检查。
  - no-data manifest 必须校验 `publishScope=code-only` 且无数据目录。
