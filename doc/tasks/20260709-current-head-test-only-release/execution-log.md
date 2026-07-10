# Execution Log - 20260709 current HEAD test-only release

- USER_REQUEST: 仅基于当前分支最新已提交代码构建并发布到测试服务器；未提交改动不得进入构建产物；发布后验证真实运行态、运行控制台版本号和变更说明，并记录问题和沉淀前置经验。
- BDD: 当前 HEAD 测试服发布 -> Given 三仓主工作区存在未提交改动且目标 HEAD 已固定 / When 从目标 HEAD 创建干净临时 worktree 构建并发布到测试服 / Then 发布包 manifest 必须证明 sourceRepos 为目标提交且 dirty=false，测试服真实运行态必须运行同一 releaseTag。
- BDD: 发布信息可追溯 -> Given build-release 生成发布包 / When 检查 manifest、版本号和变更说明 / Then 版本号和变更说明必须对应本次构建 releaseTag 与组件范围，否则阻塞发布。
- GREEN: task-doc-init -> PASS, taskDir=D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260709-current-head-test-only-release.
- GREEN: experience-preflight -> PASS, 已读取并摘录发布/构建/manifest/worktree/PowerShell/测试服运行态门禁；高风险动作仅允许在干净临时 worktree 与结构化验证通过后继续。
- GREEN: initial-git-baseline -> PASS, maintance=1fe4d64a6d4a8840aca061aca3c0c6d72a07d280, backend=ebe2bd33e664ce910b9505cec4bdfb8b46a82a1c, frontend=cbf1896104dbc7d5797a615928e118cccabc4d04; 三仓主工作区均非 clean，必须创建干净临时 worktree；证据=evidence/initial-repo-heads-and-dirty-status.json.

## 问题记录
- ISSUE: source HEAD drift before build; 阶段=构建前 worktree 门禁；现象=后端 source HEAD 从旧 worktree 的 ebe2bd33e664ce910b9505cec4bdfb8b46a82a1c 前进到 6b0a114e2c9231ef42b4f94f3de7f73112d7d9de；影响=旧 r260709t 不再代表“当前分支最新已提交代码”，必须废弃，不得构建；原因判断=并行开发提交推进 int_main；处理动作=安全移除未构建旧 worktree，重新创建 $newRoot；结果=三仓新 worktree 均匹配当前 source HEAD 且 dirty=false；是否可前置检查=是；是否可自动化=是；下次避免=build 前最后一步再次比较 source HEAD 与 worktree HEAD。
- GREEN: release-worktree-recreate-after-head-drift -> PASS, newWorktreeRoot=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709t2; maintance=1fe4d64a6d4a8840aca061aca3c0c6d72a07d280, backend=6b0a114e2c9231ef42b4f94f3de7f73112d7d9de, frontend=cbf1896104dbc7d5797a615928e118cccabc4d04; 证据=evidence/release-worktree-recreated-after-head-drift.json.- GREEN: task-doc-variable-fix -> PASS, releaseTag 与 worktree/buildDir 变量残留已修正。
- ISSUE: maintenance build capture failed on pnpm stderr; 阶段=维护控制台构建；现象=corepack pnpm@10.25.0 build 2>&1 | Tee-Object 在 Vite 构建完成后因 PowerShell NativeCommandError 中断，未进入 Maven 打包；影响=本次构建未完成，不能继续发布包构建；原因判断=PowerShell 5.1 在 $ErrorActionPreference=Stop 下把 native stderr 当成终止错误，而 Vite 黄色提示不等于构建失败；处理动作=改用 Start-Process/重定向文件捕获 stdout/stderr 并以进程退出码判定；结果=待重试；是否可前置检查=是；是否可自动化=是；下次避免=发布构建日志采集不得使用会把 stderr 自动升级为终止错误的管道。- ISSUE: maintenance build retry helper incompatible with Windows PowerShell ProcessStartInfo.ArgumentList; 阶段=维护控制台构建重试；现象=封装函数调用 corepack 前报 null-valued expression；影响=未执行构建命令；原因判断=当前运行时不支持按集合追加 ArgumentList；处理动作=改用 Start-Process + 参数字符串 + stdout/stderr 文件重定向；结果=待重试；是否可前置检查=是；是否可自动化=是；下次避免=PowerShell 5.1 中优先使用 Arguments 字符串或 Start-Process 参数字符串。
- GREEN: maintenance-runtime-build -> PASS, pnpm=10.25.0; jar=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709t2\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar; distIndex=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709t2\m\frontend\dist\index.html; 证据=evidence/maintenance-build-summary.json 与 evidence/maintenance-build-retry2.log.
- ISSUE: clean maintenance worktree missing runtime-control.local.yaml; 阶段=运行控制台启动；现象=临时维护仓 HEAD 只包含 config/runtime-control.example.yaml，不包含本机 operator local config；影响=首次启动配置切换失败，尚未启动控制台；原因判断=runtime-control.local.yaml 是本机未跟踪运行配置，不属于构建源码；处理动作=先冻结 main/worktree config 文件证据，下一步仅复制本机 operator config 到临时 worktree 并改 repo/frontend/ops/state 路径，不将其纳入发布包源码；结果=待执行；是否可前置检查=是；是否可自动化=是；下次避免=启动临时维护控制台前先检查 local config 是否存在并明确来源。
- GREEN: runtime-control-config-copy-switch-and-start -> PASS, pid=14148, health=123 34 115 116 97 116 117 115 34 58 34 85 80 34 125; 上一次启动命令因会话返回码异常未写入成功记录，本次独立诊断确认 48181 监听与 health=UP；证据=evidence/runtime-control-start-summary-after-diagnosis.json。
- ISSUE: r260709t2 cleanup required scoped residual removal; 阶段=旧临时 worktree 清理；现象=maintenance worktree 已注销但构建残留导致 git worktree remove 报 Directory not empty，backend/frontend 仍注册；影响=无法复用该路径继续当前 HEAD 发布；处理动作=确认无 r260709t2 Java 进程后，先移除已注册 b/f worktree，再限定删除 D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709t2 残留；结果=已创建 r260709t3 干净发布输入；是否可前置检查=是；是否可自动化=是；下次避免=worktree remove 失败后区分 Git 注册状态与残留目录。
- GREEN: release-worktree-r260709t3-created -> PASS, newWorktreeRoot=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709t3; maintance=1fe4d64a6d4a8840aca061aca3c0c6d72a07d280, backend=51901743cc8f3ca63082b564132a2baa5e143859, frontend=5e644c5318c04e83cb989045280c983154ab9099; 证据=evidence/release-worktree-r260709t3-created.json.
- GREEN: release-target-freeze-before-maintenance-build -> PASS, releaseRoot=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709t3; 三仓发布目标 worktree 均 clean；后续构建以该冻结目标提交为准，不允许未提交改动进入。证据=evidence/release-target-freeze-before-maintenance-build.json。
- GREEN: runtime-control-r260709t3-start -> PASS, pid=66524, health={"status":"UP"}; 上次命令已实际启动，本次补写启动证据；证据=evidence/runtime-control-start-r260709t3-summary.json。
- GREEN: build-release-preview -> PASS, action=build-release, Component=intruoyi, publishScope=code-only, releaseTag=release-20260709-current-head-test, SkipDatabaseSync/SkipMinioSync present, no prod/backup/SmartRelease action; 证据=evidence/build-release-preview.json。
- GREEN: build-release-execute-started -> PASS, operationId=op-2026-07-09T131818532463200Z-6a0e89b5-5104-4450-b93a-4e07718cb01d, releaseTag=release-20260709-current-head-test。
- GREEN: build-release-operation -> PASS, operationId=op-2026-07-09T131818532463200Z-6a0e89b5-5104-4450-b93a-4e07718cb01d, releaseTag=release-20260709-current-head-test, status=SUCCESS; 证据=evidence/build-release-operation-latest.json / evidence/build-release-operation.log。
- GREEN: manifest-validation -> PASS, packageRoot=E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260709-current-head-test; publishScope=code-only; backend=51901743cc8f3ca63082b564132a2baa5e143859 dirty=false; frontend=5e644c5318c04e83cb989045280c983154ab9099 dirty=false; imageTarSize=815089152; changeSummary=Release package release-20260709-current-head-test; 证据=evidence/manifest-validation.json。
- ISSUE: publish-test preview validation expected -TargetEnvironment arg; 阶段=publish-test 预览本地校验；现象=preview.data.environment=test 但 arguments 未包含 -TargetEnvironment，脚本由 publish-test action 固定 test 环境参数；影响=首次 publish-test 未执行；原因判断=本地校验规则沿用 deploy action 通用参数，未匹配当前维护控制台 PUBLISH_TEST 映射；处理动作=读取 preview JSON 与 RuntimeControlOperationAction，改为以 preview.data.environment=test、Mode=deploy-release、TestServerHost=172.30.30.58、ReleaseTag 匹配且无 prod/backup 动作为准；结果=待重试；是否可前置检查=是；是否可自动化=是；下次避免=publish-test 校验以结构化 environment 字段优先，不强制不存在的 -TargetEnvironment 参数。
- GREEN: publish-test-preview-retry -> PASS, action=publish-test, Mode=deploy-release, Environment=test, ServerHost/TestServerHost=172.30.30.58, RemoteAppDir=/opt/intruoyi/runtime, releaseTag=release-20260709-current-head-test; 未出现 promote-prod/promote-backup/mark-tested；证据=evidence/publish-test-preview-retry.json。
- GREEN: publish-test-execute-started -> PASS, operationId=op-2026-07-09T133736857125Z-7f65f377-b8cf-4a9b-9115-8f733ab81ceb, releaseTag=release-20260709-current-head-test。
- BLOCKER: publish-test -> FAILED, operationId=op-2026-07-09T133736857125Z-7f65f377-b8cf-4a9b-9115-8f733ab81ceb, releaseTag=release-20260709-current-head-test; summary=å½ä»¤éåºç é 0: 1; 证据=evidence/publish-test-operation-latest.json / evidence/publish-test-operation.log。

