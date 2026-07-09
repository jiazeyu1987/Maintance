# 执行日志

## 2026-07-09T09:20:00+08:00

- USER: 仅基于当前分支最新已提交代码完成一次测试服发布，未提交改动不得进入构建产物；发布成功后记录问题并沉淀前置经验。
- BDD: 当前 HEAD 测试服发布 -> Given 三仓主工作区存在未提交改动且目标 HEAD 已固定 / When 从目标 HEAD 创建干净临时 worktree 构建并发布到测试服 / Then 发布包 manifest 必须证明 sourceRepos 为目标提交且 dirty=false，测试服真实运行态必须运行同一 releaseTag。
- BDD: 发布信息可追溯 -> Given build-release 生成发布包 / When 检查 manifest、版本号和变更说明 / Then 版本号和变更说明必须能对应本次构建提交，否则阻塞发布。
- GREEN: docs-preflight-read -> PASS，已读取发布技能、构建/发布/PowerShell/worktree 前置引用、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`、`docs\experience-index.md` 与 `docs\release-build-preflight-lessons.md`。
- GREEN: git-baseline -> PASS，维护仓 `int_main` HEAD=`91700a6b65190e1d6a651cf9a16a1f96207ed2a5`，后端 `int_main` HEAD=`549fa9199a7b8e8663d62aaee3d1c47d76e7a83a`，前端 `int_main` HEAD=`d2022624d7c362400f0f8a976da59b828a06881f`。
- ISSUE: 三仓主工作区均存在未提交改动；阶段=构建前 Git 状态；影响=不得直接构建，避免脏内容进入发布包；原因判断=当前系统仍在并行开发；处理动作=创建本轮短路径干净临时 worktree 并固定到目标 HEAD；结果=待执行；是否可前置检查=是；是否可自动化=是；下次避免=发布任务开始自动输出三仓 branch/HEAD/status 并强制 release worktree。
- GREEN: experience-preflight -> PASS，本次属于发布/构建/worktree/PowerShell 高风险任务；已摘录门禁到 `task.md`，后续真实发布前按门禁执行。

## 2026-07-09T09:23:30+08:00

- GREEN: release-worktree-create -> PASS，短路径临时发布 worktree 已创建并验证 clean：维护仓 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709h\m` HEAD=`91700a6b65190e1d6a651cf9a16a1f96207ed2a5`；后端 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709h\b` HEAD=`549fa9199a7b8e8663d62aaee3d1c47d76e7a83a`；前端 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709h\f` HEAD=`d2022624d7c362400f0f8a976da59b828a06881f`；三者 `git status --porcelain` 均为空。
- BUILD_INPUT: 构建目录固定为维护仓 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709h\m`，业务后端输入固定为 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709h\b`，业务前端输入固定为 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709h\f`。

## 2026-07-09T09:28:30+08:00

- RED: maintenance-runtime-build -> FAIL，在干净维护 worktree 执行 `pnpm --dir D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709h\m\frontend approve-builds --all` 返回 `There are no packages awaiting approval`，但随后的 `pnpm install --frozen-lockfile` 与 `scripts\build.ps1` 均因 `ERR_PNPM_IGNORED_BUILDS` 阻断 `esbuild@0.27.7`、`vue-demi@0.14.10`，最终 `frontend\dist\index.html` 缺失，未生成可用维护控制台 jar。
- ISSUE: pnpm build scripts approval 空结果仍阻断 install；阶段=维护控制台构建；影响=不能构建维护控制台，不能继续发布；原因判断=pnpm 11 审批状态/`pnpm-workspace.yaml` 配置不完整；处理动作=冻结 stdout/stderr，调查是否可用用户级或工具链级配置满足审批且保持 release worktree 源码 clean；结果=调查中；是否可前置检查=是；是否可自动化=是；下次避免=构建前同时检查 `pnpm approve-builds --all`、`pnpm install --frozen-lockfile` 和 `pnpm config list`，发现占位审批值立即 fail fast。
- ROOT_CAUSE: `pnpm` 命令解析到 Codex runtime bundled pnpm `11.7.0`，而维护前端 `package.json` 声明 `packageManager=pnpm@10.25.0`；pnpm 11 在临时 worktree 生成未跟踪 `frontend\pnpm-workspace.yaml`，其中 `allowBuilds` 是占位字符串，导致 install fail fast。
- GREEN: maintenance-runtime-build -> PASS，删除 pnpm 11 生成的未跟踪 `frontend\pnpm-workspace.yaml` 后，通过 `corepack pnpm@10.25.0` 执行维护控制台构建；`vue-tsc --noEmit`、`vite build`、Maven test/package 通过，Maven 测试 `26` 项通过，生成 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709h\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`，`frontend\dist\index.html` 存在。
- ISSUE: 初次 pnpm 10 install 输出 `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`；阶段=维护控制台依赖恢复；影响=install preflight 不干净但后续 `scripts\build.ps1` 完成 typecheck/build/test/package；原因判断=pnpm 11 已生成 node_modules 后，pnpm 10 在无 TTY 环境拒绝删除重建；处理动作=继续以完整 `scripts\build.ps1` 作为最终构建证据并记录该异常；结果=构建通过；是否可前置检查=是；是否可自动化=是；下次避免=首次构建前固定 pnpm 版本，避免 pnpm 11 先污染 node_modules。
- ISSUE: PowerShell here-doc 语法误用导致首次运行控制台切换命令解析失败；阶段=运行控制台配置切换；影响=首次命令未改配置、未启动；原因判断=PowerShell 5.1 不支持 `python - <<'PY'` 形态；处理动作=改用 .NET UTF-8 API 原生读写 YAML 后重试；结果=重试成功；是否可前置检查=是；是否可自动化=是；下次避免=Windows PowerShell 中嵌入脚本使用 here-string 管道或原生 API，不使用 Bash heredoc。
- GREEN: runtime-control-config-switch -> PASS，干净维护控制台配置 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709h\m\config\runtime-control.local.yaml` 已指向 `repo-root=D:/ProjectPackage/Int/IntRuoyiWorktrees/r260709h/b`、`frontend-root=D:/ProjectPackage/Int/IntRuoyiWorktrees/r260709h/f`、`ops-root=D:/ProjectPackage/Int/IntRuoyiWorktrees/r260709h/m/ops`、`state-dir=D:/ProjectPackage/Int/IntRuoyiWorktrees/r260709h/m/runtime/runtime-control`。
- GREEN: runtime-control-start -> PASS，旧 48181 Java 进程已停止，干净维护控制台进程 `pid=57124` 使用 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709h\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 启动，`http://127.0.0.1:48181/actuator/health` 返回 HTTP 200 / `{"status":"UP"}`。
- NOTE: 干净维护 worktree 当前仅出现未跟踪 `runtime/`，来源为运行控制台 state-dir；不作为构建源码输入，后续发布包 manifest 仍必须以 `sourceRepos.dirty=false` 判定业务后端/前端输入。

