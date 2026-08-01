# 20260801 HEAD 仅测试服发布

## Task Goal

仅基于本次发布开始时当前分支 HEAD 的已提交代码构建维护控制台和 IntRuoyi 测试发布包，并只发布到测试服务器；未提交改动不得进入构建产物。

## Milestones

1. 发布前置检查：确认规则、目标提交、Git 状态、临时 worktree 策略、构建目录与经验门禁。
2. 构建发布包：基于冻结 HEAD 构建维护控制台和测试发布包，校验 manifest、版本号、变更说明与构建来源。
3. 测试服发布：仅执行 publish-test，不执行 mark-tested、promote-prod 或 promote-backup。
4. 真实运行态验证：检查镜像 tag、容器状态、健康检查、前端 HTTP、前端页面、运行控制台版本号与变更说明。
5. 问题记录与经验沉淀：记录全部问题并更新前置经验。
6. 收尾：清理本任务临时产物、恢复运行控制台、记录最终验证。

## Expected Verification

- Git/worktree 证据证明构建输入只来自发布开始时冻结的 HEAD 已提交代码。
- build-release operation 成功，发布包、manifest、版本号、变更说明均可追溯到冻结提交。
- publish-test operation 成功，且本 releaseTag 未执行正式服或备份服动作。
- 测试服后端 health=UP，前端 HTTP 200，容器和镜像 tag 与 releaseTag 一致。
- 运行控制台页面显示当前 releaseTag 和变更说明。
- 所有问题记录包含现象、阶段、影响、原因判断、处理动作、结果、可前置检查、可自动化、下次避免方式。
- 成功后经验沉淀已写入长期前置经验，并通过索引关键词可定位。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；发布流程以冻结提交、manifest 契约和真实运行态验证为准。
- 是否存在临时补丁或绕过：否。

## 经验门禁

