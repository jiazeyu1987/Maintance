# 20260712 当前 HEAD 仅测试服发布问题台账

## P001 三仓主工作区均存在未提交内容

- 现象：maintenance、backend、frontend 主工作区均 dirty。
- 阶段：构建前 Git 状态检查。
- 影响：不得直接从主工作区构建，否则无法证明产物只包含当前分支 HEAD 已提交内容。
- 原因判断：并行开发和历史任务遗留文件存在于主工作区。
- 处理动作：按发布门禁创建本轮专用短路径干净临时 release worktree，并检出冻结 HEAD。
- 结果：已通过短路径 release worktree 隔离，三个构建目录均 clean。
- 是否可前置检查：是。
- 是否可自动化：是，三仓 `git status --short --branch` 与 `git status --porcelain` 可自动采集。
- 下次如何避免：发布启动脚本先生成冻结基线 JSON，dirty=true 时自动进入短路径 worktree 流程。

## P002 PowerShell here-doc 语法不兼容

- 现象：`python -X utf8 - <<'PY'` 在 PowerShell 5.1 中解析失败，提示 `<` 运算符保留。
- 阶段：临时发布 worktree 冻结证据写入。
- 影响：首次命令在解析阶段失败，未创建 worktree，未触发构建或服务器动作。
- 原因判断：误用了 Bash here-doc 语法，不符合本机 PowerShell 规则。
- 处理动作：改为 PowerShell 原生命令和后续 patch 记录证据，重新执行 worktree 创建与验证。
- 结果：已修复，worktree 冻结通过。
- 是否可前置检查：是。
- 是否可自动化：是，PowerShell 命令 lint 可禁止 `<<` here-doc。
- 下次如何避免：涉及多行 Python/SQL/SSH 标准输入时固定使用 PowerShell here-string、脚本文件或原生 PowerShell 结构，不使用 Bash here-doc。

## P003 后端迁移 SQL 缺 release-migration metadata

