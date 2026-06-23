# 任务：基于当前 HEAD 完整发布三环境

## Goal

基于当前分支 `int_main` 最新已提交代码 `552a9dafac759012e1a199c2a9106d25372c1769` 构建维护控制台与 IntRuoyi 发布包，并按测试服、正式服、备份服顺序完成发布与真实运行态验证。构建产物不得包含当前工作区未提交改动。

## 上一任务检查

- 上一相关任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-runtime-control-current-release-notes\task.md`
- 状态：`COMPLETED`
- 处理：上一任务已提交为当前 HEAD，本次仅使用 HEAD 作为发布输入；根工作区存在大量未提交改动，必须创建干净 worktree 或等效干净 HEAD 构建来源。

## Scope

- 检查 Git 分支、HEAD、工作区脏状态，并建立干净构建来源。
- 构建维护控制台，并使用当前 HEAD 触发 `code-only` 发布包构建。
- 校验发布包、manifest、版本号、变更说明与 HEAD 提交一致。
- 发布到测试服务器并验证真实运行态。
- 测试服通过后，发布正式服务器与备份服务器并验证真实运行态。
- 将发布耗时点、失败点、重复操作和自动化优化项沉淀到经验文档。

## Non-Scope

- 不发布未提交改动。
- 不执行数据库/MinIO/展厅数据同步，除非发布 manifest 或预检明确要求且再次记录授权。
- 不修改正式服、测试服、备份服业务数据。
- 不以 mock、默认成功、静默跳过或手工改状态替代真实发布验证。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - 构建前确认运行控制台当前版本和构建预览命令。
  - 发布完成必须具备 operation、manifest、远端 `.env` / 镜像 tag、健康检查和真实页面证据。
  - dirty worktree 不得作为部署输入；发布包 manifest 必须证明 `sourceRepos.dirty=false`。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - 发布包必须校验 manifest、releaseTag、component、publishScope、变更说明和 artifact sha256。
  - 测试服先发布并验证，通过后才能继续正式服和备份服。
  - 远端 `.env`、后端镜像、前端镜像和发布 manifest 必须属于同一 `IMAGE_TAG`。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
  - 当前任务已由用户明确授权发布测试服、正式服和备份服。
  - 发布前确认目标主机、目录、容器、数据盘和远端容量；备份服必须显式使用 `/mnt/intruoyi-data`。
  - 远端凭据不得写入仓库、脚本、任务文档或运行控制台配置。
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
  - 涉及管理前端验证时使用真实页面；登录或页面异常必须记录实际入口与影响，不得静默切换环境或账号。
- `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
  - 根工作区脏时不得直接出包；发布隔离 worktree 必须记录路径、分支、commit、构建命令和验证命令。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
  - 同一 releaseTag 必须一次性走通 build/test/prod/backup；不要拼接多轮结果。
  - 处理 RUNNING 锁前必须核活跃进程和 operation 真实状态，禁止直接改锁。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；缺少凭据、manifest、schema/迁移证据、远端访问或真实运行态证据时直接阻塞。
- `是否从根因和长期维护角度解决`：是；本次通过干净 HEAD worktree、manifest 校验和三环境运行态证据闭环发布。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 干净 HEAD 构建 -> Given 根工作区存在未提交改动 When 创建干净 worktree 并从 HEAD 构建 Then 发布包 sourceRepos 显示 dirty=false 且 commit 为 552a9dafac759012e1a199c2a9106d25372c1769。`
- `BDD: 测试服先行发布 -> Given 发布包 manifest 校验通过 When 部署测试服 Then 远端 .env、前后端镜像 tag、健康检查、前端页面和运行控制台版本说明均显示本次 releaseTag。`
- `BDD: 正式服与备份服发布门禁 -> Given 测试服验证通过 When 发布正式服和备份服 Then 两个环境真实运行态均与同一 releaseTag 一致，运行控制台显示版本号和变更说明。`

## Milestones

1. 完成任务文档、经验门禁、Git HEAD 和 dirty 状态记录。`COMPLETED`
2. 创建干净 HEAD 构建来源并构建维护控制台。`COMPLETED`
3. 通过运行控制台或等价前端操作构建发布包并校验 manifest。`COMPLETED`
4. 发布测试服并验证真实运行态。`COMPLETED`
5. 发布正式服和备份服并验证真实运行态。`COMPLETED`
6. 记录经验沉淀、收尾清理预览、提交本任务文档。`IN_PROGRESS`

## Expected Verification

- `git status --short --branch` 记录根工作区 dirty 状态。
- `git worktree add <clean-path> int_main` 或等效干净 HEAD 来源。
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1` 在干净 worktree 通过。
- 发布包 manifest 校验：`releaseTag`、`component=intruoyi`、`publishScope=code-only`、`sourceRepos.dirty=false`、HEAD commit、artifact sha256、changeSet。
- 测试服、正式服、备份服：远端 `.env`、`docker compose ps`、后端健康、前端页面、运行控制台 release-status。

## Current Status

COMPLETED：`release-20260624-head-full-v3` 已从干净已提交代码构建并发布到测试服、正式服、备份服；三环境运行态和控制台版本信息均验证通过；task-closeout-cleanup 预览通过，无删除项、无阻塞。

## Verification Evidence