- 2026-07-09T21:53:29
  - BDD: 测试服发布 SQL 不使用 prepared SIGNAL -> Given 发布 SQL 包含 fail-fast 数据冲突检查；When 发布脚本通过 mysql 客户端执行 required SQL；Then SQL 不得通过 PREPARE/EXECUTE 执行 SIGNAL SQLSTATE，避免 MySQL prepared-statement 协议 1295 错误。
  - RED: python -X utf8 -m pytest script/tests/test_release_sql_no_prepared_signal.py -q -> FAIL, expected reason: prepared SIGNAL detected in 20260613_mes_smart_scheduling_t1_schema.sql; evidence: evidence/red-release-sql-no-prepared-signal.log.
- ISSUE: backend repo missing experience index; 阶段=发布失败后后端 SQL 修复任务建档；现象=后端 worktree 与源仓均缺少 docs/experience-index.md；影响=无法按后端仓本地索引摘取经验门禁；原因判断=后端仓未建立统一经验索引文件；处理动作=记录为流程问题，按维护仓发布经验索引继续本次发布 SQL 修复；结果=后端任务文档已写入该问题和维护仓发布门禁；是否可前置检查=是；是否可自动化=是；下次避免=发布修复任务开始前自动检查所有参与仓 docs/experience-index.md 是否存在。
- 2026-07-09T22:03:08
  - ISSUE: backend commit hook required TDD_TASK_DIR; 阶段=后端修复提交；现象=首次 git commit 被钩子拦截：TDD compliance failed: set TDD_TASK_DIR；影响=未产生提交，修复仍在暂存区；原因判断=提交钩子要求显式绑定任务目录；处理动作=记录问题并带 TDD_TASK_DIR 重试提交；结果=待重试；是否可前置检查=是；是否可自动化=是；下次避免=所有仓库提交前统一设置 TDD_TASK_DIR 为当前任务目录。
- GREEN: backend-sql-fix-committed-in-release-worktree -> PASS, firstCommit=b0dedcdc904ec66800ecedd601cfc5ed7a9600a1, finalHead=b1ff9a54085d5e538de5b9a75c420f1af90da434; 后续必须先合回后端 int_main，再从最新已提交 HEAD 创建新发布 worktree 重建发布包。
- GREEN: backend-fix-ff-merged-to-int-main -> PASS, targetCommit=b1ff9a54085d5e538de5b9a75c420f1af90da434; sourceBranch=int_main; dirty files checked for overlap before merge; evidence=evidence/backend-fix-ff-merge-to-int-main.log.
- ISSUE: frontend source HEAD drift after backend SQL fix; 阶段=重新冻结发布输入；现象=前端 source HEAD 已前进到 33b5c4532e2443191a73657ad02c6bf4a147fcaf，而旧 release worktree 仍是 5e644c5318c04e83cb989045280c983154ab9099；影响=旧 worktree 不再满足“当前分支最新已提交代码”；原因判断=并行开发提交推进前端 int_main；处理动作=确认前端 release worktree clean 后 checkout --detach 到当前 HEAD；结果=三仓 release worktree 与 source HEAD 一致，后续 releaseTag=release-20260709-current-head-test-v2；是否可前置检查=是；是否可自动化=是；下次避免=修复提交合入后重建发布包前再次比较三仓 source HEAD 与 release worktree HEAD。
- GREEN: release-target-refreeze-after-frontend-drift -> PASS, releaseRoot=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709t3, backend=b1ff9a54085d5e538de5b9a75c420f1af90da434, frontend=33b5c4532e2443191a73657ad02c6bf4a147fcaf, maintenance=1fe4d64a6d4a8840aca061aca3c0c6d72a07d280; evidence=evidence/release-target-refreeze-after-frontend-checkout.json.
- GREEN: frontend-current-head-build-reproduction -> FAIL, command=pnpm build:test, frontendHead=6a7e761855f4b5d635defc3f1febb2225293df2a, exitCode=3; evidence=evidence/frontend-current-head-build-test-process.json.
## 阶段记录：发布输入再次漂移阻塞（2026-07-09 22:41:48 +08:00）

- 当前进度：已完成维护控制台启动、首轮构建、首轮测试发布失败诊断、发布 SQL 修复提交、前端构建问题诊断；尚未完成新一轮测试服发布。
- 阻塞点：构建输入在长时间过程中再次漂移，当前源仓 HEAD 与临时发布 worktree 不一致，不能继续构建或发布。
- 目标约束：本次发布只允许基于当前分支最新已提交代码构建，未提交改动不得进入构建产物。
- 当前维护源 HEAD：1fe4d64a6d4a8840aca061aca3c0c6d72a07d280，发布 worktree HEAD：1fe4d64a6d4a8840aca061aca3c0c6d72a07d280。
- 当前后端源 HEAD：aa0b10bfe81d7e4ac12af4b04258638d5ae82cc6，发布 worktree HEAD：b1ff9a54085d5e538de5b9a75c420f1af90da434。
- 当前前端源 HEAD：a9fe40e8416958eaa0d724c109fe598b567f37e7，发布 worktree HEAD：6a7e761855f4b5d635defc3f1febb2225293df2a。
- BLOCKER: release-input-head-drift -> 后端源仓已前进到 aa0b10bfe8，前端源仓已前进到 a9fe40e84，发布 worktree 仍停留在旧 HEAD；继续构建会违反“当前分支最新已提交代码”验收条件。
- 影响：暂停 build-release-v3 / publish-test；必须重新冻结后端和前端发布 worktree 到当前源仓 HEAD，并验证 worktree clean 后再构建。
- 处理动作：记录阻塞与证据，下一步重新 checkout 发布 worktree 到当前源仓 HEAD 后重新执行构建。
- 是否可前置检查：是；每次重试 build-release 前必须对比 source HEAD 与 release worktree HEAD。
- 是否可自动化：是；发布脚本或前置检查可加入 source/release HEAD 一致性校验。
- 下次如何避免：长耗时排障后，不复用旧冻结结论；每次重新构建前强制 refreeze 并写入 evidence。

