# 不带数据构建发布包 E2E 验证

## Task Goal

通过独立运行控制台 `http://127.0.0.1:48181/` 的真实前端页面，使用真实配置触发一次 `build-release` 不带数据发布包构建，并验证发布包构建结果。只构建发布包，不包含数据库 dump 或 MinIO 快照，不执行发布、晋级、备份、恢复、回滚、重启或远端清理动作。

## Milestones

- [x] 创建任务文档，记录 BDD/TDD、经验门禁与高风险限制。
- [x] 检查独立控制台健康状态、脚本、配置、被管理源码路径、Playwright 与发布包构建前置条件。
- [x] 通过 Playwright 操作运行控制台页面，发现原 `with-data` 范围与用户最新要求冲突后中止并清理半成品。
- [x] 通过 Playwright 操作运行控制台页面，预览并确认 `build-release` 命令，构建范围使用 `code-only`。
- [x] 轮询并核验不带数据构建操作结果、发布包 manifest 与未执行发布类动作的证据。
- [x] 更新任务记录，按验证结果决定是否提交本任务文档变更。

## Expected Verification

- `GET http://127.0.0.1:48181/actuator/health` 返回 `UP`。
- Playwright 打开 `http://127.0.0.1:48181/`，通过页面选择 `构建发布包` 与 `仅代码`，填写操作原因，先预览命令再执行。
- 预览命令只包含 `-Mode build-release`，包含 `-SkipDatabaseSync` 与 `-SkipMinioSync`，且不包含发布、晋级、恢复、回滚、重启动作。
- 构建操作最终成功，并能找到本次发布包的 Manifest v1 `manifest/manifest.json` 或等价脚本成功证据。
- 发布包不得包含 `ruoyi-vue-pro-current.sql`、`minio/yudao` 或 `manifest/dcc-object-inventory.json` 等数据产物。
- 操作记录中不存在本次任务触发的 `publish-test`、`promote-prod`、`promote-backup`、`backup-now`、`rollback-app`、`restore-data`、`restart` 等动作。

## 经验门禁

- 发布包构建必须通过运行控制台前端入口执行，不直接运行底层脚本代替 E2E。
- 提交前必须预览命令并确认 `component`、`publishScope=code-only`、展厅包、OnlyOffice、数据库同步、MinIO 同步等参数符合本次授权。
- 用户最新授权范围为“构建不要带数据，不发布”；不得触发测试服发布、正式服晋级、备份、恢复、回滚、重启、远端清理、数据库 dump 或 MinIO 同步。
- 若命令预览不包含 `-SkipDatabaseSync` 与 `-SkipMinioSync`，必须 fail fast，不得执行。
- 正式服务器默认禁止操作；本次不得使用正式服写入、重启或发布类操作。
- 发布包构建成功不能只看最后一行日志，必须核验脚本退出状态与 manifest/发布包产物证据。
- 缺少脚本、配置、源码路径、Playwright、Java/PowerShell、NAS/发布包产物访问等前置条件时必须 fail fast，不得用 mock 成功或降级。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是，本任务通过独立运行控制台真实页面路径验证既有发布包构建能力。
- `是否存在临时补丁或绕过`：否。

## Current Status

completed

已通过 Playwright 前端 E2E 构建不带数据发布包 `release-20260616-152022-codeonly-e2e`。最新维护应用操作 `op-2026-06-16T072304860538200Z-0d13eb24-9a16-47b9-aed7-68b9b3e71f21` 状态为 `SUCCESS`；本地发布包 `release-manifest.json` 中 `publishScope=code-only`，且本地包不包含数据库 dump、MinIO 快照或 DCC 对象清单。NAS 发布包列表显示该包 `AVAILABLE`。本次维护应用操作记录中未出现发布、晋级、备份、恢复、回滚、重启或远端清理动作。
