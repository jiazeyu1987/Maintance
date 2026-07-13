# 20260713 当前 HEAD code-only 三环境重新发布执行日志

## Initial Request

- REQUEST: 用户说明“主程序又更新了，需要重新发布一次”。按上一轮完整三环境发布口径，重新从当前 `int_main` 已提交 HEAD 执行 code-only 发布闭环。
- SCOPE: code-only；构建使用 `SkipDatabaseSync` 和 `SkipMinioSync`；不执行备份、恢复或回滚；同一 releaseTag 必须完成测试服、正式服、备份服发布和真实运行态验证。
- HARD RULE: 不得让未提交改动、未跟踪文件、脏工作区内容进入发布包；不得拼接不同 `releaseTag`；不得 mock、默认成功、静默跳过或手工标绿。
- STARTED: 2026-07-13T14:30:00+08:00。

## Milestone 1 - Task Records

- GREEN: previous-owned-task -> PASS，上一轮任务 `20260712-intmain-codeonly-three-env-release` 已标记 `completed`。
- GREEN: task-directory -> PASS，创建 `doc/tasks/20260713-current-head-codeonly-three-env-rerun/`。
- GREEN: task-doc-bootstrap -> PASS，已写入 `task.md` 与 `execution-log.md` 初始目标、里程碑、验证标准和设计约束。

## BDD Scenarios

- BDD: clean committed release input -> Given 三仓 `int_main` 有已提交 HEAD 且主工作区存在脏改, When 本次重新发布开始, Then 必须创建本次专用临时 release worktree 并只从冻结 HEAD 构建。
- BDD: updated frontend included -> Given 前端主程序已更新到新的已提交 HEAD, When build-release 完成, Then Manifest sourceRepos 必须记录最终 refreeze frontend commit 为 `a86c8da404fcd0fdd712375347494a1f711b925b` 且 dirty=false。
- BDD: code-only manifest contract -> Given 本轮发布为 code-only 且使用 `SkipDatabaseSync`/`SkipMinioSync`, When build-release 完成, Then Manifest 必须为 `publishScope=code-only`、sourceRepos clean 且发布包不包含数据目录。
- BDD: full release chain -> Given 测试服验证通过且本次按完整三环境重新发布, When 执行完整发布闭环, Then 同一 releaseTag 必须依次完成 `publish-test`、`mark-tested`、`promote-prod 且五个 operation 均为 SUCCESS。
- BDD: real runtime validation -> Given 发布动作成功, When 判定环境完成, Then 必须分别在测试服、正式服、备份服验证 `.env IMAGE_TAG`、镜像 tag、backend health、frontend HTTP、PDF worker HTTP，备份服还要验证 `/mnt/intruoyi-data`。

## Milestone 2 - Experience Preflight

- COMMAND: 读取并摘录 `docs/experience-index.md`、`docs/release-build-preflight-lessons.md `docs/test-release-preflight.md
- GREEN: experience-preflight -> PASS，当前完整三环境 code-only 重新发布命中干净发布输入、Manifest v1、required SQL/migration、publish-test、mark-tested、promote-prod `/mnt/intruoyi-data`、PowerShell/SSH/日志脱敏和 closeout 门禁。

## Milestone 3 - Current HEAD and Dirty Status

- COMMAND: 核对三仓主工作区 HEAD 与 dirty 状态。
- RESULT: maintenance=`1535b827e6089549c978b670b8c8349e5362c63a`，backend=`738cfaeb04cc1b123de42283a01560b63fdac2b2`，frontend=`cac1c25d0f9b15e511167b0d26c3e9d13ee550ea`。
- NOTE: 三仓主工作区均存在未提交或未跟踪内容；本轮构建必须只使用新建干净 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713h\m|b|f`，主工作区脏内容不得进入发布包。

## Milestone 3b - Updated HEAD Refreeze

- REQUEST: 用户补充“主程序又更新了，需要重新发布一次”，本轮以重新冻结时点的三仓 `int_main` 已提交 HEAD 为唯一发布输入。
- RESULT: maintenance=`1535b827e6089549c978b670b8c8349e5362c63a`，backend=`dd986dc1a03c36d279f20ee93822a666aaf628ff`，frontend=`a86c8da404fcd0fdd712375347494a1f711b925b`。
- NOTE: 已存在旧临时 release worktree `r260713i`，但 backend=`04df1fdfd40451123444b95c6d09cf8c07abe634` 且已落后于本轮冻结 backend HEAD，不能作为本轮发布输入；将按 clean/stale worktree 处理并新建 `r260713j`。
- ISSUE: stale-release-worktree -> 现象：旧 release worktree 与最新后端 HEAD 不一致；阶段：Git/worktree 前置检查；影响：若复用会发布旧主程序；原因判断：主程序在旧 worktree 创建后又有新提交；处理动作：新建本轮专用 `r260713j`，旧 worktree 只在确认 clean、配置未指向后删除；结果：待执行；是否可前置检查：是；是否可自动化：是；下次如何避免：每次用户要求“重新发布”时重新冻结三仓 HEAD 并判废旧 release worktree。