## 阶段记录：build-release-v3 已提交（2026-07-09 22:42:23 +08:00）

- releaseTag：release-20260709-current-head-test-v3
- 后端发布 HEAD：aa0b10bfe81d7e4ac12af4b04258638d5ae82cc6
- 前端发布 HEAD：a9fe40e8416958eaa0d724c109fe598b567f37e7
- 构建范围：code-only，仅测试服发布前构建。
- 操作 ID：
- GREEN: release-input-refreeze-v3 -> PASS，source HEAD 与 release worktree HEAD 一致，后端/前端发布 worktree clean。


## 阶段记录：build-release-v3 完成（2026-07-09 22:56:45 +08:00）

- releaseTag：release-20260709-current-head-test-v3
- 操作 ID：op-2026-07-09T144223086798200Z-ada09c10-e67d-4697-8ac3-1c40520a984c
- 结果：SUCCESS
- 摘要：å½ä»¤æ§è¡å®æ
- GREEN: build-release-v3 -> PASS
- 证据：evidence/build-release-v3-operation-latest.json；evidence/build-release-v3-operation.log


## 阶段记录：发布包与 manifest 校验通过（2026-07-09 22:58:23 +08:00）

- releaseTag：release-20260709-current-head-test-v3
- 发布包目录：E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260709-current-head-test-v3
- manifest：E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260709-current-head-test-v3\manifest.json
- 后端目标提交：aa0b10bfe81d7e4ac12af4b04258638d5ae82cc6
- 前端目标提交：a9fe40e8416958eaa0d724c109fe598b567f37e7
- GREEN: manifest-release-source-v3 -> PASS，manifest 包含 releaseTag、后端 HEAD、前端 HEAD 与 code-only 范围。
- 证据：evidence/build-release-v3-manifest-validation.json


## 阶段记录：publish-test-v3 预览通过（2026-07-09 22:59:22 +08:00）

- releaseTag：release-20260709-current-head-test-v3
- 后端 manifest 提交：aa0b10bfe81d7e4ac12af4b04258638d5ae82cc6
- 前端 manifest 提交：a9fe40e8416958eaa0d724c109fe598b567f37e7
- GREEN: publish-test-preview-v3 -> PASS，预览 action=publish-test，未包含 promote-prod / promote-backup / mark-tested。
- 证据：evidence/pre-publish-v3-source-check.json；evidence/publish-test-v3-preview.json


## 阶段记录：release-20260709-current-head-test-v3 发布前源提交漂移（2026-07-09 22:59:52 +08:00）

- 现象：publish-test-v3 预览后，源仓 HEAD 与 v3 manifest / release worktree 不一致。
- 阶段：发布到测试服务器前置检查。
- 影响：不得继续发布 release-20260709-current-head-test-v3，否则发布包不再代表当前分支最新已提交代码。
- 原因判断：长时间构建/排障期间其他任务继续向源仓提交。
- 处理动作：终止 v3 发布，重新冻结发布 worktree 到当前源仓 HEAD，改用 release-20260709-current-head-test-v4 重新构建。
- 结果：进入 v4 重新构建流程。
- 是否可前置检查：是，publish-test 执行前必须再次校验 source HEAD = release HEAD = manifest commit。
- 是否可自动化：是，发布脚本可在执行 deploy-release 前强制比较源仓 HEAD 与 manifest commit。
- 下次如何避免：预览和实际发布之间也要做最终 HEAD 锁定检查。
- BLOCKER: publish-test-v3-source-drift -> frontend source 27b1db976 != release a9fe40e84。


## 阶段记录：build-release-v4 已提交（2026-07-09 22:59:55 +08:00）

- releaseTag：release-20260709-current-head-test-v4
- 后端发布 HEAD：aa0b10bfe81d7e4ac12af4b04258638d5ae82cc6
- 前端发布 HEAD：27b1db976b61bf91f91ffc083c4b2ac1f7bc92ea
- 构建范围：code-only，仅测试服发布前构建。
- 操作 ID：op-2026-07-09T145955768990Z-cccbfc10-4bdb-416b-b747-cb6a2a0f4e22
- GREEN: release-input-refreeze-v4 -> PASS，source HEAD 与 release worktree HEAD 一致，后端/前端发布 worktree clean。
- 证据：evidence/release-target-refreeze-v4.json；evidence/build-release-v4-submit.json


## 阶段记录：runtime-control 不可用后的本地诊断（2026-07-09 23:24:54 +08:00）

- 现象：恢复轮询 build-release-v4 时本机 48181 无法连接。
- 阶段：构建操作恢复检查。
- 影响：不能通过 API 查询操作状态，改为检查操作日志与发布包目录。
- 处理动作：读取本地 operation log、检查发布包与 manifest。
- 结果：LIKELY_SUCCESS_LOG_REVIEW_REQUIRED。
- 证据：evidence/runtime-down-build-v4-local-diagnosis.json


## 阶段记录：v4 中断后继续诊断（2026-07-09 23:25:45 +08:00）

- 现象：上一轮恢复检查发现 runtime-control 不可连接，补充检查进程、operation log、v4 发布包目录和前端构建产物。
- 结果：诊断证据已写入 evidence/continue-recon-after-v4-runtime-down.json。


## 阶段记录：v4 构建中断根因补充检查（2026-07-09 23:26:32 +08:00）

- 阶段：build-release-v4 前端构建后。
- 处理动作：检查 operation log、残留进程、前端 dist-intruoyi-test、发布包目录和源码 HEAD。
- 证据：evidence/v4-hang-root-cause-inspection.json


## 阶段记录：v4 构建未闭合，准备 v5（2026-07-09 23:27:03 +08:00）

- 现象：本机运行控制台 48181 不可连接，v4 发布包目录存在但 manifest.json 不存在，operation log 停在前端 pnpm build:test 附近。
- 阶段：build-release-v4 结果确认。
- 影响：v4 无法证明发布包完整、manifest、版本号和变更说明，因此不得继续发布。
- 原因判断：长时间操作/中断后运行控制台进程已退出，构建流程未生成最终 manifest。
- 处理动作：记录 v4 为未闭合构建；因后端源仓 HEAD 又前进到 81049db212，必须重新冻结并改用 release-20260709-current-head-test-v5 重建。
- 结果：进入 v5 前置检查与运行控制台恢复。
- 是否可前置检查：是；构建完成后必须检查 manifest 存在且 operation SUCCESS。
- 是否可自动化：是；构建脚本应在前端构建后和写 manifest 前持续写阶段状态，便于恢复判断。
- 下次如何避免：长时间构建时避免中断轮询；恢复后先检查 manifest，不复用半成品发布包。
- BLOCKER: build-release-v4-incomplete -> runtime-control down and manifest missing.

## 阶段记录：build-release-v5 已提交（2026-07-09 23:29:44 +08:00）

- releaseTag：release-20260709-current-head-test-v5
- 运行控制台：127.0.0.1:48181 health=UP
- 后端发布 HEAD：81049db2125cc237f73f29abcfcbddd3c41e743d
- 前端发布 HEAD：27b1db976b61bf91f91ffc083c4b2ac1f7bc92ea
- 构建范围：code-only，仅测试服发布前构建。
- 操作 ID：op-2026-07-09T152944883286600Z-97cb6dc8-be4b-4ffb-b01e-eca5e315ef2a
- GREEN: release-input-refreeze-v5 -> PASS，source HEAD 与 release worktree HEAD 一致，后端/前端发布 worktree clean。
- 证据：evidence/release-target-refreeze-v5.json；evidence/build-release-v5-submit.json


