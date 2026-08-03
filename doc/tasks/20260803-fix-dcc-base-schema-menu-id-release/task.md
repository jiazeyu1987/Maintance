# 20260803-fix-dcc-base-schema-menu-id-release

## Task Goal

修复上一轮仅测试服发布中 `20260513_dcc_base_schema.sql` 因 checksum 漂移重放导致 `system_menu.id=6813` 主键重复的问题，补充回归测试与迁移门禁后，基于新的已提交 HEAD 创建 clean release worktree，重新构建并仅发布到测试服务器；禁止复用失败 releaseTag，禁止执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

## Milestones

- [x] 任务前置门禁：确认上一轮 blocker、读取命中经验、记录 BDD/TDD 与发布安全约束。
- [x] RED：用可重复测试复现菜单 required SQL 在 checksum 漂移重放时固定 ID 已存在会失败或被门禁阻塞不足。
- [x] GREEN：修复 SQL 幂等性或发布前门禁，使重复执行不触发 `system_menu.PRIMARY` 冲突，并运行目标测试通过。
- [x] 回归验证：运行 migration policy gate、相关 SQL 静态/契约测试和必要构建测试。
- [x] 提交修复：仅提交本任务源代码、测试与任务记录，记录 commit hash。
- [x] 重新构建：从新的已提交 HEAD 创建 clean release worktree，构建维护控制台和测试发布包，校验 manifest、版本号和变更说明。
- [x] 仅测试服发布：只执行 `publish-test`，验证 operation、镜像 tag、容器、health、frontend HTTP、页面、运行控制台版本号与变更说明。
- [x] 问题记录与经验沉淀：记录所有问题和长耗时复盘，沉淀前置经验。
- [x] 收口清理：合回主程序 `int_main`、恢复 48181 主维护路径、清理本任务 release/fix worktree 和 state。

## Expected Verification

- 修复前 RED 测试失败，原因指向菜单 required SQL 重放固定 ID 主键冲突或缺少前置阻塞。
- 修复后目标 SQL/迁移测试 PASS，且 `run-release-migration-policy-gate.py` PASS。
- 新 releaseTag 的 manifest 证明 sourceRepos 均为新的已提交 HEAD 且 `dirty=false`。
- 测试服发布 `operation=SUCCESS`，远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP=200、`release-info.json`、运行控制台版本号和变更说明均指向同一新 releaseTag。
- 未执行 `mark-tested`、`promote-prod`、`promote-backup`。
- 所有问题、处理动作、结果、可前置化/自动化项均记录并沉淀。

## Current Status

completed

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。修复必须让迁移本身可幂等或让非幂等重放在发布前 fail fast，不允许跳过 SQL、手改 release state 或 mock 成功。
- 是否从根因和长期维护角度解决：是。根因是 required SQL checksum 漂移后重放时固定菜单 ID 和业务键幂等条件不一致，需通过源 SQL/门禁和测试治理。
- 是否存在临时补丁或绕过：否。不手工删除远端菜单、不覆盖迁移状态、不复用失败 releaseTag。

## Prior Blocker

- 上一轮 releaseTag `release-20260803-intmain-head-test-r260803a-r1` 的 `publish-test` 失败于 `20260513_dcc_base_schema.sql` line 1298，MySQL `ERROR 1062 Duplicate entry '6813' for key 'system_menu.PRIMARY'`。
- preflight-plan 将 `20260513_dcc_base_schema` 判定为 `APPLY`，原因是目标 checksum `9c6d4004565813ebfc8b1ad0454c6eb7d27302a348f426f1ad94795774c2bd33` 与 manifest checksum `4751b23cf28e932d936f3c6a81d9aee109afbd6fa509189dd50d589ac6abfe28` 不一致。
- 测试服已稳定回上一轮运行 tag；失败 releaseTag 不得复用。

## 经验门禁

- 仅测试服发布门禁：本轮只允许 `build-release -> publish-test`，目标测试服 `172.30.30.58`，禁止 `mark-tested`、`promote-prod`、`promote-backup`；成功必须同时核 operation、manifest、远端 `.env IMAGE_TAG`、实际镜像 tag、backend health、frontend HTTP、release-info、release lock、migration 和运行控制台版本变更说明。
- Clean worktree 来源门禁：维护仓、后端仓、前端仓主工作区 dirty 不得进入构建；必须创建本轮专用临时 release worktree，构建后核 `manifest.json sourceRepos[*].dirty=false` 且 commit 等于冻结提交。
- Required SQL checksum 漂移门禁：`20260513_dcc_base_schema` 这类 required SQL 若 target checksum 与 manifest checksum 不一致会重放，菜单 SQL 不得硬编码已占用 `system_menu.id`；失败 releaseTag 必须判废并用新 releaseTag 重建。
- PowerShell / SSH 承载门禁：中文文件读写显式 UTF-8；PowerShell 不使用 `&&`；远端 SSH 多行脚本用 UTF-8 bytes + LF；日志和配置输出必须脱敏。
- 失败后环境漂移门禁：`publish-test` 非 SUCCESS 时必须同时记录 operation、release lock、migration、`.env IMAGE_TAG`、实际镜像、health、HTTP；不得手改 release lock / migration / 远端菜单或复用失败 releaseTag。

## Fix Commit

- 主程序修复 worktree：`D:\IntRuoyiWorktree\20260803-fix-dcc-base-schema-menu-id-release`
- 修复分支：`codex/20260803-fix-dcc-base-schema-menu-id-release`
- 修复提交：`ae4c85511f050785f91b51f29c22c511df8e7cdc`
- 变更：`20260513_dcc_base_schema.sql` 的 DCC 受控打印菜单 seed 移除硬编码 `id=6813`，改由 `system_menu` 自增 ID 分配；新增静态合同测试防止回归。

