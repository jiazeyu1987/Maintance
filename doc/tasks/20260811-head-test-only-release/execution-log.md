# 2026-08-11 当前 HEAD 仅测试服发布执行日志

## BDD

- BDD: 仅测试服发布冻结 HEAD -> Given 维护仓和主程序仓主工作区均存在未提交改动，When 发布开始，Then 只记录开始时当前分支 HEAD 并从该 HEAD 创建本轮专用 clean worktree 构建，不让未提交改动进入产物。
- BDD: 发布包来源可证明 -> Given 构建完成，When 检查发布包，Then manifest、release-info、版本号、变更说明、sourceRepos commit/dirty 和 artifact hash 必须全部与冻结 HEAD 一致，否则停止发布。
- BDD: 只发布测试服 -> Given 发布包校验通过，When 执行发布，Then 仅允许同一 releaseTag 的 publish-test SUCCESS，禁止 mark-tested/promote-prod/promote-backup 与正式服/备份服写入。
- BDD: 真实运行态验收 -> Given publish-test SUCCESS，When 验收测试服，Then .env IMAGE_TAG、实际镜像、容器、health、HTTP、页面、release-info、release lock/migration 和运行控制台版本变更说明必须全部匹配本轮 releaseTag。

## Preflight Evidence

- 2026-08-11T00:00:00+08:00 PLAN: 本任务使用 CI/CD Environment Delivery 技能；已读取 `ci-cd-environment-delivery/SKILL.md` 与 `references/cicd-contract.md`。
- 2026-08-11T00:00:00+08:00 PREVIOUS-TASK: `doc/tasks/20260809-head-test-only-release/task.md` 为 `completed`，同类前序任务不阻塞本轮。
- 2026-08-11T00:00:00+08:00 PRECHECK: 已读取 `AGENTS.md`、`docs/experience-index.md`、`docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\login-access.md`、`E:\IntRuoyi\docs\worktree-memory.md`、`E:\IntRuoyi\docs\powershell-memory.md`。
- 2026-08-11T00:00:00+08:00 GREEN: experience-preflight -> PASS，适用门禁已摘取到 `task.md`；后续服务器写入、publish-test、Playwright 页面验收和 worktree 清理均按该门禁执行。
- 2026-08-11T00:00:00+08:00 GIT: 维护仓 branch=`int_main` HEAD=`697f81688bf80527e9a3a7e4a680e8656f0e05b0` dirty count 初查约 `162`；主程序仓 branch=`int_main` HEAD=`5699b804576851ea8cdebf36045d381f044fb5e8` dirty 且 ahead origin/int_main 7。
- 2026-08-11T00:00:00+08:00 DECISION: 两个主工作区均不得直接作为构建目录；创建 `r260811a` 专用 release worktree 并只基于冻结 HEAD 构建。

## Issues

### I001 主工作区 dirty 且主程序 git status 出现 target_corrupt warning