## 阶段记录：build-release-v5 完成（2026-07-09 23:42:47 +08:00）

- releaseTag：release-20260709-current-head-test-v5
- 操作 ID：op-2026-07-09T152944883286600Z-97cb6dc8-be4b-4ffb-b01e-eca5e315ef2a
- 结果：SUCCESS
- 摘要：å½ä»¤æ§è¡å®æ
- GREEN: build-release-v5 -> PASS
- 证据：evidence/build-release-v5-operation-latest.json；evidence/build-release-v5-operation.log


## 阶段记录：build-release-v5 manifest 校验失败（2026-07-09 23:43:57 +08:00）

- releaseTag：release-20260709-current-head-test-v5
- 失败项：frontendManifestMatchesSource
- 影响：不得执行 publish-test。
- BLOCKER: manifest-validation-v5 -> frontendManifestMatchesSource。
- 证据：evidence/build-release-v5-manifest-validation.json


## 阶段记录：release-20260709-current-head-test-v5 发布前提交漂移（2026-07-09 23:45:33 +08:00）

- 现象：release-20260709-current-head-test-v5 构建成功后，manifest 提交与源仓当前 HEAD 不一致。
- 阶段：publish-test 前 manifest/source 终检。
- 影响：不得发布 release-20260709-current-head-test-v5，否则不满足当前分支最新已提交代码。
- 原因判断：长时间构建期间源仓继续新增提交。
- 处理动作：停止 release-20260709-current-head-test-v5 发布，重新冻结发布 worktree，改用 release-20260709-current-head-test-v6 重建。
- 结果：进入 release-20260709-current-head-test-v6 构建。
- 是否可前置检查：是，publish-test 前强制比对 manifest commit 与源仓 HEAD。
- 是否可自动化：是，部署动作可内置 manifest/source HEAD 终检。
- 下次如何避免：构建成功后立即执行终检并发布，若源仓漂移则废弃旧 tag。
- BLOCKER: publish-test-v5-source-drift -> frontend manifest 27b1db976b != source a77812a43。
- 证据：evidence/v5-source-drift-before-publish.json

## 阶段记录：build-release-v6 已提交（2026-07-09 23:45:37 +08:00）

- releaseTag：release-20260709-current-head-test-v6
- 后端发布 HEAD：81049db2125cc237f73f29abcfcbddd3c41e743d
- 前端发布 HEAD：a77812a43103eb77c794b481c3ded898811fce69
- 构建范围：code-only，仅测试服发布前构建。
- 操作 ID：op-2026-07-09T154537061989200Z-db79556a-69bf-4644-ae05-68603649bc79
- GREEN: release-input-refreeze-v6 -> PASS，source HEAD 与 release worktree HEAD 一致，后端/前端发布 worktree clean。
- 证据：evidence/release-target-refreeze-v6.json；evidence/build-release-v6-submit.json

BLOCKER: build-release-v6-manifest-source-gate -> operation detail request failed: 远程服务器返回错误: (404) 未找到。; build-release v6 operation is missing; cannot validate package; manifest missing: E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260709-current-head-test-v6\manifest.json

BLOCKER: build-release-v6-diagnosis-retry -> 已重新采集 v6 operation 404 与 manifest 缺失诊断，证据见 evidence/build-release-v6-404-missing-manifest-diagnosis.json。下一步按诊断结果决定重提构建或记录阻塞。

BLOCKER: build-release-v6-operation-poll -> operation=op-2026-07-09T154537061989200Z-db79556a-69bf-4644-ae05-68603649bc79，轮询后状态 RUNNING，manifestExists=True，继续等待或诊断队列阻塞；证据见 evidence/build-release-v6-poll-after-running.json。

GREEN: build-release-v6-operation-final -> PASS，operation=op-2026-07-09T154537061989200Z-db79556a-69bf-4644-ae05-68603649bc79，状态 SUCCESS。

BLOCKER: build-release-v6-manifest-source-package-validation -> backend source HEAD drift: source d766b6c1569c054e21f44f5532027fe4c43d16cd != release 81049db2125cc237f73f29abcfcbddd3c41e743d; frontend source HEAD drift: source 8bb322f41d3abab08363e2d4477b35c6f3e3d660 != release a77812a43103eb77c794b481c3ded898811fce69

ISSUE: v6-source-head-drift-before-publish -> 阶段=发布前 manifest/source gate；现象=v6 包 manifest 后端 81049db212、前端 a77812a43，但源仓 HEAD 已变为后端 d766b6c1569c054e21f44f5532027fe4c43d16cd、前端 8bb322f41d3abab08363e2d4477b35c6f3e3d660；影响=按本次验收标准 v6 不得发布；原因判断=并行开发在长时间构建期间继续提交；处理动作=停止 v6 发布，重新冻结 v7 到当前源仓 HEAD；结果=v7 release worktree 已干净对齐；是否可前置检查=是；是否可自动化=是；下次避免=build 成功后 publish 前强制 source HEAD gate，失败即自动重建或要求发布冻结窗口。

GREEN: release-target-refreeze-v7 -> PASS，backend=d766b6c1569c054e21f44f5532027fe4c43d16cd，frontend=8bb322f41d3abab08363e2d4477b35c6f3e3d660，维护仓=1fe4d64a6d4a8840aca061aca3c0c6d72a07d280；发布 worktree 均干净，继续 build-release。

GREEN: build-release-v7-submit -> PASS，releaseTag=release-20260709-current-head-test-v7，operation=op-2026-07-09T160054904850200Z-30627f85-2e3a-41c9-a066-759281d6e349。

BLOCKER: build-release-v7-operation-and-package-gate -> backend source HEAD drift: source c88a47ee2dc9c151cc307aff9cd4d7a494f6f520 != release d766b6c1569c054e21f44f5532027fe4c43d16cd

ISSUE: v7-source-head-drift-before-publish -> 阶段=发布前 manifest/source gate；现象=v7 包 manifest 后端 d766b6c156、前端 8bb322f41d，但源仓 HEAD 已变为后端 c88a47ee2dc9c151cc307aff9cd4d7a494f6f520、前端 8bb322f41d3abab08363e2d4477b35c6f3e3d660；影响=按当前发布门禁 v7 不得发布；原因判断=并行开发在长时间构建期间继续提交；处理动作=停止 v7 发布，重新冻结 v8 到当前源仓 HEAD；结果=v8 release worktree 已干净对齐；是否可前置检查=是；是否可自动化=是；下次避免=发布窗口冻结源仓或由发布脚本在 build 成功后自动执行 source HEAD gate。

GREEN: release-target-refreeze-v8 -> PASS，backend=c88a47ee2dc9c151cc307aff9cd4d7a494f6f520，frontend=8bb322f41d3abab08363e2d4477b35c6f3e3d660，维护仓=1fe4d64a6d4a8840aca061aca3c0c6d72a07d280；发布 worktree 均干净，继续 build-release。

GREEN: build-release-v8-submit -> PASS，releaseTag=release-20260709-current-head-test-v8，operation=op-2026-07-09T161521964954900Z-93a6bc48-c074-48cd-9acd-b018156ce690。

GREEN: build-release-v8-operation-and-package-gate -> PASS，operation=op-2026-07-09T161521964954900Z-93a6bc48-c074-48cd-9acd-b018156ce690，manifest/source/worktree/package 校验通过。

GREEN: publish-test-v8-preview -> PASS，预览限定 publish-test/test server 172.30.30.58，未包含正式服、备份服或 mark-tested 动作。

GREEN: publish-test-v8-submit -> PASS，releaseTag=release-20260709-current-head-test-v8，operation=op-2026-07-09T162703776338100Z-e95db3dc-88e5-4dbf-88c8-2f636e3277a8。

BLOCKER: publish-test-v8-operation -> publish operation status is FAILED, expected SUCCESS；尾部日志见 evidence/publish-test-v8-operation-tail.log。

