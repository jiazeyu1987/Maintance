# Candidate Error Prevention Evidence

- Generated At: 2026-06-21T18:10:35
- Project Root: D:\ProjectPackage\Int\IntRuoyiMaintance
- Source Files Scanned: 4
- Files With Matches: 4
- Context Lines: 1
- Keywords: 错误, 失败, 阻塞, 问题, 风险, 修复, 原因, 影响, 不得, 必须, 告警, 回归, fail, failed, error, blocked, root cause, regression, risk, must, should not, do not

Review these snippets before writing any durable project rule.

## AGENTS.md

### Match 1 (lines 10-12)

```text
- Thread baseline: 正式环境/测试环境登录方式统一见 `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`；涉及登录验证、联调或 E2E 时先按该文档使用对应租户账号。
- Thread baseline: 涉及备份、恢复、发布、构建、回滚任务前必须先阅读 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`。
- Thread baseline: 正式服 /mnt/nas 是公司共享盘，禁止删除、清空或移除挂载/fstab。
```

### Match 2 (lines 15-17)

```text

- 本项目为混合 Git 工作区；凡要求新建或使用新分支，必须在每个 Git 仓库创建同名新分支。
- Thread baseline: 涉及 worktree 创建、合并、清理或排障时，先阅读 docs/worktree-memory.md。
```

### Match 3 (lines 19-21)

```text
- Thread baseline: IntRuoyi 根目录 Git 不作为融合结果判断项；融合以前后端 `ruoyi-vue-pro` 与 `yudao-ui-admin-vue3` 仓库为准。
- Thread baseline: worktree 合并后必须在合并结果上验证相关功能正确性；验证未通过不得视为完成或继续清理 worktree。

```

### Match 4 (lines 23-25)

```text

- All frontend work must follow `D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`.
- The shared frontend baseline is the IntPP production order list style; read the style file before creating or redesigning frontend pages, components, tables, filters, forms, or action areas.
```

### Match 5 (lines 32-50)

```text

- Before starting any task, the Agent must create or identify the task directory under `doc/tasks/<task-id>/` and write the task document first.
- Thread baseline: 每次任务将用户每条需求与执行命令记录到 docs/request-command-log.md。
- Thread baseline: 每次任务创建或识别任务目录后，必须先读取 `docs/experience-index.md`，按索引只打开命中的经验文档，并在任务文档写入 `经验门禁` 小节，列出本任务适用的强制门禁；不得只写“已阅读”而不摘取门禁。
- Thread baseline: 涉及真实 E2E、Playwright 长链路、登录后写入、服务器写入/重启/发布/备份/恢复/回滚、大文件上传、批量导入、worktree 合并/清理、数据库 schema/迁移/权限/菜单/租户数据修改等高风险动作前，必须在 `execution-log.md` 记录 `GREEN: experience-preflight -> PASS` 或明确 `BLOCKER: experience-preflight -> <原因>`，否则不得执行该高风险动作。
- The task document must include the task goal, milestone list, expected verification, and current status before production code changes begin.
- The task document must include a fixed `设计约束检查` section before production code changes begin:
  - `是否引入 fallback/降级/吞异常`：是/否；如是，必须注明用户明确要求、触发条件、风险与移除/回滚策略。
  - `是否从根因和长期维护角度解决`：是/否；如否，必须先阻塞并说明缺少的正式方案前置条件。
  - `是否存在临时补丁或绕过`：是/否；如是，必须注明用户明确批准范围、风险和后续处理。
- After each milestone is reached, the Agent must update the task document with milestone status, completed work, verification evidence, and remaining blockers.
- When the task is finished, the Agent must mark the task document as completed and record the final verification result.
- Before starting a new task, the Agent must check the previous task document in the same service repository. If it is not marked completed, the Agent must finish or explicitly block the old task document before working on the new task.
- If the previous task cannot be completed because of missing prerequisites, the Agent must record the blocker and impact in the old task document, then report it before starting the new task.

- For all six microservice Agents, every completed work item must be committed to the owning service Git repository after required verification passes.
- Each commit must include only files directly produced by the current work item; do not include unrelated user edits, other Agent changes, or temporary output.
- If verification fails or a required precondition is missing, fail fast and report the exact blocker and impact before committing.
- Use a concise commit message that names the result, preferably in Chinese, for example `任务: 更新权限校验`.
```

### Match 6 (lines 53-64)

```text

- 后续所有功能、修复、重构和行为变更默认采用 BDD + 严格 TDD。
- BDD 必须先写清楚用户、业务或接口可观察的 `Given / When / Then` 场景，再进入实现。
- TDD 必须按 `RED -> GREEN -> REGRESSION` 执行：先失败测试，再最小实现，最后回归验证。
- BDD 场景与 TDD 证据必须记录到 `doc/tasks/<task-id>/execution-log.md`。
- 建议使用 `BDD: <scenario name> -> Given/When/Then`、`RED: <command> -> FAIL, <expected reason>`、`GREEN: <command> -> PASS` 标记。
- 缺少前置条件、依赖、测试环境或测试数据时必须失败并报告；不得用 mock 成功、静默跳过、降级或 fallback 掩盖。

- Thread baseline: 当前仓库所有功能、修复、重构和行为变更默认采用严格 TDD：先失败测试，再最小实现，最后回归验证。
- Thread baseline: 后续所有功能、修复、重构和行为变更默认采用 BDD + 严格 TDD：先用 BDD 写清楚用户、业务或接口可观察的 `Given / When / Then` 场景，再按 TDD 执行失败测试、最小实现和回归验证；BDD 场景与 TDD 证据必须记录到 `doc/tasks/<task-id>/execution-log.md`，建议使用 `BDD: <scenario name> -> Given/When/Then`、`RED: <command> -> FAIL, <expected reason>`、`GREEN: <command> -> PASS` 标记；缺少前置条件、依赖、测试环境或测试数据时必须失败并报告，不得用 mock 成功、静默跳过、降级或 fallback 掩盖。
- Thread baseline: 未明确说明时，e2e 测试用例必须使用真实数据，不得使用 mock 数据。
- Thread baseline: 测试统一使用独立测试租户登录，禁止用备份数据方案代替真实测试环境。
```

### Match 7 (lines 67-72)

```text

- 每完成一项任务并完成必要验证后，必须立即将本任务产生的改动单独提交到当前项目的 Git 仓库。
- 提交前只暂存与当前任务直接相关的文件，不得顺手提交其他任务、用户改动或临时输出。
- 如果验证失败、缺少前置条件或存在未解决阻塞，必须先报告失败原因和影响，不得用 mock 成功、静默跳过、降级或 fallback 掩盖后提交。
- 提交信息必须简洁说明任务结果，优先使用中文，格式建议为 `任务: <简短说明>`。

```

### Match 8 (lines 74-77)

```text

- 凡涉及任何修改，包括功能、修复、重构、配置、脚本、文档、测试与其他交付物变更，必须先从长期可维护、可扩展的方向评估方案，优先采用正式可持续方案，不得默认提交短期临时方案、一次性补丁或仅为绕过当前问题的权宜改动。
- 如用户明确要求临时方案，必须先记录适用范围、触发条件、风险与后续移除/回滚策略，并仅在用户明确批准的范围内最小化实施。

```

### Match 9 (lines 79-89)

```text

- 凡涉及重构，必须先从长期可维护、可扩展的方向评估方案，先写任务文档，再采用 Subagent-Driven Development 方式执行重构。

- Thread baseline: E2E 必须走真实用户路径；只用 Playwright 操作前端，接口仅用于最终校验，前端无入口则先修前端并失败。

- Thread baseline: E2E 不得为测试额外增加前端控件或内容；发现错误必须主动暴露，不得隐藏或绕过。
- Thread baseline: 删除前端控件时必须同步删除对应后端功能，更新相关文档和测试，并运行受影响测试。
- Thread baseline: DCC审核矩阵/审批路线必须保持与 `D:\ocr2\resource\审核会签.pdf` 确认版一致；未经用户明确批准，任何测试、联调或 E2E 不得切换、覆盖或改写 live 审核矩阵版本。
- Thread baseline: 本机展厅默认文件配置 `infra_file_config.id=28`、默认 bucket `yudao`、默认域 `http://127.0.0.1:9000/yudao` 视为受保护资源；未经用户明确授权，任何 E2E、联调、脚本或人工操作不得修改、切换、覆盖或绑定到其他 bucket/domain/endpoint。
- Thread baseline: 任何 E2E、联调、脚本或人工操作都不得把 `config_id=28` 且 `path LIKE 'showroom/%'` 的默认展厅媒体 URL 改写到非默认受保护域；发现默认展厅文件配置或 `showroom/%` 媒体 URL 漂移时必须 fail fast，禁止继续启动、继续 E2E 或用临时同步/回填掩盖问题，除非用户明确批准本次修复范围。
- Thread baseline: PowerShell 5.1 不使用 `&&`；命令改为分行执行或用 `;` 连接。
```

### Match 10 (lines 92-111)

```text

- All Chinese text in `AGENTS.md`, task docs, source files, scripts, Markdown, JSON, SQL, CSV, logs, and generated docs must be read and written with explicit UTF-8 handling. Do not rely on ANSI/GBK/OEM/default code pages.
- New plain-text/code/doc files with Chinese default to UTF-8 without BOM unless the target toolchain already requires another confirmed encoding. Do not silently convert existing files to BOM, GBK, UTF-16LE, or mixed encodings.
- On Windows PowerShell 5.1, never use `Get-Content`, `Set-Content`, `Add-Content`, `Out-File`, `>` or `>>` on Chinese text without explicit encoding. Default `Get-Content` misreads UTF-8 no-BOM, default `Set-Content` writes ANSI/GBK, and `Out-File` or redirection writes UTF-16LE.
- When reading this workspace's `AGENTS.md` or any UTF-8 Chinese file in PowerShell, use `Get-Content -Encoding utf8` or a UTF-8-aware runtime such as `python -X utf8`; do not inspect them with default `Get-Content`.
- When writing or appending Chinese text from PowerShell, prefer `apply_patch`, Python `Path.read_text` / `Path.write_text` with `encoding='utf-8'`, or `[System.IO.File]::WriteAllText(..., [System.Text.UTF8Encoding]::new($false))`. If a file already uses another confirmed encoding, preserve it exactly or stop and ask.
- For command output that contains Chinese, set `[Console]::InputEncoding`, `[Console]::OutputEncoding`, and `$OutputEncoding` to UTF-8 before emitting text. Treat `chcp 65001` only as a session helper, not as the sole safeguard.
- Do not use `cmd /c echo`, batch `echo`, `type`, `more`, `findstr`, shell redirection, or unspecified export defaults to create, rewrite, or inspect Chinese files unless the encoding is explicit and verified. Prefer `python -X utf8`, UTF-8-aware Node APIs, `rg`, or other commands with verified encoding flags.
- After writing Chinese text, verify the target by re-reading it with the expected encoding or by checking raw bytes. If the encoding is unknown, mixed, or already garbled, fail fast and report the exact file and risk instead of silently rewriting it.

- Thread baseline: 测试强制不得修改芋道源码租户数据；只能修改测试租户数据。
- Thread baseline: E2E开发调试和修复只改测试租户；最终用芋道源码/admin只验证，发现问题回测试租户修复。
- Thread baseline: 本机测试租户 `tenant_id=122`、账号 `aoteman` 用于真实 E2E 写入验证时，应保持完整菜单权限基线；若页面代码存在但访问 404、菜单不显示或动态路由未注册，先检查 `system_menu`、`system_role_menu`、`get-permission-info`，不得把权限缺失误判为前端组件缺失。
- Thread baseline: 芋道动态菜单页面交付必须同时核对前端组件文件、`system_menu.path/component/component_name/permission`、目标租户角色菜单绑定和登录后权限响应；新增页面缺少菜单 SQL 或测试租户绑定时不得视为 E2E 可验收。
- Thread baseline: 前端请求失败不得使用空 `catch {}`、静默 toast 缺失或页面无反馈掩盖；后端真实错误必须能在页面、控制台或网络响应中暴露，便于区分权限、接口和组件问题。
- Thread baseline: 编写或修复 SQL 前，以当前真实库 `DESCRIBE` / `SHOW TABLES` 为准核对表名字段，尤其是 MES 老表和动态菜单相关表；不得仅凭 DO 类名、历史记忆或推断字段写运行 SQL。
- Thread baseline: 正式服务器默认禁止操作；仅在用户明确授权的发布、联调、排障场景下按文档执行。
- Thread baseline: 默认提到的修改需求只在本机修改，未经明确授权不操作服务器或远程环境。
- Thread baseline: 所有端到端测试必须由 Playwright 实际打开页面并先登录后操作；禁止接口绕过发布流程，仅使用既有真实数据，禁止模拟、自创数据和兜底，缺少数据自动失败。
- Thread baseline: `测试租户`指租户名称`测试租户`、账号名称`aoteman`；`芋道源码`指租户名称`芋道源码`、账号名称`admin`。
```
## doc/tasks/20260620-frontend-release-full-flow/execution-log.md

### Match 1 (lines 2-15)

```text

- BDD: 页面真实提交发布全链路 -> Given 运行控制台前端可访问 / When 用户在页面上依次执行构建发布包、发布测试服、发布正式服、发布备份服 / Then 每一步都必须由真实页面动作触发并最终成功。
- BDD: 页面链路失败必须记录并修复后重走 -> Given 任一步页面提交或后台执行失败 / When 排查和修复问题 / Then 必须先把失败与根因写入执行日志，再从页面重新走完整流程直到一次性通过。

