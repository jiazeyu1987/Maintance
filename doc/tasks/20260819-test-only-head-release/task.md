# 20260819 仅测试服 HEAD 发布

## Task Goal

基于当前分支最新已提交代码（HEAD）构建维护控制台与测试发布包，并仅发布到测试服务器；未提交改动、未跟踪文件和脏工作区内容不得进入构建产物。

## Milestones

1. 启动门禁与任务文档：确认适用规则、经验门禁、发布/服务器/登录/worktree 文档。
2. Git 与 worktree 输入锁定：记录当前分支、HEAD、脏工作区状态、目标提交、构建目录、临时 worktree 路径。
3. 构建发布包：在干净临时 worktree 中基于目标 HEAD 执行 build-release，并校验包、manifest、版本号、变更说明。`r260819f-r1` 已因测试 eDHR 凭据/桶绑定漂移在产物生成前失败；`r260819f-r2` 虽构建成功，但 changeSet 仅含通用发布包信息，不能证明变更说明对应冻结提交，已按验收门禁判废。当前正式修复 commit-bound changeSet 契约，修复提交后必须使用新 worktree 和新 releaseTag 重建。
4. 仅测试服发布：执行 publish-test；禁止 mark-tested、promote-prod、promote-backup。待新 releaseTag 的构建、manifest、版本号和提交绑定变更说明全部通过后执行。
5. 测试服真实运行态验收：核 operation=SUCCESS、远端 `.env IMAGE_TAG`、backend/frontend 镜像 tag、容器状态、backend health=UP、frontend HTTP 200、前端页面、运行控制台版本号和变更说明。待执行。
6. 问题记录与长过程复盘：记录发布过程所有问题、耗时点、处理结果和可前置检查项。
7. 经验沉淀与收尾：发布成功后沉淀前置经验，执行 closeout 预览/清理，删除本任务临时 worktree，记录最终验证。

## Expected Verification

- 构建产物只包含本次启动时记录的当前分支 HEAD 已提交代码。
- build-release 产物、manifest、版本号、变更说明可追溯到目标提交。
- publish-test 成功且不触发正式服/备份服流程。
- 测试服务器真实运行态全部通过：镜像 tag、容器、健康检查、HTTP、页面、运行控制台版本和变更说明。
- 所有问题按“现象、阶段、影响、原因判断、处理动作、结果、是否可前置检查、是否可自动化、下次如何避免”记录。
- 发布成功后将新增问题沉淀为前置经验，并完成 task-closeout。

## 经验门禁

- 测试服发布主门禁：只允许单一 releaseTag 的 `build-release -> publish-test`；禁止 `mark-tested`、`promote-prod`、`promote-backup`；目标测试主机固定 `172.30.30.58`，远端运行目录 `/opt/intruoyi/runtime`。
- Git / worktree 门禁：维护仓与主程序仓均从启动时记录的当前分支 HEAD 新建本轮专用干净 release worktree；构建开始后不追逐后续新增提交；worktree dirty、HEAD 不一致或配置指向旧/主工作区即 fail fast。
- 构建门禁：`build-release` 后必须验证 operation=SUCCESS、发布包目录、`manifest.json`、legacy manifest、artifact hash、`sourceRepos[*].dirty=false`、后端/前端 commit 等于冻结 HEAD、版本号和变更说明可确认。
- 发布门禁：`publish-test` 预览/执行必须证明 `environment=test`、`ServerHost=172.30.30.58`、无正式/备份/mark-tested 动作；operation 非 SUCCESS、release lock/migration 异常、`.env` 与实际镜像漂移即 fail fast。
- 运行态门禁：发布后同时核 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=UP、frontend HTTP 200、`release-info.json`、运行控制台版本/变更说明真实页面。
- PowerShell / SSH 门禁：全程 UTF-8；不使用 `&&`；多行 SSH 脚本用 UTF-8 bytes + LF；native 命令以退出码和产物后置断言共同判定；不得提交 secret-bearing raw log。
- 经验沉淀门禁：发布成功后把可复用问题优先更新到 `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md` 和 `docs/experience-index.md`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；Object Lock verifier 仍为必须通过的阻断门禁，没有跳过或降级。
- 是否从根因和长期维护角度解决：是；本任务按正式发布链路和现有脚本执行，仅测试服范围内验收。
- 是否存在临时补丁或绕过：是；本机 Python 3.12 的 WMI 查询会在 boto3 user-agent 初始化时卡死，已在任务证据目录提供仅对本任务运行控制台进程生效的 `sitecustomize.py`。触发条件仅为命中该 WMI 卡死；风险限定为该进程的系统版本探测信息降级，不改变发布逻辑、源码、构建包或服务器；收尾时随任务证据清理并停止该进程。