ISSUE: v8-sql-conflict-guard-duplicate-diagnosis -> 阶段=publish-test SQL migration；现象=测试服执行 20260613_mes_smart_scheduling_t1_schema.sql 时 tmp_mes_pro_route_schedule_config_conflict_guard 主键重复，publish-test 失败；影响=v8 未发布成功；处理动作=已采集 SQL 320-390 行、Git 状态和发布尾部日志，下一步修复迁移脚本冲突检测逻辑。

GREEN: sql-conflict-guard-fix-inspection -> PASS，已定位 SQL 文件 sql\mysql\20260613_mes_smart_scheduling_t1_schema.sql 与测试文件存在性，证据见 evidence/sql-conflict-guard-fix-inspection.json。

GREEN: readonly-test-db-route-schedule-conflict-query -> PASS，已只读查询测试服 mes_pro_route_schedule_config 冲突组，证据见 evidence/readonly-test-db-route-schedule-conflict.tsv。

GREEN: route-schedule-config-sql-context-inspection -> PASS，已读取 20260613 SQL 260-430 行与相关测试索引，确认 v8 失败是数据冲突门禁触发还是迁移逻辑可修复。

GREEN: sql-route-schedule-config-tests-full-read -> PASS，已完整读取相关 SQL 契约测试与迁移 SQL，证据见 evidence/sql-route-schedule-config-tests-full.json。

BLOCKER: remote-state-after-v8-publish-failure -> 远端状态只读采集失败，exit=1，stderr=ssh.exe : curl: (7) Failed to connect to 127.0.0.1 port 48080: 拒绝连接
At line:49 char:1
+ & ssh @sshArgs 1> $tmpOut 2> $tmpErr
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (curl: (7) Faile...ort 48080: 拒绝连接:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError

bash: -c:行21: 未预期的符号 `(' 附近有语法错误
bash: -c:行21: `docker exec intruoyi-mysql mysql -uroot -p123456 --default-character-set=utf8mb4 --batch ruoyi-vue-pro -
e SELECT target_environment, operation_id, status, release_tag, started_at, finished_at, LEFT(error_message, 300) AS er
ror_message FROM infra_release_operation_lock WHERE target_environment='test'; 2>&1 || true'
close - IO is still pending on closed socket. read:1, write:0, io:000002B3E2AB5CE0
。

## 阶段记录：v8 测试服发布被真实数据冲突阻塞（2026-07-10 00:46:04 +08:00）

- 现象：publish-test 执行 sql/mysql/20260613_mes_smart_scheduling_t1_schema.sql 时失败，MySQL 报 ERROR 1062 Duplicate entry '1' for key 'tmp_mes_pro_route_schedule_config_conflict_guard.PRIMARY'。
- 阶段：测试服发布 required SQL / migration 门禁。
- 影响：
elease-20260709-current-head-test-v8 未发布成功；不得判定测试发布成功，不得继续运行态验收为通过。
- 原因判断：只读查询测试服确认 mes_pro_route_schedule_config 存在 4 组真实配置冲突：tenant_id=1、route_version_id=3、route_process_id=900124/900125/900126/900127，同一工序同时存在全局配置行和 item_id=902262 的产品级配置行，且产能、夜班或日历配置不同。当前迁移会把产品维度收敛为工序维度，无法无损判断应保留哪一组配置，因此 fail fast 是正确行为。
- 处理动作：已停止继续发布；已只读采集冲突数据、发布失败日志、远端 .env IMAGE_TAG、镜像 tag、容器状态、前端/后端运行态和 release lock 证据。
- 结果：发布状态为 FAILED；远端 .env IMAGE_TAG 已写为
elease-20260709-current-head-test-v8，但实际运行容器仍是旧镜像
elease-20260709-codeonly-three-env-head-v10；v8 镜像已加载到测试服但容器未切换，后端健康检查未通过当前端口探测。
- 是否可前置检查：是。发布前应在测试服只读执行同等冲突检查，发现冲突即阻塞，不进入镜像加载和 .env 更新。
- 是否可自动化：是。发布脚本可在 required SQL 前增加 mes_pro_route_schedule_config 冲突 precheck，并在失败时输出具体 tenant/version/process/id/item/config 差异。
- 下次如何避免：发布前先清理或明确业务决策；不得在发布中自动猜测保留全局配置或产品级配置，不得通过删除/覆盖测试数据绕过迁移门禁。
- BLOCKER: test-db-route-schedule-config-conflict -> 需要用户明确批准一种正式处理方案后才能继续：1) 由业务确认并修复测试服冲突数据；2) 修改迁移设计以保留产品级配置语义；3) 明确批准一次性测试服数据修复脚本。
- 证据：evidence/publish-test-v8-operation-result.json；evidence/publish-test-v8-operation-tail.log；evidence/readonly-test-db-route-schedule-conflict.tsv；evidence/remote-state-after-v8-publish-failure.out.log。

## 继续复核：阻塞审计 2（2026-07-10 08:42:17 +08:00）

- USER_REQUEST: 继续。
- ISSUE: resume-audit-2-powershell-quoting -> 现象=首次只读复核命令在本地 PowerShell 解析阶段因远端命令字符串转义错误失败；阶段=只读复核命令准备；影响=未连接服务器、未执行数据库或远端命令；原因判断=双引号字符串内嵌远端 shell 变量导致 PowerShell 提前解析；处理动作=改为不含嵌套变量的单引号远端命令并重试；结果=第二次命令成功；是否可前置检查=是；是否可自动化=是；下次如何避免=多层 PowerShell/SSH 命令优先使用无变量远端命令或受控脚本文件，并先通过本地解析检查。
- GREEN: resume-after-blocked-audit-2-readonly -> PASS，数据库仅执行 SELECT，远端仅读取 `.env`、容器状态和 HTTP；未发布、未重启、未修改数据。
- BLOCKER: test-db-route-schedule-config-conflict-still-present -> 冲突组数量仍为 4：tenant_id=1、route_version_id=3、route_process_id=900124/900125/900126/900127；每组全局配置与 item_id=902262 产品级配置不同，无法无损自动选择。
- BLOCKER: v8-not-running -> `.env IMAGE_TAG=release-20260709-current-head-test-v8`，实际 backend/frontend 镜像仍为 `release-20260709-codeonly-three-env-head-v10`；旧版本 backend health HTTP 200、frontend HTTP 200，不能判定 v8 发布成功。
- BLOCKER: release-source-head-drift-after-v8 -> 当前 backend source HEAD=b11030a4d694d1e37831e40226f003e66db30664、frontend source HEAD=40b59bce8e87e8ae44e875db41d8cc0739f01839；v8 worktree 仍为 backend c88a47ee2dc9c151cc307aff9cd4d7a494f6f520、frontend 8bb322f41d3abab08363e2d4477b35c6f3e3d660。冲突解除后必须新建 releaseTag 并从当时最新已提交 HEAD 重建。
- RESULT: 发布任务保持 BLOCKED；未执行 publish-test、正式服、备份服、容器重启、数据库写入或 worktree 清理。
- EVIDENCE: evidence/resume-after-blocked-audit-2.json。

## 测试服冲突数据修复授权与前置门禁（2026-07-10 08:47:09 +08:00）