- GREEN: previous-task-check -> PASS，上一维护仓任务 `20260620-fupan-prod-release-v7` 已 `COMPLETED`。
- GREEN: experience-preflight -> PASS，已读取 `release-build-preflight-lessons.md`、`release-backup-restore.md`、`server-access.md` 与 `project-error-prevention.md`；当前允许进入真实页面发布流，但仍必须坚持“页面提交动作不走接口替代”。
- BLOCKER: in-app-browser-runtime -> 应用内浏览器插件按 `control-in-app-browser` 技能接入时失败，`node_repl/js` 返回环境级错误 `missing field sandboxPolicy`；该阻塞属于工具接入问题，不是运行控制台页面问题，也不改变“必须走页面点击”的任务约束。
- GREEN: playwright-page-fallback -> PASS，已确认 `http://127.0.0.1:48181/` 返回 HTTP 200，且维护仓运行控制台前端真实存在“构建发布包 / 部署测试服 / 上线正式服 / 上线备份服”页面按钮与预览/执行对话框；后续改用 Playwright 包装器继续执行真实页面点击流，不使用接口替代按钮。
- GREEN: build-release-preview-v1 -> PASS，Playwright 在运行控制台页面填写 `releaseTag=release-20260620-page-full-flow-v1`、原因“页面真实发布全链路验证：测试服->正式服->备份服”，预览命令确认包含 `-Mode build-release -ReleaseTag release-20260620-page-full-flow-v1 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59`，未出现 `promote-prod`、`backup-now`、`rollback`、`restore-data` 或正式服误操作参数。
- GREEN: build-release-submit-v1 -> PASS，Playwright 在预览弹窗点击“执行”，页面新增 operation `op-2026-06-20T155635029222800Z-98030fbd-717b-4d21-956b-4e4c80db009d`，初始状态 `RUNNING`，摘要为“命令已提交到本机执行队列”。
- IN_PROGRESS: build-release-operation-v1 -> 页面日志先后确认 eDHR 受保护存储校验 `PASS`、Docker daemon 检查 `PASS`、后端 `mvn -f ... -pl yudao-server -am -DskipTests clean package` 已 `BUILD SUCCESS`；随后前端 `vite build --mode test` 一度长时间无新日志但对应 `node.exe` 持续占用 CPU，继续只读跟踪后已看到 `Build successful. Please see dist-intruoyi-test directory`，当前 operation 正推进到 backend Docker image 构建阶段，尚未收口为最终 `SUCCESS/FAILED`。
- GREEN: build-release-operation-v1 -> PASS，operation `op-2026-06-20T155635029222800Z-98030fbd-717b-4d21-956b-4e4c80db009d` 最终 `SUCCESS`；日志确认发布迁移门禁通过、前端 `vite build --mode test` 成功、发布包已上传 `Backup/ReleasePackage/release-20260620-page-full-flow-v1`。
- GREEN: deploy-test-preview-v1 -> PASS，Playwright 在运行控制台页面选择“部署测试服”，填写 `releaseTag=release-20260620-page-full-flow-v1` 与原因“页面真实发布全链路验证：部署测试服”，预览命令确认包含 `-Mode deploy-release -Environment test -ReleaseTag release-20260620-page-full-flow-v1 -ServerHost 172.30.30.58 -RemoteAppDir /opt/intruoyi/runtime -RemoteReleaseRoot /var/lib/docker/intruoyi-releases -RemoteDataRoot /var/lib/docker/intruoyi-data/runtime-data -RemoteDataDiskMount /var/lib/docker -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59`，未出现 `prod`、`backup`、`rollback`、`restore` 漂移参数。
- GREEN: deploy-test-submit-v1 -> PASS，Playwright 在预览弹窗点击“执行”，运行控制台生成 operation `op-2026-06-20T161404384847500Z-005f1a69-1cbf-4059-a7e3-50fcb80cb708`，初始状态 `RUNNING`，摘要为“命令已提交到本机执行队列”。
```

### Match 2 (lines 17-22)

```text
- GREEN: deploy-test-runtime-verify-v1 -> PASS，只读核对测试服 `172.30.30.58` 的 `/opt/intruoyi/runtime/.env` 为 `IMAGE_TAG=release-20260620-page-full-flow-v1`；`docker ps` 显示 `intruoyi-backend` 与 `intruoyi-frontend` 运行镜像均为 `release-20260620-page-full-flow-v1`；页面入口 `http://172.30.30.58:8081/` 返回 HTTP 200。
- BLOCKER: promote-prod-preview-gate-v1 -> 运行控制台页面在“上线正式服”表单顶部提示 `releaseTag 尚未测试通过: release-20260620-page-full-flow-v1`；按真实页面流程必须先完成“标记测试通过”动作，不能直接进入正式服预览/提交。
- BLOCKER: mark-release-tested-preview-gate-v1 -> 运行控制台页面在“标记测试通过”点击预览后提示 `selectedRecoverySetCandidateId is required for action: mark-release-tested`；按真实页面流程必须先在“恢复集候选”中选择现有可恢复备份点，不能跳过该门禁。
- BLOCKER: restore-candidate-empty-root-cause-v1 -> 只读核对 `RuntimeControlService#getRestoreCandidates`、`RuntimeControlOperationAction#MARK_RELEASE_TESTED`、`release-backup-restore.md` 与历史请求日志后确认：恢复集候选直接来自 NAS `Backup/BackupPackage` 的最终备份点，`mark-release-tested` 强制要求 `selectedRecoverySetCandidateId` 指向一个当前 `AVAILABLE` 的恢复候选；当前页面下拉显示 `No data`，说明阻塞根因是“尚无最终可用恢复集候选”，不是前端下拉渲染问题，也不能手填旧 ID 绕过。
- GREEN: mark-release-tested-next-step-decision-v1 -> PASS，基于当前契约与发布基线，下一步必须继续走运行控制台页面真实动作“立即备份”，尝试生成 NAS 最终恢复点，再返回页面继续执行“标记测试通过 -> 上线正式服 -> 上线备份服”；期间仍禁止直接调用接口或命令行脚本代替页面按钮。
- BLOCKER: prod-write-authorization-gate-v1 -> 运行控制台页面在“立即备份”点击预览后提示 `环境未授权执行写动作: 正式环境写动作未授权，当前独立控制台默认禁止写入、重启、发布、回滚或恢复正式服务器`；当前真实链路尚未进入备份脚本，而是先被控制台写权限门禁阻断。
```

### Match 3 (lines 25-31)

```text
- GREEN: backup-now-preview-v1 -> PASS，Playwright 在同一真实页面链路重新预览“立即备份”，页面弹窗确认将执行 `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops\scripts\backup-ops.ps1`，参数为 `-Mode backup-now -NonInteractive -TargetEnvironment prod -OperatorName local-operator`；说明当前已越过正式环境写权限门禁，进入真实备份动作提交前状态。
- BLOCKER: backup-now-operation-missing-secrets-v1 -> Playwright 在真实页面点击“立即备份”执行后，operation `op-2026-06-20T164241687774200Z-08e3c043-8037-4198-a9d1-78a653d80739` 立即 `FAILED`；页面日志与本机 operation log 一致报 `INTBK-1001`，原因是缺少启动所需文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops\config\backup-ops.secrets.json`。该失败发生在真实页面触发后的本机脚本启动前置校验阶段，不得绕过。
- GREEN: backup-now-missing-secrets-root-cause-v1 -> PASS，只读核对 `ops/backup-ops/scripts/backup-ops.ps1`、`modules/Core/Config.psm1`、`backup-ops.secrets.example.json` 与原 IntRuoyi 后端仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\backup-ops\config\backup-ops.secrets.json` 后确认：维护仓缺少的并非公开模板，而是本机私有 secrets 实文件；原仓存在同名私有来源，且结构包含额外 `credentialSources` 配置，说明当前阻塞根因是“维护仓未恢复本机 backup-ops 私有 secrets”，不是页面参数错误，也不能用示例模板或空值伪造通过。
- BLOCKER: backup-now-production-confirm-contract-v1 -> 补齐本机私有 secrets 后，Playwright 在真实页面再次执行“立即备份”，operation `op-2026-06-20T165254350585600Z-ba3295d1-f71e-4945-ac40-cd5911b1dd2c` 不再报缺件，但新的页面日志返回 `INTBK-1003`：`backup-ops.ps1` 要求针对正式备份显式传入 `-ProductionBackupConfirmText 'PROD-BACKUP-172.30.30.57'`；而运行控制台页面虽然有“生产确认”输入框，后端预览参数却只传 `-Mode backup-now -NonInteractive -TargetEnvironment prod -OperatorName local-operator`，并未透传脚本所需的正式备份确认文本。
- RED: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#backupNowPreviewPassesProductionBackupConfirmTextToScript test` -> FAIL，先后复现两层真实契约门禁：其一是测试默认 `prod.access-enabled=false` 时预览直接被控制台正式写动作授权拦截；补齐测试授权后，进一步暴露运行控制台统一只接受 `prodConfirmText=PROD`，而正式备份脚本需要 `PROD-BACKUP-172.30.30.57`，说明 `backup-now` 不能继续复用普通发布动作的统一确认语义。
- GREEN: backup-now-production-confirm-contract-fix-v1 -> PASS，最小修复运行控制台正式备份契约：后端对 `backup-now` 保留正式写动作授权门禁，但不再强制复用通用 `PROD` 确认校验；同时在 `backup-now/prod` 预览与执行命令中显式透传 `-ProductionBackupConfirmText <页面输入值>` 给 `backup-ops.ps1`。前端同步把该动作的确认输入标签/占位提示调整为正式备份所需文本 `PROD-BACKUP-172.30.30.57`，避免页面继续误导用户输入 `PROD`。
- GREEN: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#backupNowPreviewPassesProductionBackupConfirmTextToScript test` -> PASS
```

### Match 4 (lines 34-83)

```text
- GREEN: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1` -> PASS，停止占用 `48181` 的旧 Java 进程后重新构建前后端，`spring-boot:repackage` 成功替换最新维护控制台 jar。
- GREEN: local-runtime-restart-after-confirm-fix-v1 -> PASS，重新执行 `scripts/start.ps1` 并确认 `http://127.0.0.1:48181/actuator/health` 返回 `200`；Playwright 重新进入真实页面后，“立即备份”表单确认标签已变为 `正式备份确认`，占位提示为 `PROD-BACKUP-172.30.30.57`，证明前端静态资源已切到修复后版本。
- GREEN: backup-now-preview-pass-through-v2 -> PASS，Playwright 在真实页面填写原因“页面真实发布全链路验证：立即备份生成恢复集”和确认文本 `PROD-BACKUP-172.30.30.57` 后预览命令；弹窗确认参数已包含 `-Mode backup-now -NonInteractive -TargetEnvironment prod -ProductionBackupConfirmText PROD-BACKUP-172.30.30.57 -OperatorName local-operator`。
- GREEN: backup-now-submit-v2 -> PASS，Playwright 在预览弹窗点击“执行”，运行控制台生成 operation `op-2026-06-20T170847988455500Z-6d597657-15b5-4356-9d19-078af36fd74c`，初始状态 `RUNNING`，摘要为“命令已提交到本机执行队列”。
- GREEN: backup-now-runtime-progress-v2 -> PASS，只读跟踪 operation 日志、状态文件与 NAS 落盘证据；真实页面链路已完整跑过 `校验 NAS 挂载 -> 创建备份工作目录 -> 导出 MySQL -> 备份 MinIO 对象 -> 生成 checksums 与 manifest`，其中 MySQL dump 成功写入 `/mnt/nas/Backup/BackupPackage/20260621-010849/mysql/ruoyi-vue-pro.sql.gz`，对象阶段也已生成 `objects/manifest-object-copy-plan.tsv` 与 `manifest-object-copy.sh`。
- BLOCKER: backup-now-dcc-manifest-blocked-v2 -> operation `op-2026-06-20T170847988455500Z-6d597657-15b5-4356-9d19-078af36fd74c` 最终 `FAILED`，页面/状态文件摘要为 `命令退出码非 0: 2`；本机阻塞日志 `D:\IntRuoyi-BackupOps\logs\202606\20260621_010849_backup-now_blocked.log` 与报告 `20260621_010849_backup-now_blocked.report.md` 一致返回 `INTBK-6001`：`DCC 备份 manifest 构建失败`，要求人工按 `D:\IntRuoyi-BackupOps\tmp\20260621-010849\manifest\dcc-backup-manifest.json` 中的 errors 修复后再重试。
- BLOCKER: backup-now-dcc-manifest-root-cause-v2 -> 只读核对 `dcc-backup-manifest.json` 后确认当前真实阻塞不是 MySQL/NAS/对象备份脚本传输失败，而是 manifest 校验发现 `dcc_object_inventory_missing` 共 `384` 条，`uniqueMissingReferenceCount=288`；缺失对象集中在 `codex-e2e/...pdf.original.pdf|published.pdf|stamped.pdf`，影响为“数据库记录可恢复但对象文件不在 inventory 中，备份不可视为完整可恢复点”。下一步必须先判明这些对象是实际丢失、inventory 漏采，还是 DCC 快照残留脏引用，再修复后重新从页面执行“立即备份”。
- GREEN: backup-now-dcc-history-evidence-v2 -> PASS，已读取主仓历史任务 `D:\ProjectPackage\Int\IntRuoyi\doc\tasks\20260613-prod-data-backup\task.md`、`database-schema-evidence.md` 与 `docs/request-command-log.md`；仓库已有同类正式备份阻塞放行记录：当时同样是测试租户 `122` 的 `96` 条 `CODEX-E2E%` 历史残留记录触发 `dcc_object_inventory_missing`，在导出回滚 SQL 后对该 96 条主记录执行最小软删除，随后正式备份点 `20260614-002617` 成功生成。
- GREEN: backup-now-dcc-current-vs-history-match-v2 -> PASS，只读比对当前最新正式备份快照 `D:\IntRuoyi-BackupOps\tmp\20260621-010849\manifest\dcc-database-snapshot.json` 与历史清单 `D:\ProjectPackage\Int\IntRuoyi\doc\tasks\20260613-prod-data-backup\affected-dcc-codex-e2e-records.csv`；结果为 `EXACT_MATCH`，当前受影响 `96` 条 `tenant_id=122`、`ACTIVE`、`CODEX-E2E-T4-*` 记录与 2026-06-14 已授权修复范围完全一致，无新增、无缺失。
- GREEN: prod-dcc-cleanup-authorization-v2 -> PASS，用户于 2026-06-21 在当前线程明确授权：允许在正式服沿用 2026-06-14 历史同一路径，对这 96 条测试租户 `CODEX-E2E-T4-*` 历史残留记录执行最小软删除修复，并在修复后继续真实页面链路“立即备份 -> 标记测试通过 -> 上线正式服 -> 上线备份服”。
- GREEN: prod-dcc-cleanup-rollback-export-v2 -> PASS，已先导出本轮正式服修复前回滚 SQL 到 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-frontend-release-full-flow\prod-dcc-repair-before-20260621.sql`；来源为正式服 `dcc_controlled_file` 中 `tenant_id=122 AND status='ACTIVE' AND deleted=0 AND file_number LIKE 'CODEX-E2E-T4-%'` 的完整当前行快照，满足“先留可回滚证据、再做最小修复”的门禁。
- GREEN: prod-dcc-cleanup-soft-delete-v2 -> PASS，已在正式服对这 96 条测试租户历史残留执行最小软删除：`UPDATE dcc_controlled_file SET deleted=1, updater='codex-prod-backup-20260621', update_time=NOW() WHERE tenant_id=122 AND status='ACTIVE' AND deleted=0 AND file_number LIKE 'CODEX-E2E-T4-%';`；执行返回 `repair_result=96`，后置核对返回 `post_deleted_summary=96 96 0`，含义为共命中 96 条、现已删除 96 条、剩余 `ACTIVE+deleted=0` 为 0。下一步必须回到运行控制台页面重新执行“立即备份”验证 manifest 阻塞是否解除。
- GREEN: backup-now-submit-v3 -> PASS，Playwright 回到运行控制台真实页面，在“立即备份”动作填写原因“页面真实发布全链路验证：立即备份生成恢复集（修复DCC测试残留后重试）”与确认文本 `PROD-BACKUP-172.30.30.57` 后点击预览/执行；页面生成 operation `op-2026-06-20T223216314028100Z-b7fa2fe1-41f1-4818-b3a9-36058c47e64a`。
- GREEN: backup-now-operation-v3 -> PASS，operation `op-2026-06-20T223216314028100Z-b7fa2fe1-41f1-4818-b3a9-36058c47e64a` 最终 `SUCCESS`。日志确认真实链路完成 `校验 NAS 挂载 -> 创建备份工作目录 -> 导出 MySQL -> 备份 MinIO 对象 -> 生成 checksums 与 manifest -> 同步到测试服务器 -> 写入结果并发送通知` 七个阶段，结果代码 `INTBK-0000`，备份点 `20260621-063218`，成功日志 `D:\IntRuoyi-BackupOps\logs\202606\20260621_063217_backup-now_success.log`。
- GREEN: backup-now-artifacts-v3 -> PASS，最新备份点 `20260621-063218` 已生成完整关键产物：`mysql/ruoyi-vue-pro.sql.gz`、`objects/manifest-object-copy-plan.tsv`、`objects/manifest-object-inventory.json`、`manifest/checksums.txt`、`manifest/dcc-backup-manifest.json`、`manifest/dcc-database-snapshot.json` 与 `manifest/manifest.json`；说明此前 `dcc_object_inventory_missing` 阻塞已被正式解除。下一步回到页面执行“标记测试通过”。
- BLOCKER: mark-release-tested-candidate-empty-v2 -> 备份成功后，Playwright 回到真实页面切换“标记测试通过”，页面已渲染“恢复集候选”下拉控件，但点击展开后弹出 `No data`，尚未出现刚生成的 `20260621-063218` 恢复点。该阻塞发生在真实页面继续链路时，下一步必须先只读排查候选数据为何未进入下拉，再继续页面动作。
- BLOCKER: restore-candidates-object-store-root-v3 -> 只读直接请求 `/admin-api/infra/runtime-control/restore-candidates` 并核对 NAS `Backup/BackupPackage` 目录后确认，接口把 `object-store` 目录错误当成恢复点候选参与枚举；该目录下不存在 `manifest/manifest.json`，导致此前真实环境中候选请求直接在 `buildRestoreCandidate` 过程中抛出 `STATUS_OBJECT_NAME_NOT_FOUND (0xc0000034)`，页面下拉最终表现为 `No data`。根因在服务端恢复点目录识别过宽，不是前端渲染问题，也不能手填候选 ID 绕过。
- RED: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#restoreCandidatesIgnoreObjectStoreRootAndStillReturnRealBackupPoints test` -> FAIL，新增回归场景复现 `Backup/BackupPackage` 同时存在合法备份点 `20260621-063218` 与 `object-store` 目录时，接口返回了 2 条数据，其中把 `restore:object-store` 作为 `BLOCKED` 候选错误暴露出来，证明当前逻辑没有把“对象仓根目录”和“恢复点目录”区分开。
- BLOCKER: restore-candidates-object-store-isregularfile-v4 -> 将回归夹具补齐到与真实 SMB 行为一致后，再次 RED 复现发现第二层根因：`RuntimeControlNasBrowser.isRegularFile()` 在父目录 `object-store/manifest` 不存在时会直接抛 `RuntimeControlException`，导致即使已在候选枚举前加“是否存在 `manifest/manifest.json`”过滤，过滤逻辑本身仍会被异常打断，接口继续返回 500。
- GREEN: restore-candidates-object-store-filter-fix-v4 -> PASS，最小修复 `RuntimeControlService#getRestoreCandidates()`：仅将包含 `manifest/manifest.json` 的目录识别为恢复点；同时把 `isRestorePointDirectory()` 中“父目录不存在/路径不是文件”的探测失败视为“非恢复点目录”，不再让 `object-store` 这类明显非恢复点目录中断整个候选接口。该修复保持了真正恢复点仍进入 `buildRestoreCandidate` 做完整阻断校验的正式语义，属于恢复点目录识别根因修复而非 fallback。
- GREEN: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#restoreCandidatesIgnoreObjectStoreRootAndStillReturnRealBackupPoints test` -> PASS
- GREEN: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS
- GREEN: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1` -> PASS，已将恢复候选修复重新打入最新维护控制台前后端产物。
- GREEN: restore-candidates-runtime-verify-v4 -> PASS，重启本地运行控制台后，只读核对 `http://127.0.0.1:48181/admin-api/infra/runtime-control/restore-candidates` 返回 HTTP `200`，且候选仅包含真实恢复点 `restore:20260621-063218`，状态 `AVAILABLE`；此前 `object-store` 误入候选并触发 `STATUS_OBJECT_NAME_NOT_FOUND` 的 500 已消失。
- GREEN: mark-release-tested-page-candidate-visible-v4 -> PASS，Playwright 重新进入真实页面“标记测试通过”，当前“恢复集候选”下拉已成功展开并显示 `20260621-063218 · AVAILABLE`；说明本轮阻塞已从后端接口 500 收口，下一步可以继续纯页面动作选择候选并执行“标记测试通过”。
- GREEN: mark-release-tested-preview-v4 -> PASS，Playwright 在真实页面选中恢复点 `20260621-063218`、将生产确认切回通用 `PROD` 后点击“预览命令”；弹窗确认本次将执行 `publish-int-ruoyi.ps1 -Mode mark-tested`，并已绑定 `-SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218` 等真实恢复集参数。
- BLOCKER: mark-release-tested-migration-metadata-gate-v5 -> Playwright 在真实页面点击“标记测试通过”执行后，运行控制台生成 operation `op-2026-06-20T231058149703700Z-a3e87030-a2c9-45fb-bbea-01cf147a8da9`，但脚本立即 `FAILED`；本机 operation log 明确报错 `[FAIL] Release migration metadata missing: D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql\20260621_srm_phase1_supplier_portal.sql`。这说明当前真实页面链路已前进到“测试通过标记”脚本层，但被发布迁移元数据门禁拦下，不能继续上线正式服。
- GREEN: mark-release-tested-metadata-misreport-evidence-v5 -> PASS，只读核对同一路径后确认 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql\20260621_srm_phase1_supplier_portal.sql` 文件实际存在，且 `20260621_srm_phase3_purchase_order.sql` 的 `dependsOn=20260621_srm_phase1_supplier_portal` 与对应脚本测试也都存在；因此当前不是“文件缺失”，而是 `mark-tested` 使用的迁移元数据校验路径/识别逻辑对现有 SQL 发生误判。下一步必须先修复该根因，再回到真实页面重走“标记测试通过”。
- RED: `python -X utf8 -m pytest script\tests\test_srm_phase1_schema_sql.py -q` -> FAIL，新增断言后稳定复现 `20260621_srm_phase1_supplier_portal.sql` 首行并非 `release-migration` 元数据，而是直接从 `CREATE TABLE` 开始；这与 `mark-tested` 在真实页面执行时的门禁失败一致。
- GREEN: srm-phase1-portal-release-metadata-fix-v5 -> PASS，为 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql\20260621_srm_phase1_supplier_portal.sql` 补齐正式 `release-migration` 元数据：`allowedEnvironments=test,backup,prod; dependsOn=20260620_srm_phase1_supplier_access_profile; type=schema; riskLevel=medium`。该修复属于正式迁移契约补齐，不是 fallback。
- GREEN: `python -X utf8 -m pytest script\tests\test_srm_phase1_schema_sql.py -q` -> PASS
- GREEN: `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，迁移门禁清单现已包含 `20260621_srm_phase1_supplier_portal` 与 `20260621_srm_phase3_purchase_order` 的正确依赖链。下一步返回真实页面重走“标记测试通过”。
- GREEN: mark-release-tested-submit-v6 -> PASS，修复 SRM SQL 正式迁移元数据后，Playwright 回到真实页面“标记测试通过”，沿用恢复点 `20260621-063218`、生产确认 `PROD` 与验证结论“回归通过，允许上线正式服”，再次点击预览/执行，生成 operation `op-2026-06-20T231610219440500Z-62163986-e842-4cf2-ace5-cb1a65954752`。
- GREEN: mark-release-tested-operation-v6 -> PASS，重新抓取运行控制台真实页面快照后，操作记录中 `op-2026-06-20T231610219440500Z-62163986-e842-4cf2-ace5-cb1a65954752` 已从 `RUNNING` 收口为 `SUCCESS`，结果为“命令执行完成”；对应本机 operation log 关键输出为 `Release package marked as tested: release-20260620-page-full-flow-v1`，说明页面真实“标记测试通过”链路已走通。
- GREEN: mark-release-tested-gate-open-v6 -> PASS，当前运行控制台页面顶部摘要已显示最新动作 `SUCCESS / 标记测试通过`，正式服上线门禁从“releaseTag 尚未测试通过”推进到可继续预览/执行“上线正式服”；下一步继续真实页面动作“上线正式服 -> 上线备份服”。
- BLOCKER: promote-prod-missing-dry-run-evidence-v7 -> Playwright 在真实页面切换“上线正式服”，将 `releaseTag` 修正为 `release-20260620-page-full-flow-v1` 后预览/执行，生成 operation `op-2026-06-20T232011628082400Z-19f06c06-8815-4e57-83eb-39d0b7aba973`；页面刷新后该 operation `FAILED`，本机 log 明确报 `Production deploy-release requires -ProdDryRunEvidencePath from a passed preflight-release dry-run.`。说明当前真实页面链路已进入正式发布脚本，但页面/后端请求契约没有为正式服上线携带 dry-run 证据。
- BLOCKER: promote-prod-no-frontend-entry-for-dry-run-evidence-v7 -> 只读核对 `frontend/src/App.vue`、`frontend/src/api/runtimeControl.ts`、`backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeDtos.java`、`RuntimeControlOperationAction.java` 与 `publish-int-ruoyi.ps1` 后确认：正式服脚本门禁本身正确，`deploy-release/prod` 确实强制要求 `-ProdDryRunEvidencePath`；但当前运行控制台前端既无单独 `preflight-release` 页面入口，也无 `prodDryRunEvidencePath` 字段透传，导致用户即使严格走页面，也无法把正式 dry-run 证据绑定到“上线正式服”执行。按仓库 E2E 基线，前端无入口时必须先修前端/契约，再继续真实页面流。
- BLOCKER: promote-prod-build-artifact-manifest-mismatch-v8 -> 在补做 `PROMOTE_PROD` 自动 dry-run 证据测试时，手工复跑 `run-deploy-precheck-report.ps1` 读取真实页面构建产物 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260620-page-full-flow-v1`，确认该包内 `manifest.json` 只有 `manifestVersion/releaseTag/packageId/targetRequirements` 四类最小字段；而 `DeployPrecheckReport.psm1`/`ReleaseManifestValidator.psm1` 的 `report-only` 门禁要求完整 Manifest v1、资源引用清单和文件声明，因此自动 dry-run 无法直接通过。该阻塞属于 build 产物契约与正式 precheck 契约不一致，不是页面点击误操作。
- BLOCKER: promote-prod-local-cache-polluted-by-test-fixture-v9 -> 继续只读核对 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260620-page-full-flow-v1` 与其他真实发布包（如 `release-20260620-current-head-prod-target-v7`、`release-20260616-152022-codeonly-e2e`）后确认：当前 `page-full-flow-v1` 本地目录的时间戳已是 `2026-06-21 07:33`，且只剩 `manifest.json/preflight-plan.json/release-manifest.json` 三个文件；这不是 2026-06-20 页面 build 的原样，而是此前同名后端单测夹具曾错误复用了真实 release tag，导致本地 dry-run 读取到被污染的最小测试包。根因已通过改测试夹具的独立 tag 收口，但当前这份真实 release tag 本地缓存已不可信，不能继续拿它做正式页面发布。
- GREEN: promote-prod-auto-dry-run-test-fix-v9 -> PASS，已将 `RuntimeControlOriginalParityTest#promoteProdPreviewAutoGeneratesDryRunEvidence` 改为独立测试 tag `release-20260621-prod-dry-run-fixture`，并补齐最小可通过 Manifest v1 夹具；`mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` 重新全绿，后续不会再污染真实页面 release tag 的本地缓存目录。
- GREEN: build-release-preview-v2 -> PASS，Playwright 在真实页面重新填写 `releaseTag=release-20260621-page-full-flow-v2`、原因“页面真实发布全链路验证：重建干净发布包并重走测试服-正式服-备份服”，预览命令确认包含 `-Mode build-release -ReleaseTag release-20260621-page-full-flow-v2 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59`，说明新的页面重跑链路参数正确。
- GREEN: build-release-submit-v2 -> PASS，Playwright 在预览弹窗点击“执行”，运行控制台真实生成 operation `op-2026-06-20T235144305204100Z-e8b0a823-14ad-4eb0-8f6b-6629f49a1c1b`；只读查询 `/admin-api/infra/runtime-control/operations` 已确认该 operation 落库，不是页面点击丢失。
- BLOCKER: build-release-backend-jar-locked-v2 -> operation `op-2026-06-20T235144305204100Z-e8b0a823-14ad-4eb0-8f6b-6629f49a1c1b` 很快 `FAILED`，本机日志明确报错：`Backend jar is locked before Maven clean: D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-server\target\yudao-server.jar. Possible locking process: pid=48576 name=java.exe; pid=45732 name=java.exe. Restart the local backend with restart-ruoyi-backend.bat so it runs from a copied runtime jar, then retry build-release.` 当前阻塞根因是本机后端仍直接占用源码仓 `target\yudao-server.jar`，导致真实页面 build-release 无法通过 Maven clean 前置门禁；必须先修正本机后端启动方式，再回到页面重新点击“构建发布包”。
- GREEN: local-backend-jar-unlock-v2 -> PASS，按门禁提示执行 `D:\ProjectPackage\Int\IntRuoyi\restart-ruoyi-backend.bat` 后，本机运行 jar 已切换到 `E:\Int\CacheData\IntRuoyi\runtime\backend-20260621-075408.jar`，源码仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-server\target\yudao-server.jar` 不再被直接占用；虽然 `48081` 仍因既有 Quartz/JobStartupSyncRunner 问题退出，但这不再阻塞维护控制台重新执行页面 `build-release`。
- GREEN: build-release-submit-v3 -> PASS，Playwright 回到同一真实页面会话，再次点击“构建发布包”，生成新的 operation `op-2026-06-20T235900978902100Z-cd7053fd-48c2-4f27-ad42-9ac8cf36baea`；页面、`/admin-api/infra/runtime-control/operations` 与本机 log 已确认本轮新构建真实进入执行队列。
- GREEN: build-release-backend-package-pass-v3 -> PASS，只读跟踪本机日志确认本轮新构建已顺利越过上轮 jar 锁门禁，完成 `eDHR protected storage` 校验、`docker info`、backend runtime base image load，并执行 `mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-server -am -DskipTests clean package` 得到 `BUILD SUCCESS`；当前已推进到前端 `node D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\node_modules\vite\bin\vite.js build --mode test` 阶段。
- BLOCKER: build-release-frontend-vite-stall-v3 -> 截至 2026-06-21 08:01:52，本机 operation log `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-20T235900978902100Z-cd7053fd-48c2-4f27-ad42-9ac8cf36baea.log` 最后输出停在 `Building frontend static assets for the test server` / `Run: node ... vite.js build --mode test`；页面与 `/admin-api/infra/runtime-control/operations` 仍显示该 operation 为 `RUNNING`，同时本机存在对应 `node.exe` 进程 `ProcessId=16260`，命令行为 `D:\Programs\node.exe D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\node_modules\vite\bin\vite.js build --mode test`。连续两次只读检查日志文件 `LastWriteTime` 均固定在 `2026-06-21 08:01:52`、`Length=117769`，说明当前新的真实页面构建已从“jar 锁失败”推进到“前端构建阶段疑似卡住/静默无进度”的新阻塞；下一步必须先定位 `vite build --mode test` 为何不再产生日志，再决定如何修复并回页面重走。
- RED: `$env:NODE_OPTIONS='--max-old-space-size=8192'; $env:VITE_BASE_URL=''; $env:VITE_BASE_PATH='/'; $env:VITE_OUT_DIR='dist-intruoyi-test-repro'; node D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\node_modules\vite\bin\vite.js build --mode test` -> FAIL/TIMEOUT，独立在前端仓 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 直接复现当前发布脚本同等构建上下文，命令运行 244 秒后仍未结束，被外层超时回收。该证据确认问题不在页面提交或运行控制台调度，而在当前前端 `test` 模式 Vite 构建链本身。
- GREEN: vite-build-debug-evidence-v3 -> PASS，追加 `DEBUG='vite:*'` 并将输出重定向到 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\vite-test-debug.stderr.log` 后确认：前端 `test` 模式构建并非永久卡死，而是在长时间 `vite:resolve` 资源解析阶段后最终打印 `Build successful. Please see dist-intruoyi-test-debug directory`。这说明此前“静默卡住”判断过早，真实问题更接近“test 模式构建耗时极长、普通同步日志面上长期无新增”，而不是明确失败。
- GREEN: build-release-operation-v3 -> PASS，随后重新只读核对运行控制台 `/admin-api/infra/runtime-control/operations` 与本机 operation log，确认真实页面构建 operation `op-2026-06-20T235900978902100Z-cd7053fd-48c2-4f27-ad42-9ac8cf36baea` 已最终收口为 `SUCCESS`；日志尾部显示 `Release package uploaded to NAS: Backup/ReleasePackage/release-20260621-page-full-flow-v2`、`Release package built: release-20260621-page-full-flow-v2`。因此新 tag 的页面构建阶段已真实完成，可以继续页面下一步“部署测试服”。
```

### Match 5 (lines 86-102)

```text
- GREEN: deploy-test-submit-v2 -> PASS，Playwright 在真实页面点击“部署测试服”的预览弹窗“执行”，生成 operation `op-2026-06-21T002749215627300Z-ceee763a-3578-4831-8ff5-c075d7295215`。
- BLOCKER: deploy-test-required-sql-supplier-profile-route-v2 -> operation `op-2026-06-21T002749215627300Z-ceee763a-3578-4831-8ff5-c075d7295215` 最终 `FAILED`；本机日志 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T002749215627300Z-ceee763a-3578-4831-8ff5-c075d7295215.log` 明确显示 required SQL `20260619_srm_d7_2_supplier_access_risk.sql` 执行 MySQL 时报错 `ERROR 1644 (45000) at line 321: Missing SRM supplier-profile route menu for get-permission-info`。这说明真实页面测试服发布已进入 required SQL 阶段，但被 SRM D7-2 菜单路由契约阻断。
- GREEN: deploy-test-lock-release-v2 -> PASS，尽管 required SQL 失败，发布锁在同一 operation 尾部已释放，日志明确返回 `LOCK_RELEASED`；当前可以在修复后重新从页面提交新的测试服发布，不存在测试服发布锁残留阻塞。
- RED: `python -X utf8 -m pytest script\tests\test_srm_d7_d10_sql_contract.py -q` -> FAIL，新增回归断言 `test_srm_t1_route_menu_guards_do_not_confuse_query_buttons_with_pages` 后稳定复现当前根因：D7-2 SQL 的三个页面路由守卫 (`991011/991020/991024`) 仍把查询 permission 直接当成页面已存在证据，导致当测试库中只残留 `type=3` 查询按钮时，会错误跳过页面路由插入。
- GREEN: srm-d7-2-route-guard-fix-v2 -> PASS，已将 `20260619_srm_d7_2_supplier_access_risk.sql` 中 `supplier-access`、`supplier-risk`、`supplier-profile` 三个页面路由的 `NOT EXISTS` 守卫统一收窄为：仅接受同 `id`、同 `component`，或同 `permission` 且 `type=2` 的页面菜单，不再把 `type=3` 查询按钮误判为页面路由存在。该修复是长期契约修复，不是绕过。
- GREEN: `python -X utf8 -m pytest script\tests\test_srm_d7_d10_sql_contract.py -q` -> PASS，13 项测试全部通过。
- GREEN: `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，D7-2 SQL 修复后发布迁移门禁仍通过，`20260619_srm_d7_2_supplier_access_risk` 的 metadata/依赖链保持有效。
- BLOCKER: deploy-test-rebuild-required-after-d7-2-fix-v2 -> 当前修复仅存在于源码与测试中，而页面已构建成功的 `release-20260621-page-full-flow-v2` 发布包不包含本次 SQL 变更；因此不能直接继续拿 `v2` 重试测试服发布。下一步必须严格回到真实页面重新执行“构建发布包”，生成新的 release tag，再重走“部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服”。
- GREEN: build-release-preview-v3 -> PASS，Playwright 在真实页面重新填写 `releaseTag=release-20260621-page-full-flow-v3` 与原因“页面真实发布全链路验证：D7-2路由守卫修复后重建发布包并重走测试服-正式服-备份服”；首次预览仍沿用旧 `release-20260620-page-full-flow-v1` 参数，继续按真实用户动作切换焦点、关闭旧预览并重新点击“预览命令”后，新的预览弹窗已正确显示 `-Mode build-release -ReleaseTag release-20260621-page-full-flow-v3 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59`。该现象说明当前页面表单至少在此路径上需要失焦后才会把输入值提交到预览状态，但本次通过真实页面交互已得到正确预览参数。
- GREEN: build-release-submit-v4 -> PASS，Playwright 在真实页面点击“构建发布包”预览弹窗“执行”，生成 operation `op-2026-06-21T024523486951200Z-fc58e07c-db7d-4604-8f5a-3539af0ad13d`，目标发布标签为 `release-20260621-page-full-flow-v3`。
- GREEN: build-release-operation-v4 -> PASS，只读轮询 `http://127.0.0.1:48181/admin-api/infra/runtime-control/operations`、operation 状态文件与本机日志 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T024523486951200Z-fc58e07c-db7d-4604-8f5a-3539af0ad13d.log` 后确认：该真实页面构建先完成 backend `mvn ... clean package` 并得到 `BUILD SUCCESS`，随后在前端 `vite build --mode test` 长耗时阶段保持 `node.exe` 持续占用 CPU，最终于 2026-06-21 10:58:27 收口为 `SUCCESS`；日志尾部明确写入 `Release package uploaded to NAS: Backup/ReleasePackage/release-20260621-page-full-flow-v3` 与 `Release package built: release-20260621-page-full-flow-v3`。下一步回到真实页面继续“部署测试服”。
- GREEN: deploy-test-preview-v3 -> PASS，Playwright 在真实页面切换到“部署测试服”，将操作原因改为“页面真实发布全链路验证：部署测试服（v3）”，预览命令确认目标环境为 `test`、发布标签为 `release-20260621-page-full-flow-v3`，参数未漂移到 `prod/backup/rollback/restore`。
- GREEN: deploy-test-submit-v3 -> PASS，Playwright 在真实页面点击“部署测试服”预览弹窗“执行”，生成 operation `op-2026-06-21T030252892482500Z-0cf0dc70-5cbe-48bd-8d3c-740fbc777f96`。
- BLOCKER: deploy-test-required-sql-access-profile-syntax-v3 -> operation `op-2026-06-21T030252892482500Z-0cf0dc70-5cbe-48bd-8d3c-740fbc777f96` 最终 `FAILED`；只读轮询页面、operation 接口和本机日志后确认，链路先成功执行并登记 `20260619_srm_d7_2_supplier_access_risk.sql`，随后在 required SQL `20260620_srm_phase1_supplier_access_profile.sql` 阶段失败。远端 MySQL 报错 `ERROR 1064 (42000) at line 6 ... near 'IF NOT EXISTS \`portal_contact_name\` varchar(64) ...'`，说明当前阻塞根因是该 SQL 直接使用 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`，与测试服真实 MySQL 语法不兼容，不是页面提交流程问题。
- GREEN: deploy-test-lock-release-v3 -> PASS，尽管 `20260620_srm_phase1_supplier_access_profile.sql` 执行失败，本次测试服发布锁在同一 operation 尾部已释放，日志明确返回 `LOCK_RELEASED`；修复后可以继续从真实页面重提测试服部署。
- RED: `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_srm_phase1_schema_sql.py -q` -> FAIL，新增断言要求 `20260620_srm_phase1_supplier_access_profile.sql` 改用与真实目标库兼容的正式幂等加列写法，不再允许 `ADD COLUMN IF NOT EXISTS`；旧 SQL 稳定命中断言。
- GREEN: srm-phase1-access-profile-syntax-fix-v4 -> PASS，已将 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql\20260620_srm_phase1_supplier_access_profile.sql` 重写为 `ensure_srm_phase1_supplier_access_profile()` 存储过程：按列查询 `information_schema.COLUMNS`，仅在缺列时执行对应 `ALTER TABLE ... ADD COLUMN ...`，执行后 `CALL` 并删除过程定义，不引入 fallback。
```

