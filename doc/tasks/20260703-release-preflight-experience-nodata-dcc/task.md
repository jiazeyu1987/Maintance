# 20260703 release-preflight-experience-nodata-dcc

## 任务目标

- 将 2026-07-03 不带数据测试服发布中暴露的问题沉淀为发布前置经验，防止后续继续在 `code-only`、DCC `lifecycle_stage` 迁移、远端 MySQL 查询、`runtime-control.local.yaml` 临时 worktree 配置和 no-data manifest 校验上重复犯错。

## 经验门禁

- 适用索引：`docs/experience-index.md`
- 命中经验：`docs/release-build-preflight-lessons.md`
- 命中执行清单：`docs/release-agent-checklist.md`
- 本任务强制门禁：
  - 不带数据发布不等于跳过 schema、required SQL、migration 或约束变更。
  - DCC `lifecycle_stage` 改为 `NOT NULL` 前必须检查全表空值，包含 `deleted=1` 历史归档行。
  - 远端 MySQL 查询必须以真实容器库名和容器内密码变量为准，避免 PowerShell/SSH/sh/mysql 多层引号误判。
  - `runtime-control.local.yaml` 指向临时发布 worktree 后，收尾前必须恢复稳定主路径并验证健康检查。
  - no-data 发布必须验证 manifest `publishScope=code-only` 且无数据目录。

## 里程碑

- [x] 读取既有经验索引和发布前置经验文档。
- [x] 将不带数据发布暴露的问题写入前置经验文档和索引。
- [x] 将关键门禁同步到发布执行清单，保证后续发布前可执行检查。
- [x] 验证文档包含关键门禁并完成任务记录。
- [x] 提交本任务直接产生的文档改动。

## 预期验证

- `docs/experience-index.md` 能按关键词路由到 `docs/release-build-preflight-lessons.md`。
- `docs/release-build-preflight-lessons.md` 包含 2026-07-03 不带数据测试服发布前置门禁。
- `docs/release-agent-checklist.md` 包含本次新增的可执行前置门禁。
- `git diff --check` 通过。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，将发布失败根因前移到经验索引、前置经验和执行清单。
- 是否存在临时补丁或绕过：否。

## 当前状态

- 状态：已完成。
- 已完成：
  - `docs/experience-index.md` 增加 no-data、DCC `lifecycle_stage`、远端 MySQL、runtime-control 关键词路由。
  - `docs/release-build-preflight-lessons.md` 增加 2026-07-03 不带数据测试服发布前置门禁和证据入口。
  - `docs/release-agent-checklist.md` 增加可执行的 2026-07-03 不带数据发布新增前置门禁。
- 验证结果：
  - `git diff --check`：PASS。
  - `document-keyword-gate`：PASS。
- 待完成：无。