- USER_AUTHORIZATION: 用户回复“授权”；授权范围按上下文限定为修复测试服 `mes_pro_route_schedule_config` 冲突数据，不包含正式服、备份服、硬删除、历史排产快照改写或绕过 required SQL。
- GREEN: route-schedule-config-current-contract -> PASS，最新后端提交 `b11030a4d694d1e37831e40226f003e66db30664` 与 v8 的迁移契约一致；当前服务保存时强制 `item_id=NULL`，唯一性和读取维度均为 `routeVersionId + routeProcessId`。
- GREEN: route-schedule-config-business-reference-audit -> PASS，较新配置 `203–206` 创建于 2026-07-08，供待排产工单 26 的四个工序快照使用；较旧配置 `128–131` 创建于 2026-07-01，供五个生产中工单的 20 个既有快照使用。提交代码仅在创建快照时写入 `routeScheduleConfigId`，后续产能使用快照字段，不动态反查配置。
- DESIGN_DECISION: 保留较新且被待排产工单使用的 `203–206`，将 `item_id` 转为 NULL；仅软删除旧 `128–131`；不修改任何 `mes_pro_schedule_order_process` 引用及产能快照。
- GREEN: test-db-route-schedule-config-backup -> PASS，8 行原始数据已导出至 `evidence/test-db-route-schedule-config-before-fix.sql`，SHA256=`e55601279b88f288d4a6442907e47ab3aa94fb5f3f6ee7c727c726301e516e37`；24 行引用已导出至 `evidence/test-db-route-schedule-config-references-before-fix.tsv`，SHA256=`67e5374933eb6540381d838355d7a328390e233f9a1b373494dc271af4e049f5`。
- GREEN: target-unique-index-preflight -> PASS，无历史软删除目标键重复，无活跃三行以上重复；其余 20 组均为配置相同的双行，可由现有迁移保留一行并软删除一行；目标唯一索引尚未创建。
- GREEN: experience-preflight -> PASS，测试服写入前已完成授权范围、当前提交契约、真实引用、备份、目标唯一键和 fail-fast 事务脚本检查；脚本任一前置条件变化即重复键失败并回滚。
- NEXT: 先将 `evidence/test-db-route-schedule-config-fix.sql` 的最终 COMMIT 替换为 ROLLBACK 做同事务演练；演练通过后再执行原脚本提交。

## 测试服冲突数据修复执行（2026-07-10 08:48:33 +08:00）

- GREEN: test-db-route-schedule-config-fix-dry-run -> PASS，将正式脚本唯一的最终 `COMMIT` 替换为 `ROLLBACK` 执行；事务内确认旧行软删除 4、新行转工序级 4、冲突数 4→0；新连接复核冲突数仍为 4 且 8 行恢复原状。证据：`evidence/test-db-route-schedule-config-fix-dry-run.json`、`evidence/test-db-route-schedule-config-fix-dry-run.log`。
- GREEN: test-db-route-schedule-config-fix-apply -> PASS，正式脚本提交成功；旧配置 `128–131` 软删除，新配置 `203–206` 的 `item_id` 已置 NULL，冲突组数从 4 降为 0。
- GREEN: test-db-route-schedule-config-reference-preservation -> PASS，8 个配置 ID 的排产工序引用数保持 `5,5,5,5,1,1,1,1`，未改写 `mes_pro_schedule_order_process`。
- GREEN: test-server-health-after-data-fix -> PASS，backend HTTP 200，frontend HTTP 200。
- GREEN: test-db-route-schedule-config-fix-evidence -> PASS，正式执行日志 SHA256=`10dee328f643530884b247f61c7f8cc47da04f348483c56f645d6295ad3d83ec`；证据：`evidence/test-db-route-schedule-config-fix-apply.json`、`evidence/test-db-route-schedule-config-fix-apply.log`。
- RESULT: required SQL 的真实数据冲突阻塞已解除；目标唯一索引仍由正式发布迁移创建，不在手工数据修复中提前创建。
- NEXT: 重新冻结当前 source HEAD 到专用发布 worktree，使用新 releaseTag 重建，禁止复用 v8。

## v9 冻结基线、构建与发布包门禁（2026-07-10）

- USER_POLICY_UPDATE: 用户明确要求程序持续开发期间不必因源分支后续提交反复重建；本次以构建开始前记录并检出的发布 worktree 提交为冻结基线。冻结完成后的源分支 HEAD 漂移不影响本次包，发布验收只比较发布 worktree、Manifest v1 和构建产物。
- GREEN: release-target-refreeze-v9 -> PASS，releaseTag=`release-20260709-current-head-test-v9`；maintenance=`1fe4d64a6d4a8840aca061aca3c0c6d72a07d280`，backend=`f1ef04912951ef15ae0d2881c974c964c182d76e`，frontend=`d33339bd7e29f705d12d92d8409d7bc37d314566`；backend/frontend 发布 worktree 均 clean。
- GREEN: build-release-v9-operation -> PASS，operation=`op-2026-07-10T005259232612400Z-cb2a74e8-4ae2-4b97-a24a-ae0398d266b2`，状态 `SUCCESS`。
- GREEN: build-release-v9-manifest-v1 -> PASS，`manifest.json` 的 `sourceRepos` 同时记录冻结 backend/frontend 提交且 `dirty=false`；版本=`release-20260709-current-head-test-v9`，变更说明=`Release package release-20260709-current-head-test-v9`，组件=`intruoyi`。
- GREEN: build-release-v9-artifacts -> PASS，Manifest v1 所列 281 个产物全部存在，大小与 SHA256 全部匹配；required SQL 源文件哈希匹配；禁止携带的 data/database/minio/website/showroom 根目录均不存在。
- ISSUE: v9-legacy-manifest-overstrict-local-validator -> 现象=首次本地校验要求旧版 `release-manifest.json` 包含 frontend commit，导致唯一一项误报 FAIL；阶段=构建后 manifest 门禁；影响=若不复核会错误阻断已满足正式契约的发布包；原因判断=`release-manifest.json` 是兼容清单，只定义单一 backend `gitCommit` 与 281 项产物清单，frontend 来源由权威 `manifest.json` Manifest v1 的 `sourceRepos` 表达；处理动作=按两份清单各自契约重新校验，保留 Manifest v1 的双仓提交/dirty 门禁，并对旧版清单的 releaseTag、目录、组件、发布范围、backend commit、281 项产物哈希逐项校验；结果=修正后 38 项门禁及 281/281 产物全部 PASS；是否可前置检查=是；是否可自动化=是；下次如何避免=校验器按 manifest schema/version 分流，禁止把 Manifest v1 字段强加给 legacy manifest。
- GREEN: build-release-v9-manifest-package-validation-corrected -> PASS，证据=`evidence/build-release-v9-manifest-package-validation-corrected.json`，SHA256=`39807ef7f86b16d46c412fbed1b70d389bf83bd5977703fca91a3be3426a4d39`。
- GREEN: experience-preflight -> PASS，发布前已确认冻结提交、干净 worktree、构建 operation SUCCESS、Manifest v1 来源、版本号、变更说明、281 项产物哈希、required SQL 哈希、测试服冲突修复结果及仅测试服动作边界；任何一项不通过即 fail fast，不执行 publish-test。

## v9 仅测试服发布与真实运行态验收（2026-07-10）

- GREEN: publish-test-v9-preview -> PASS，动作=`publish-test`，环境=`test`，主机=`172.30.30.58`，远端目录=`/opt/intruoyi/runtime`；预览中无正式服、备份服、推广或 `mark-tested` 动作。
- GREEN: publish-test-v9-submit -> PASS，operation=`op-2026-07-10T011318297410400Z-dbee4822-c99c-40ff-894c-71f75679440a`。
- GREEN: publish-test-v9-operation -> PASS，operation 最终状态=`SUCCESS`，发布日志结尾为 `Publish completed for test.`。
- GREEN: test-runtime-v9-image-and-container -> PASS，远端 `.env IMAGE_TAG=release-20260709-current-head-test-v9`；backend/frontend 实际镜像均为 v9，两个容器均为 running。
- GREEN: test-runtime-v9-http -> PASS，backend health HTTP 200 且状态 `UP`；frontend HTTP 200 且 HTML 非空。
- GREEN: test-runtime-v9-db-contract -> PASS，活跃路由排程配置冲突数=0；唯一索引 `uk_mes_pro_route_schedule_config_process` 为 UNIQUE，列顺序=`tenant_id,route_version_id,route_process_id,deleted`；迁移 `20260613_mes_smart_scheduling_t1_schema`、`20260709_mes_route_flow_config_unification` 和 test release lock 均为 APPLIED。
- GREEN: test-runtime-v9-playwright-required-ui -> PASS，使用业务前端仓 Playwright 1.60.0 与系统 Chrome，真实登录测试租户，通过 `基础设施 -> 监控中心 -> 运行控制台` 打开页面；发布信息对话框显示 v9、构建时间、code-only、组件、变更说明、变更项及冻结的后端/前端提交；页面错误数=0。
- GREEN: no-production-or-backup-action -> PASS，发布日志和操作记录中对 `172.30.30.57`、`172.30.30.59` 的发布/SSH/scp 动作为 0，推广与 `mark-tested` 动作为 0。
- RESULT: `final-test-release-v9-acceptance` -> PASS，32/32 必需检查通过；运行控制台运维矩阵缺陷状态=`DEGRADED_RECORDED`，未替代或降低真实运行态验证。