- 现象：维护仓主工作区 dirty count 初查约 162；主程序仓 dirty 且 `git status` 输出多个 `target_corrupt_m4_20260802_1327` warning。
- 阶段：Git / worktree 启动门禁。
- 影响：主工作区不能证明构建只来自已提交代码，且 status warning 会干扰结构化摘要。
- 原因判断：并行开发和历史 Maven target 残留导致主工作区不适合作为发布构建输入。
- 处理动作：冻结当前 HEAD，创建本轮专用 clean release worktree；后续所有构建和发布 API 均指向 release worktree。
- 结果：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a\m` 与 `D:\IntRuoyiWorktree\r260811a-release-app` 均已创建为 detached clean worktree，HEAD 分别匹配冻结提交。
- 是否可前置检查：是。
- 是否可自动化：是，发布脚本启动前固定输出 dirty count、status hash、warning 摘要和 worktree clean 断言。
- 下次如何避免：仅测试服发布默认从专用 release worktree 开始，不在主工作区执行构建。

## Long-running Stage Reviews

- 启动阶段：完成规则、经验、Git 和路径门禁；下一步创建 clean release worktree 并运行构建前校验。
- Git / worktree 阶段：本轮 release worktree 创建并复核 clean；下一步运行构建前 migration/manifest 脚本门禁与维护控制台构建。

## Worktree Evidence

- GREEN: maintenance-release-worktree -> PASS，path=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a\m`，HEAD=`697f81688bf80527e9a3a7e4a680e8656f0e05b0`，dirtyCount=0。
- GREEN: app-release-worktree -> PASS，path=`D:\IntRuoyiWorktree\r260811a-release-app`，HEAD=`5699b804576851ea8cdebf36045d381f044fb5e8`，dirtyCount=0。
- GREEN: release-source-isolation -> PASS，构建目录只使用上述 release worktree；主工作区 dirty 内容不进入产物。
- GREEN: runtime-control-config-isolation -> PASS，local config 已复制到维护 release worktree，`repo-root`/`frontend-root` 指向 `D:\IntRuoyiWorktree\r260811a-release-app`，`ops-root` 指向维护 release worktree，`state-dir` 指向 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a-state`；只记录非敏感路径字段。

## Maintenance Build

- GREEN: maintenance-build -> PASS，`scripts\build.ps1` 完成 pnpm install/typecheck/build 与 Maven test/package；Maven tests run=26，failures=0，errors=0，skipped=0。
- GREEN: maintenance-jar -> PASS，`backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` SHA256=`ae2b9cc2c0b4f3ed7119e27977e96ad2832c0efd6cc203b7c636c227e8ab1e37`。
- GREEN: maintenance-ignored-builds -> PASS，构建后按 pnpm 提示临时加入 `onlyBuiltDependencies=[esbuild, vue-demi]` 并执行 `pnpm rebuild --pending`，随后恢复 package.json；`pnpm ignored-builds` 输出 `None`。
- GREEN: maintenance-worktree-clean-after-build -> PASS，已清理由维护测试生成的 `runtime/runtime-control-original-governance-parity-test` JSON，维护 release worktree `git status --porcelain` 为空。
- GREEN: migration-policy-gate -> PASS，构建前 required SQL 元数据和依赖策略通过，输出保存到 `doc/tasks/20260811-head-test-only-release/migration-policy-gate.json`。
- GREEN: runtime-control-isolation -> PASS，隔离运行控制台启动于 `http://127.0.0.1:48182`，PID=`60224`，health=`UP`；进程命令行指向 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a\m` jar。
- GREEN: pre-build-release-clean-status -> PASS，维护 release worktree 与 app release worktree 在启动运行控制台后仍为 clean。
- RED: build-release-r1 -> FAIL，operation=`op-2026-08-10T162932888425700Z-1d7e964a-3a61-4fc3-bf49-ca3154c2d8ff`；后端 Maven build SUCCESS，但主程序前端 `pnpm build:test` 因 `node_modules` 缺失、`cross-env` 不存在而失败；未生成可发布 manifest，不得继续 publish-test。

### I005 主程序 release worktree 未安装前端依赖导致 build-release-r1 失败

- 现象：`build-release-r1` 日志显示 `Local package.json exists, but node_modules missing`，且 `'cross-env' 不是内部或外部命令`。
- 阶段：build-release 前端 build:test。
- 影响：r1 发布包无可确认 manifest、版本号或变更说明；按门禁判废，禁止 publish-test。
- 原因判断：新建 clean app release worktree 后未先执行前端 `pnpm install --frozen-lockfile`，构建脚本不会自动恢复前端依赖。
- 处理动作：冻结 r1 operation/log 证据；在同一冻结 HEAD app release worktree 内补齐前端依赖并复核 clean；使用新的 `release-20260811-intmain-head-test-r260811a-r2` 重建。
- 结果：待 r2 构建。
- 是否可前置检查：是。
- 是否可自动化：是，build-release preview 前检查 `IntRuoyiFronted/node_modules/.bin/cross-env.cmd`、`vite.cmd`、`vue-tsc`，缺失即先 install。
- 下次如何避免：所有新 app release worktree 在 build-release 前固定执行前端依赖恢复和 ignored-builds gate。

### I004 空端口查询脚本对空 PID 调用 Get-Process 报错