## Current Status

in_progress

## Notes

- 2026-08-19 启动只读 bootstrap 时，首次 Python `-c` 命令因 PowerShell 字符串中的换行转义导致 `SyntaxError`；已改用 UTF-8 here-string 重跑成功。该问题将补录到 `execution-log.md` 的问题记录中。
- 初始 Git 检查显示维护仓主工作区和主程序仓主工作区均存在大量既有 dirty/untracked 内容；本轮发布必须使用干净临时 worktree，构建输入固定为启动时冻结的 HEAD。
- 2026-08-19 build-release operation `op-2026-08-18T174311645827300Z-818527d7-fab1-4411-9cec-bb27e29acdec` 在 manifest 生成前失败；维护仓实际 ops gate 阻塞 `schema` 迁移依赖 evidence-only `backfill`。本轮 releaseTag 未生成发布包，不允许继续 publish-test。
- 阻塞影响：未发布测试服、未触发正式服/备份服/mark-tested，保留本轮临时 worktree 与 runtime state 作为失败证据；后续需要正式修复迁移依赖并提交后，用新的冻结 HEAD 与新的 releaseTag 重新开始。
- 2026-08-19 新用户请求恢复仅测试服发布；本次作为同任务新一轮 `r260819b` 尝试执行，继续只允许基于启动时冻结的当前分支 HEAD 已提交代码构建，不追逐后续提交。
- 2026-08-19 本轮维护仓目标提交：`eba06a66a78ee3027397e54cea412ee6b8b0b741`（`int_main`，`任务: 修复基础镜像加载时机`）；主程序目标提交：`037e55c280c346df8aa8d89453240ce5c7e0c83a`（`int_main`）。维护仓和主程序主工作区均 dirty，本轮必须新建干净 release worktree。
- 2026-08-19 `r260819b` 已创建干净维护仓 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260819b\m` 和主程序 worktree `D:\IntRuoyiWorktree\r260819b\a`；实际维护仓 ops migration policy gate 在构建前再次阻塞同一 `schema -> backfill` 违规依赖。
- 2026-08-19 阻塞影响：`release-20260819-intmain-head-test-r260819b-r1` 未生成发布包、manifest、版本号或变更说明；未执行 `build-release`、`publish-test`、`mark-tested`、`promote-prod`、`promote-backup`，未写入测试/正式/备份服务器。本任务不能继续，直到主程序正式源码修复迁移依赖并提交新的 HEAD。
- 2026-08-19 用户授权正式源码修复后，主程序仓已提交 `e0c488267dabf77ce566acd0013cc400fdf88bfe`（实现修复）和 `22fce6c341c770cb6ac78eb5b2f9f82d5bbcd843`（修复记录收口）；本轮 `r260819c` 从维护仓 HEAD `eba06a66a78ee3027397e54cea412ee6b8b0b741` 与主程序 HEAD `22fce6c341c770cb6ac78eb5b2f9f82d5bbcd843` 重新冻结。
- 2026-08-19 `r260819c` 已创建干净维护仓 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260819c\m` 和主程序 worktree `D:\IntRuoyiWorktree\r260819c\a`；app gate 与维护仓实际 ops migration policy gate 均通过 505 个迁移。
- 2026-08-19 `r260819c` 维护控制台已从冻结维护 HEAD 完整构建，Maven 26 tests PASS，最终 JAR SHA-256=`73c7ee3e2f36dc4579e3bb6356fe5ae980496b080ffc559a56464053068007e6`；构建测试生成的 task-owned `runtime/` 已清理，维护 worktree 恢复 clean。
- 2026-08-19 主程序/维护前端依赖均按 frozen lockfile 恢复；pnpm ignored-builds 已通过临时最小 allowlist + `rebuild --pending` 清零，两个 `package.json` 按原始字节恢复且两个 release worktree clean。
- 2026-08-19 隔离运行控制台已在 `127.0.0.1:48182` 启动并 health=UP；build-release preview 已验证脚本、releaseTag、component=intruoyi、code-only 参数、冻结 repo roots 和三环境 host metadata，未包含禁止动作。下一步提交唯一 build-release operation。
- 2026-08-19 `r260819c` publish-test operation `op-2026-08-19T023827875413100Z-13472fce-31e6-4fa5-89d5-8a16f28dccd8` 在 required SQL `20260812_mes_pqc_dcc_qa_c00_postflight.sql` 失败，错误为 `input_manifest_sha256` 不能为空；releaseTag 判废且不得复用。
- 2026-08-19 用户再次授权后，主程序仓已提交 `adeb3aabc89e03d1f231552015d37bc78e0f2adb`（`任务: 修复C00发布后空哈希`）；本轮 `r260819d` 从维护仓 HEAD `eba06a66a78ee3027397e54cea412ee6b8b0b741` 与主程序 HEAD `adeb3aabc89e03d1f231552015d37bc78e0f2adb` 重新冻结，干净 release worktree 和 app/ops migration policy gate 已通过。
- 2026-08-19 `r260819d-r1` build-release 初次失败源于 app release worktree 缺少前端 `node_modules` / `cross-env`；已恢复依赖并通过 ignored-builds gate，再以同一冻结 HEAD 重提 `r260819d-r2`。
- 2026-08-19 `r260819d-r2` build-release operation `op-2026-08-19T042941283451700Z-b0f3d097-fb52-42a6-9d49-ad7c44a67312` 已 SUCCESS；包路径 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260819-intmain-head-test-r260819d-r2`，`manifest.json` / `release-manifest.json` / 前端 `release-info.json` 的 releaseTag、packageId、变更说明与 sourceRepos commit 均一致指向 `adeb3aabc89e03d1f231552015d37bc78e0f2adb`。
- 2026-08-19 `r260819d-r2` 首次 publish-test 在 eDHR Object Lock 前置校验主动失败：测试服既有 `.env` 指向正式服 `172.30.30.57:9000`，继续会越过本次仅测试服授权范围；终止点在镜像上传、迁移和容器切换之前。
- 2026-08-19 已通过测试服 MinIO `172.30.30.58:9000` 完成独立 Object Lock verifier，9 项检查 PASS；本机 Python 3.12 WMI 卡死通过仅对任务进程生效的 `PYTHONPATH/sitecustomize.py` 处理，未进入源码或发布包。下一步重启隔离控制台后重提同一已构建 releaseTag 的 publish-test。

- 2026-08-19 `r260819d-r2` publish retry failed at `20260812_mes_route_version_snapshot_identity_enforce.sql` because all 47 `mes_pro_route_version` rows lacked snapshot identity columns; failure tag 判废。维护仓已提交 `74b3a87` 增加 backend image `BACKFILL/READINESS` hook，下一轮 `r260819e` 使用维护 HEAD `74b3a87` 和主程序固定提交 `adeb3aabc89e03d1f231552015d37bc78e0f2adb` 重新构建发布。
- 2026-08-19 用户再次回复“授权”后继续仅测试服发布；本轮 `r260819e` 已冻结维护仓 `74b3a87bf60be40d0f5ccf6bbe37874a5a7ea465` 和主程序 `adeb3aabc89e03d1f231552015d37bc78e0f2adb`，干净 release worktree 为 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260819e\m` 与 `D:\IntRuoyiWorktree\r260819e\a`。
- 2026-08-19 `r260819e` runtime-control 配置摘要、app migration policy gate 和维护仓实际 ops migration policy gate 已通过；维护控制台构建 PASS。
- 2026-08-19 `release-20260819-intmain-head-test-r260819e-r1` 在 build-release 期间因前台 48182 控制台被中断而留下 stale RUNNING state 与不完整本地包；该 tag 缺 manifest/版本说明，已判废，不得发布。下一步在同一冻结 worktree/提交上使用新 releaseTag `release-20260819-intmain-head-test-r260819e-r2` 重建。
- 2026-08-19 `r260819e-r2` 已完成 build-release SUCCESS、manifest/sourceRepos/release-info 校验和 publish-test 预览；publish operation `op-2026-08-19T123706070455900Z-1dfb7779-a297-4a37-9f7c-c378926f64f6` 在路线快照身份 BACKFILL hook 阶段失败，未切换 backend/frontend 容器。失败 releaseTag 判废，不得复用。
- 2026-08-19 失败根因：维护脚本以 `docker compose run ... -e ARGS=<migration args>` 覆盖了 Compose backend 原有完整 `ARGS`，一次性容器回退连接 `127.0.0.1:23306`，导致 MySQL connection refused；失败收束又把完整 Spring 堆栈拼进 SSH 命令，远端锁释放未成功，测试服残留该 operation 的 `RUNNING` lock，`.env IMAGE_TAG` 已写入失败 tag 而实际容器仍为旧镜像。已记录为 P034-P037，进入正式脚本修复前置阶段。
- 2026-08-19 维护仓提交 `7464294`（`任务: 修复测试发布迁移参数与失败收束`）已快进合入 `int_main`；维护发布脚本/Dockerfile/回归测试 23 项 PASS。该提交增加 hook 参数隔离、错误状态安全收束和目标 eDHR endpoint package 绑定；下一轮必须使用新 releaseTag 和新专用 release worktree。
- 2026-08-19 `r260819e-r2` 残留 lock 已按精确 operation 收束为 `FAILED`，影响 1 行；437 条 migration 证据保留。新 tag `release-20260819-intmain-head-test-r260819f-r1` 发布前检查通过：无 RUNNING lock、无目标 migration、backend health=UP、frontend HTTP=200。
- 2026-08-19 当前状态：开始创建 `r260819f` 专用干净 release worktree；未执行任何正式服、备份服或 `mark-tested` 操作。
- 2026-08-19 `r260819f` 已冻结维护仓 `7464294a7db03bcd75323116f6ada6c108002494` 与主程序 `adeb3aabc89e03d1f231552015d37bc78e0f2adb`，两个专用 worktree 均 detached clean；app/ops migration gate、维护控制台构建、主程序前端 `pnpm ts:check` 与 `pnpm build:test` 均通过。
- 2026-08-19 `release-20260819-intmain-head-test-r260819f-r1` 的唯一 build-release operation 在发布包目录创建前 fail fast：测试端点与测试服旧 `.env` 的失效 Access Key/不存在 bucket 被错误混用，Object Lock verifier 返回 HTTP 403 `InvalidAccessKeyId`。该 tag 无 package/manifest/release-info，已判废，未写测试服、正式服或备份服。
- 2026-08-19 已从测试服现有受控 `.env.copytest` 只读取测试环境绑定到当前进程并重新执行 Object Lock verifier：endpoint=`http://172.30.30.58:9000`、bucket=`edhr-retention-verifier-20260530`，9 项检查 PASS。下一步使用同一冻结 worktree/提交与新 tag `release-20260819-intmain-head-test-r260819f-r2` 重建。
- 2026-08-19 `release-20260819-intmain-head-test-r260819f-r2` build-release operation `op-2026-08-19T155932383630800Z-bf57b59b-0327-46d9-86c1-53e233b37888` 已 SUCCESS，package/manifest/sourceRepos/image/runtime-env 门禁均通过；但 manifest 与镜像内 `release-info.json` 的 `changeSet` 只有发布包和组件范围，没有冻结提交 `adeb3aabc...` 的提交主题 `任务: 修复C00发布后空哈希`。按“版本号和变更说明必须与构建提交一致”验收标准，该 tag 判废，未执行 publish-test。
- 当前阶段：按 BDD/TDD 正式修复维护发布脚本，使 `changeSet.summary/items` 从冻结 sourceRepos 提交读取并 fail fast；修复验证并提交后创建下一轮专用干净 release worktree，使用新 releaseTag 重建。禁止手工改包、manifest 或镜像内 release-info 绕过重新构建。
- 2026-08-20 `r260819g-r1` build-release SUCCESS 后再次按门禁判废：变更说明含短提交但中文 subject mojibake，且 `runtime-env/test.env` 指向正式服 eDHR endpoint `172.30.30.57`。未执行 publish-test 或任何正式/备份动作。
- 2026-08-20 维护仓已提交修复 `2d5a42bbe900b2b04bd5f4b8283d99994e0d0950`（`任务: 修复发布说明与测试环境边界`）：Git subject 改为 UTF-8 输出采集，target-specific eDHR 优先生效，test runtime env 阻断正式/备份主机端点；Node 合同 4/4、发布相关 pytest 33/33、UTF-8 subject 探针均 PASS。
- 2026-08-20 新一轮 `r260820a` 已创建干净 release worktree：维护 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260820a\m` @ `2d5a42bbe900b2b04bd5f4b8283d99994e0d0950`，主程序 `D:\IntRuoyiWorktree\r260820a\a` @ `adeb3aabc89e03d1f231552015d37bc78e0f2adb`；计划 releaseTag `release-20260820-frozen-head-test-r260820a-r1`，继续仅测试服发布。
- 2026-08-20 `r260820a-r2` build-release 与 manifest/release-info/runtime-env 校验通过，但 publish-test 在 route snapshot BACKFILL hook 阶段失败：一次性 backend 启动后 Quartz job 查询尚未迁移出的 `mes_pro_edhr_work_task.pqc_release_application_scope_id`，导致 `Unknown column`；该 releaseTag 判废，未切换实际 backend/frontend 容器，测试服发布未成功。
- 2026-08-20 当前正式继续轮次为 `r260820b`：维护仓冻结提交 `59bc2330b4e2998415f738bdf6f10206135adb7c`（禁用发布迁移 hook 调度器），主程序仍固定 `adeb3aabc89e03d1f231552015d37bc78e0f2adb`；干净 release worktree 为 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260820b\m` 与 `D:\IntRuoyiWorktree\r260820b\a`；计划 releaseTag `release-20260820-frozen-head-test-r260820b-r1`。
- `r260820b-r1` build-release SUCCESS 但完整 manifest validator 在 `runtime-env/*.env` 发现 eDHR endpoint/目标 IP 契约冲突，且 prod/backup runtime-env 继承测试 eDHR；该 tag 判废，未执行 publish-test。正式修复已提交到 `codex/20260820-release-hook-args-fix`：`e3c3fedf8ccb7bca81925ab8b892c59bdd3097ab`（`任务: 修复发布包环境边界校验`），目标为非 test 环境不继承 generic eDHR、validator 对 runtime-env eDHR endpoint 做字段级例外并保留其他 IP 扫描。
- 下一轮必须新建专用 release worktree，维护仓冻结 `e3c3fedf8ccb7bca81925ab8b892c59bdd3097ab`，主程序仍固定 `adeb3aabc89e03d1f231552015d37bc78e0f2adb`，使用新 releaseTag `release-20260820-frozen-head-test-r260820c-r1`；不得复用 `r260820b-r1` 包或旧 validator 结果。
- 2026-08-19 `r260820c` 已创建新的专用 release worktree：维护 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260820c\m` @ `e3c3fedf8ccb7bca81925ab8b892c59bdd3097ab`，主程序 `D:\IntRuoyiWorktree\r260820c\a` @ `adeb3aabc89e03d1f231552015d37bc78e0f2adb`；两个 worktree 均 detached clean，构建目录固定为维护 worktree、发布输入固定为主程序 worktree。
- 2026-08-19 `r260820c` 构建前置已完成：维护控制台 JAR SHA-256=`663C5FCA90F49FCCFC36264A43EEDCCE06C668C09CF6955F5023A38915BC1B99`，app/ops migration gate 均为 505 migrations PASS，app `ts:check`/`build:test` PASS，隔离控制台 48182 health=UP；目标 releaseTag 尚未占用，远端 lock/migration 和运行态预检 PASS。首次 Windows PowerShell 5.1 远端探针空值异常已记录为 P059，改用 `pwsh` 后通过。
- 2026-08-20 `r260820c-r1` 的唯一 `build-release` operation=`op-2026-08-19T234923044851500Z-7e04040e-bcca-4de7-9bab-4459efe98c65` 在发布包生成阶段因 `EDHR_S3_ENDPOINT` 指向正式 eDHR 主机 `172.30.30.57` 而 fail fast；包目录仅有部分构建内容，没有 `manifest.json`、legacy manifest 或 `release-info`，该 releaseTag 判废，不得发布或复用。失败证据见 `evidence/build-release-final-r260820c-r1.json` 与脱敏日志。
- 2026-08-20 已确认根因：r260820c 运行控制台进程重启时继承了本机/用户级 generic `EDHR_S3_*` 正式环境变量，未加载测试服 `/opt/intruoyi/runtime/.env.copytest` 的测试 eDHR 绑定；下一轮必须新建专用 worktree，并在启动运行控制台前将测试绑定同时注入 `EDHR_S3_TEST_*` 与 generic `EDHR_S3_*`，再做 binding summary 和 Object Lock verifier 预检。下一轮标识为 `r260820d`，冻结提交不变，使用新 releaseTag `release-20260820-frozen-head-test-r260820d-r1`。
- 2026-08-20 `r260820d` 专用 release worktree 已创建并复核 clean：维护 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260820d\m` @ `e3c3fedf8ccb7bca81925ab8b892c59bdd3097ab`，主程序 `D:\IntRuoyiWorktree\r260820d\a` @ `adeb3aabc89e03d1f231552015d37bc78e0f2adb`；隔离控制台配置已改绑 r260820d repo/frontend/ops/state 路径，test access enabled，prod/backup access disabled。证据=`evidence/frozen-baseline-r260820d.json`。
- 2026-08-20 `r260820d` 构建前置已完成：app/ops migration gate 均 PASS 505 个迁移；维护控制台 build PASS，JAR SHA-256=`9C82D28C0953BDFCF250E95D0B66EFC2B918DDE9339C8107D4CE4B01133919D6`；维护/主程序 pnpm ignored-builds 均清零；主程序前端 `pnpm ts:check` 与 `pnpm build:test` PASS；两个 worktree tracked clean。证据=`evidence/build-preflight-summary-r260820d.json`。