## v9 发布阶段问题记录

- ISSUE: powershell-interpolation-path-colon -> 现象=refreeze 脚本中的 `$Path:` 被 PowerShell 解析为非法变量引用；阶段=Git/worktree 重新冻结；影响=首次冻结命令未执行；原因判断=变量名后直接跟冒号；处理动作=改为 `${Path}:`；结果=冻结成功；是否可前置检查=是；是否可自动化=是；下次如何避免=脚本提交前执行 PowerShell Parser.ParseFile。
- ISSUE: powershell-automatic-args-collision -> 现象=函数参数命名为 `$Args` 后参数内容异常；阶段=Git/worktree 辅助函数；影响=命令参数传递失败；原因判断=`$Args` 是 PowerShell 自动变量；处理动作=改用明确参数名；结果=命令恢复；是否可前置检查=是；是否可自动化=是；下次如何避免=PSScriptAnalyzer 禁止覆盖自动变量。
- ISSUE: git-checkout-stderr-false-failure -> 现象=`git checkout` 正常提示写 stderr，配合 `$ErrorActionPreference=Stop` 被误判失败；阶段=worktree 冻结；影响=产生重复诊断；原因判断=原生命令 stderr 不等于非零退出码；处理动作=使用 Start-Process 并只按 ExitCode 判定；结果=冻结成功；是否可前置检查=是；是否可自动化=是；下次如何避免=所有原生命令统一记录 stdout/stderr/ExitCode。
- ISSUE: v9-legacy-manifest-overstrict-local-validator -> 现象=首次本地校验要求 legacy `release-manifest.json` 包含 frontend commit；阶段=manifest 门禁；影响=误报 FAIL，若不复核会阻断正确发布包；原因判断=混淆 Manifest v1 与 legacy schema；处理动作=按 schema/version 分流校验；结果=38 项门禁与 281/281 产物 PASS；是否可前置检查=是；是否可自动化=是；下次如何避免=校验器先识别 schema 再断言字段。
- ISSUE: publish-submit-reason-encoding -> 现象=operation response 中中文 submit reason 显示为 `????`；阶段=发布提交记录；影响=审计文本可读性下降，不影响操作状态与发布内容；原因判断=PowerShell 管道编码不一致；处理动作=以 operation ID、状态和 UTF-8 证据为权威；结果=发布成功且问题记录；是否可前置检查=是；是否可自动化=是；下次如何避免=进程边界使用 UTF-8 字节读写并加入中文 round-trip 检查。
- ISSUE: publish-log-nas-share-garbled -> 现象=发布日志 NAS share 中文显示乱码；阶段=发布日志采集；影响=日志可读性下降，路径和发布动作未受影响；原因判断=原生进程输出代码页不一致；处理动作=同时核对 operation、发布目录和远端运行态；结果=发布成功且问题记录；是否可前置检查=是；是否可自动化=是；下次如何避免=日志采集统一 UTF-8 并保存原始字节。
- ISSUE: ssh-bash-crlf-from-python-text-mode -> 现象=两次 SSH 运行态脚本因 `subprocess text=True` 将 LF 转 CRLF，远端 `bash -s` 解析失败；阶段=发布后远端验证；影响=首次两次验证未产出有效结果，未修改远端；原因判断=Windows 文本模式换行转换；处理动作=改为 bytes input；结果=远端验证 PASS；是否可前置检查=是；是否可自动化=是；下次如何避免=SSH stdin 脚本固定 UTF-8 bytes + LF。
- ISSUE: mysql-index-row-count-misclassification -> 现象=初始校验把一个四列索引返回的 4 行误当作 4 个索引；阶段=数据库契约验证；影响=唯一索引门禁误报；原因判断=按行数而非索引名和列序聚合；处理动作=按索引名、Non_unique 和 Seq_in_index 校验；结果=索引契约 PASS；是否可前置检查=是；是否可自动化=是；下次如何避免=数据库元数据校验使用结构化聚合。
- ISSUE: mysql-concat-literal-tab -> 现象=MySQL `CONCAT` 中使用字面量 `\t`，本地解析器未识别 migration/lock 行；阶段=数据库状态采集；影响=迁移状态首次漏报；原因判断=MySQL 与本地转义预期不一致；处理动作=查询直接输出真实制表符分隔；结果=迁移与 release lock 均确认 APPLIED；是否可前置检查=是；是否可自动化=是；下次如何避免=优先使用 `--batch --raw` 的天然 TSV。
- ISSUE: playwright-inline-chinese-regex-encoding -> 现象=首次 Playwright 内联脚本中文正则变为 `????`；阶段=真实页面验证；影响=中文菜单定位失败；原因判断=PowerShell 到 Node 源码管道编码丢失；处理动作=脚本源码仅使用 ASCII 和 Unicode 转义；结果=真实页面验证 PASS；是否可前置检查=是；是否可自动化=是；下次如何避免=自动化脚本避免依赖终端传递裸中文。
- ISSUE: tenant-element-plus-combobox-locator -> 现象=登录页租户字段不是可见普通 input，隐藏 input locator 无法交互；阶段=Playwright 登录；影响=首次真实登录失败；原因判断=Element Plus combobox 交互模型；处理动作=点击可见 combobox 并选择测试租户选项；结果=真实测试租户登录成功；是否可前置检查=是；是否可自动化=是；下次如何避免=先检查 DOM/ARIA 角色再编写 locator。
- ISSUE: runtime-menu-three-level-route-discovery -> 现象=多次按错误菜单层级和路由尝试运行控制台；阶段=Playwright 页面导航；影响=增加重复操作和耗时；原因判断=实际入口为三层菜单，动态路由不可凭历史路径推断；处理动作=核对 `system_menu`、权限响应和页面菜单，使用 `基础设施 -> 监控中心 -> 运行控制台`；结果=页面打开成功；是否可前置检查=是；是否可自动化=是；下次如何避免=E2E 前先从权限响应解析目标菜单链。
- ISSUE: runtime-console-release-summary-in-dialog -> 现象=运行控制台主面板未直接渲染变更说明；阶段=UI 验收；影响=直接文本断言失败；原因判断=版本与变更说明设计在全局 ReleaseInfoDock 对话框；处理动作=按真实用户入口打开发布信息对话框；结果=v9 与变更说明可见；是否可前置检查=是；是否可自动化=是；下次如何避免=验收前确认产品实际信息入口，不假设主面板字段。
- ISSUE: test-runtime-control-linux-powershell-status-probe -> 现象=测试服 Linux 后端运维矩阵以 working dir `/opt/intruoyi/ops/backup-ops/linux-native` 调用 `powershell.exe`，矩阵显示 ERROR/unknown；阶段=运行控制台真实页面；影响=矩阵不能用于判断真实运行态；原因判断=跨平台探测实现错误；处理动作=独立验证镜像、容器、health、HTTP、数据库并保留缺陷；结果=发布验收通过，缺陷 OPEN_RECORDED；是否可前置检查=是；是否可自动化=是；下次如何避免=Linux 使用原生 shell/HTTP/Docker 探测并增加容器平台测试。
- ISSUE: test-runtime-control-release-status-current-tag-null -> 现象=测试服后端 `/release-status` 返回 current tag 为 null；阶段=运行控制台真实页面；影响=运维面板当前版本字段不可信；原因判断=`release-status` 依赖失败的 overview；处理动作=用全局 release-info、维护控制台 API 和远端运行态交叉验证；结果=验收信息可见，缺陷 OPEN_RECORDED；是否可前置检查=是；是否可自动化=是；下次如何避免=发布状态接口与运维矩阵解耦并增加 API 契约测试。