## 2026-07-09T09:24:30+08:00

- RED: build-release-preview-local-gate -> FAIL，本地校验脚本误把 build-release 预览中的 `-BackupServerHost 172.30.30.59` 判定为备份服动作，并只在 arguments 中查找 `code-only`；实际预览的 `parameters.publishScope=code-only`，`BackupServerHost` 是 build-release 生成多环境包 URL/存储检查参数，不代表执行备份服部署。
- ISSUE: build-release 预览本地门禁误判；阶段=发布包构建预览；影响=首次预览被本地检查阻断，未执行构建；原因判断=门禁规则未区分 build-release 构建参数与 deploy-release 部署动作；处理动作=修正预览门禁：`publishScope` 以 parameters 为准，备份服阻断只检查 deploy/promote 动作，不阻断 build-release 所需 `BackupServerHost`；结果=待重试；是否可前置检查=是；是否可自动化=是；下次避免=预览校验按 action 分层，build-release 与 publish-test 分别维护允许参数清单。
- RED: build-release -> FAIL，releaseTag=`release-20260709-head-test-v1`，operationId=`op-2026-07-09T011857958133700Z-e405e8f5-a462-42ad-9f6d-43f44fa845cd`，发布脚本失败于 `Invalid release migration metadata segment in ...\sql\mysql\20260709_mes_route_process_master_alignment.sql: intruoyi_align_mes_route_process_to_process_master_by_code`。
- ISSUE: 后端 SQL release metadata 非 key-value 形态；阶段=build-release / manifest 前 required SQL 元数据收集；影响=无法生成可确认来源的发布包，必须废弃 v1 releaseTag；原因判断=SQL 首行使用说明性过程名而非 `allowedEnvironments/dependsOn/type/riskLevel` 发布契约；处理动作=在后端主仓按严格 TDD 修复 metadata 并补测试；结果=后端已提交 `87cb9f9996f1d5cf5e2c05ee57586e9bd2a403d5`；是否可前置检查=是；是否可自动化=是；下次避免=build-release 前先运行发布脚本同款 metadata 解析或全量 release migration policy gate。
- GREEN: backend-release-metadata-fix -> PASS，后端主仓提交 `87cb9f9996f1d5cf5e2c05ee57586e9bd2a403d5`，`python -X utf8 -m pytest script/tests/test_mes_route_process_alignment_sql.py -q` 6 tests 通过，单文件与全量 `sql/mysql` release migration policy gate 通过。
- GREEN: backend-release-worktree-update -> PASS，后端临时发布 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260709h\b` 已从原始 HEAD `549fa9199a7b8e8663d62aaee3d1c47d76e7a83a` 更新到已提交修复 HEAD `87cb9f9996f1d5cf5e2c05ee57586e9bd2a403d5`，更新后 `git status --porcelain` 为空。
- RED: build-release -> FAIL，releaseTag=`release-20260709-head-test-v2`，operationId=`op-2026-07-09T012312011537500Z-11ba10f7-568e-4410-8fe9-dd862cf6b3e9`；后端/前端镜像与本地 package manifest 已生成，但 operation 最终失败于 `[FAIL] Missing -SmartReleaseBaselineManifestPath; Smart Release report-only requires explicit local input files.`。
- ISSUE: Smart Release report-only 参数缺失；阶段=build-release / manifest 生成后报告阶段；影响=operation 非 SUCCESS，v2 releaseTag 必须判废，不得继续 publish-test；原因判断=本次请求只要求测试服发布与真实运行态验证，运行控制台开启了 `enableSmartReleaseReport=true` 但未提供 baseline/candidate 显式输入文件；处理动作=记录失败并使用新 releaseTag 重建，关闭 Smart Release report-only；结果=待重建；是否可前置检查=是；是否可自动化=是；下次避免=build-release 预览若启用 `-EnableSmartReleaseReport`，必须同时校验 baseline/candidate manifest 参数，否则 fail fast 或关闭该可选报告。
- GREEN: build-release -> PASS，releaseTag=`release-20260709-head-test-v3`，operationId=`op-2026-07-09T013606785826300Z-45bc8231-d958-4e92-b0a9-00bf09c6010c`，发布包已构建并上传 NAS `Backup/ReleasePackage/release-20260709-head-test-v3`。
- GREEN: manifest-validation -> PASS，`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260709-head-test-v3\manifest.json` 存在；`publishScope=code-only`；backend commit=`87cb9f9996f1d5cf5e2c05ee57586e9bd2a403d5` dirty=false；frontend commit=`d2022624d7c362400f0f8a976da59b828a06881f` dirty=false；`release-manifest.json` tag 匹配；`intruoyi-images_release-20260709-head-test-v3.tar` 存在；未包含 `database/mysql/minio/files` 数据目录。
- GREEN: release-notes-validation -> PASS，manifest `changeSet.summary=Release package release-20260709-head-test-v3`，`changeSet.items=发布包：release-20260709-head-test-v3 | 组件范围：intruoyi`，与本次 releaseTag / 组件范围一致。
- ISSUE: 运行控制台 `release-status` 查询超时；阶段=构建后候选包列表读取；影响=不影响本地 manifest 直接校验，但会影响后续运行控制台版本信息展示验证；原因判断=候选包扫描或响应耗时超过 20 秒；处理动作=先以发布包根目录 manifest 作为构建来源校验，部署后再用更长超时复核运行控制台展示；结果=待复核；是否可前置检查=是；是否可自动化=是；下次避免=release-status 校验使用合理超时并输出扫描耗时。

## 阶段记录 - publish-test 首次传输失败后远端预检
- 当前进度：release-20260709-head-test-v3 构建包已成功生成并通过 manifest/sourceRepos/code-only 检查；首次 publish-test 在大镜像 tar scp 阶段失败。
- 阻塞点：需确认测试服 SSH、磁盘、目标目录和残留部分文件状态，再决定是否按同一 releaseTag 重试测试服发布。
- 下一步动作：执行远端只读检查；若预检通过，清理或覆盖同一路径的残留传输文件并重试 publish-test。
### 问题 - publish-test 大镜像 tar 传输中断
- 现象：首次 publish-test 在 scp intruoyi-images_release-20260709-head-test-v3.tar 时出现 Connection reset / Broken pipe，远端残留 tar 大小 2121793536 字节，本地 tar 大小 2454713856 字节。
- 阶段：测试服发布 / 镜像包传输。
- 影响：测试服未完成加载镜像与启动验证，不得判定发布成功。
- 原因判断：SSH/scp 传输中断导致远端文件不完整；远端磁盘剩余约 1.4T，不是磁盘空间不足。
- 处理动作：仅删除 /var/lib/docker/intruoyi-releases/release-20260709-head-test-v3/intruoyi-images_release-20260709-head-test-v3.tar 这个不完整传输文件，然后按同一 releaseTag 重试 publish-test。
- 结果：等待重试结果。
- 是否可前置检查：是，发布前检查远端磁盘、目标目录残留 tar 与本地 tar 大小。
- 是否可自动化：是，传输后自动比对 tar 字节数，失败即 fail fast 并提示清理。
- 下次如何避免：大文件传输阶段增加大小校验与可重试传输策略；重试前必须限定清理路径为当前 releaseTag 下的不完整文件。

### 问题 - PowerShell 远端清理命令引用错误
- 现象：首次清理残留 tar 的命令在 PowerShell 解析阶段报 Unexpected token，未执行远端删除与发布重试。
- 阶段：测试服发布 / 失败恢复操作。
- 影响：发布重试未启动，但未改变远端文件。
- 原因判断：把 Bash case 命令嵌入 PowerShell 双引号字符串时转义不足。
- 处理动作：改用 PowerShell 单引号 here-string 保存远端 Shell 脚本，再传给 ssh 执行。
- 结果：等待本次重试结果。
- 是否可前置检查：是，对复杂远端 Shell 片段统一使用 here-string。
- 是否可自动化：是，封装受保护路径删除函数。
- 下次如何避免：PowerShell 中不直接拼接复杂 Bash 控制流，改用 here-string 或脚本文件。

## 阶段记录 - publish-test 重试前清理
- 当前进度：确认远端残留 tar 不完整，测试服 .env IMAGE_TAG 已写入 release-20260709-head-test-v3，但发布流程未成功完成。
- 下一步动作：删除同一 releaseTag 目录下的不完整 tar 并重试 publish-test，仅测试服。
### 问题 - publish-test 重试 API 返回 404
- 现象：远端不完整 tar 已删除，但调用本地维护控制台 `POST /api/release/execute` 返回 404。
- 阶段：测试服发布 / 本地维护控制台操作。
- 影响：publish-test 重试未启动，需要确认本地 48181 端口当前绑定服务、健康状态和可用 API 路由。
- 原因判断：可能是本地维护控制台进程已变化、端口绑定到错误服务、API 路由上下文变化或前端静态服务接管请求。
- 处理动作：检查 48181 监听进程、健康接口、根路径响应、维护控制台日志和 release 相关路由线索。
- 结果：等待检查结果。
- 是否可前置检查：是，发布操作前先检查 `/actuator/health` 和 release API 可达性。
- 是否可自动化：是，在发布按钮/脚本前增加 API health + route smoke。
- 下次如何避免：维护控制台启动后先记录 PID、jar 路径和 health，再执行 release 操作。
### 问题 - 本地端口诊断脚本使用保留变量
- 现象：48181 端口诊断时使用 `$pid` 变量触发 `Cannot overwrite variable PID because it is read-only or constant`。
- 阶段：测试服发布 / 本地维护控制台排障。
- 影响：监听进程命令行未被正确识别，需重新诊断；未影响远端和发布包。
- 原因判断：PowerShell 变量名大小写不敏感，`$PID` 是内置只读变量。
- 处理动作：改用 `$listenerPid` 重新检查监听进程，并从代码与 actuator mappings 查找 release 执行接口。
- 结果：等待检查结果。
- 是否可前置检查：是，脚本禁止使用 PowerShell 内置变量名。
- 是否可自动化：是，发布辅助脚本 lint 保留变量名。
- 下次如何避免：诊断脚本变量使用明确业务前缀，如 `$listenerProcessId`。
### 问题 - 维护控制台 API 路径误用
- 现象：本地维护控制台 48181 的根页面和 health 正常，但 `/api/release/execute` 返回 404。
- 阶段：测试服发布 / 本地维护控制台操作。
- 影响：publish-test 重试未启动，需要改用后端真实 Controller 路径。
- 原因判断：此前使用了错误的简化 API 路径；前端代码显示实际请求绑定在 runtime-control 模块，后端直接暴露 `/admin-api/infra/runtime-control/...`。
- 处理动作：读取 Controller 与前端 API 定义，确认精确 execute endpoint 后重试。
- 结果：等待路径确认与重试结果。
- 是否可前置检查：是，发布操作前用 Controller 映射或前端 API 文件确认路径。
- 是否可自动化：是，维护控制台启动后执行 release API route smoke。
- 下次如何避免：不要凭历史路径调用发布 API，统一从源码或 OpenAPI/映射中获取。
## 阶段记录 - publish-test 重试接口修正
- 当前进度：已确认维护控制台真实执行接口为 `/admin-api/infra/runtime-control/actions`，此前 `/api/release/execute` 是错误路径。
- 下一步动作：带上必填 reason 字段执行预览；预览确认仅 `deploy-release test` 后，再执行同一 releaseTag 的 publish-test。
### 问题 - publish-test 预览校验过度依赖文本匹配
- 现象：预览返回 code=0，且 arguments 中明确包含 `-Mode deploy-release` 与 `-Environment test`，但本地 guard 查找连续文本 `Environment test` 导致误判失败。
- 阶段：测试服发布 / 执行前安全校验。
- 影响：publish-test 重试未启动；未影响发布包和远端运行态。
- 原因判断：对结构化 JSON 使用了脆弱的字符串匹配，没有按 arguments 数组解析参数键值。
- 处理动作：改为解析 `data.environment`、`data.scriptPath` 与 `data.arguments` 参数对，确认仅 deploy-release + test + 指定 releaseTag 后执行。
- 结果：等待重试执行结果。
- 是否可前置检查：是，所有发布预览校验必须按结构化字段解析。
- 是否可自动化：是，把 release preview guard 封装为参数数组解析器。
- 下次如何避免：禁止用连续文本匹配验证发布预览，必须检查参数数组中的相邻键值。

## 阶段记录 - publish-test 结构化预览校验后重试
- 当前进度：确认正确 API 与必填 reason；修正预览 guard。
- 下一步动作：重新预览并执行 release-20260709-head-test-v3 的 test-only publish-test。
## 阶段记录 - publish-test 运行中
- 当前进度：已提交修正后的 publish-test 操作 $opId，releaseTag=release-20260709-head-test-v3。
- 下一步动作：轮询本地 operation 状态；成功后执行测试服真实运行态验证，失败则记录阶段问题并阻塞。
### 问题 - publish-test 重试在 NAS 包下载到本地缓存阶段失败
- 现象：第二次 publish-test 操作 `op-2026-07-09T020308904687Z-63c7d2b2-9b70-46bd-931c-a102bac4ee2f` 未进入远端传输阶段，在 `Copy-Item` 将 NAS 发布包复制到本地缓存时失败。
- 阶段：测试服发布 / 发布包下载与本地缓存刷新。
- 影响：测试服未重新部署，仍不得判定发布成功。
- 原因判断：需确认本地缓存目录是否已有同名大文件占用、Copy-Item 是否试图覆盖正在使用的 tar、NAS 包是否可读以及脚本该阶段的复制策略。
- 处理动作：检查失败日志、脚本 2354 附近逻辑、本地缓存文件、远端残留 tar 和相关进程占用。
- 结果：等待检查结果。
- 是否可前置检查：是，重试前检查本地缓存目标文件是否存在、是否可覆盖、大小是否与 NAS 包一致。
- 是否可自动化：是，下载发布包前先清理或校验 releaseTag 专属本地缓存目录。
- 下次如何避免：发布脚本在 Copy-Item 前对目标 releaseTag 缓存目录做显式状态检查并输出可读错误。
## 阶段记录 - 本地缓存与 NAS 发布包预检
- 当前进度：publish-test 重试在 NAS -> 本地缓存复制阶段失败，且本地 releaseTag 缓存目录只残留 docker-compose.yml。
- 下一步动作：检查 E 盘空间、NAS 发布包目录与大 tar 可读性；确认是否为本地空间、NAS 连接或 Copy-Item 大文件复制问题。
### 问题 - NAS 大文件尾部读取检查脚本 Int32 溢出
- 现象：NAS tar 首部 1MB 可读，但尾部读取检查使用 `[Math]::Max(0,$fs.Length-1048576)` 时触发 Int32 溢出。
- 阶段：测试服发布 / NAS 发布包预检。
- 影响：未完成 NAS tar 尾部可读性验证；未修改发布包和远端运行态。
- 原因判断：PowerShell 调用 `[Math]::Max` 时把常量 `0` 推断为 Int32，无法处理 2.45GB 文件偏移。
- 处理动作：改用 Int64 常量 `[Int64]0` 重新做 NAS tar 首尾读取与本地缓存精确恢复。
- 结果：等待检查结果。
- 是否可前置检查：是，大文件脚本统一使用 Int64。
- 是否可自动化：是，发布预检脚本封装大文件 size/seek 校验。
- 下次如何避免：所有超过 2GB 的文件偏移、大小比较、seek 计算必须显式使用 Int64。
GREEN: nas-local-cache-restore release-20260709-head-test-v3 -> PASS, tarSize=2454713856.

## 阶段记录 - publish-test 再次重试前置条件恢复
- 当前进度：NAS 发布包 tar 首尾可读；本地 releaseTag 缓存目录已用 robocopy 恢复，tar 大小与 NAS 一致。
- 下一步动作：再次执行 release-20260709-head-test-v3 的 publish-test，仅测试服；完成后进行真实运行态验证。
### 问题 - publish-test 再次在大镜像 tar scp 阶段断开
- 现象：本地缓存恢复并通过大小校验后，publish-test 再次在 scp `intruoyi-images_release-20260709-head-test-v3.tar` 到测试服时失败，报 `Connection reset by 172.30.30.58 port 22` / `Broken pipe`。
- 阶段：测试服发布 / 大镜像包传输。
- 影响：镜像未完整上传，测试服未完成部署和真实运行态验证，不得判定发布成功。
- 原因判断：构建包与 NAS 可读性已排除；需进一步确认测试服 SSH/系统日志、远端残留文件大小、磁盘 inode/空间、sshd 配置和资源限制。
- 处理动作：执行测试服只读排障检查，不变更正式服/备份服，不跳过发布验证。
- 结果：等待检查结果。
- 是否可前置检查：是，发布前应检查 SSH 大文件传输稳定性与远端 release 目录残留文件大小。
- 是否可自动化：是，部署前先做可控大小传输探针或对目标 tar 做传输后字节数校验。
- 下次如何避免：大包传输失败后必须记录残留大小、服务端日志和明确原因；不得反复盲目重试。
## 阶段记录 - 定位发布脚本传输封装
- 当前进度：测试服 SSH 日志确认大 tar 传输会被 sshd 判定 `Timeout, client not responding` 后断开；远端空间、inode、内存和 NAS 包均正常。
- 下一步动作：检查发布脚本中 scp 封装与 tar 上传调用点，评估改为正式的分块/校验传输方案。
### 问题 - 发布脚本扫描辅助命令变量类型错误
- 现象：定位 scp 封装时，辅助脚本使用 `$matches` 变量触发 PowerShell 自动变量冲突，出现 `A hash table can only be added to another hash table`。
- 阶段：测试服发布 / 脚本排障。
- 影响：未输出完整上下文块；已通过 rg 得到关键位置，不影响发布包和远端运行态。
- 原因判断：`$Matches` 是 PowerShell 正则匹配自动变量，大小写不敏感；不应作为数组变量名。
- 处理动作：改用 `$lineIndexes` 重新读取 `New-ScpArgumentList`、`Copy-ToServer` 和镜像 tar 上传段。
- 结果：等待读取结果。
- 是否可前置检查：是，PowerShell 辅助脚本避免使用自动变量名。
- 是否可自动化：是，脚本 lint 检查 `$PID`、`$Matches` 等保留/自动变量。
- 下次如何避免：临时排障脚本变量统一使用明确前缀，例如 `$diagnosticLineIndexes`。
## 阶段记录 - 传输修正前测试与文件定位
- 当前进度：确认 `publish-int-ruoyi.ps1` 在镜像 tar 上传处调用通用 `Copy-ToServer`，走普通 scp，测试服反复在大文件传输中被 sshd 判定 client timeout。
- 下一步动作：查找现有发布脚本测试与 PowerShell 测试约定，先补 RED，再最小实现镜像 tar 分块传输与字节数校验。
### 问题 - 测试定位命令包含不存在目录
- 现象：扫描测试约定时把不存在的 `tests` 目录传给 `rg`，导致 `系统找不到指定的文件` 并提前退出。
- 阶段：测试服发布 / 发布脚本修复前定位。
- 影响：未完成测试文件定位；未修改代码、发布包和远端运行态。
- 原因判断：临时扫描命令没有先过滤存在路径。
- 处理动作：改为仅扫描已存在的 backend/src/test、scripts、ops 等目录。
- 结果：等待重新扫描结果。
- 是否可前置检查：是，脚本扫描前先 Test-Path 过滤。
- 是否可自动化：是，封装项目路径扫描函数。
- 下次如何避免：PowerShell 中传给 rg 的路径必须先解析并过滤存在目录。
## 阶段记录 - 准备维护仓发布传输修正
- 当前进度：测试服发布失败已定位为维护仓发布脚本对 2.45GB 镜像 tar 使用普通 scp，测试服 sshd 日志显示 `Timeout, client not responding`。
- 方案判断：这是发布工具正式缺陷；需要以 TDD 修改维护仓脚本，新增镜像 tar 专用分块上传与远端字节数校验，再用已提交工具版本继续同一 releaseTag 测试服发布。
- 下一步动作：检查维护仓主工作区脚本与临时 worktree 脚本是否一致、确认可改文件范围，然后补测试与实现。
## 阶段记录 - RED 测试准备
- 当前进度：确认主工作区 `ops/deploy/publish-int-ruoyi.ps1` 未修改；需要在维护仓正式修复镜像 tar 传输策略，再同步到临时发布 worktree。
- BDD: 镜像 tar 分块上传 -> Given 测试服 SSH 会在普通 scp 大文件传输中断开, When 发布脚本上传 `intruoyi-images_*.tar`, Then 发布脚本必须使用镜像 tar 专用分块上传并在远端按字节数校验后才执行 docker load。
- 下一步动作：新增脚本契约测试，先验证当前脚本缺少分块上传函数和镜像 tar 专用调用，形成 RED。
## 阶段记录 - 分块上传实现后验证
- 当前进度：已在维护仓主工作区增加 `Copy-LargeFileToServerInChunks`、远端字节数校验，并将镜像 tar 上传调用从普通 `Copy-ToServer` 切换为分块上传。
- 下一步动作：运行 Node 契约测试和 PowerShell 语法解析检查；如失败，按测试结果修正。
### 问题 - 分块上传契约测试匹配过窄
- 现象：实现已使用 `chunk-{0:D6}.part` 和 `$chunkIndex++` 生成递增分片，但测试强行匹配不存在的 `.part$chunkIndex` 字符串。
- 阶段：发布脚本 TDD / GREEN 验证。
- 影响：测试未通过，无法进入同步和发布重试。
- 原因判断：契约测试绑定了具体字符串拼接形态，而不是实际行为结构。
- 处理动作：改为检查分片命名模板、chunkIndex 自增、远端字节数校验和镜像 tar 专用调用。
- 结果：等待重新验证结果。
- 是否可前置检查：是，契约测试只约束必要行为，不约束无关实现细节。
- 是否可自动化：是，后续可改为 AST/片段级测试减少误报。
- 下次如何避免：测试先描述行为契约，再匹配最小必要结构。
GREEN: publish-image-tar-transfer-contract -> PASS, node --test scripts/tests/publish_image_tar_transfer_contract.test.mjs.
GREEN: publish-script-parse -> PASS, PowerShell Parser.ParseFile ops/deploy/publish-int-ruoyi.ps1.

## 阶段记录 - 维护仓发布工具修正提交前检查
- 当前进度：镜像 tar 分块上传实现与契约测试已通过，PowerShell 语法解析通过。
- 下一步动作：只暂存本任务直接相关的发布脚本、测试、任务文档和请求命令日志，提交维护仓；提交后同步临时发布 worktree 到新 HEAD。