- 现象：检查 48181/48182/48183 端口空闲时，`Get-NetTCPConnection` 无结果，但后续 `Get-Process -Id $null` 报参数错误。
- 阶段：运行控制台启动前端口门禁。
- 影响：承载脚本退出码为 1，但没有发现端口占用；不能把该错误误判为端口被占。
- 原因判断：脚本没有处理空 PID 集合。
- 处理动作：改用空结果判定端口无监听，启动后再用 PID=60224 和 48182 listener 复核。
- 结果：运行控制台在 48182 健康启动。
- 是否可前置检查：是。
- 是否可自动化：是，端口检查脚本对空集合直接输出 listener=0。
- 下次如何避免：PowerShell 端口/PID 查询要先判断结果数量，不对 null 调用 Get-Process。

### I003 pnpm ignored build scripts 需要临时 allowlist 后恢复源码

- 现象：`scripts\build.ps1` 首次 pnpm install 后提示 esbuild 和 vue-demi 的 build scripts 被 ignored。
- 阶段：维护控制台构建后依赖门禁。
- 影响：若不处理，依赖原生产物状态不可证明完整；若保留 allowlist 改动，会污染 clean release worktree。
- 原因判断：冻结提交未在 package.json 中声明 pnpm v10 所需的 onlyBuiltDependencies。
- 处理动作：在 release worktree 内临时加入 `pnpm.onlyBuiltDependencies`，执行 `pnpm rebuild --pending`，确认 ignored-builds=None 后恢复 package.json。
- 结果：依赖构建脚本清零，package.json 恢复，worktree clean。
- 是否可前置检查：是。
- 是否可自动化：是，在维护构建脚本中固化 ignored-builds gate，并在 finally 恢复/复核 Git clean。
- 下次如何避免：将依赖构建批准清单纳入正式构建前检查，避免每轮手工临时变更。

### I002 主程序 worktree 创建期间过早复核产生 46081 条假删除

- 现象：`git worktree add` 仍在更新文件时，一次并发 `git status` 看到 app release worktree `locked initializing` 并输出 46081 条删除。
- 阶段：Git / worktree 复核。
- 影响：该次复核不能作为构建来源证据，若误采信会错误阻塞或污染任务记录。
- 原因判断：长 checkout 期间启动了后续 verify 命令，读取到未完成工作树。
- 处理动作：等待 worktree add 进程退出码 0 后重新执行 status 与 registry 复核。
- 结果：以重新复核结果为准，只有 HEAD 匹配且 dirtyCount=0 才进入构建。
- 是否可前置检查：是。
- 是否可自动化：是，worktree add 返回 session_id 时必须 wait 到 exit_code 后再跑 status。
- 下次如何避免：禁止在 worktree registry 显示 `locked initializing` 时进行构建或 clean 判定。

## App Frontend Dependency Recovery

- GREEN: app-frontend-install -> PASS，冻结 app release worktree 执行 `pnpm install --frozen-lockfile`，耗时约 39m25.8s；`cross-env.cmd`、`vite.cmd`、`vue-tsc.cmd` 均存在；worktree HEAD 仍为 `5699b804576851ea8cdebf36045d381f044fb5e8`。
- GREEN: app-frontend-ignored-builds -> PASS，临时加入 `pnpm.onlyBuiltDependencies=[@parcel/watcher,@swc/core,core-js,core-js-pure,es5-ext,esbuild,vue-demi]` 后执行 `pnpm rebuild --pending`，`pnpm ignored-builds` 输出 `None`；随后恢复 `package.json` 到 HEAD，app release worktree `git status --porcelain` 为空。
- GREEN: app-pre-r2-clean-status -> PASS，维护 release worktree 与 app release worktree 均 clean；r2 构建仍只基于发布开始时冻结 HEAD。
- GREEN: build-release-r2 -> PASS，operation=`op-2026-08-10T180157565021500Z-7a75427f-088a-4ec9-8fb7-74ac81973a84`，status=`SUCCESS`；后端 Maven build SUCCESS，前端 `pnpm build:test` SUCCESS，Docker backend/frontend image build、image tar export、NAS upload 完成。
- GREEN: manifest-r2-validation -> PASS，官方校验器 `ops\\release\\validate-release-manifest.ps1 -PackagePath <package>` 返回 `MANIFEST_VALIDATION_PASSED`，输出保存到 `manifest-r2-validation.json`。
- GREEN: release-info-r2 -> PASS，前端 `dist-intruoyi-test\\release-info.json` 的 releaseTag/packageId 为 `release-20260811-intmain-head-test-r260811a-r2`，sourceRepos backend/frontend commit 均为冻结主程序 HEAD `5699b804576851ea8cdebf36045d381f044fb5e8`，dirty=false；变更说明包含发布包和组件范围 `intruoyi`。

