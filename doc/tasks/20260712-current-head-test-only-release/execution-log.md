# 20260712 当前 HEAD 仅测试服发布执行日志

## BDD

- BDD: 仅测试服发布冻结 HEAD -> Given 三仓主工作区可能存在未提交改动 When 执行仅测试服发布 Then 构建输入必须来自任务开始时冻结的三仓 HEAD 干净临时 worktree，未提交改动不得进入产物。
- BDD: 测试服真实运行态验收 -> Given build-release 与 publish-test 已完成 When 校验测试服 Then operation、manifest、远端 `.env IMAGE_TAG`、实际镜像、容器、health、HTTP、release-info、真实页面、运行控制台版本号和变更说明必须全部一致。
- BDD: 禁止正式链路动作 -> Given 用户仅授权测试服发布 When 发布成功 Then 不得执行 `mark-tested`、`promote-prod`、`promote-backup` 或任何正式服/备份服动作。

## Startup

- REQUEST: 基于当前分支最新已提交代码构建维护控制台和测试发布包，仅发布测试服务器；未提交改动不得进入构建产物；构建发布开始后只跟随本轮 worktree 冻结提交，不追逐后续源码提交。
- COMMAND INTENT: 读取发布、worktree、服务器、PowerShell、经验索引门禁；创建任务目录；冻结三仓当前 HEAD；因三仓主工作区均 dirty，后续必须创建干净临时 release worktree。
- GREEN: experience-preflight -> PASS，已命中 `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`。

## Frozen Baseline

- maintenance: branch=`int_main`, HEAD=`481d03c1940f233ba12576801286ff2617e3a441`, subject=`任务: 记录当前HEAD仅测试服发布`, main workspace dirty=true。
- backend: branch=`int_main`, HEAD=`ad23d54eab81ec20bf057db60920833e4d633035`, subject=`任务: 修正路线工序产能排产窗口`, main workspace dirty=true。
- frontend: branch=`int_main`, HEAD=`5c3c45333adb06785b01c51715ce4c37910dd428`, subject=`任务: 提示未参与重排工单`, main workspace dirty=true。

## TDD / Verification Evidence

- GREEN: worktree-freeze -> PASS，maintenance/backend/frontend 三个 worktree 均为 detached HEAD，`git status --porcelain` 为空。

## Release Worktree Freeze

- COMMAND: 创建短路径临时发布 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712t\m|b|f`，分别检出本任务冻结 HEAD。
- RESULT: maintenance=`481d03c1940f233ba12576801286ff2617e3a441`，backend=`ad23d54eab81ec20bf057db60920833e4d633035`，frontend=`5c3c45333adb06785b01c51715ce4c37910dd428`，三者 clean。
- ISSUE: 首次 worktree 创建命令使用 Bash 风格 here-doc，PowerShell 5.1 在解析阶段失败；未创建 worktree，已改为 PowerShell 原生命令执行。
- BUILD DIRS: maintenance=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712t\m`；backend=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712t\b`；frontend=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712t\f`。
- EVIDENCE: `doc/tasks/20260712-current-head-test-only-release/evidence/worktree-freeze.json`。

## Build Release Preflight Blocked

- COMMAND: 对冻结 backend d23d54eab81ec20bf057db60920833e4d633035 执行全量 release migration policy gate。
- RED: python -X utf8 D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712t\m\ops\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712t\b\sql\mysql --output ...\release-migration-policy-gate-rerun.json -> FAIL，原因：sql/mysql/20260711_mes_batch_record_cell_link_rule.sql 缺 release-migration metadata。
- RESULT: BLOCKED；未生成 releaseTag、manifest、发布包版本号或变更说明；未执行 build-release preview/submit，未执行 publish-test，未连接或写入测试服/正式服/备份服。
- IMPACT: 当前冻结 backend HEAD 不满足发布契约，无法证明 required SQL 的 allowedEnvironments、dependsOn、type、riskLevel；按门禁不得继续发布。
- SAFETY: 本地 48181 运行控制台仍为原主路径进程，本任务未切换控制台；已清理本任务在 release worktree 内产生的 untracked
untime/，三仓 release worktree 保持 clean 作为阻塞证据。
- EVIDENCE: evidence/release-migration-policy-gate-rerun.json、evidence/blocked-final-worktree-status.json。
- NEXT REQUIRED INPUT: 需要用户明确授权修复并提交后端 SQL metadata 后，才能以新后端提交重新冻结并重启仅测试服发布流程；否则本次发布到此失败并保持阻塞。