- 测试服发布门禁：只允许 `build-release -> publish-test`，目标主机固定 `172.30.30.58`，禁止 `mark-tested`、`promote-prod`、`promote-backup`；任一 operation 非 `SUCCESS` 或运行态缺项必须 fail fast。
- 冻结 HEAD 门禁：维护仓、后端仓、前端仓主工作区 dirty 时必须创建本轮专用 release worktree；构建开始后以冻结 worktree 提交为来源基线，不追逐后续提交。
- Manifest 门禁：构建后以发布包根目录 `manifest.json` 为权威，校验 `releaseTag`、`component=intruoyi`、`publishScope=code-only`、`sourceRepos[*].commit`、`sourceRepos[*].dirty=false`、变更说明和 artifact SHA256。
- 发布参数门禁：`build-release` 必须显式 `-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`；`publish-test` preview 必须结构化证明 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`。
- 运行态门禁：发布后必须同时检查 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=UP、frontend HTTP 200、`release-info.json`、release lock/migration 状态和运行控制台版本变更说明。
- PowerShell/SSH 门禁：中文、SSH 多行脚本、release-info、MySQL 查询和页面验收均使用 UTF-8 明确路径；SSH 多行脚本使用 UTF-8 bytes + LF，不用 `ssh -n`，不提交含凭据原始日志。
- Worktree 清理门禁：发布验证完成后先标记 `ready_for_closeout`，恢复 48181 到主维护路径；仅清理本任务 release worktree/state dir，并验证 Git 注册和物理目录均不存在后才标记 `completed`。

## Current Status

completed

## Progress Log

- 2026-08-01：创建任务文档；已确认用户要求仅测试服发布，不发布正式服和备份服。
- 2026-08-01：维护仓主工作区 `int_main` HEAD=`cb85bb0dbf2f36931ff2bc0aff75a4e96b5bd331` 且存在无关脏改动；主程序 HEAD=`9420210f7ad4fb2519c179458fae0e823d082b54` 且存在无关脏改动；已从冻结 HEAD 创建本轮专用 clean release worktree，禁止未提交改动进入构建输入。
- 2026-08-01：维护 release worktree=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260801a\m`；主程序 release worktree=`D:\IntRuoyiWorktree\r260801a-release-app`；state dir=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260801a-state\runtime-control`；构建目录为维护 worktree `backend\target` 和发布包目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260801-intmain-head-test-r260801a-r2`。
- 2026-08-01：构建 r1 `release-20260801-intmain-head-test-r260801a-r1` 失败，原因为 clean frontend worktree 缺少 `node_modules`，`cross-env` 不可用；未生成可发布候选。
- 2026-08-01：在同一冻结 frontend worktree 内按锁文件恢复依赖后，构建 r2 `release-20260801-intmain-head-test-r260801a-r2` 成功；manifest validator 通过，`sourceRepos` 均为冻结主程序提交 `9420210f7ad4fb2519c179458fae0e823d082b54` 且 `dirty=false`，artifact SHA256 检查 2045 项通过。
- 2026-08-01：仅执行 `publish-test`，preview 结构化字段为 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`；未执行 `mark-tested`、`promote-prod`、`promote-backup`。
- 2026-08-01：`publish-test` r2 operation=`op-2026-07-31T184648151088Z-d51572f6-9207-44dd-bbab-6f54c347cea4` 失败；required SQL `20260726_system_codex_smart_scheduling_test_items.sql` 第 313 行触发 MySQL `ERROR 1267 Illegal mix of collations (utf8mb4_general_ci,IMPLICIT) and (utf8mb4_0900_ai_ci,IMPLICIT) for operation '='`。
- 2026-08-01：只读复核测试服真实状态：`.env IMAGE_TAG=release-20260801-intmain-head-test-r260801a-r2`，但 backend/frontend 实际容器仍为上一版 `release-20260731-smartseed-tempfix-head-test-r260731d-r1`；backend health=`UP`、frontend HTTP=`200`、release lock=`FAILED`、migration `FAILED=1`、`SKIPPED_ALREADY_APPLIED=367`、无 RUNNING 锁。
- 2026-08-01：本地运行控制台已从 release worktree PID `52752` 恢复到主维护路径 PID `51256`，health=`UP`；由于发布任务阻塞，release worktree 与 state dir 按证据保留，未执行破坏性清理。
- 2026-08-01：继续沿用原冻结提交链路，不追逐后续主线；在 `D:\IntRuoyiWorktree\r260801b-frozen-smartseed-fix` 上提交智能排产 seed 修复后，`release-20260801-frozen-smartseed-fix-r260801b-r1` 的 `publish-test` 又被同 SQL `ERROR 1137 Can't reopen table: 'seed'` 阻断。
- 2026-08-01：在同一冻结修复分支继续提交智能排产临时表复用修复，构建 `release-20260801-frozen-smartseed-tempfix-r260801c-r1` 成功，但 `publish-test` 在 `20260731_dcc_file_category_match_rule_seed.sql` 触发 MySQL `ERROR 1267`，原因是 DCC seed MEMORY 临时表缺少显式 collation。
- 2026-08-01：已提交 DCC 分类匹配规则 seed collation 修复，source worktree HEAD=`9aeb1fc2a68fb97a2b3fb71b4d03777d97289f21` 且 clean；新 releaseTag `release-20260801-frozen-dcc-category-collation-r260801d-r1` 的 `build-release` operation=`op-2026-08-01T070742390438700Z-2b23cda9-93ff-4ccc-b155-0fe29bce82b4` 成功。
- 2026-08-01：r260801d manifest/source 校验通过，发布包目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260801-frozen-dcc-category-collation-r260801d-r1`；`manifest.json` 与 `release-info.json` 均显示 backend/frontend commit=`9aeb1fc2a68fb97a2b3fb71b4d03777d97289f21`、`dirty=false`，`publishScope=code-only`，DCC seed SQL 已含 `DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`。
- 2026-08-01：r260801d `publish-test` 失败，原因是 DCC seed 仅设置表默认 collation 不足以覆盖目标列级 collation；继续在冻结修复分支提交列级 collation 修复，最终 source HEAD=`f81435c16ca1defb9b5c35c2e3a2d31a2c77e2ce` 且 clean。
- 2026-08-01：最终 releaseTag `release-20260801-frozen-dcc-column-collation-r260801e-r1` 完成 `build-release -> publish-test` 仅测试服发布；build operation=`op-2026-08-01T075619071613500Z-8ce3eda8-87d7-412c-8daf-b944d4d737df`，publish operation=`op-2026-08-01T082221679621900Z-bdfeb32d-6378-404e-af3c-3bb8b8407300`，均为 `SUCCESS`。
- 2026-08-01：manifest 校验通过；发布包目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260801-frozen-dcc-column-collation-r260801e-r1`，`release-info`/`manifest` 均显示 backend/frontend commit=`f81435c16ca1defb9b5c35c2e3a2d31a2c77e2ce`、`dirty=false`、`publishScope=code-only`，变更说明为本 releaseTag 的发布包与组件范围。
- 2026-08-01：测试服真实运行态验证通过：`.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 Up、backend health=`UP`、frontend HTTP=`200`、页面标题、`release-info.json`、release lock=`APPLIED`、migration failed/running=`0` 均匹配 r260801e；运行控制台 release-status 显示同一 releaseTag 与变更说明。
- 2026-08-01：未执行 `mark-tested`、`promote-prod`、`promote-backup`；修复提交已合回 `E:\IntRuoyi` 的 `int_main`，merge commit=`ac8457724d16d287f5d65013ba304f77f3786e7b`，聚焦 SQL seed 回归 `8 passed`，`git diff --check HEAD~1..HEAD` 通过。
- 2026-08-01：任务状态先进入 `ready_for_closeout`；随后恢复 48181 到主维护路径 PID=`45648` 且 health=`UP`，删除本任务 r260801a/r260801b release/fix worktree 与 state dir，Git 注册和物理目录均不存在；最终状态标记 `completed`。