### I007 manifest 校验器参数名误用

- 现象：首次运行官方校验器时使用 `-ManifestPath`，脚本报 `A parameter cannot be found that matches parameter name ManifestPath`。
- 阶段：r2 发布包 manifest 校验。
- 影响：该次校验无效，不能作为发布前通过证据；若误判会绕过官方 manifest gate。
- 原因判断：校验脚本参数是 `-PackagePath`，不是按 manifest 文件路径入参。
- 处理动作：读取脚本参数后使用 `-PackagePath E:\\Int\\CacheData\\IntRuoyi\\publish-int-ruoyi\\release-20260811-intmain-head-test-r260811a-r2 -OutputPath manifest-r2-validation.json` 重新执行。
- 结果：官方校验器返回 `MANIFEST_VALIDATION_PASSED`。
- 是否可前置检查：是。
- 是否可自动化：是，在发布任务脚本中封装固定校验命令，不手写参数。
- 下次如何避免：运行发布脚本前先读 help/param block，或复用历史任务的 `-PackagePath` 命令模板。

### I006 app 前端依赖恢复耗时且 ignored build scripts 覆盖更多包

- 现象：`pnpm install --frozen-lockfile` 在 clean app release worktree 中耗时约 39m25.8s；安装完成后仍报告 `@parcel/watcher`、`@swc/core`、`core-js`、`core-js-pure`、`es5-ext`、`esbuild`、`vue-demi` 的 build scripts 被 ignored。
- 阶段：build-release r2 前置依赖门禁。
- 影响：若不处理，前端原生依赖构建状态不可证明完整，不能继续生成可发布 manifest。
- 原因判断：pnpm v10 在新 worktree 中默认阻止依赖 build scripts，且 app 前端依赖范围比维护控制台更大。
- 处理动作：在冻结 release worktree 内临时写入 onlyBuiltDependencies，执行 `pnpm rebuild --pending`，确认 `pnpm ignored-builds=None` 后恢复 `package.json` 并复核 git clean。
- 结果：依赖门禁通过，未保留源码改动，允许进入 r2 构建。
- 是否可前置检查：是。
- 是否可自动化：是，build-release preview 前固定检查 app 前端 `node_modules/.bin/cross-env.cmd`、`vite.cmd`、`vue-tsc.cmd` 和 `pnpm ignored-builds`。
- 下次如何避免：新 app release worktree 创建后先执行依赖恢复和 ignored-builds gate，再提交 build-release operation。

## Publish Test

- GREEN: publish-test-r2-preview -> PASS，预览 action=`publish-test`、Environment=`test`、ServerHost=`172.30.30.58`、RemoteAppDir=`/opt/intruoyi/runtime`，releaseTag=`release-20260811-intmain-head-test-r260811a-r2`；未包含 `mark-tested`、`promote-prod`、`promote-backup` 执行动作。
- GREEN: publish-test-r2 -> PASS，operation=`op-2026-08-10T184419479334Z-b3dd4c79-c0f1-4a8c-bc32-5a930700a511`，status=`SUCCESS`，日志尾部显示 `Publish completed for test`。
- GREEN: publish-test-log-sanitized -> PASS，已生成脱敏日志 `publish-test-r2-operation-log-sanitized.log`，secret scan 对原始 MySQL 密码、默认登录密码、password/token/secret 形态命中 0。

## Runtime Verification