### Match 6 (lines 104-133)

```text
- GREEN: `python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，返回 `status=passed`，且依赖链正确保留 `20260620_srm_phase1_supplier_access_profile -> 20260621_srm_phase1_supplier_portal -> 20260621_srm_phase3_purchase_order`。
- BLOCKER: deploy-test-rebuild-required-after-access-profile-fix-v4 -> 当前已构建完成的 `release-20260621-page-full-flow-v3` 发布包不包含最新 access-profile 语法修复，不能直接继续页面部署测试服。下一步必须通过真实页面重新构建新 tag `release-20260621-page-full-flow-v4`，再重走“部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服”。
- GREEN: build-release-preview-v4-tag -> PASS，Playwright 在真实页面重新填写 `releaseTag=release-20260621-page-full-flow-v4` 与原因“页面真实发布全链路验证：Phase1 access-profile语法修复后重建发布包并重走测试服-正式服-备份服”，预览命令确认包含 `-Mode build-release -ReleaseTag release-20260621-page-full-flow-v4 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59`，未漂移到 `prod/backup/rollback/restore`。
- GREEN: build-release-submit-v4-tag -> PASS，Playwright 在真实页面点击“构建发布包”预览弹窗“执行”，生成 operation `op-2026-06-21T033855757114300Z-eeb75421-362d-407a-82b3-b0887b4491e0`。
- GREEN: build-release-operation-v4-tag -> PASS，只读轮询运行控制台页面、`/admin-api/infra/runtime-control/operations`、operation 状态文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T033855757114300Z-eeb75421-362d-407a-82b3-b0887b4491e0.json`、operation log 与本地/NAS 发布目录后确认：该真实页面构建先完成 backend `mvn ... clean package`，随后在前端 `vite build --mode test` 长耗时阶段长时间无新日志，再继续进入 backend image `docker build` 与发布包落盘阶段；最终状态文件与接口都收口为 `SUCCESS`，本地发布目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-v4` 已生成 `intruoyi-images_release-20260621-page-full-flow-v4.tar`、`release-manifest.json`、`manifest.json`，并已上传到 NAS `Backup/ReleasePackage/release-20260621-page-full-flow-v4`。下一步回到真实页面继续“部署测试服”。
- GREEN: deploy-test-preview-v4 -> PASS，Playwright 复用真实页面会话 `frontend-release-full-flow`，切换到“部署测试服”，将操作原因改为“页面真实发布全链路验证：部署测试服（v4）”，预览命令确认目标环境为 `test`、发布标签为 `release-20260621-page-full-flow-v4`，参数未漂移到 `prod/backup/rollback/restore`。
- GREEN: deploy-test-submit-v4 -> PASS，Playwright 在真实页面点击“部署测试服”预览弹窗“执行”，生成 operation `op-2026-06-21T035603828833Z-c1598389-017f-4d4e-8c9c-43fb3fea82e5`。
- GREEN: deploy-test-operation-v4 -> PASS，只读轮询运行控制台页面、`/admin-api/infra/runtime-control/operations`、operation 状态文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T035603828833Z-c1598389-017f-4d4e-8c9c-43fb3fea82e5.json` 与本机日志 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T035603828833Z-c1598389-017f-4d4e-8c9c-43fb3fea82e5.log` 后确认：本轮真实页面测试服发布已成功越过此前两次阻塞的 `20260620_srm_phase1_supplier_access_profile.sql`、`20260621_srm_phase1_supplier_portal.sql` 与 `20260621_srm_phase3_purchase_order.sql`，随后完成远端 Quartz/showroom schema 检查、`backend/frontend` 容器重建、远端 readiness、scheduler smoke runtime 核对、发布锁释放与远端临时文件清理，最终收口为 `SUCCESS`。
- GREEN: deploy-test-runtime-verify-v4 -> PASS，只读核对测试服 `172.30.30.58` 的 `/opt/intruoyi/runtime/.env` 为 `IMAGE_TAG=release-20260621-page-full-flow-v4`；`docker ps` 显示 `intruoyi-backend` 与 `intruoyi-frontend` 运行镜像均为 `release-20260621-page-full-flow-v4`；`http://172.30.30.58:48081/actuator/health`、`http://172.30.30.58:8081/` 与 `http://172.30.30.58:8081/pdfjs/pdf.worker.mjs` 均返回 HTTP `200`。下一步继续在真实页面执行“标记测试通过”。
- GREEN: mark-release-tested-preview-v4 -> PASS，Playwright 复用真实页面会话 `frontend-release-full-flow`，在“标记测试通过”填写原因“页面真实发布全链路验证：标记测试通过（v4）”、生产确认 `PROD`、验证结论“回归通过，允许上线正式服”，并通过页面下拉真实选中恢复点 `20260621-063218 · AVAILABLE`；预览弹窗确认本次将执行 `publish-int-ruoyi.ps1 -Mode mark-tested -ReleaseTag release-20260621-page-full-flow-v4 -TestConclusion 回归通过，允许上线正式服 -SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218 ...`，参数未漂移到 `deploy-release/backup-now/rollback/restore-data`。
- GREEN: mark-release-tested-submit-v4 -> PASS，Playwright 在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T041405918994500Z-24330a04-ecfe-4786-8a55-8c95fc0e1f18`；页面操作记录新增 `test / 标记测试通过 / RUNNING / 命令已提交到本机执行队列`。
- GREEN: mark-release-tested-operation-v4 -> PASS，只读轮询 operation 状态文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T041405918994500Z-24330a04-ecfe-4786-8a55-8c95fc0e1f18.json` 与本机日志 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T041405918994500Z-24330a04-ecfe-4786-8a55-8c95fc0e1f18.log` 后确认：该真实页面 `mark-tested` 已最终 `SUCCESS`，参数落库为 `releaseTag=release-20260621-page-full-flow-v4`、`selectedRecoverySetCandidateId=restore:20260621-063218`；日志确认 `Release package marked as tested: Backup/ReleasePackage/release-20260621-page-full-flow-v4`，并同步记录 `rollback-compatibility.json status=BLOCKED` 元数据。下一步继续在真实页面执行“上线正式服”。
- BLOCKER: promote-prod-precheck-report-only-failed-v10 -> Playwright 复用真实页面会话切换到“上线正式服”，保持 `releaseTag=release-20260621-page-full-flow-v4`、`targetEnvironment=正式服`、`prodConfirmText=PROD` 后点击“预览命令”；页面未进入执行队列，而是在预览阶段直接弹出错误 `正式 deploy precheck report-only 失败: status=failed mode=report-only output=D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-v4-deploy-precheck-report.json`。这说明当前新的真实页面阻塞已前移到正式服 dry-run/precheck 阶段。
- BLOCKER: promote-prod-precheck-undeclared-package-files-v10 -> 只读打开 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-v4-deploy-precheck-report.json` 后确认，`report-only` 失败根因不是网络、服务器连通或页面参数漂移，而是发布包 manifest 契约不完整：报告包含大量 `PACKAGE_UNDECLARED_FILE`，例如 `.env`、`post-import.sql`、`preflight-plan.json`、`preflight-target-state-test.json`、`ops-runtime/actions/*.bat`、`ops-runtime/scripts/modules/Core/*.psm1` 等文件均存在于包中但未被 manifest 声明。下一步必须按严格 TDD 修复构建产物/manifest 契约，再回到真实页面重走“上线正式服 -> 上线备份服”。
- RED: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#promoteProdPreviewUsesSanitizedPackageWorkspace test` -> FAIL，新增回归场景先构造一个 Manifest v1 完整的本地发布包目录，再故意写入 `.env`、`preflight-plan.json` 与带目标 IP 的 `post-import.sql` 模拟测试服部署后的本地污染。旧逻辑仍直接把该目录作为 `run-deploy-precheck-report.ps1 -PackagePath` 输入，预览返回 `正式 deploy precheck report-only 失败`，稳定复现当前页面阻塞。
- GREEN: prod-dry-run-sanitized-workspace-fix-v11 -> PASS，已在 `RuntimeControlService#generateProdDryRunEvidence` 引入正式 dry-run 隔离工作区：先从 `manifest.json` 提取声明文件清单，仅复制声明文件与 `manifest.json/release-manifest.json` 到临时副本，再对该副本执行 `run-deploy-precheck-report.ps1 -Mode report-only`。这样真实部署动作写回本地缓存目录的 `.env`、`post-import.sql`、`ops-runtime/`、`preflight-plan.json` 等工件不会再污染正式预检。
- GREEN: `mvn -f backend/pom.xml " -Dtest=RuntimeControlOriginalParityTest#promoteProdPreviewUsesSanitizedPackageWorkspace+RuntimeControlOriginalParityTest#promoteProdPreviewAutoGeneratesDryRunEvidence" test` -> PASS，污染目录回归场景与原有“自动生成 dry-run 证据”场景都通过。
- GREEN: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS，14 项一致性/契约测试全部通过。
- GREEN: `python -X utf8 C:\Users\BJB110\.codex\skills\bug-regression-fix-loop\scripts\validate_bug_regression.py --evidence D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-frontend-release-full-flow\bug-regression-evidence.md` -> PASS，当前缺陷证据结构有效。
- BLOCKER: local-runtime-jar-lock-after-prod-dry-run-fix-v11 -> 在将正式 dry-run 隔离工作区修复合入后，执行 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1` 时再次卡在 `spring-boot:repackage`：Maven 无法将 `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 改名为 `.original`。只读核对 `Get-NetTCPConnection -LocalPort 48181` 与 `Win32_Process` 后确认，当前监听 `127.0.0.1:48181` 的旧维护控制台进程 `PID 59068` 仍直接以 `java -jar ...\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 运行，导致新包无法覆盖。下一步必须先停掉该本机旧进程，再重建并重启本地维护控制台，之后才能回到真实页面继续“上线正式服 -> 上线备份服”。
- GREEN: promote-prod-preview-after-dry-run-workspace-fix-v12 -> PASS，重建并重启本地维护控制台后，Playwright 复用真实页面会话 `frontend-release-full-flow` 再次进入“上线正式服”，当前页面已能正确通过 `正式 deploy precheck report-only` 预览门禁，并恢复显示真实执行预览弹窗。
- GREEN: promote-prod-submit-v12 -> PASS，Playwright 在真实页面“上线正式服”预览弹窗点击“执行”，生成正式服真实 operation `op-2026-06-21T050013146743700Z-46beb4fb-5f6c-4d2a-ba1c-4f1171a3f54b`；参数落库为 `releaseTag=release-20260621-page-full-flow-v4`、`prodDryRunEvidencePath=D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-v4-preflight-release-dry-run.json`。
- BLOCKER: promote-prod-preflight-plan-blocked-env-v12 -> operation `op-2026-06-21T050013146743700Z-46beb4fb-5f6c-4d2a-ba1c-4f1171a3f54b` 最终 `FAILED`；本机日志 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T050013146743700Z-46beb4fb-5f6c-4d2a-ba1c-4f1171a3f54b.log` 明确显示失败点不是预览、不是真正执行某条 required SQL，而是在正式服执行阶段生成并读取 `preflight-plan.json` 后，直接因 `preflight-plan.json status must be passed before deploy-release: blocked` fail-fast。
- BLOCKER: promote-prod-preflight-plan-test-backup-only-migrations-v12 -> 只读核对 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-v4\preflight-plan.json` 与 `manifest.json` 后确认，本次 prod preflight 被 8 个 `BLOCKED_ENV_NOT_ALLOWED` 项阻断：`20260618_post_release_role_e2e_gate`、`20260618_post_release_role_e2e_gate_password_fix`、`20260618_post_release_role_e2e_gate_smoke_contract`、`20260619_post_release_role_e2e_gate_smoke_username_fix`、`20260619_post_release_role_e2e_gate_smoke_username_password_freshness_fix`、`20260619_post_release_role_e2e_gate_smoke_z_erp_job_permission_fix`、`20260619_post_release_role_e2e_gate_smoke_admin_resource_capacity_fix`、`20260619_post_release_role_e2e_gate_smoke_route_900026_line_fix`。这些 SQL 源文件的 metadata 都显式声明 `allowedEnvironments=test,backup`，但当前发布包 `database.schemaMigrations` 仍把它们带入跨环境候选包，导致 prod preflight 把“不适用当前环境的迁移”误当成整包阻塞。
- BLOCKER: promote-prod-release-environment-contract-regression-v12 -> 对比已成功上线正式服的旧包 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260620-current-head-prod-target-v7\manifest.json` 与当前 `release-20260621-page-full-flow-v4\manifest.json` 后确认：旧包 `database.schemaMigrations` 中不含上述 8 个 `post_release_role_e2e_gate*` test/backup-only 迁移，而当前包包含它们。这说明当前新的正式服阻塞根因已经收敛为“发布包环境契约 / prod preflight 对非目标环境迁移的处理语义不一致”，下一步必须按严格 TDD 修复源码发布输入与 preflight 计划逻辑，再回到真实页面重走整条链路。
- GREEN: promote-prod-release-environment-contract-fix-v13 -> PASS，源码仓 `20260621-release-preflight-environment-contract` 已按严格 TDD 完成修复：`release_preflight_plan.py` 把非目标环境迁移改为 `SKIP_ENV_NOT_ALLOWED`，dependency 环境范围不自洽由 migration policy gate fail-fast，build-release 统一打包跨环境 required SQL，deploy-release 改为从包内 `manifest.json` 读回真实 `allowedEnvironments`。目标回归命令 `test_release_preflight_plan.py/test_release_deploy_executor.py/test_release_migration_policy_gate.py/test_publish_int_ruoyi_to_test_tooling.py` 均已 `PASS`，实际运行的维护仓 `ops\deploy\publish-int-ruoyi.ps1` 与 `ops\release\*.py` 也已同步并通过文本契约核对。
- IN_PROGRESS: page-flow-full-rerun-required-after-v13 -> 本轮修复同时改变了 build-release 的跨环境 SQL 打包契约与 deploy-release/preflight 语义，因此不能继续沿用已构建完成的 `release-20260621-page-full-flow-v4` 当作“修复后的一次性走通”证据。下一步必须回到真实页面，从新的 release tag 重新执行 `构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服` 全链路。
- GREEN: rerun-preflight-v5 -> PASS，已重新读取 `release-build-preflight-lessons.md`、`release-backup-restore.md`、`server-access.md`、`project-error-prevention.md` 与 `login-access.md`，并确认 `Get-Command npx`、`Invoke-WebRequest http://127.0.0.1:48181/` 和 Playwright 会话 `frontend-release-full-flow` 均正常；允许继续从真实页面发起新的 `release-20260621-page-full-flow-v5` 全链路重跑。
- GREEN: build-release-preview-v5 -> PASS，Playwright 在真实页面切换到“构建发布包”，填写原因“页面真实发布全链路验证：v13环境契约修复后重建发布包并从测试服-正式服-备份服重跑”与 `releaseTag=release-20260621-page-full-flow-v5`，预览弹窗确认执行参数包含 `-Mode build-release -ReleaseTag release-20260621-page-full-flow-v5 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59`，未漂移到 `prod/backup/rollback/restore-data`。
- GREEN: build-release-submit-v5 -> PASS，Playwright 在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T063453670081300Z-d06ecbd1-508c-4014-a2fc-eb97e0b749e6`；页面操作记录已显示 `release / 构建发布包 / RUNNING / 命令已提交到本机执行队列`。
```