## User Scope Update - int_main Only

- REQUEST: 用户确认“只发布intmain”。
- COMMAND INTENT: 重新检查当前三仓 int_main HEAD 和 dirty 状态；后续只允许从当前 int_main 已提交 HEAD 创建干净发布 worktree，未提交改动仍不得进入构建。
- EVIDENCE: evidence/intmain-current-head-check.json。
## int_main 最新 HEAD 重新冻结

- REQUEST: 用户确认只发布 int_main。
- COMMAND: 从当前三仓 int_main HEAD 创建新的干净发布 worktree：D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712i。
- RESULT: maintenance=481d03c1940f233ba12576801286ff2617e3a441; backend=51bfedc5c575155c22f08da880da19bce75b60dd; frontend=2d10335f75a72f934aac52839fdb78a696036304; 三者 detached 且 clean。
- RED: int_main release migration policy gate -> exit=1。
- EVIDENCE: evidence/intmain-worktree-freeze.json, evidence/intmain-release-migration-policy-gate.json, evidence/intmain-blocked-worktree-status.json。
- RESULT: BLOCKED；当前 int_main 后端 HEAD 仍不满足迁移发布元数据门禁，未执行 build-release、publish-test 或服务器写入。

## 非 int_main worktree 清理完成性复核 2

- COMMAND: 继续清理非 int_main worktree 注册和残留目录；所有删除路径限定在批准 worktree 根下。
- RESULT: 目标 0 个，停止进程 0 个；清理结果见证据。
- EVIDENCE: `evidence/worktree-delete-final-2.json`。

## 后端迁移 metadata 修复提交

- COMMAND: 仅暂存并提交 `sql/mysql/20260711_mes_batch_record_cell_link_rule.sql`。
- GREEN: targeted migration policy gate -> PASS。
- GREEN: full migration policy gate -> PASS。
- NOTE: `scripts/tests/test_release_sql_preflight_gate.py` 现有维护仓契约测试 1 项失败，失败点为发布脚本 applyItems 断言与当前脚本实现不一致；本次后端 SQL metadata 修复不修改维护仓发布脚本。
- COMMIT: backend `51bfedc5c575155c22f08da880da19bce75b60dd`，message=`任务: 补充批记录单元格链接迁移元数据`。
- EVIDENCE: `evidence/metadata-fix-commit.json`。

## r260712p 发布冻结与构建

- REQUEST: 用户要求删除非 int_main worktree、修复后端错误，然后构建发布；程序持续更新，本轮发布只跟随开始时 worktree 记录的提交。
- COMMAND: 新建本轮专用 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712p\m|b|f`，只从 int_main 已提交 HEAD 构建。
- RESULT: maintenance=`481d03c1940f233ba12576801286ff2617e3a441`，backend=`c7753b28997dbd8d8b3581250961646f00b14ccb`，frontend=`2d10335f75a72f934aac52839fdb78a696036304`，三者 detached HEAD；backend/frontend clean，maintenance 后续只产生本任务运行控制台 runtime 目录。
- GREEN: backend targeted migration gate -> PASS，见 `evidence/r260712p-targeted-migration-gate.json`。
- GREEN: backend full migration gate -> PASS，见 `evidence/r260712p-full-migration-gate.json`。
- GREEN: maintenance console build -> PASS，jar=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712p\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`，SHA256=`2E1A10C39298BB3F44E00D8A00571B5B12E9DA60F2B27DC662B2E8C9D28BDBD7`。
- COMMAND: 本地 48181 运行控制台切换到 r260712p 维护 worktree 配置，repo-root/frontend-root/ops-root/state-dir 均指向本轮冻结路径。
- GREEN: runtime-control health -> UP，见 `evidence/runtime-control-switch-r260712p.json`。

## Build Release