- GREEN: remote-env-image-tag -> PASS，测试服 `/opt/intruoyi/runtime/.env` 的 `IMAGE_TAG=release-20260811-intmain-head-test-r260811a-r2`。
- GREEN: remote-container-images -> PASS，`intruoyi-backend:release-20260811-intmain-head-test-r260811a-r2` 与 `intruoyi-frontend:release-20260811-intmain-head-test-r260811a-r2` 均 running。
- GREEN: remote-health-http -> PASS，backend `/actuator/health` 返回 `{"status":"UP"}`，frontend HTTP 200，PDF worker HTTP 200 application/javascript。
- GREEN: remote-release-info -> PASS，测试服 `/release-info.json` 的 releaseTag/packageId、sourceRepos commit=`5699b804576851ea8cdebf36045d381f044fb5e8`、dirty=false、变更说明 `发布包：release-20260811-intmain-head-test-r260811a-r2` / `组件范围：intruoyi` 均匹配最终发布包。
- GREEN: remote-release-lock-migration -> PASS，`infra_release_operation_lock` test 行为 `test-release-20260811-intmain-head-test-r260811a-r2 APPLIED`；目标 releaseTag migration count 为 `APPLIED=5`、`SKIPPED_ALREADY_APPLIED=419`，无 FAILED/RUNNING。
- GREEN: playwright-test-frontend -> PASS，Playwright CLI 打开 `http://172.30.30.58:8081/` 跳转登录页，页面标题 `瑛泰管理系统 - 登录`，可见 `瑛泰数字化平台` 和 `登录`；同一页面 fetch `/release-info.json` 断言通过。
- GREEN: playwright-runtime-console -> PASS，Playwright CLI 打开 `http://127.0.0.1:48182/`，运行控制台可见 publish-test SUCCESS operation、软件版本 `2026.06.0`、测试服 releaseTag、发布包和组件范围变更说明。

## Additional Issues

### I008 PowerShell 到 SSH/MySQL 的标准输入与变量展开导致首次 DB 查询失败

- 现象：首次用 PowerShell here-string 管道到 `ssh ... bash -s` 查询 release lock/migration 时，远端出现 `set: 未找到命令`、MySQL 访问拒绝和空结果。
- 阶段：测试服运行态 DB 验收。
- 影响：该次 DB 验收无效，不能作为 release lock 或 migration 证据；不影响已完成的 publish-test operation。
- 原因判断：PowerShell 发送文本带 BOM/编码污染，且双引号 here-string 让 `$MYSQL_ROOT_PASSWORD` 在本地被展开为空。
- 处理动作：改用不暴露密码值的远端短命令，远端容器内通过 `MYSQL_PWD="$MYSQL_ROOT_PASSWORD"` 执行 MySQL 查询，并使用 `CHAR(...)` 避免多层引号污染。
- 结果：release lock=`APPLIED`，migration counts=`APPLIED 5 / SKIPPED_ALREADY_APPLIED 419`。
- 是否可前置检查：是。
- 是否可自动化：是，发布后 DB 验收统一封装为固定 SSH 命令模板或 UTF-8 LF stdin 脚本，禁止临场拼四层引号。
- 下次如何避免：先跑 `MYSQL_ROOT_PASSWORD_PRESENT` 探针且不打印值；命令输出只记录状态字段和计数。

### I009 Playwright 依赖上下文与浏览器缓存缺失导致页面验收重试

- 现象：`npx --package playwright node <script>` 运行外部脚本时 `Cannot find module 'playwright'`；随后 Playwright screenshot 报 `chromium_headless_shell-1234` 不存在。
- 阶段：页面验收。
- 影响：首次页面断言脚本无效，截图验收无法启动；不影响测试服运行态。
- 原因判断：npx package 上下文未进入外部脚本模块解析路径；本机 Playwright 浏览器缓存缺少当前版本 headless shell。
- 处理动作：改用 Playwright CLI 的 `screenshot`、`open`、`eval`、`snapshot` 会话命令；安装缺失 Chromium/headless shell 后重跑。
- 结果：测试服前端截图、运行控制台截图和 DOM/release-info 断言均通过。
- 是否可前置检查：是。
- 是否可自动化：是，页面验收前固定检查 `npx playwright --version`、browser executable、CLI `open/eval` 能力；优先使用已有稳定 Chrome channel，避免发布验收中临时下载。
- 下次如何避免：不要用 `npx --package` 运行 repo 外脚本；需要脚本时绑定已有前端依赖根或使用 Playwright CLI 会话。