### Match 7 (lines 135-152)

```text
- GREEN: build-release-candidate-verify-v5 -> PASS，只读核对本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-v5` 后确认 `manifest.json` 的 `releaseTag/packageId` 均为 `release-20260621-page-full-flow-v5`，且 `release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-v5.tar` 已生成；页面刷新后操作记录也显示该 operation 为 `SUCCESS / 命令执行完成`。下一步继续在真实页面执行“部署测试服”。
- GREEN: deploy-test-preview-v5 -> PASS，Playwright 复用真实页面会话 `frontend-release-full-flow`，切换到“部署测试服”，填写原因“页面真实发布全链路验证：部署测试服（v5）”，预览命令确认目标环境为 `test`、发布标签为 `release-20260621-page-full-flow-v5`，参数未漂移到 `prod/backup/rollback/restore`。
- GREEN: deploy-test-submit-v5 -> PASS，Playwright 在真实页面点击“部署测试服”预览弹窗“执行”，生成 operation `op-2026-06-21T065051239510Z-922f4185-63ef-4e8b-9045-210a4298d355`；页面操作记录新增 `test / 部署发布包到测试服 / RUNNING / 命令已提交到本机执行队列`。
- GREEN: deploy-test-operation-v5 -> PASS，只读轮询 operation 状态文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T065051239510Z-922f4185-63ef-4e8b-9045-210a4298d355.json` 与本机日志 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T065051239510Z-922f4185-63ef-4e8b-9045-210a4298d355.log` 后确认：本轮真实页面测试服发布已最终 `SUCCESS`，日志显示跨环境 required SQL 已按修复后契约分别 `SKIPPED_ALREADY_APPLIED/APPLIED` 落库，随后完成远端 Quartz/showroom schema 检查、`backend/frontend` 容器重建、远端 readiness、scheduler smoke runtime 核对、发布锁释放 `LOCK_RELEASED` 与远端临时文件清理。
- GREEN: deploy-test-runtime-verify-v5 -> PASS，只读核对测试服 `172.30.30.58` 的 `/opt/intruoyi/runtime/.env` 为 `IMAGE_TAG=release-20260621-page-full-flow-v5`；`docker ps` 显示 `intruoyi-backend` 与 `intruoyi-frontend` 运行镜像均为 `release-20260621-page-full-flow-v5`；`http://172.30.30.58:48081/actuator/health`、`http://172.30.30.58:8081/` 与 `http://172.30.30.58:8081/pdfjs/pdf.worker.mjs` 均返回 HTTP `200`。下一步继续在真实页面执行“标记测试通过 -> 上线正式服 -> 上线备份服”。
- GREEN: mark-release-tested-preview-v5 -> PASS，Playwright 复用真实页面会话 `frontend-release-full-flow`，在“标记测试通过”填写原因“页面真实发布全链路验证：标记测试通过（v5）”、生产确认 `PROD`、验证结论“回归通过，允许上线正式服（v5）”，并通过页面下拉真实选中恢复点 `20260621-063218 · AVAILABLE`；预览弹窗确认本次执行 `publish-int-ruoyi.ps1 -Mode mark-tested -ReleaseTag release-20260621-page-full-flow-v5 -TestConclusion 回归通过，允许上线正式服（v5） -SelectedRecoverySetCandidateId restore:20260621-063218 ...`，参数未漂移到 `deploy-release/backup-now/rollback/restore-data`。
- GREEN: mark-release-tested-submit-v5 -> PASS，Playwright 在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T070744282571900Z-f9bdfe1e-7382-4a1d-979f-da8fc18335e5`；页面操作记录新增 `test / 标记测试通过 / RUNNING / 命令已提交到本机执行队列`。
- GREEN: mark-release-tested-operation-v5 -> PASS，只读轮询 operation 状态文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T070744282571900Z-f9bdfe1e-7382-4a1d-979f-da8fc18335e5.json` 与本机日志 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T070744282571900Z-f9bdfe1e-7382-4a1d-979f-da8fc18335e5.log` 后确认：该真实页面 `mark-tested` 已最终 `SUCCESS`，参数落库为 `releaseTag=release-20260621-page-full-flow-v5`、`selectedRecoverySetCandidateId=restore:20260621-063218`；日志确认 `Release package marked as tested: Backup/ReleasePackage/release-20260621-page-full-flow-v5`，并同步记录 `rollback-compatibility.json status=BLOCKED` 元数据。下一步继续在真实页面执行“上线正式服 -> 上线备份服”。
- GREEN: promote-prod-preview-v5 -> PASS，Playwright 复用真实页面会话 `frontend-release-full-flow`，在“上线正式服”保持 `releaseTag=release-20260621-page-full-flow-v5`、`targetEnvironment=正式服`、`prodConfirmText=PROD` 后点击“预览命令”；页面弹窗确认本次执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment prod -ReleaseTag release-20260621-page-full-flow-v5 -ConfirmText PROD -RequireTested -ProdDryRunEvidencePath D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-v5-preflight-release-dry-run.json ...`，参数未漂移到 `test/backup/rollback/restore-data`。
- GREEN: promote-prod-submit-v5 -> PASS，Playwright 在真实页面“上线正式服”预览弹窗点击“执行”，生成正式服真实 operation `op-2026-06-21T071527391565200Z-43bbbf19-75ce-473f-9747-5693c04947ff`；页面操作记录新增 `prod / 上线已验证发布包 / RUNNING / 命令已提交到本机执行队列`。
- BLOCKER: promote-prod-stale-release-lock-v5 -> operation `op-2026-06-21T071527391565200Z-43bbbf19-75ce-473f-9747-5693c04947ff` 最终 `FAILED`；只读核对状态文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T071527391565200Z-43bbbf19-75ce-473f-9747-5693c04947ff.json`、本机日志 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T071527391565200Z-43bbbf19-75ce-473f-9747-5693c04947ff.log` 与 dry-run 证据 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-v5-preflight-release-dry-run.json` 后确认：本次不是 `ProdDryRunEvidencePath` 缺失，也不是 preflight report-only 失败；`release-20260621-page-full-flow-v5-preflight-release-dry-run.json` 仍为 `status=passed`。真实执行在完成 `post-import.sql` 与 `infra_release_migration/infra_release_operation_lock` 引导后，于 `LOCK_ACQUIRED` 阶段直接失败。
- BLOCKER: promote-prod-stale-release-lock-root-cause-v5 -> 继续只读查询正式库 `infra_release_operation_lock` 后确认，当前 `target_environment='prod'` 仅存在 1 条锁记录且仍为旧链路 `operation_id=prod-release-20260621-page-full-flow-v4`、`release_tag=release-20260621-page-full-flow-v4`、`status=RUNNING`、`started_at=2026-06-21 13:04:44`、`finished_at=NULL`。这说明新的 `prod-release-20260621-page-full-flow-v5` 并不是在发布包内容阶段失败，而是被 v4 遗留的正式服发布锁阻断；下一步必须先按严格 TDD 修复发布锁生命周期并清理该陈旧锁，再回到真实页面继续“上线正式服 -> 上线备份服”。
- RED: `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_release_lock_cleanup.py -q` -> FAIL，新增“已持锁后 fail-fast 也必须释放发布锁”回归场景后，旧 `publish-int-ruoyi.ps1` 稳定复现 `2 failed`，证明 `Fail()` 直接 `exit 1` 会绕过外层 `try/catch` 并遗留 `infra_release_operation_lock`。
- GREEN: publish-release-lock-cleanup-fix-v5 -> PASS，在 `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\deploy\publish-int-ruoyi.ps1` 引入脚本级锁状态位 `$script:ReleaseOperationLockHeld/$script:ReleaseOperationLockReleasing`，并让 `Fail()` 在已持锁时先调用 `Invoke-ReleaseOperationLockRelease -Status 'FAILED' -ErrorMessage <message>` 再退出，从根因上收口“fail-fast 留锁”问题。
- GREEN: `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_release_lock_cleanup.py -q` -> PASS
- GREEN: `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_release_lock_cleanup.py D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_package_slimming.py D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_scheduler_smoke_release_config.py D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_showroom_release_sql_contract.py -q` -> PASS，相关回归共 `10 passed`。
- GREEN: prod-stale-lock-manual-cleanup-v5 -> PASS，只读确认当前不存在活跃中的本地同类发布进程后，已将正式库残留锁 `operation_id=prod-release-20260621-page-full-flow-v4` 手动从 `RUNNING` 收口为 `FAILED`，并补写 `finished_at=2026-06-21 15:36:30` 与 `error_message='manual stale-lock cleanup after release lock fail-fast bug fix for page-flow v5'`；该操作仅清理旧失败链路残留，不改动 `release-20260621-page-full-flow-v5` 包内容。
- GREEN: promote-prod-submit-retry-v5 -> PASS，Playwright 回到同一真实页面会话 `frontend-release-full-flow`，在“上线正式服”预览弹窗再次点击“执行”，生成新的正式服真实 operation `op-2026-06-21T073844572460600Z-694fba69-6b1c-4507-994e-9aac8f490123`。
```