## Release Evidence

- 维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260803b\m`，HEAD `ed7ef820d57fc0185e5c16a8be2e820a13384b15`，detached clean。
- 主程序 release worktree：`D:\IntRuoyiWorktree\r260803b-release-app`，HEAD `ae4c85511f050785f91b51f29c22c511df8e7cdc`，detached clean。
- releaseTag：`release-20260803-dcc-menu-replay-fix-test-r260803b-r1`；失败 releaseTag `release-20260803-intmain-head-test-r260803a-r1` 未复用。
- build-release operation：`op-2026-08-03T014004195140200Z-27256ee2-7aa4-4539-a982-044bd4f86239`，`SUCCESS`。
- publish-test operation：`op-2026-08-03T020027072659300Z-324edfd7-4658-4822-89ed-0e35e37f7feb`，`SUCCESS`。
- Manifest：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260803-dcc-menu-replay-fix-test-r260803b-r1\manifest.json`；`sourceRepos` 均为 `ae4c85511f050785f91b51f29c22c511df8e7cdc` 且 `dirty=false`，`publishScope=code-only`，`component=intruoyi`，changeSet 含发布包和组件范围。
- 测试服运行态：`remote-release-postcheck-r260803b-r1.json` 通过；`.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 Up、backend health=UP、frontend HTTP=200、`release-info.json`、release lock=APPLIED、当前 release migration FAILED/RUNNING=0。
- 运行控制台页面：Playwright 真实页面显示测试服 releaseTag，点击“查看变更”显示 `发布包：release-20260803-dcc-menu-replay-fix-test-r260803b-r1` 和 `组件范围：intruoyi`；截图位于 `output\playwright\r260803b-runtime-control\.playwright-cli\page-2026-08-03T02-29-55-705Z.png`。
- 测试服前端页面：Playwright 打开 `http://172.30.30.58:8081/`，返回登录页标题 `瑛泰管理系统 - 登录`；截图位于 `output\playwright\r260803b-runtime-control\.playwright-cli\page-2026-08-03T02-30-19-847Z.png`。

## Closeout Evidence

- 主程序合回：`E:\IntRuoyi` `int_main` 提交 `6b1fd19eb`（`任务: 合回DCC受控打印菜单重放修复`），只包含 `IntRuoyiBackend/script/tests/test_release_sql_idempotency_contract.py` 与 `IntRuoyiBackend/sql/mysql/20260513_dcc_base_schema.sql` 两个文件。
- 合回方式：先移出非本任务暂存文档，再用索引级补丁只暂存 SQL 中 `dcc:controlled-file:print` 菜单 hunk；同一 SQL 文件中的 product onboarding 未暂存 hunk 未进入本任务提交。
- 合回验证：`python -X utf8 -m pytest IntRuoyiBackend\script\tests\test_release_sql_idempotency_contract.py -q` 在 `E:\IntRuoyi` PASS，`15 passed in 0.33s`；提交当时 `git diff ae4c85511f050785f91b51f29c22c511df8e7cdc..HEAD -- <task files>` 无输出，证明主线目标文件与发布修复提交一致。
- 48181 恢复：停止本任务 release worktree 维护控制台 PID `33196`，从 `D:\ProjectPackage\Int\IntRuoyiMaintance` 启动主维护目录服务 PID `57912`，`http://127.0.0.1:48181/actuator/health` 返回 `UP`。
- worktree/state 清理：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260803b\m`、`D:\IntRuoyiWorktree\r260803b-release-app`、`D:\IntRuoyiWorktree\20260803-fix-dcc-base-schema-menu-id-release`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260803b-state` 均已删除；`git worktree list` 不再包含 r260803b release/fix worktree。
- task-closeout-cleanup：preview/apply 均通过，`delete=<none>`、`blocked=<none>`、`warnings=<none>`；发布证据按精确保留清单保留。
- 最终并发复核：收口后其它任务继续提交到 `E:\IntRuoyi` HEAD `134434c78`；`6b1fd19eb` 仍是当前 HEAD 祖先，且 `6b1fd19eb` 提交范围仍只含本任务两文件。当前目标两文件无暂存/工作区改动；相对 fix commit 的后续 SQL 差异来自其它任务提交，不属于本任务。

## Cleanup Keep

- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/build-release-log-tail-r260803b-r1.redacted.txt`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/build-release-operation-final-r260803b-r1.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/build-release-operation-latest-r260803b-r1.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/build-release-preview-gate-r260803b-r1.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/build-release-preview-r260803b-r1.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/build-release-submit-r260803b-r1.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/frontend-release-info-image-r260803b-r1.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/main-merge-migration-policy-gate-r260803b.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/manifest-summary-r260803b-r1.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/manifest-validation-r260803b-r1.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/migration-policy-gate-r260803b.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/publish-test-log-tail-r260803b-r1.redacted.txt`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/publish-test-operation-final-r260803b-r1.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/publish-test-operation-latest-r260803b-r1.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/publish-test-preview-gate-r260803b-r1.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/publish-test-preview-r260803b-r1.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/publish-test-submit-r260803b-r1.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/remote-release-postcheck-r260803b-r1.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/remote-release-precheck-r260803b-r1.json`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/remote_release_probe_r260803b.py`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/runtime_control_build_release.py`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/runtime_control_publish_test.py`
- `doc/tasks/20260803-fix-dcc-base-schema-menu-id-release/stage_main_fix_patch.py`
- `output/playwright/r260803b-runtime-control/`