## 长时间过程复盘

- 当前进度：v9 已完成仅测试服发布和全部必需运行态验收，进入本地恢复、worktree 清理和任务提交阶段。
- 已完成步骤：Git 冻结、维护控制台构建、v9 包构建、双 manifest 校验、281 项哈希、测试服数据冲突授权修复、publish-test、服务器/数据库/HTTP/Playwright 验收、经验文档更新。
- 阻塞点：v8 required SQL 被 4 组真实配置冲突阻塞；授权修复后解除。v9 无发布阻塞。
- 耗时原因：早期持续追逐源分支新增提交导致 v3-v8 重复构建；v8 数据冲突需业务关系核对、备份、回滚演练；多层 PowerShell/SSH/中文编码和动态菜单定位产生重复诊断。
- 下一步动作：恢复本地主路径维护控制台；运行 closeout preview；删除本轮无提交 worktree；验证只剩主工作区；提交任务记录。

## 经验沉淀结果

- GREEN: release-preflight-lessons-v9 -> PASS，`docs/release-build-preflight-lessons.md` 已补充冻结发布基线、路由配置冲突 precheck、Manifest v1/legacy schema 分流校验、真实运行态与控制台显示分离校验、Linux/PowerShell 探测 fail-fast。
- GREEN: powershell-preflight-lessons-v9 -> PASS，`docs/powershell-preflight-lessons.md` 已补充中文管道编码、SSH bytes/LF、原生命令 ExitCode、`${Path}:` 与 `$Args` 自动变量门禁。
- GREEN: experience-index-v9 -> PASS，`docs/experience-index.md` 已增加上述关键词路由。

## 发布收尾与临时 worktree 清理（2026-07-10）

- GREEN: task-closeout-cleanup-preview -> PASS，预览只保留 `task.md`、`execution-log.md`，删除本任务 `evidence/` 临时证据目录；blocked=0，warnings=0。
- ISSUE: closeout-status-heading-contract -> 现象=首次 closeout apply 将任务状态识别为 unknown 并阻塞；阶段=任务附属证据清理；影响=evidence 未删除，其他文件未受影响；原因判断=清理脚本只读取英文 `## Current Status` 且要求内容以 `completed` 开头，中文 `## 当前状态` 与 `Status: COMPLETED` 不属于其契约；处理动作=补充正式英文状态节 `## Current Status` / `completed`；结果=满足 apply 前置；是否可前置检查=是；是否可自动化=是；下次如何避免=任务模板同时保留脚本可解析的英文状态节。
- GREEN: runtime-control-main-path-restore -> PASS，停止发布 worktree 维护控制台 PID 12528；将冻结维护提交构建的 Jar 放入主工作区 `backend/target`，从 `D:\ProjectPackage\Int\IntRuoyiMaintance` 启动 PID 57312；监听 48181，health=`UP`，进程命令行只引用主工作区 Jar，发布 worktree 路径不再被运行进程占用。
- ISSUE: runtime-restore-invokewebrequest-byte-content -> 现象=首次恢复脚本已成功启动主工作区控制台，但脚本最终 exit=1 且无摘要；阶段=本地运行控制台恢复；影响=产生一次误报失败，服务实际已启动；原因判断=当前 PowerShell 环境的 `Invoke-WebRequest.Content` 为 byte[]，直接使用 `-match 'UP'` 始终不成立，循环超时后抛错；处理动作=独立检查监听进程、启动日志并改用 `Invoke-RestMethod`；结果=health=`UP` 且主工作区 Jar 归属确认；是否可前置检查=是；是否可自动化=是；下次如何避免=健康检查统一解析 JSON 对象的 `status` 字段，不对未解码 Content 做字符串匹配。
- ISSUE: runtime-overview-root-field-assumption -> 现象=恢复验证要求 overview JSON 直接包含 repo-root/frontend-root，检查失败；阶段=本地运行控制台恢复验证；影响=一次校验误报，不影响服务；原因判断=overview API 仅返回组件、环境和状态，不暴露配置根路径；处理动作=改用主配置文件、Java 命令行、工作目录日志、health 和发布路径无进程引用交叉验证；结果=主路径恢复通过；是否可前置检查=是；是否可自动化=是；下次如何避免=按真实 API 契约断言，不假设未定义字段。
- ISSUE: worktree-lock-check-matched-current-shell -> 现象=首次清理前进程扫描把正在执行清理命令的 PowerShell PID 7636 识别为引用发布 worktree；阶段=worktree 清理前置；影响=清理未执行，未删除任何目录；原因判断=命令行本身包含目标路径且未排除 `$PID`；处理动作=确认该临时进程已退出，按 worktree 记忆规则排除当前执行壳后重试；结果=进入正式清理；是否可前置检查=是；是否可自动化=是；下次如何避免=路径进程扫描固定排除当前壳及已确认的父执行壳。
- ISSUE: frontend-worktree-remove-directory-not-empty -> 现象=`git worktree remove --force` 返回 exit 255，前端物理目录因深层 `node_modules` 残留未删除；阶段=临时 worktree 清理；影响=Git 注册已移除但目录仍存在，不能判定收口完成；原因判断=Windows 深层依赖目录删除未完成；处理动作=读取 `docs/worktree-memory.md`，确认目标路径位于本任务固定根、任一仓库均不再注册、无外部进程引用后，使用受限绝对路径递归删除；结果=前端残留目录删除；是否可前置检查=是；是否可自动化=是；下次如何避免=worktree remove 后强制执行“注册为空 + 物理目录不存在”双检查并自动进入受限残留清理。
- ISSUE: maintenance-worktree-remove-directory-not-empty -> 现象=维护 worktree `git worktree remove --force` 返回 exit 255，运行时/构建目录残留；阶段=临时 worktree 清理；影响=Git 注册已移除但物理目录仍存在；原因判断=Windows 非空构建目录无法由 Git 完整删除；处理动作=确认维护 worktree 无 tracked/staged 改动、无新提交、Git 注册已移除、路径严格位于 `r260709t3\m` 后递归删除；结果=维护残留目录与父根目录删除；是否可前置检查=是；是否可自动化=是；下次如何避免=复用 `docs/worktree-memory.md` 的注销后受限路径残留清理门禁。
- GREEN: release-worktree-closeout -> PASS，backend worktree 由 Git 正常移除；frontend/maintenance 在 Git 注册移除后按固定根路径清理物理残留；最终 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709t3` 不存在，三仓 worktree 列表均不包含本轮路径。
- GREEN: release-worktree-commit-merge-state -> PASS，本轮三个发布 worktree 均无新提交，因此无需合回 `int_main`；清理未修改后端或前端主工作区。
- GREEN: runtime-control-after-worktree-cleanup -> PASS，发布 worktree 删除后本地维护控制台 health 仍为 `UP`，进程继续引用主工作区 Jar。
- GREEN: closeout-experience-gate -> PASS，worktree remove 非空残留问题已命中并复用 `docs/worktree-memory.md` 既有“注册为空 + 固定路径 + 无进程引用 + 物理目录不存在”门禁，未引入扩大删除范围或静默跳过。
- FINAL: test-only-release-v9 -> COMPLETED，测试服发布和真实运行态验收通过；正式服、备份服、推广和 `mark-tested` 均未执行；问题记录、长过程复盘、前置经验与本轮临时 worktree 清理完成。