- 现象：全量 release migration policy gate 返回 missing release-migration metadata: D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712t\b\sql\mysql\20260711_mes_batch_record_cell_link_rule.sql。
- 阶段：build-release 前置契约门禁。
- 影响：无法确认该 required SQL 的发布环境、依赖、类型和风险等级；禁止生成 releaseTag、manifest 和发布包，禁止执行 publish-test。
- 原因判断：冻结后端 HEAD 中新增迁移 SQL 文件首部缺少发布元数据注释，不满足维护仓发布脚本契约。
- 处理动作：立即停止发布流程，复跑门禁确认失败，读取问题 SQL 前 60 行作为证据，未继续 build-release/publish-test。
- 结果：本次仅测试服发布阻塞，测试服务器未写入。
- 是否可前置检查：是。
- 是否可自动化：是，build-release 前固定运行
un-release-migration-policy-gate.py --sql-root <backend>\sql\mysql。
- 下次如何避免：所有新增 sql/mysql/*.sql 在进入可发布 HEAD 前必须先补齐 release-migration metadata，并把 migration policy gate 纳入后端提交前验证。

## P004 门禁失败后仍继续构建维护控制台

- 现象：首次构建脚本批处理里 migration policy gate 输出失败 JSON 后，因未立即检查 native command exit code，后续继续执行维护控制台前端与后端构建。
- 阶段：build-release 前置门禁与维护控制台构建。
- 影响：未造成服务器写入，也未生成 releaseTag/manifest；但增加了耗时，并在 maintenance release worktree 内产生了临时
untime/ 目录。
- 原因判断：PowerShell 脚本未在 native Python 命令后立即判断 $LASTEXITCODE，ErrorActionPreference 不会自动拦截该 native exit code。
- 处理动作：复跑 migration gate 并显式记录 policy_exit=1；清理本任务产生的 untracked
untime/；停止发布流程。
- 结果：已纠正流程状态，release worktree 恢复 clean。
- 是否可前置检查：是。
- 是否可自动化：是，所有 native gate 命令后必须统一断言 $LASTEXITCODE -eq 0。
- 下次如何避免：把 migration gate 独立为第一阶段命令，成功后再启动维护控制台构建；禁止把硬门禁和后续构建串成无退出码检查的长批处理。

## P005 Scope 更新日志 Add-Content 参数顺序错误

- 现象：记录“只发布intmain”时，PowerShell Add-Content 因未显式使用 -Value 参数而把多行文本解析为位置参数。
- 阶段：用户 scope 更新记录。
- 影响：首次日志追加失败；未影响 Git 冻结、构建、发布或服务器状态。
- 原因判断：PowerShell 参数绑定对多行中文字符串较敏感，且命令参数顺序不够显式。
- 处理动作：改用 System.IO.File.AppendAllText 显式 UTF-8 追加。
- 结果：已修复并重新记录 scope 更新。
- 是否可前置检查：是。
- 是否可自动化：是，PowerShell 记录类命令统一使用显式 -Value 或 .NET UTF-8 写入 API。
- 下次如何避免：中文多行日志写入不用隐式位置参数。

## P006 当前 int_main 后端 HEAD 仍缺迁移 metadata

- 现象：当前 int_main backend HEAD 51bfedc5c575155c22f08da880da19bce75b60dd 的 migration policy gate 仍失败，错误为 sql/mysql/20260711_mes_batch_record_cell_link_rule.sql 缺 release-migration metadata。
- 阶段：用户要求只发布 int_main 后的重新冻结与 build-release 前置门禁。
- 影响：不能生成 releaseTag、manifest、版本号或变更说明，不能执行 publish-test。
- 原因判断：最新已提交 int_main 仍包含不满足发布契约的 required SQL。
- 处理动作：从最新 int_main HEAD 创建干净发布 worktree 后复跑门禁，确认失败，停止发布。
- 结果：本次发布继续阻塞；测试服未写入。
- 是否可前置检查：是。
- 是否可自动化：是，所有发布前必须先跑全量 migration policy gate。
- 下次如何避免：后端 int_main 合入 SQL 前必须要求 release-migration metadata gate 通过。

## P007 本轮发布冻结后源分支继续前进

- 现象：r260712p 发布 worktree 冻结后，backend/frontend 主工作区 HEAD 后续继续前进。
- 阶段：构建前 Git 状态检查、closeout 前复核。
- 影响：如果重新读取主工作区 HEAD 构建，会混入发布开始后代码，违反本次“只构建发布一开始 worktree 里记录的”约束。
- 原因判断：开发分支仍在持续推进，发布流程与开发并行。
- 处理动作：固定 releaseTag=`release-20260712-intmain-test-r260712p-r3`，构建、manifest、publish-test 和运行态验收全部只认 r260712p 冻结提交。
- 结果：发布产物 backend=`c7753b28997dbd8d8b3581250961646f00b14ccb`、frontend=`2d10335f75a72f934aac52839fdb78a696036304`，未追逐后续提交。
- 是否可前置检查：是。
- 是否可自动化：是，build-release 前后比对 release worktree HEAD 与 manifest sourceRepos。
- 下次如何避免：发布启动后把冻结提交写入任务文档和 manifest 校验脚本，后续只按冻结 JSON 验证。

## P008 后端门禁脚本路径误判

- 现象：修复迁移 metadata 后，曾误用历史路径 `scripts\release_sql_preflight_gate.py` 复跑门禁。
- 阶段：后端修复验证。
- 影响：会把脚本路径缺失误判为迁移验证失败，拖慢恢复发布。
- 原因判断：维护仓当前权威门禁脚本在 `ops\release\run-release-migration-policy-gate.py`。
- 处理动作：改用维护仓 ops 脚本执行 targeted/full migration policy gate。
- 结果：targeted 与 full gate 均通过。
- 是否可前置检查：是。
- 是否可自动化：是，发布任务从维护仓配置读取门禁脚本路径并先检查 `Test-Path`。
- 下次如何避免：经验索引和发布 checklist 只保留权威脚本入口，旧路径出现即 fail fast。

## P009 `$PID` 是 PowerShell 保留变量

- 现象：切换运行控制台时使用 `$PID` 作为普通变量导致命令失败。
- 阶段：本地 48181 运行控制台切换。
- 影响：运行控制台未按预期切换，build-release 无法使用本轮 worktree 配置。
- 原因判断：PowerShell `$PID` 是自动变量，不能赋值复用。
- 处理动作：改用非保留变量名记录进程 ID，重新切换并验证 health。
- 结果：运行控制台成功切到 r260712p worktree 并返回 health=`UP`。
- 是否可前置检查：是。
- 是否可自动化：是，PowerShell lint 禁止写入 `$PID`、`$Args` 等自动变量。
- 下次如何避免：脚本变量统一使用业务前缀，例如 `$runtimePid`、`$previewArgs`。

## P010 维护前端构建 stderr 造成假失败

- 现象：维护前端 Vite/pnpm build 已生成 dist，但 PowerShell 包装命令因 stderr/ANSI 输出判定失败。
- 阶段：维护控制台构建。
- 影响：造成一次误判和重复检查，增加耗时。
- 原因判断：native 命令可能把 warning 或进度输出写到 stderr，不能只凭 stderr 非空判失败。
- 处理动作：复核 dist、jar 和 SHA256，以退出码与产物存在性作为判定依据。
- 结果：维护控制台 Jar 构建成功，SHA256=`2E1A10C39298BB3F44E00D8A00571B5B12E9DA60F2B27DC662B2E8C9D28BDBD7`。
- 是否可前置检查：是。
- 是否可自动化：是，包装器按 exit code + expected artifact 校验。
- 下次如何避免：对 pnpm/Vite/Maven 等 native 命令记录 stderr 但不单独以 stderr 非空失败。

## P011 release worktree 前端依赖缺失

- 现象：build-release 首轮失败，干净前端 worktree 缺少 `node_modules`。
- 阶段：应用前端构建。
- 影响：不能完成前端构建和发布包产出。
- 原因判断：临时 release worktree 是新建干净目录，不能假设主工作区依赖已存在。
- 处理动作：在 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712p\f` 执行 `corepack pnpm@10.25.0 --dir ... install --frozen-lockfile`。
- 结果：依赖恢复后继续构建。
- 是否可前置检查：是。
- 是否可自动化：是，build-release 前检查 `node_modules` 与 pnpm lockfile。
- 下次如何避免：每次新 release worktree 创建后先按锁文件安装/验证前端依赖。

## P012 Smart Release 报告缺少基线 manifest

- 现象：r2 build-release 启用 `enableSmartReleaseReport` 后失败，日志提示缺少 `SmartReleaseBaselineManifestPath`。
- 阶段：build-release。
- 影响：发布包未生成，不能继续 publish-test。
- 原因判断：Smart Release report-only 是可选报告能力，但启用时必须提供显式本地基线 manifest。
- 处理动作：记录失败 releaseTag，禁用该可选报告参数，以同一冻结输入重建新 releaseTag。
- 结果：r3 build-release 成功。
- 是否可前置检查：是。
- 是否可自动化：是，preview 中若 `enableSmartReleaseReport=true` 必须校验 baseline manifest 可读。
- 下次如何避免：无基线 manifest 时不要开启 Smart Release 报告；需要报告时先准备并校验基线文件。

## P013 preview 主机 token 检查过宽

- 现象：build-release/publish-test preview 中出现 `BackupServerHost=172.30.30.59`，被初始 forbidden token 检查误判为备份服发布风险。
- 阶段：build-release preview、publish-test preview。
- 影响：造成两次人工复核和流程停顿。
- 原因判断：运行控制台会把 TestServerHost/BackupServerHost 等作为参数元数据传入脚本；真实目标应以 `-Environment`、`-ServerHost`、`-Mode` 判断。
- 处理动作：改为解析参数角色，确认 publish-test 的 `-Environment test`、`-ServerHost 172.30.30.58`、`-Mode deploy-release`，且无 `promote-prod`、`promote-backup`、`mark-tested`。
- 结果：publish-test preview target gate 通过，仅发布测试服。
- 是否可前置检查：是。
- 是否可自动化：是，preview gate 解析参数数组而非全文 token。
- 下次如何避免：禁止用裸 IP token 作为唯一阻断条件；必须区分目标字段和元数据字段。

## P014 Manifest v1 与 legacy manifest schema 混用

- 现象：首次 manifest 校验查找 root `component` 失败。
- 阶段：发布包校验。
- 影响：可能误判 manifest 不合格，阻塞发布。
- 原因判断：Manifest v1 的组件字段位于 `changeSet.component`，legacy `release-manifest.json` 才有 root `component`。
- 处理动作：按两个 schema 分开校验，Manifest v1 读取 `changeSet.component` 和 sourceRepos，legacy manifest 只按兼容概要校验。
- 结果：r3 package/manifest 校验通过。
- 是否可前置检查：是。
- 是否可自动化：是，schema-specific validator 固化字段路径。
- 下次如何避免：不要用 legacy 字段路径校验 Manifest v1。

## P015 build-release/publish-test 耗时较长

- 现象：build-release 与 publish-test 均经历长时间 Docker 构建、镜像导出、NAS/远端传输和启动等待。
- 阶段：build-release、publish-test。
- 影响：命令可能超过普通交互超时，容易误判为失败或重复提交。
- 原因判断：镜像 tar 约 815MB，发布脚本包含 Docker build/save/load、NAS 包同步和远端服务启动。
- 处理动作：通过运行控制台 operations API 轮询最终 operation status，并记录 log tail。
- 结果：build-release r3 与 publish-test r3 均最终 SUCCESS。
- 是否可前置检查：是。
- 是否可自动化：是，所有长任务统一提交后轮询 operation store。
- 下次如何避免：长任务使用 operationId 恢复状态，不重复提交同一 releaseTag。

## P016 runtime-control release-status PowerShell 输出中文乱码

- 现象：PowerShell `Invoke-RestMethod | ConvertTo-Json` 输出中 actionLabel/summary/changes 出现乱码。
- 阶段：运行控制台版本号和变更说明验证。
- 影响：如果只看 PowerShell 文本，会误判变更说明不可读。
- 原因判断：PowerShell 5.1 JSON/控制台编码链路对中文不稳定。
- 处理动作：改用 Python 直接请求 API 并按 UTF-8 解析，验证 `testCurrentReleaseTag`、summary、changes 和 sourceRepos。
- 结果：运行控制台版本号和变更说明验证通过。
- 是否可前置检查：是。
- 是否可自动化：是，中文 JSON 验收统一使用 UTF-8 runtime。
- 下次如何避免：PowerShell 中文输出只作辅助，权威证据用 UTF-8 Python/Node 采集。

## P017 运行控制台恢复主路径首次验证误判

- 现象：首次恢复本地 48181 时未识别仍占用端口的 r260712p 进程，启动主路径 Jar 后端口仍由旧进程占用，验证失败。
- 阶段：closeout 运行控制台恢复。
- 影响：不能删除临时 worktree，否则 48181 会继续引用待删路径。
- 原因判断：进程命令行中的反斜杠转义导致字符串匹配条件过窄。
- 处理动作：重新采集端口 owner 和 Java command line，停止 r260712p 进程后从主路径 Jar 启动并验证 health。
- 结果：48181 已由主路径 `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 提供，health=`UP`。
- 是否可前置检查：是。
- 是否可自动化：是，按端口 owner 精确映射进程，并同时检查是否含 worktree 路径。
- 下次如何避免：删除 release worktree 前必须确认无 Java 进程 command line 引用该路径。

## P018 worktree 删除进程守卫匹配到自身命令

- 现象：worktree 删除守卫用 `Get-CimInstance Win32_Process` 全量匹配 `r260712p`，结果匹配到正在执行清理的 PowerShell 自身命令。
- 阶段：closeout worktree 删除。
- 影响：首次删除被误阻塞，未删除 worktree。
- 原因判断：清理命令文本本身包含待删除路径，不能作为长期占用进程。
- 处理动作：改为仅阻塞 `java.exe` 等长生命周期运行态进程引用，忽略当前清理命令自身。
- 结果：r260712p 三仓 worktree 注册和物理目录均删除成功。
- 是否可前置检查：是。
- 是否可自动化：是，进程守卫按进程类型与 owner 过滤。
- 下次如何避免：删除脚本避免用“命令行包含目标路径”的宽泛规则阻塞自身。