## Milestone 3c - Task Directory De-duplication

- 2026-07-13T16:02:28+08:00 ISSUE: duplicate-task-bootstrap -> 现象：恢复执行时短暂创建了重复任务目录
elease-intruoyi-full-20260713-republish；阶段：任务证据识别；影响：若保留可能造成后续提交范围混乱；原因判断：先按新请求创建目录，随后识别到同线程已有未完成任务 20260713-current-head-codeonly-three-env-rerun；处理动作：沿用已有任务目录并删除重复目录；结果：重复目录已删除；是否可前置检查：是；是否可自动化：是；下次如何避免：恢复发布任务先检查同日下午未完成任务目录再创建新目录。

## Milestone 6a - Log Redaction Correction

- ISSUE: publish-test-log-tail-secret -> 现象：运行控制台 `/operations/{id}/log` 返回的 publish-test 日志尾部包含 `mysql -p...` 参数，初次保存到 `publish-test-log-tail-r260713j-r1.redacted.json` 时尚未完成脱敏，且旧 r260713i 日志证据也命中同类模式；阶段：测试服发布证据保存；影响：这些文件不得以原样进入提交，且必须证明提交前 secret scan 为 0；原因判断：API 返回原始 operation log，文件名 `.redacted` 不等于内容已脱敏；处理动作：立即将本任务目录内所有 `mysql -p<secret>` 形态脱敏为 `mysql -p<redacted>`，并生成 `secret-scan-r260713j-after-publish-test.json`；结果：脱敏扫描通过；是否可前置检查：是；是否可自动化：是；下次如何避免：所有 operation log 保存后立即执行 secret scan，扫描通过前不得进入下一发布阶段或提交。


## Milestone 7a - Test Runtime Verification Parser Correction

- ISSUE: release-info-crlf-parser -> 现象：测试服第一次运行态采集 `release-info` 只删除 LF，保留 CR 后逐行解析只得到 `{`，导致 `releaseInfoTagOk=false`；阶段：测试服真实运行态验证；影响：应用运行态实际通过但证据解析失败，不能进入 mark-tested；原因判断：远端 JSON 为 CRLF/多行格式，采集脚本需要同时删除 CR 和 LF 或用 JSON parser；处理动作：改为 `tr -d '\r\n'` 后重新采集并核对 releaseTag 与双仓 commit；结果：复验通过；是否可前置检查：是；是否可自动化：是；下次如何避免：release-info 验证统一使用 JSON parser 或 CRLF-safe compact 采集。


## Milestone 10a - Runtime Console Page Probe Parser Correction

- ISSUE: console-error-string-parser -> 现象：运行控制台页面 Playwright probe 中 console 输出为 `Errors: 0, Warnings: 0`，但初始脚本用字符串包含 `error` 判定导致误报；阶段：运行控制台版本/变更说明页面验证；影响：页面和 console 实际通过但证据判定失败，不能收口；原因判断：扫描规则未区分统计字段和真实 console error；处理动作：改为显式检查 `Errors: 0` 与 `Warnings: 0`，并重新保存页面证据；结果：复验通过；是否可前置检查：是；是否可自动化：是；下次如何避免：Playwright console 验证用结构化统计或精确模式。

## Milestone 11a - Runtime Control Restore

- GREEN: runtime-control-main-restore -> PASS，已停止
260713j 维护控制台进程 PID 61980，启动主工作区 jar，48181 /actuator/health=UP，进程命令行指向 D:\ProjectPackage\Int\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar。
- ISSUE: powershell-pid-variable-reuse -> 现象：端口归属复核命令中使用 $PID 作为自定义变量导致 PowerShell 报只读变量错误；阶段：运行控制台恢复验证；影响：首轮归属核验命令报错但未影响已完成的进程恢复；原因判断：PowerShell 自动变量名误用；处理动作：改用 $listenPid 重新核验并保存
untime-control-main-process-r260713j.json；结果：复核通过；是否可前置检查：是；是否可自动化：是；下次如何避免：PowerShell 脚本禁止把 $PID//System.Management.Automation.Internal.Host.InternalHost 用作自定义变量。

## Milestone 7 - Test Runtime Verification

- GREEN: test-runtime-verification -> PASS，`172.30.30.58` `.env IMAGE_TAG`、backend/frontend image tag、backend health、frontend HTTP、PDF worker HTTP、release-info 与 release lock 均匹配 `release-20260713-intmain-codeonly-three-env-r260713j-r1`。
- Evidence: `test-runtime-verification-r260713j-r1.json`。

## Milestone 8 - Mark Tested

- GREEN: mark-tested -> PASS，operation `op-2026-07-13T082842115595300Z-4a697216-cf00-4a78-a510-24ee79f105b9` status=`SUCCESS`，`selectedRecoverySetCandidateId=restore:20260621-063218`，未携带 `targetEnvironment`。

## Milestone 9 - Promote Prod