### Match 8 (lines 159-165)

```text
- GREEN: promote-backup-progress-v5 -> PASS，只读轮询 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T075931265053700Z-7d81cab2-c347-4f49-8618-1427c837cf2f.json` 与对应本机 log 后确认：该真实页面备份服发布最初长时间停留在 backup smoke 阶段的 `'/opt/intruoyi/runtime/smoke/bin/npm' install --no-audit --no-fund`，随后继续推进并依次完成 Playwright smoke 运行时准备、`required-sql` 分发、`20260613_dcc_file_view_matrix_seed.sql` 与 `20260615_showroom_hall_canvas_background.sql` 登记/执行，说明此前“长时间无新日志”只是首次运行时镜像/依赖准备耗时，不是永久卡死。
- BLOCKER: promote-backup-required-sql-missing-scheduler-role-v5 -> operation `op-2026-06-21T075931265053700Z-7d81cab2-c347-4f49-8618-1427c837cf2f` 最终 `FAILED`；只读核对状态文件与本机日志后确认，失败点位于备份服 required SQL `20260618_post_release_role_e2e_gate.sql`。远端执行 `cat '/mnt/intruoyi-data/intruoyi-releases/release-20260621-page-full-flow-v5/required-sql/20260618_post_release_role_e2e_gate.sql' | docker exec -i intruoyi-mysql mysql ...` 时返回 `ERROR 1644 (45000) at line 226: Missing enabled scheduler role; cannot prepare zhaojie smart scheduling E2E account`。这说明当前新的真实页面阻塞不是页面提交流程、不是备份服发布锁残留，也不是 `v5` 包整体不可部署，而是备份服执行 post-release E2E gate 迁移时缺少“enabled scheduler role”前置条件，或该迁移对 `backup` 环境的 fail-fast 契约本身存在设计问题。
- GREEN: promote-backup-lock-release-v5 -> PASS，尽管 `20260618_post_release_role_e2e_gate.sql` 在备份服执行失败，修复后的 `publish-int-ruoyi.ps1` 仍已在同一 operation 尾部把 `target_environment='backup'` 的发布锁收口为 `FAILED` 并返回 `LOCK_RELEASED`；这保证后续定位并修复后可以继续从真实页面重新触发“上线备份服”。
- GREEN: backup-role-gate-root-cause-audit-v5 -> PASS，只读读取业务仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql\20260618_post_release_role_e2e_gate.sql`、`20260617_mes_scheduler_role_smart_scheduling_tab.sql`、相关契约测试与测试服/备份服真实库后确认：当前 SQL 目标租户是 `tenant_id=1 / 芋道源码`；测试服真实存在启用中的 `排产员` 角色，而备份服仅有 `showroom_publicity` 与 `wenkong`。父迁移 `20260617_mes_scheduler_role_smart_scheduling_tab.sql` 在“无目标角色”时本就 no-op，因此无法为备份服补出 admin 租户排产员角色；真正缺口是 `20260618_post_release_role_e2e_gate.sql` 对备份基线假设过强。
- RED: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> FAIL，业务仓新增合同 `test_post_release_role_gate_bootstraps_missing_scheduler_role_for_admin_tenant` 后，旧 SQL 稳定缺少 `INSERT INTO system_role` 自补齐逻辑，并保留 `Missing enabled scheduler role; cannot prepare zhaojie smart scheduling E2E account` 的硬失败语义。
- GREEN: backup-role-gate-scheduler-bootstrap-fix -> PASS，业务仓 `20260618_post_release_role_e2e_gate.sql` 已改为：缺角色时在 `tenant_id=1` 正式插入新的 `排产员` 角色并用 `LAST_INSERT_ID()` 回填；命中历史角色时统一启用、补齐基础字段并继续复用；不再把“缺排产员角色”直接当成备份服发布阻塞。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> PASS，11 passed。
```