- RED: build-release r1 preview 被本任务过宽 forbidden token 检查拦截；预览中 `BackupServerHost=172.30.30.59` 是动作参数元数据，不是实际 deploy target。处理：改为校验 `-Environment`、`-ServerHost`、`-Mode` 和 forbidden action。
- RED: build-release r2 -> FAIL，原因：开启 `enableSmartReleaseReport` 但未提供 `SmartReleaseBaselineManifestPath`；处理：记录问题，禁用该报告参数后重建。
- GREEN: build-release r3 -> PASS，operation=`op-2026-07-12T031646245278700Z-f1006e17-c7b6-445b-9eaa-5d67e4b66ed1`，status=`SUCCESS`，releaseTag=`release-20260712-intmain-test-r260712p-r3`。
- GREEN: package/manifest validation -> PASS，packageRoot=`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260712-intmain-test-r260712p-r3`；Manifest v1 sourceRepos backend=`c7753b28997dbd8d8b3581250961646f00b14ccb` dirty=false，frontend=`2d10335f75a72f934aac52839fdb78a696036304` dirty=false；publishScope=`code-only`；changeSet.summary=`Release package release-20260712-intmain-test-r260712p-r3`。
- EVIDENCE: `evidence/build-release-r3-continue-status.json`、`evidence/release-package-manifest-validation-r3-corrected.json`。

## Publish Test

- GREEN: publish-test preview target gate -> PASS，action=`publish-test`，mode=`deploy-release`，environment=`test`，ServerHost=`172.30.30.58`，RemoteAppDir=`/opt/intruoyi/runtime`，releaseTag=`release-20260712-intmain-test-r260712p-r3`，无 `mark-tested`、`promote-prod`、`promote-backup`、正式服 IP；`BackupServerHost=172.30.30.59` 仅作为参数元数据出现，不是 `ServerHost`。
- COMMAND: POST `/admin-api/infra/runtime-control/actions`，body action=`publish-test`，releaseTag=`release-20260712-intmain-test-r260712p-r3`。
- GREEN: publish-test operation -> PASS，operation=`op-2026-07-12T043308044248700Z-d8e299c3-a64e-43cc-bd5a-949db86dc67f`，environment=`test`，status=`SUCCESS`。
- EVIDENCE: `evidence/publish-test-preview-r3-target-gate-v2.json`、`evidence/publish-test-r3-final-status.json`。

## 测试服真实运行态验证

- GREEN: remote `.env IMAGE_TAG` -> `release-20260712-intmain-test-r260712p-r3`。
- GREEN: backend actual image -> `intruoyi-backend:release-20260712-intmain-test-r260712p-r3`，container running。
- GREEN: frontend actual image -> `intruoyi-frontend:release-20260712-intmain-test-r260712p-r3`，container running。
- GREEN: backend health -> `{"status":"UP"}`，远端与本机 HTTP 均 200。
- GREEN: frontend HTTP -> 200，content-type=`text/html`，index SHA256=`4075b57eb5061df6225564fe5c30f266aae76cfb3c5233349aa78cf8c1368938`。
- GREEN: frontend `/release-info.json` -> 200，包含 releaseTag、publishScope=`code-only`、changeSet.summary、backend/frontend 冻结提交和 dirty=false。
- RESULT: 测试服真实运行态验证通过，未执行正式服、备份服、mark-tested、promote-prod、promote-backup。
- EVIDENCE: `evidence/test-server-runtime-verification-r3.json`。

## Closeout Preparation

- COMMAND: 采集 closeout 前状态，确认 r260712p worktree 注册仍存在，maintenance worktree 仅有本任务 runtime/ 未跟踪目录；backend/frontend worktree clean。
- RESULT: 任务状态改为 ready_for_closeout；下一步恢复本地运行控制台稳定路径并删除本任务临时 release worktree。
- EVIDENCE: `evidence/closeout-preflight-before-docs-r3.json`。

## Closeout Completed

- GREEN: runtime-control restore -> PASS，本地 48181 恢复为主工作区维护 Jar，`/actuator/health` 返回 `UP`。
- GREEN: release worktree removal -> PASS，`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712p` 已删除，维护仓 worktree 注册仅保留 `int_main` 主工作区。
- GREEN: task-closeout cleanup preview/apply -> PASS，保留核心任务文档和 `issues.md`，删除一次性 helper/evidence 文件；其中包含原始发布日志的 evidence 已清理，避免提交明文敏感输出。
- GREEN: preflight lessons -> PASS，已更新测试服发布、构建、PowerShell 和经验索引门禁，并追加 request-command-log 脱敏摘要。
- RESULT: 任务完成；测试服 releaseTag=`release-20260712-intmain-test-r260712p-r3`，未执行 `mark-tested`、`promote-prod`、`promote-backup`，未发布正式服或备份服。