- GREEN: promote-prod -> PASS，operation `op-2026-07-13T083054217937200Z-3408b81b-491c-44c7-9557-75c859340e60` status=`SUCCESS`，使用已验证发布包并通过正式服运行态验证。
- GREEN: prod-runtime-verification -> PASS，`172.30.30.57` `.env IMAGE_TAG`、backend/frontend image tag、backend health、frontend HTTP、PDF worker HTTP、release-info 与 release lock 均匹配 `release-20260713-intmain-codeonly-three-env-r260713j-r1`。

## Milestone 10 - Promote Backup

- GREEN: promote-backup -> PASS，operation `op-2026-07-13T092109387694Z-f88175d9-76a4-4689-9279-8528c32400a3` status=`SUCCESS`。
- GREEN: backup-runtime-verification -> PASS，`172.30.30.59` `.env IMAGE_TAG`、backend/frontend image tag、backend health、frontend HTTP、PDF worker HTTP、release-info、release lock、`/mnt/intruoyi-data` mount、release dir 与 data root 均验证通过。

## Milestone 11 - Closeout Verification

- GREEN: runtime-control-main-health-final -> PASS，`http://127.0.0.1:48181/actuator/health=UP`，进程命令行指向主工作区 Jar。
- GREEN: runtime-console-page -> PASS，运行控制台页面显示 `release-20260713-intmain-codeonly-three-env-r260713j-r1`、测试/正式/备份三环境版本号、变更说明和五个 SUCCESS operation，console `Errors: 0, Warnings: 0`。
- ISSUE: residual-release-worktree-root -> 现象：初始 `worktree-cleanup-r260713j.json` 显示 Git worktree 注册已删除、state dir 已删除，但 `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713j` 物理根目录仍存在且包含 `m`、`f` 残留目录；阶段：closeout/worktree cleanup；影响：不满足“临时发布 worktree 已删除”完成标准；原因判断：`git worktree remove`/前置清理删除了注册和部分物理目录，残留目录已不是 Git repository；处理动作：先核对三仓 `git worktree list --porcelain` 均无 `r260713j`，确认残留路径在固定 `D:/ProjectPackage/Int/IntRuoyiWorktrees` 下且 leaf 为 `r260713j`，确认 `m`、`f` 不是 Git repo 后用固定路径删除；结果：`worktree-cleanup-r260713j-final.json` status=`PASS`，root/state/registrations 均不存在；是否可前置检查：是；是否可自动化：是；下次如何避免：closeout 必须同时检查 Git 注册和物理根目录，不能只看 `git worktree list`。
- NOTE: closeout 时主工作区 backend/frontend `int_main` 已继续前进；按用户“程序在不断更新，不用每次都从 git 获取最新，只构建发布一开始 worktree 里记录的”的规则，本轮仍以 `dd986dc1a03c36d279f20ee93822a666aaf628ff` / `a86c8da404fcd0fdd712375347494a1f711b925b` 冻结输入为唯一发布基线。

## Milestone 12 - Experience Consolidation

- GREEN: experience-consolidation -> PASS，已将 release-info CRLF 验证、运行控制台页面 console 结构化判定、临时 worktree 物理根目录复核沉淀到 `docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md` 和 `docs/experience-index.md`。
- GREEN: verification-report -> PASS，`verification-report.md` 已从 PENDING 更新为 PASS 并覆盖发布链路、manifest、三环境运行态、运行控制台和 closeout 证据。
- STATUS: ready_for_closeout，待执行 task-closeout preview/apply 后标记 completed 并提交隔离文档。


## Milestone 13 - Task Closeout Cleanup

- RED: task-closeout apply -> FAIL，首次 apply 因 `runtime-control-main-r260713j.err.log` 被 48181 运行控制台进程占用而返回 `PermissionError WinError 32`；失败证据已冻结到 `closeout-apply-log-lock-freeze-r260713j.json` 后由 cleanup apply 删除，核心信息保留在本日志。
- ISSUE: task-closeout-runtime-log-lock -> 现象：主路径运行控制台恢复后 stdout/stderr 仍重定向到本任务目录，导致 task-closeout 无法删除任务附属日志；阶段：closeout cleanup；影响：任务无法完成清理和提交；原因判断：长运行进程日志位置仍在待清理任务目录；处理动作：停止 PID 32652，从主工作区 Jar 重启 PID 43072，并将 stdout/stderr 重定向到主仓 `logs/`；验证 health=UP、进程命令行指向主工作区 Jar；结果：第二次 task-closeout apply 成功；是否可前置检查：是；是否可自动化：是；下次如何避免：恢复主路径运行控制台时不得把长运行进程日志放在 task-closeout 待清理目录。
- GREEN: task-closeout preview -> PASS，status=ready，keep=`task.md`/`execution-log.md`/`verification-report.md`，blocked=<none>，warnings=<none>。
- GREEN: task-closeout apply -> PASS，status=applied，linked=False，current_branch=`int_main`，main_branch=`int_main`，blocked=<none>，warnings=<none>，仅删除本任务附属 JSON/log/evidence，保留核心任务记录。
- GREEN: final-runtime-control-health -> PASS，重启后的运行控制台仍为主工作区 Jar，`/actuator/health=UP`。
- STATUS: completed。