### Match 9 (lines 167-171)

```text
- GREEN: `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，返回 `status=passed`。
- GREEN: `python C:\Users\BJB110\.codex\skills\bug-regression-fix-loop\scripts\validate_bug_regression.py --evidence D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260621-post-release-role-e2e-gate-backup-scheduler-role\bug-regression-evidence.md` -> PASS，业务仓缺陷回归证据结构有效。
- BLOCKER: backup-role-gate-rebuild-required-after-fix-v6 -> 本次修复改变了业务仓发布输入，当前 `release-20260621-page-full-flow-v5` 包不包含该 SQL 变更，不能继续拿它重试备份服。下一步必须回到真实页面重新构建新的 release tag，再从“部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服”整链重走，新的单次完整链路成功后才能视作本任务完成。
- GREEN: build-release-preview-v6 -> PASS，Playwright 复用真实页面会话 `frontend-release-full-flow`，在运行控制台切回“构建发布包”，填写原因“页面真实发布全链路验证：备份服角色gate修复后重建发布包并从测试服-正式服-备份服重跑”与 `releaseTag=release-20260621-page-full-flow-v6`，页面预览弹窗确认执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-v6 -Component intruoyi -SkipDatabaseSync -SkipMinioSync -TestServerHost 172.30.30.58 -BackupServerHost 172.30.30.59 ...`，参数未漂移到 `prod/backup/rollback/restore-data`。
- GREEN: build-release-submit-v6 -> PASS，Playwright 在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T084758011335300Z-cabf4fb6-0ce0-4f3c-930b-0b6a876caa10`；页面操作记录先显示 `RUNNING / 命令已提交到本机执行队列`，随后在刷新后收口为 `SUCCESS / 命令执行完成`。
```

### Match 10 (lines 173-181)

```text
- GREEN: build-release-candidate-verify-v6 -> PASS，只读核对本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-v6` 后确认 `required-sql/`、`resources/`、`runtime-env/`、`smoke/`、`manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-v6.tar` 已全部生成；operation log 也明确记录 `Release package built: release-20260621-page-full-flow-v6` 与 `NAS release path: Backup/ReleasePackage/release-20260621-page-full-flow-v6`。下一步继续在真实页面执行“部署测试服（v6） -> 标记测试通过（v6） -> 上线正式服（v6） -> 上线备份服（v6）”。
- GREEN: deploy-test-preview-v6 -> PASS，Playwright 复用真实页面会话 `frontend-release-full-flow`，切换到“部署测试服”，填写原因“页面真实发布全链路验证：部署测试服（v6）”，预览命令确认目标环境为 `test`、发布标签为 `release-20260621-page-full-flow-v6`，参数未漂移到 `prod/backup/rollback/restore`。
- GREEN: deploy-test-submit-v6 -> PASS，Playwright 在真实页面点击“部署测试服”预览弹窗“执行”，生成 operation `op-2026-06-21T090329614747700Z-cf86a6a0-e411-4ce2-a2fa-cdcb10bc2517`；页面操作记录新增 `test / 部署发布包到测试服 / RUNNING / 命令已提交到本机执行队列`。
- GREEN: deploy-test-operation-v6 -> PASS，只读轮询 operation 状态文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T090329614747700Z-cf86a6a0-e411-4ce2-a2fa-cdcb10bc2517.json` 与本机日志 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T090329614747700Z-cf86a6a0-e411-4ce2-a2fa-cdcb10bc2517.log` 后确认：本轮真实页面测试服发布已最终 `SUCCESS`，日志显示 `20260618_post_release_role_e2e_gate.sql` 与 `20260621_srm_phase45_simulated_execution.sql` 已正确 `APPLIED`，其他跨环境 SQL 继续按修复后契约 `SKIPPED_ALREADY_APPLIED` 落库；随后完成远端 Quartz/showroom schema 检查、`backend/frontend` 容器重建、远端 readiness、scheduler smoke runtime 核对、测试服发布锁释放 `LOCK_RELEASED` 与远端临时文件清理。
- GREEN: deploy-test-runtime-verify-v6 -> PASS，只读核对测试服 `172.30.30.58` 的 `/opt/intruoyi/runtime/.env` 为 `IMAGE_TAG=release-20260621-page-full-flow-v6`；`docker ps` 显示 `intruoyi-backend` 与 `intruoyi-frontend` 运行镜像均为 `release-20260621-page-full-flow-v6`；`http://172.30.30.58:48081/actuator/health`、`http://172.30.30.58:8081/` 与 `http://172.30.30.58:8081/pdfjs/pdf.worker.mjs` 均返回 HTTP `200`。下一步继续在真实页面执行“标记测试通过（v6） -> 上线正式服（v6） -> 上线备份服（v6）”。
- GREEN: mark-release-tested-preview-v6 -> PASS，Playwright 复用真实页面会话 `frontend-release-full-flow`，在“标记测试通过”填写原因“页面真实发布全链路验证：标记测试通过（v6）”、生产确认 `PROD`、验证结论“回归通过，允许上线正式服（v6）”，并通过页面下拉真实选中恢复点 `20260621-063218 · AVAILABLE`；预览弹窗确认本次执行 `publish-int-ruoyi.ps1 -Mode mark-tested -ReleaseTag release-20260621-page-full-flow-v6 -TestConclusion 回归通过，允许上线正式服（v6） -SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218 ...`，参数未漂移到 `deploy-release/backup-now/rollback/restore-data`。
- GREEN: mark-release-tested-submit-v6 -> PASS，Playwright 在真实页面预览弹窗点击“执行”，生成 operation `op-2026-06-21T091823235755100Z-c8d2d09d-d2a8-4982-952b-366613690af2`；页面操作记录新增 `test / 标记测试通过 / RUNNING / 命令已提交到本机执行队列`。
- GREEN: mark-release-tested-operation-v6 -> PASS，只读轮询 operation 状态文件 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-21T091823235755100Z-c8d2d09d-d2a8-4982-952b-366613690af2.json` 与本机日志 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\logs\op-2026-06-21T091823235755100Z-c8d2d09d-d2a8-4982-952b-366613690af2.log` 后确认：该真实页面 `mark-tested` 已最终 `SUCCESS`，参数落库为 `releaseTag=release-20260621-page-full-flow-v6`、`testConclusion=回归通过，允许上线正式服（v6）`、`selectedRecoverySetCandidateId=restore:20260621-063218`；日志确认 `Release package marked as tested: Backup/ReleasePackage/release-20260621-page-full-flow-v6`，并同步记录 `rollback-compatibility.json status=BLOCKED` 元数据。下一步继续在真实页面执行“上线正式服（v6） -> 上线备份服（v6）”。
- GREEN: promote-prod-preview-v6 -> PASS，Playwright 复用真实页面会话 `frontend-release-full-flow`，在“上线正式服”保持 `releaseTag=release-20260621-page-full-flow-v6`、`targetEnvironment=正式服`、`prodConfirmText=PROD` 后点击“预览命令”；页面弹窗确认本次执行 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment prod -ReleaseTag release-20260621-page-full-flow-v6 -ConfirmText PROD -RequireTested -ProdDryRunEvidencePath D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-v6-preflight-release-dry-run.json ...`，参数未漂移到 `test/backup/rollback/restore-data`。
```

### Match 11 (lines 186-188)

```text
- 当前结论：`release-20260621-page-full-flow-v6` 已在真实页面链路完成“构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服”，且正式服只读运行态与展厅受保护边界核验通过。下一步继续在同一页面会话执行“上线备份服（v6）”，以收齐本任务的一次性全链路证据。
- GREEN: promote-backup-preview-v6 -> PASS，Playwright 复用真实页面会话 `frontend-release-full-flow`，切换到“上线备份服”，将操作原因改为“页面真实发布全链路验证：上线备份服（v6）”，点击“预览命令”后确认页面弹窗执行参数为 `publish-int-ruoyi.ps1 -Mode deploy-release -Environment backup -ReleaseTag release-20260621-page-full-flow-v6 -ConfirmText PROD -RequireTested -ServerHost 172.30.30.59 -RemoteReleaseRoot /mnt/intruoyi-data/intruoyi-releases -RemoteDataRoot /mnt/intruoyi-data/runtime-data -RemoteDataDiskMount /mnt/intruoyi-data -RemoteDataDiskDevice /dev/mapper/cl-home ...`，未漂移到 `test/prod/rollback/restore-data`。
- GREEN: promote-backup-submit-v6 -> PASS，Playwright 在真实页面“上线备份服”预览弹窗点击“执行”，生成备份服真实 operation `op-2026-06-21T094430298907500Z-870bf604-f8f1-4b4d-a9a8-f193e5d6f9c2`；页面操作记录新增 `backup / 上线备份服务器 / RUNNING / 命令已提交到本机执行队列`。
```

### Match 12 (lines 191-192)

```text
- GREEN: promote-backup-showroom-boundary-verify-v6 -> PASS，按真实表 `infra_file` 做只读核验：`config_id=28 AND path LIKE 'showroom/%' AND url LIKE '%127.0.0.1:9000%'` 的记录数为 `0`，`config_id=28 AND path LIKE 'showroom/%' AND url LIKE 'http://172.30.30.59:9000/yudao/%'` 的记录数为 `1434`。这说明本轮备份服真实页面发布后，默认展厅受保护域边界同样未漂移到本机默认域。
- GREEN: final-page-flow-v6 -> PASS，`release-20260621-page-full-flow-v6` 已按真实页面链路一次性完整走通 `构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服`，过程中未用接口替代页面提交；此前所有新阻塞也都已遵循“先记录到任务文档，再修复，再从页面重走”的门禁。
```
## doc/tasks/20260620-frontend-release-full-flow/task.md

### Match 1 (lines 4-6)

```text

严格使用运行控制台前端页面，真实执行一次“构建发布包 -> 发布测试服务器 -> 发布正式服务器 -> 发布备份服务器”的全流程。过程中禁止用接口替代页面提交；如页面链路或后台链路出现问题，必须先记录到任务文档，修复后继续从页面重走，直到整条链路可以一次性走通。

```

### Match 2 (lines 10-12)

```text
- 状态：`COMPLETED`
- 处理：上一任务只做复盘与短记忆更新，不存在未收尾发布阻塞；本任务作为新的真实页面发布演练单独建档。

```

### Match 3 (lines 16-24)

```text
  - 正式走一遍构建发布到测试服务器、发布到正式服务器、发布到备份服务器的全流程
  - 必须使用页面前端进行操作
  - 禁止直接调用接口替代页面
  - 遇到问题先记录、修复后继续，直到全流程一次性走通
- 本任务边界：
  - 可使用本机终端做只读核验、日志排障、代码修复和必要重启
  - 不得用接口直接提交 build/deploy 动作替代页面按钮
  - 涉及真实服务器写入前，必须先在 `execution-log.md` 记录 `GREEN: experience-preflight -> PASS`

```

### Match 4 (lines 31-39)

```text
    - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 构建发布包必须通过运行控制台页面按钮提交，不得命令行替代页面产出正式候选包。
  - 发布验证不能只看健康检查，必须同时核 operation、manifest、远端 `IMAGE_TAG`/镜像、迁移状态和真实页面入口。
  - 正式环境发布前必须先补齐目标环境只读 preflight 证据并校验版本一致；缺证据或存在写动作直接阻塞。
  - 备份服必须显式使用 `/mnt/intruoyi-data` 相关参数，不得回退到 `/var/lib/docker` 默认路径。
  - 遇到发布链问题要先记录完整失败，再统一修复并重新从页面重走。

```

### Match 5 (lines 42-44)

```text
- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。所有页面链路阻塞都以正式修复运行控制台/发布脚本/契约为目标，不靠接口绕过完成。
- `是否存在临时补丁或绕过`：否。
```

### Match 6 (lines 47-50)

```text

- `BDD: 页面真实提交发布全链路 -> Given 运行控制台前端可访问 / When 用户在页面上依次执行构建发布包、发布测试服、发布正式服、发布备份服 / Then 每一步都必须由真实页面动作触发并最终成功。`
- `BDD: 页面链路失败必须记录并修复后重走 -> Given 任一步页面提交或后台执行失败 / When 排查和修复问题 / Then 必须先把失败与根因写入执行日志，再从页面重新走完整流程直到一次性通过。`

```

### Match 7 (lines 52-54)

```text

1. 建立任务文档并确认页面入口、经验门禁与高风险动作前置。`DONE`
2. 通过页面真实执行构建发布包并完成候选包核验。`DONE`
```

### Match 8 (lines 57-59)

```text
5. 通过页面真实发布备份服并验证成功。`DONE`
6. 汇总全流程问题、修复与最终一次性走通证据。`DONE`

```

### Match 9 (lines 65-67)

```text
- 正式服 `website` 数据边界未被破坏
- 遇到的每个问题都有失败记录、根因修复记录和重跑结果

```

### Match 10 (lines 69-94)