- 根维护仓 HEAD：`552a9dafac759012e1a199c2a9106d25372c1769`，提交信息 `任务: 增加当前版本变动说明`。
- 维护控制台干净 worktree：`D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260624-head`，detached HEAD `552a9dafac759012e1a199c2a9106d25372c1769`，初始 `git status` 干净。
- 后端干净 worktree：`D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260624-head`，detached HEAD `faa5a6b2c87201b510b4f33bd4e5aa1eef1ac147`，初始 `git status` 干净。
- 前端干净 worktree：`D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260624-head`，detached HEAD `317056aa6a2db9dc1cf51e5bbf5e00d9e163729d`，初始 `git status` 干净。
- `python -X utf8 ops\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260624-head\sql\mysql` -> FAIL，错误为 `missing release-migration metadata: ...\20260623_dcc_view_matrix_independent_source.sql`。
- 全量只读扫描缺失元数据文件数量：`1`，文件为 `20260623_dcc_view_matrix_independent_source.sql`。
- 后端仓库已提交修复：`bdf2e35a30a1b679c59b6253f2a62250b62ffd43`，提交信息 `任务: 补齐DCC查看矩阵发布元数据`。
- 后端验证：`python -X utf8 -m pytest script\tests\test_dcc_view_matrix_independent_source_sql.py -q` -> PASS，`3 passed`。
- 后端验证：`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，`migrationCount=188`。
- 维护控制台 clean build 第一次失败：缺少 `doc/tasks/20260620-prod-release-current-latest/prod-target-config.json`。
- 维护控制台 clean build 第二次失败：`RuntimeControlOriginalParityTest.promoteProdPreviewUsesSanitizedPackageWorkspace` 报告干运行净化工作区缺少 `resources/resource-reference-manifest.json`。
- 维护控制台 targeted 验证：`mvn -f backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#promoteProdPreviewUsesSanitizedPackageWorkspace -DtrimStackTrace=false test` -> PASS。
- 维护控制台主工作区完整构建：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1` -> PASS，前端 typecheck/build、后端 23 tests、jar 打包均通过。
- 维护控制台干净 worktree 完整构建：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1` -> FAIL，`RuntimeControlOriginalParityTest.promoteProdPreviewUsesSanitizedPackageWorkspace` 在深层 worktree 路径下报告 `resources/resource-reference-manifest.json` 找不到。
- 维护控制台路径长度修复 targeted 验证：`mvn -f backend\pom.xml -Dtest=RuntimeControlOriginalParityTest#promoteProdPreviewUsesSanitizedPackageWorkspace -DtrimStackTrace=false test` -> PASS。
- 维护控制台路径长度修复主工作区完整构建：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1` -> PASS，前端 typecheck/build、后端 23 tests、jar 打包均通过。
- 维护控制台干净 worktree：`D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260624-0736fb7`，HEAD `0736fb715451a4f88829880a39272db0d7ea4f2c`，完整构建 PASS。
- 发布包最终版本：`release-20260624-head-full-v3`。
- 发布包 manifest：`releaseTag=release-20260624-head-full-v3`，`publishScope=code-only`，`component=intruoyi`，后端 sourceRepo `bdf2e35a30a1b679c59b6253f2a62250b62ffd43 dirty=false`，前端 sourceRepo `317056aa6a2db9dc1cf51e5bbf5e00d9e163729d dirty=false`。
- 构建 operation：`op-2026-06-23T173205500308500Z-280a1cfd-ce31-4016-a2e5-45a71886e6c6` -> SUCCESS。
- 测试服发布 operation：`op-2026-06-23T174444462635200Z-f8253075-3157-4647-8588-eed209b0a9da` -> SUCCESS。
- 测试服运行态：`172.30.30.58` `.env IMAGE_TAG=release-20260624-head-full-v3`；`intruoyi-backend` / `intruoyi-frontend` 镜像 tag 均为 v3 且 running；后端健康 HTTP 200；前端 HTTP 200；Playwright 打开登录页成功，截图 `output/playwright/release-20260624-head-full-v3-test-frontend.png`。
- 标记测试通过 operation：`op-2026-06-23T180242570470700Z-d7a4ccad-d746-498b-a353-019e38749182` -> SUCCESS。
- 正式服发布 operation：`op-2026-06-23T180402319749900Z-96551295-7c9b-49e6-b5d7-66af9943671e` -> SUCCESS。
- 正式服运行态：`172.30.30.57` `.env IMAGE_TAG=release-20260624-head-full-v3`；`intruoyi-backend` / `intruoyi-frontend` 镜像 tag 均为 v3 且 running；后端健康 HTTP 200；前端 HTTP 200；控制台 prod 当前版本 v3。
- 备份服发布 operation：`op-2026-06-23T181552882833300Z-bae3d087-739d-4269-be02-e6cd7eb7c9b9` -> SUCCESS。
- 备份服运行态：`172.30.30.59` `.env IMAGE_TAG=release-20260624-head-full-v3`；`intruoyi-backend` / `intruoyi-frontend` 镜像 tag 均为 v3 且 running；后端健康 HTTP 200；前端 HTTP 200；控制台 backup 当前版本 v3。
- 控制台 release-status：test/prod/backup 均为 `release-20260624-head-full-v3`，release notes 指向 `Backup/ReleasePackage/release-20260624-head-full-v3/manifest.json`，sourceRepos 均为后端 `bdf2e35... dirty=false`、前端 `317056a... dirty=false`。

## Blockers

- 暂无阻塞。

## Next Required Action

- 提交本任务文档与经验沉淀。