### I010 Playwright snapshot 暴露登录页默认密码文本

- 现象：Playwright CLI `snapshot` 输出登录表单时包含默认密码文本。
- 阶段：页面验收证据采集。
- 影响：snapshot 原始文件不能进入任务记录或提交；否则违反凭据脱敏规则。
- 原因判断：登录页密码框默认值会被可访问性 snapshot 作为文本输出。
- 处理动作：删除本轮 `.playwright-cli/page-2026-08-10T19-35-*.yml` snapshot 文件，仅保留不含敏感文本的截图和手工脱敏结构化证据；后续任务日志不复制该 snapshot 原文。
- 结果：`.playwright-cli` 本轮 snapshot 文件已清空，任务目录 secret scan 命中 0。
- 是否可前置检查：是。
- 是否可自动化：是，发布页面验收禁用或立即清理登录页 snapshot；证据只记录字段名、布尔断言、截图路径和 releaseTag。
- 下次如何避免：打开登录页后不要保存 snapshot 原文；如必须 snapshot，先确认页面无默认凭据或立即执行脱敏删除。

## Experience Consolidation

- GREEN: experience-consolidation -> PASS，已按 project-experience-consolidation 技能将本轮增量归并到既有文档：`docs/release-build-preflight-lessons.md`、`docs/test-release-preflight.md`、`docs/powershell-preflight-lessons.md` 和 `docs/experience-index.md`；未新建长期经验文档。

## Closeout Preparation

- GREEN: ready-for-closeout -> PASS，`task.md` 已置为 `ready_for_closeout`；下一步执行 task-closeout-cleanup preview/apply，并清理本轮 release worktree、state dir 和临时 Playwright 输出。

## Closeout Completion

- GREEN: task-closeout-preview -> PASS，`task-closeout-cleanup --mode preview` 仅保留 `task.md`、`execution-log.md`、`verification-report.md`，仓库内待删项均为本任务一次性证据，blocked/warnings 均为 none。
- GREEN: task-closeout-apply -> PASS，`task-closeout-cleanup --mode apply` 已删除仓库内一次性证据和 `output/playwright/20260811-head-test-only-release`，仅保留三份正式任务记录。
- GREEN: external-worktree-cleanup -> PASS，`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a\m`、`D:\IntRuoyiWorktree\r260811a-release-app`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a-state` 均不存在；维护仓与主程序仓 `git worktree list --porcelain` 均无 `r260811a`。
- GREEN: runtime-console-cleanup -> PASS，本轮隔离运行控制台端口 `48182` 无监听。
- GREEN: post-cleanup-test-server-check -> PASS，清理后测试服仍为 `IMAGE_TAG=release-20260811-intmain-head-test-r260811a-r2`，backend/frontend 镜像 tag 匹配且 running，backend health=`UP`，frontend HTTP 200；OpenSSH `IO is still pending on closed socket` 仅作为 carrier warning 记录。
- GREEN: task-completed -> PASS，`task.md` 和 `verification-report.md` 已更新为 `completed`。

### I011 closeout 阶段多次误触 wait 工具导致无效轮询

- 现象：closeout 记录更新阶段多次对不存在的 exec cell id 调用 wait，返回 `exec cell ... not found`。
- 阶段：任务收尾记录与提交前。
- 影响：没有修改文件、服务器或 worktree 状态，但造成重复无效操作和耗时。
- 原因判断：工具焦点停留在 wait 命名空间，未立即切回命令执行器。
- 处理动作：停止依赖 wait 句柄，改用命令执行器完成最终 patch、验证和提交。
- 结果：本轮 release worktree/state 清理和测试服运行态复核已完成，任务记录已补齐。
- 是否可前置检查：是。
- 是否可自动化：是，closeout 命令应合并为单个可审计脚本，只有在 exec 返回真实 `cell_id` 时才允许 wait。
- 下次如何避免：无真实运行中 cell id 时禁止调用 wait；收尾阶段优先执行短命令并立即记录结果。