```text

IN_PROGRESS：已确认旧 tag `release-20260620-page-full-flow-v1` 的页面链路虽然曾跑通到“标记测试通过”，但用于正式服 dry-run 的本地缓存目录后来被同名后端单测夹具污染，因此必须改用新 tag `release-20260621-page-full-flow-v2` 从页面整条重跑。新 tag 首次页面构建 `op-2026-06-20T235144305204100Z-e8b0a823-14ad-4eb0-8f6b-6629f49a1c1b` 已确认因为源码仓 `yudao-server.jar` 被锁而失败；随后已按门禁提示执行 `D:\ProjectPackage\Int\IntRuoyi\restart-ruoyi-backend.bat` 解除该锁，并回到真实页面再次点击“构建发布包”，生成新的 operation `op-2026-06-20T235900978902100Z-cd7053fd-48c2-4f27-ad42-9ac8cf36baea`。
当前新 tag `release-20260621-page-full-flow-v2` 的页面构建 operation `op-2026-06-20T235900978902100Z-cd7053fd-48c2-4f27-ad42-9ac8cf36baea` 已最终 `SUCCESS`，并确认发布包已上传到 NAS `Backup/ReleasePackage/release-20260621-page-full-flow-v2`。过程中一度出现“前端 `vite build --mode test` 长时间无新日志”的现象；后续用独立 `vite --debug` 复现核对后，证实它属于高耗时长解析阶段而非永久失败，因此当前不再以“前端构建阻塞”作为主阻塞。
随后在真实页面执行“部署测试服”时，operation `op-2026-06-21T002749215627300Z-ceee763a-3578-4831-8ff5-c075d7295215` 被 required SQL `20260619_srm_d7_2_supplier_access_risk.sql` 阻断，根因已通过严格 TDD 复现并修复：D7-2 SQL 的页面路由幂等守卫把查询按钮误当成页面路由存在证据，导致缺失 `supplier-profile` 路由时跳过插入、随后又被 fail-fast 校验拦住。当前回归测试 `python -X utf8 -m pytest script\tests\test_srm_d7_d10_sql_contract.py -q` 与迁移门禁 `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` 已全部通过。
当前主阻塞已更新为新的真实页面测试服发布失败：`release-20260621-page-full-flow-v3` 的真实页面构建 operation `op-2026-06-21T024523486951200Z-fc58e07c-db7d-4604-8f5a-3539af0ad13d` 已最终 `SUCCESS`，并确认发布包已上传到 NAS `Backup/ReleasePackage/release-20260621-page-full-flow-v3`。随后回到真实页面执行“部署测试服”，operation `op-2026-06-21T030252892482500Z-0cf0dc70-5cbe-48bd-8d3c-740fbc777f96` 先成功执行 `20260619_srm_d7_2_supplier_access_risk.sql`，但在 required SQL `20260620_srm_phase1_supplier_access_profile.sql` 阶段失败：测试服真实 MySQL 返回 `ERROR 1064 (42000) ... near 'IF NOT EXISTS \`portal_contact_name\` varchar(64) ...'`。这说明当前阻塞根因不是页面提交流程，也不是上一轮 D7-2 修复未进包，而是 `20260620_srm_phase1_supplier_access_profile.sql` 直接采用 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`，与真实发布目标库的语法契约不兼容。下一步必须先按严格 TDD 修复该 SQL 的正式幂等写法，再重新从真实页面重走“构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服”。
现已在源码仓按严格 TDD 完成该阻塞修复：`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_srm_phase1_schema_sql.py -q` 已 `10 passed`，`python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` 已 `status=passed`。随后已通过真实页面重新构建新 release tag `release-20260621-page-full-flow-v4`，operation `op-2026-06-21T033855757114300Z-eeb75421-362d-407a-82b3-b0887b4491e0` 已最终 `SUCCESS`，并确认本地发布目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-v4` 与 NAS `Backup/ReleasePackage/release-20260621-page-full-flow-v4` 都已生成完整候选包。
当前 `release-20260621-page-full-flow-v4` 的真实页面测试服部署 operation `op-2026-06-21T035603828833Z-c1598389-017f-4d4e-8c9c-43fb3fea82e5` 也已最终 `SUCCESS`：本机 operation log 已确认 required SQL、远端 schema 检查、`backend/frontend` 容器重建、远端 readiness、scheduler smoke runtime 核对与发布锁释放全部通过；随后只读核对测试服 `/opt/intruoyi/runtime/.env`、运行容器镜像以及 `48081/8081/pdf.worker` 入口，均与 `release-20260621-page-full-flow-v4` 一致。因此当前待执行动作已推进为：必须在同一真实页面链路继续“标记测试通过 -> 上线正式服 -> 上线备份服”。
随后已在同一真实页面链路完成“标记测试通过”：Playwright 通过页面表单真实选择恢复点 `20260621-063218 · AVAILABLE`、预览确认 `-Mode mark-tested -ReleaseTag release-20260621-page-full-flow-v4 -SelectedRecoverySetCandidateId restore:20260621-063218` 后点击执行，生成 operation `op-2026-06-21T041405918994500Z-24330a04-ecfe-4786-8a55-8c95fc0e1f18`。只读核对状态文件与本机 log 后确认该 operation 已 `SUCCESS`，`release-20260621-page-full-flow-v4` 已被真实标记为测试通过。当前待执行动作继续推进为：必须在同一真实页面链路执行“上线正式服 -> 上线备份服”，并在每次新阻塞出现时先补执行日志再修复重走。
当前新的真实页面主阻塞已经通过严格 TDD 收口：此前 Playwright 在“上线正式服”点击“预览命令”时，页面直接返回 `正式 deploy precheck report-only 失败`，证据文件为 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-v4-deploy-precheck-report.json`。进一步核对已确认根因不是 build-release 时 manifest 漏写，而是 `RuntimeControlService#generateProdDryRunEvidence` 直接复用了 `local-cache/publish-int-ruoyi/<releaseTag>` 本地缓存目录；该目录在真实页面测试服部署后已被写入 `.env`、`post-import.sql`、`ops-runtime/`、`preflight-plan.json`、`preflight-target-state-test.json` 等运行期工件，导致正式 `report-only` 把这些部署期脏文件误判为“原始发布包未声明文件”。现已在维护仓后端完成正式 dry-run 隔离工作区修复，并通过 `RuntimeControlOriginalParityTest#promoteProdPreviewUsesSanitizedPackageWorkspace` 的 RED/GREEN 回归及整套 `RuntimeControlOriginalParityTest`。随后已重建本地维护控制台并回到同一真实页面链路继续重试“上线正式服”，页面预览与提交都已恢复可用，真实 operation `op-2026-06-21T050013146743700Z-46beb4fb-5f6c-4d2a-ba1c-4f1171a3f54b` 已成功由页面点击生成。
当前阻塞已在代码层收口：源码仓 `20260621-release-preflight-environment-contract` 已按严格 TDD 完成正式修复，维护仓真实运行脚本也已同步。修复内容包括：非目标环境迁移改为 `SKIP_ENV_NOT_ALLOWED`、dependency allowedEnvironments 必须是父迁移环境集合的子集、build-release 统一打包跨环境 required SQL、deploy-release 改为从包内 `manifest.json` 读回真实 `allowedEnvironments`。相关回归命令 `test_release_preflight_plan.py`、`test_release_deploy_executor.py`、`test_release_migration_policy_gate.py`、`test_publish_int_ruoyi_to_test_tooling.py` 与真实 SQL 树 migration policy gate 均已通过。
下一步必须回到真实页面，从新的 release tag 重新执行 `构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服`，以“修复后的单次完整链路”作为本任务最终完成证据；当前不能再把旧的 `release-20260621-page-full-flow-v4` 当作修复后全链路一次性走通的验收依据。
现已补读 `login-access.md`，并重新确认 `npx`、本机运行控制台 `http://127.0.0.1:48181/` 与 Playwright 会话 `frontend-release-full-flow` 仍可用。随后已在真实页面切回“构建发布包”，预览确认 `-Mode build-release -ReleaseTag release-20260621-page-full-flow-v5 -Component intruoyi -SkipDatabaseSync -SkipMinioSync ...` 参数正确，并点击“执行”生成 operation `op-2026-06-21T063453670081300Z-d06ecbd1-508c-4014-a2fc-eb97e0b749e6`。该 operation 现已最终 `SUCCESS`；本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-v5` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-v5.tar`，页面顶部操作记录也已刷新为 `SUCCESS / 命令执行完成`。当前下一步为继续在同一真实页面链路切到“部署测试服”，验证 `v5` 能否顺利进入测试环境。
现已在同一真实页面链路继续执行“部署测试服”：Playwright 预览确认 `targetEnvironment=test`、`releaseTag=release-20260621-page-full-flow-v5` 后点击“执行”，生成 operation `op-2026-06-21T065051239510Z-922f4185-63ef-4e8b-9045-210a4298d355`。只读轮询状态文件与本机 log 后确认该 operation 已最终 `SUCCESS`；日志显示远端 required SQL、Quartz/showroom schema 检查、`backend/frontend` 容器重建、scheduler smoke runtime 核对、发布锁释放与远端临时文件清理全部通过。随后再次只读核对测试服 `172.30.30.58` 的 `/opt/intruoyi/runtime/.env`、运行容器镜像与 `48081/8081/pdf.worker` 入口，均与 `release-20260621-page-full-flow-v5` 一致。因此当前真实页面链路已推进到：继续在同一会话执行“标记测试通过 -> 上线正式服 -> 上线备份服”，以 `v5` 作为修复后单次完整走通证据。
现已在同一真实页面链路完成“标记测试通过”：Playwright 通过页面表单真实填写原因“页面真实发布全链路验证：标记测试通过（v5）”、验证结论“回归通过，允许上线正式服（v5）”，并从页面恢复点下拉真实选中 `20260621-063218 · AVAILABLE`。预览弹窗确认本次将执行 `-Mode mark-tested -ReleaseTag release-20260621-page-full-flow-v5 -SelectedRecoverySetCandidateId restore:20260621-063218` 后点击“执行”，生成 operation `op-2026-06-21T070744282571900Z-f9bdfe1e-7382-4a1d-979f-da8fc18335e5`。只读核对状态文件与本机 log 后确认该 operation 已 `SUCCESS`，并已把 `release-20260621-page-full-flow-v5` 真实标记为测试通过，同时写入 `rollback-compatibility.json status=BLOCKED` 元数据。当前下一步为继续在同一真实页面链路执行“上线正式服 -> 上线备份服”。
现已在同一真实页面链路尝试“上线正式服（v5）”：Playwright 先在页面预览确认 `-Mode deploy-release -Environment prod -ReleaseTag release-20260621-page-full-flow-v5 -ConfirmText PROD -RequireTested -ProdDryRunEvidencePath D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-v5-preflight-release-dry-run.json ...`，随后点击“执行”生成 operation `op-2026-06-21T071527391565200Z-43bbbf19-75ce-473f-9747-5693c04947ff`。只读核对状态文件、本机 log 与 `release-20260621-page-full-flow-v5-preflight-release-dry-run.json` 后确认：本次失败不是正式 dry-run 证据缺失，也不是 releaseTag 未测试通过；dry-run 证据本身仍为 `status=passed`。实际执行在完成 target-bound `post-import.sql`、引导 `infra_release_migration/infra_release_operation_lock` 状态表后，于获取正式服发布锁阶段失败。
进一步只读查询正式库 `infra_release_operation_lock` 后确认，当前 `target_environment='prod'` 仅存在 1 条锁记录，且仍停留在旧链路 `operation_id=prod-release-20260621-page-full-flow-v4`、`release_tag=release-20260621-page-full-flow-v4`、`status=RUNNING`、`started_at=2026-06-21 13:04:44`、`finished_at=NULL`。这导致新的 `prod-release-20260621-page-full-flow-v5` 无法得到 `LOCK_ACQUIRED`，最终以 `命令退出码非 0: 1` 失败。当前新的正式服主阻塞已经收敛为“旧 v4 失败链路残留 prod 发布锁未释放”；下一步必须先按严格 TDD 修复正式服发布锁生命周期并清理该陈旧锁，再回到真实页面继续“上线正式服 -> 上线备份服”。若修复仅涉及维护控制台/发布脚本而不改变发布包内容，则继续以 `release-20260621-page-full-flow-v5` 作为同一页面链路的候选包重试。
现已按严格 TDD 收口正式服残留锁问题：在 `D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_release_lock_cleanup.py` 先新增“持锁后 fail-fast 也必须释放发布锁”的回归用例，`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_release_lock_cleanup.py -q` 先稳定 `2 failed` 复现；随后在 `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\deploy\publish-int-ruoyi.ps1` 修复 `Fail()` 路径，使其在已持锁时先调用 `Invoke-ReleaseOperationLockRelease -Status 'FAILED'` 再退出，并补上脚本级锁持有/释放状态位保护。修复后同一回归已 `PASS`，联同 `test_release_package_slimming.py`、`test_scheduler_smoke_release_config.py`、`test_showroom_release_sql_contract.py` 的相关回归一并 `10 passed`。随后只读确认当前无活动中的同类本地发布进程后，已将正式库残留锁 `prod-release-20260621-page-full-flow-v4` 从 `RUNNING` 手动收口为 `FAILED`，并记录 `error_message='manual stale-lock cleanup after release lock fail-fast bug fix for page-flow v5'`，从而为同一真实页面链路的正式服重试清空阻塞。
清理陈旧锁后，已回到同一真实页面会话继续“上线正式服（v5）”并再次点击预览/执行，生成新的真实 operation `op-2026-06-21T073844572460600Z-694fba69-6b1c-4507-994e-9aac8f490123`。只读轮询状态文件与本机 log 后确认：该 operation 已真实完成生产包同步、required SQL 登记/执行、Quartz/showroom schema 检查、`backend/frontend` 容器重建、远端 readiness、scheduler smoke runtime 核对、NAS 发布历史写入、发布锁释放与远端临时文件清理，最终收口为 `SUCCESS`。随后再次只读核对正式服 `172.30.30.57` 的 `/opt/intruoyi/runtime/.env`、运行容器镜像、`48081/8081/pdf.worker` 入口以及展厅受保护边界，结果分别为 `IMAGE_TAG=release-20260621-page-full-flow-v5`、`intruoyi-backend/intruoyi-frontend` 都运行在 `release-20260621-page-full-flow-v5`、三条 HTTP 入口均返回 `200`、`config_id=28 AND path LIKE 'showroom/%'` 下 `url LIKE '%127.0.0.1:9000%'` 的漂移记录数为 `0` 且 `url LIKE 'http://172.30.30.57:9000/yudao/%'` 的受保护记录数为 `1434`。因此当前里程碑已推进为：正式服真实页面发布和只读核验均已完成，下一步继续在同一真实页面链路执行“上线备份服”，随后汇总 `v5` 的整条一次性走通证据。
现已在同一真实页面链路尝试“上线备份服（v5）”：Playwright 先在页面预览确认 `-Mode deploy-release -Environment backup -ReleaseTag release-20260621-page-full-flow-v5 -ConfirmText PROD -RequireTested -ServerHost 172.30.30.59 -RemoteReleaseRoot /mnt/intruoyi-data/intruoyi-releases -RemoteDataRoot /mnt/intruoyi-data/runtime-data -RemoteDataDiskMount /mnt/intruoyi-data -RemoteDataDiskDevice /dev/mapper/cl-home ...`，随后点击“执行”生成 operation `op-2026-06-21T075931265053700Z-7d81cab2-c347-4f49-8618-1427c837cf2f`。只读轮询状态文件与本机 log 后确认，该 operation 在备份服 required SQL `20260618_post_release_role_e2e_gate.sql` 阶段失败：远端 MySQL 返回 `ERROR 1644 (45000) ... Missing enabled scheduler role; cannot prepare zhaojie smart scheduling E2E account`，随后发布锁已按修复后的生命周期收口为 `FAILED`。这说明当前新的主阻塞不是页面提交、不是发布锁残留，也不是 `release-20260621-page-full-flow-v5` 包在测试/正式环境下不可用，而是备份服在执行 post-release E2E gate 迁移时缺少“enabled scheduler role”前置条件，或该迁移对备份环境的 fail-fast 契约本身存在设计缺陷。下一步必须先把该阻塞按严格 TDD/缺陷合同收口清楚，再回到真实页面继续“上线备份服”，以拿到单次完整链路最终成功证据。
现已在业务源码仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 按严格 TDD 收口该阻塞：新任务 `doc/tasks/20260621-post-release-role-e2e-gate-backup-scheduler-role/` 已确认根因是 `20260618_post_release_role_e2e_gate.sql` 默认 `tenant_id=1 / 芋道源码` 预先存在启用中的排产员角色，而备份服真实基线只有 `showroom_publicity` 与 `wenkong`。修复后该 SQL 会在缺角色时正式插入新的 `排产员` 角色，在命中历史角色时统一启用并继续复用；相关 `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q`、`python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py script\tests\test_mes_scheduler_role_smart_scheduling_tab_sql.py -q` 与 `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` 均已通过。由于本次修复改变了业务仓发布输入，当前 `release-20260621-page-full-flow-v5` 包不包含该 SQL 变更，不能继续拿它重试备份服；下一步必须回到真实页面，用新的 release tag 从“构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服”整链重走，新的单次链路成功才算本任务完成。
现已按该约束回到同一真实页面会话 `frontend-release-full-flow`，使用新的 release tag `release-20260621-page-full-flow-v6` 重建候选包。页面预览确认本次执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-v6 -Component intruoyi -SkipDatabaseSync -SkipMinioSync ...`，随后点击“执行”生成 operation `op-2026-06-21T084758011335300Z-cabf4fb6-0ce0-4f3c-930b-0b6a876caa10`。只读轮询页面、状态文件与本机日志后确认：该 operation 已真实完成 backend `mvn ... clean package`、前端 `vite build --mode test`、backend Docker 镜像构建、迁移 policy gate、NAS 上传等完整链路，并最终收口为 `SUCCESS`。当前本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-v6` 已生成 `manifest.json`、`release-manifest.json`、`intruoyi-images_release-20260621-page-full-flow-v6.tar` 等关键产物，日志也确认 NAS 路径为 `Backup/ReleasePackage/release-20260621-page-full-flow-v6`。因此当前真实页面下一步已推进为：继续在同一会话执行“部署测试服（v6） -> 标记测试通过（v6） -> 上线正式服（v6） -> 上线备份服（v6）”，以 `v6` 作为修复后单次完整链路的最终验收对象。
现已在同一真实页面链路继续执行“部署测试服（v6）”：Playwright 预览确认 `targetEnvironment=test`、`releaseTag=release-20260621-page-full-flow-v6` 与原因“页面真实发布全链路验证：部署测试服（v6）” 后点击“执行”，生成 operation `op-2026-06-21T090329614747700Z-cf86a6a0-e411-4ce2-a2fa-cdcb10bc2517`。随后只读轮询状态文件与本机 log 后确认该 operation 已最终 `SUCCESS`；日志显示 `20260618_post_release_role_e2e_gate.sql`、`20260621_srm_phase45_simulated_execution.sql` 等 required SQL 已正确 `APPLIED/SKIPPED_ALREADY_APPLIED`，并完成远端 Quartz/showroom schema 检查、`backend/frontend` 容器重建、HTTP readiness、scheduler smoke runtime 核对、测试服发布锁释放与远端临时文件清理。继续只读核对测试服 `172.30.30.58` 的 `/opt/intruoyi/runtime/.env`、运行镜像与 `48081/8081/pdf.worker` 入口，均与 `release-20260621-page-full-flow-v6` 一致。因此当前真实页面链路已推进到：继续在同一会话执行“标记测试通过（v6） -> 上线正式服（v6） -> 上线备份服（v6）”，以 `v6` 作为修复后单次完整链路的最终验收对象。
现已在同一真实页面链路继续执行“标记测试通过（v6）”：Playwright 在页面真实填写原因“页面真实发布全链路验证：标记测试通过（v6）”、验证结论“回归通过，允许上线正式服（v6）”，并从恢复点下拉真实选中 `20260621-063218 · AVAILABLE`。预览弹窗确认将执行 `publish-int-ruoyi.ps1 -Mode mark-tested -ReleaseTag release-20260621-page-full-flow-v6 -TestConclusion 回归通过，允许上线正式服（v6） -SelectedRecoverySetCandidateId restore:20260621-063218 ...`，随后点击“执行”生成 operation `op-2026-06-21T091823235755100Z-c8d2d09d-d2a8-4982-952b-366613690af2`。只读轮询状态文件与本机 log 后确认该 operation 已 `SUCCESS`，并把 `release-20260621-page-full-flow-v6` 真实标记为测试通过，同时写入 `rollback-compatibility.json status=BLOCKED` 元数据。因此当前真实页面下一步已推进为：继续在同一会话执行“上线正式服（v6） -> 上线备份服（v6）”，以 `v6` 作为修复后单次完整链路的最终验收对象。
现已在同一真实页面链路继续执行“上线正式服（v6）”：Playwright 先在页面预览确认 `-Mode deploy-release -Environment prod -ReleaseTag release-20260621-page-full-flow-v6 -ConfirmText PROD -RequireTested -ProdDryRunEvidencePath D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-v6-preflight-release-dry-run.json ...`，随后通过真实弹窗点击“执行”，生成 operation `op-2026-06-21T092843334367500Z-223e010b-722c-4d05-ba35-887515eba339`。只读轮询状态文件与本机 log 后确认：该 operation 已真实完成生产包同步、required SQL 登记/执行、Quartz/showroom schema 检查、`backend/frontend` 容器重建、HTTP readiness、scheduler smoke runtime 核对、NAS 发布历史写入、发布锁释放与远端临时文件清理，最终收口为 `SUCCESS`。随后再次只读核对正式服 `172.30.30.57` 的 `/opt/intruoyi/runtime/.env`、运行镜像、`48081/8081/pdf.worker` 入口以及展厅受保护边界；其中运行态分别为 `IMAGE_TAG=release-20260621-page-full-flow-v6`、`intruoyi-backend/intruoyi-frontend` 都运行在 `release-20260621-page-full-flow-v6`、三条 HTTP 入口均返回 `200`。展厅边界核验时先 `DESCRIBE infra_file_config` 确认该表不含 `config_id/path/url`，随后按真实表 `infra_file` 只读查询得到：`config_id=28 AND path LIKE 'showroom/%' AND url LIKE '%127.0.0.1:9000%'` 的漂移记录数为 `0`，`url LIKE 'http://172.30.30.57:9000/yudao/%'` 的受保护记录数为 `1434`。因此当前里程碑已推进为：`release-20260621-page-full-flow-v6` 的正式服真实页面发布和只读核验均已完成，下一步继续在同一真实页面链路执行“上线备份服（v6）”，随后汇总单次完整链路证据。
现已在同一真实页面链路继续执行“上线备份服（v6）”：Playwright 先在页面预览确认 `-Mode deploy-release -Environment backup -ReleaseTag release-20260621-page-full-flow-v6 -ConfirmText PROD -RequireTested -ServerHost 172.30.30.59 -RemoteReleaseRoot /mnt/intruoyi-data/intruoyi-releases -RemoteDataRoot /mnt/intruoyi-data/runtime-data -RemoteDataDiskMount /mnt/intruoyi-data -RemoteDataDiskDevice /dev/mapper/cl-home ...`，随后通过真实弹窗点击“执行”，生成 operation `op-2026-06-21T094430298907500Z-870bf604-f8f1-4b4d-a9a8-f193e5d6f9c2`。只读轮询状态文件与本机 log 后确认：该 operation 已真实完成备份服 required SQL 登记/执行、Quartz/showroom schema 检查、`backend/frontend` 容器重建、HTTP readiness、scheduler smoke runtime 核对、NAS 发布历史写入、发布锁释放与远端临时文件清理，最终收口为 `SUCCESS`。此前阻断 `v5` 的 `20260618_post_release_role_e2e_gate.sql` 与其后一组 `post_release_role_e2e_gate_smoke_*` SQL 均已在本轮真实页面链路中正确 `APPLIED`。随后再次只读核对备份服 `172.30.30.59` 的 `/opt/intruoyi/runtime/.env`、运行镜像、`48081/8081/pdf.worker` 入口以及展厅受保护边界；其中运行态分别为 `IMAGE_TAG=release-20260621-page-full-flow-v6`、`intruoyi-backend/intruoyi-frontend` 都运行在 `release-20260621-page-full-flow-v6`、三条 HTTP 入口均返回 `200`，且按真实表 `infra_file` 只读查询得到：`config_id=28 AND path LIKE 'showroom/%' AND url LIKE '%127.0.0.1:9000%'` 的漂移记录数为 `0`，`url LIKE 'http://172.30.30.59:9000/yudao/%'` 的受保护记录数为 `1434`。COMPLETED：`release-20260621-page-full-flow-v6` 已按“页面前端点击操作”的真实流程一次性完整走通 `构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服`，过程中未用接口替代页面提交；本任务所遇阻塞也都已先记录、再修复、再从页面重走，并形成最终通过证据。

```
## docs/request-command-log.md

### Match 1 (lines 4-12)

```text

- 用户需求：执行 `$fupan`，把本轮“测试服发布 + 三角色真实验收 + 正式服预发布阻塞”沉淀为可复用经验，避免后续重复踩坑。
- 命中技能：`C:\Users\BJB110\.codex\skills\fupan\SKILL.md`。
- 命令记录：读取 `SKILL.md`、当前任务 `task.md`、`execution-log.md`，确认本轮已有足够证据支撑复盘。
- 命令记录：读取 `references/project-memory-template.md`、既有 `docs/agent-memory/project-error-prevention.md` 与 `docs/request-command-log.md`，按“项目级规则 / 任务专项细节”拆分候选经验。
- 命令记录：运行 `python -X utf8 C:\Users\BJB110\.codex\skills\fupan\scripts\collect_error_evidence.py --project-root D:\ProjectPackage\Int\IntRuoyiMaintance --glob doc\tasks\20260620-prod-release-current-latest\task.md --glob doc\tasks\20260620-prod-release-current-latest\execution-log.md --glob AGENTS.md --output D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-prod-release-current-latest\candidate-error-evidence.md`，生成本轮候选证据。
- 命令记录：尝试运行 `update_project_memory.py` 追加“正式服 Smart Release prod preflight 证据闭合”规则，被脚本拒绝，原因是该条目目前仍偏本次发布链专项规则，不属于项目级通用短记忆。
- 结论记录：本轮 `$fupan` 接受的长期经验仍是“发布前预检”“发布验证多证据闭环”“先全量记录失败再统一修复复测”三类；`ProdDryRunEvidencePath / target config / NasConfigPath` 保留在当前任务文档，不提升到 `AGENTS.md` 或项目级记忆；页面脚本细节不进入长期记忆。

```

### Match 2 (lines 14-20)

```text

- 用户需求：正式按页面前端点击操作的真实流程，完整走一遍构建发布到测试服、正式服、备份服；过程中禁止直接调接口替代页面动作；遇到问题先记录任务文档，修复后继续从页面重走，直到整条流程一次性走通。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`。
- 命令记录：核对上一维护仓任务 `doc/tasks/20260620-fupan-prod-release-v7/task.md` 已 `COMPLETED`，允许开启新任务 `doc/tasks/20260620-frontend-release-full-flow/`。
- 命令记录：读取并确认当前任务 `task.md`、`execution-log.md` 已落地 `BDD` 场景、`设计约束检查`、`经验门禁` 与 `GREEN: experience-preflight -> PASS`。
- 命令记录：尝试按 `control-in-app-browser` 技能接入应用内浏览器，`node_repl/js` 返回环境级错误 `missing field sandboxPolicy`；该问题已记录到当前任务 `execution-log.md`，不属于页面业务链路问题。
- 命令记录：只读验证 `http://127.0.0.1:48181/` 返回 `200`；核对维护仓前端打包产物与源码，确认运行控制台真实存在“构建发布包 / 部署测试服 / 上线正式服 / 上线备份服”按钮、预览命令弹窗和执行弹窗。
```

### Match 3 (lines 26-28)

```text
- 计划边界：仅发布测试服 `172.30.30.58`，远端目录 `/opt/intruoyi/runtime`；发布范围为 `code-only`，不访问正式服/备用服，不执行备份、恢复、回滚或正式服动作。
- 命中经验：`release-backup-restore.md`、`server-access.md`、`login-access.md`；真实 E2E 和服务器写入前必须记录 `experience-preflight`。
- 命令记录：检查 `npx` 可用，路径为 `D:\Programs\npx.ps1`。
```

### Match 4 (lines 36-39)

```text
- 命令记录：Playwright 点击构建发布包“执行”，operation `op-2026-06-17T072458143463800Z-0d5a0145-9253-4018-991a-55bf864264ef` 初始状态 `RUNNING`。
- 命令记录：构建 operation 最终 `FAILED`；后端 Maven、前端 Vite build、后端 Docker 镜像构建成功，前端 Docker 镜像构建失败，原因是拉取 `nginx:1.27-alpine` 元数据时 Docker Hub token 请求超时。
- 阻塞记录：发布包未成功生成，禁止继续发布测试服；下一步先补齐/验证 Docker 基础镜像 `nginx:1.27-alpine`。
- 命令记录：`docker pull nginx:1.27-alpine` PASS，digest `sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`。
```

### Match 5 (lines 41-44)

```text
- 命令记录：Playwright 点击第二次构建发布包“执行”，operation `op-2026-06-17T073818610888200Z-832a7d6b-133a-45ed-abd9-84dd1abfd300` 初始状态 `RUNNING`。
- 命令记录：第二次构建 operation 仍 `FAILED`；Maven、Vite、后端镜像和前端镜像成功，发布迁移策略门禁失败，原因是 `20260617_dcc_browser_performance_indexes` 依赖缺失 `20260513_dcc_base_schema.sql`。
- 阻塞记录：发布包 manifest 未生成，禁止继续发布测试服；需要先修复迁移元数据/扫描集合。
- 命令记录：在 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 修正 `sql/mysql/20260617_dcc_browser_performance_indexes.sql` 首行 `dependsOn` 为清单实际使用的迁移 ID `20260513_dcc_base_schema`。
```

### Match 6 (lines 48-50)

```text
- 命令记录：Playwright 点击第三次构建发布包“执行”，operation `op-2026-06-17T082753879349700Z-c7f3f523-d9c6-4077-9b0f-eacc6cf5bf73` 初始状态 `RUNNING`。
- 命令记录：第三次构建 operation `FAILED`；Maven 在 `yudao-module-dcc` 执行 clean 时无法删除 `target`，发布包未生成，禁止发布测试服。
- 命令记录：`mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -DskipTests clean` PASS，DCC target 清理前置恢复。
```

### Match 7 (lines 52-54)

```text
- 命令记录：Playwright 点击第四次构建发布包“执行”，operation `op-2026-06-17T083241295814300Z-dc21fdce-0784-4465-a8d8-7e6ceb485990` 初始状态 `RUNNING`。
- 命令记录：第四次构建 operation `FAILED`；Maven、Vite build、后端 Docker 镜像成功，前端 Docker 镜像解析 `nginx:1.27-alpine` 元数据时 Docker Hub 返回 EOF，发布包未生成，禁止发布测试服。
- 命令记录：`docker pull nginx:1.27-alpine` PASS，digest `sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`，本地 `docker image inspect` PASS。
```

### Match 8 (lines 56-59)

```text
- 命令记录：Playwright 点击第五次构建发布包“执行”，operation `op-2026-06-17T084524861642300Z-d778ee83-bb2c-44c5-896d-b1ffed69814a` 初始状态 `RUNNING`。
- 命令记录：第五次构建 operation `FAILED`；发布脚本在 Maven clean 前检测到本机 `yudao-server.jar` 被 Java 进程锁定。
- 命令记录：`restart-ruoyi-backend.bat` 已把本机后端切换到 `E:\Int\CacheData\IntRuoyi\runtime\backend-20260617-164706.jar`，尽管应用最终因定时任务同步失败退出，但目标 jar 锁已解除。
- 命令记录：`mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-server -DskipTests clean` PASS，确认 `yudao-server.jar` 锁前置已恢复。
```

### Match 9 (lines 69-71)

```text
- 命令记录：测试服 `infra_release_migration` 中 `20260617_dcc_browser_performance_indexes` 最新状态为 `APPLIED`。
- 命令记录：Playwright 打开 `http://172.30.30.58:8081/`，HTTP 200，跳转到 `/login?redirect=/index`，页面标题为 `瑛泰管理系统 - 登录`，未发现 console error。
- 命令记录：`task-closeout-cleanup --mode preview` PASS，仅计划删除 `runtime-control-start.out.log` 与 `runtime-control-start.err.log`。
```

### Match 10 (lines 77-83)

```text
- 计划边界：只新增本机双击入口；不执行真实重启、不操作服务器、不 SSH、不写入数据库或对象存储。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`，正式服默认禁止操作，远端重启必须有当前任务授权；本任务仅本机入口。
- 命令记录：读取 `scripts\start.ps1`、`scripts\dev-frontend.ps1`、`scripts\dev-backend.ps1`、`ops\deploy\restart-int-ruoyi-local.ps1` 与远端 bat，确认现有脚本入口。
- 命令记录：只读解析当前维护仓库 `ops\deploy\worktree-port-map.ps1` 失败，错误为缺少 `D:\ProjectPackage\Int\yudao-ui-admin-vue3`。
- 命令记录：只读解析原 IntRuoyi `worktree-port-map.ps1` 成功，`int_main` 映射到 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`、`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`、端口 `8081/48081`。
- 命令记录：`RED` 检查 `restart-frontend-backend.bat` 不存在，按预期失败。
- 命令记录：新增 `restart-frontend-backend.bat`，默认调用原 IntRuoyi 本机重启脚本 `-Component full`。
```

### Match 11 (lines 86-88)

```text
- 命令记录：`git diff --check` PASS，仅有既有换行提示。
- 命令记录：`task-closeout-cleanup --mode preview` PASS，无删除项、无阻塞、无警告。
- 结论记录：已完成本机双击重启入口；验证阶段未执行真实重启、远端操作或数据写入。
```

### Match 12 (lines 93-95)

```text
- 计划边界：只做静态审计和本地契约验证；不执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`，运行控制台相关发布包、tested、恢复候选、DCC 链和 manifest/checksum 证据必须 fail fast；`D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`，本次不改 UI，只审计前端契约。
- 命令记录：结构化解析 controller mapping，standalone 与 original 均为 33 个规范化 HTTP 路径，差异集为空。
```
