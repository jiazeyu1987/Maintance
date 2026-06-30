# Candidate Error Prevention Evidence

- Generated At: 2026-06-20T10:34:11
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
## doc/tasks/20260618-post-release-role-e2e-gate/execution-log.md

### Match 1 (lines 2-12)

```text

BDD: gaomin 展厅角色验收 -> Given 测试服发布完成且 gaomin 登录芋道源码租户 / When 打开管理前端 / Then 只看到展厅页签，并且展厅每个子页签访问无页面错误、网络错误或控制台错误。
BDD: zhaojie 智能排产角色验收 -> Given 测试服发布完成且 zhaojie 登录芋道源码租户 / When 打开管理前端并进入智能排产 / Then 只看到智能排产页签，并且智能排产冒烟测试可运行直到结束。
BDD: wangsiyu DCC角色验收 -> Given 测试服发布完成且 wangsiyu 登录芋道源码租户 / When 打开管理前端 / Then 只看到DCC文控中心页签，并且DCC文控中心每个子页签访问无页面错误、网络错误或控制台错误。
BDD: 失败统一修复发布复测 -> Given 三角色验收发现错误 / When 全部错误记录完成 / Then 统一修复、重新构建发布到测试服并完整复测三角色，直到全部通过。

- 用户需求：发布后在测试服务器按 `gaomin`、`zhaojie`、`wangsiyu` 三个芋道源码租户账号完成权限页签与页面访问验收；失败先统一记录，全部跑完后统一修复、构建发布、部署测试服并复测到通过。
- GREEN: experience-preflight -> PASS，已读取 `docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`docs/agent-memory/project-error-prevention.md`；用户本次明确授权测试服真实登录 E2E，范围仅限 `172.30.30.58` 和三个指定账号。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，首次脚本未收敛权限接口等待异常；修正后继续。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，真实测试服 E2E 证据 `evidence/post-release-role-e2e-1781790390014.json`：`gaomin` 登录业务码 500，后端日志为账号密码不正确；`zhaojie` 顶层菜单为 `MES 系统` 且缺 `智能排产` 根页签；`wangsiyu` DCC 审批任务页 BPM 待办接口 `Access Denied`。
- GREEN: root-cause-readonly-db -> PASS，只读核对测试服：`gaomin` 在 `芋道源码(tenant_id=1)` 缺用户记录；`zhaojie` 绑定排产员角色但角色菜单仍有 `MES 系统(5100)`，`智能排产(900120)` 的 `parent_id=5100`；`wangsiyu` 绑定 `wenkong` 角色但缺 `bpm:task:query` 权限菜单 `1221`。
```

### Match 2 (lines 15-21)

```text
- GREEN: `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，`migrationCount=151`，包含 `20260618_post_release_role_e2e_gate`。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781797026325.json`：`gaomin` 展厅公司页图片 `/admin-api/infra/file/28/get/20260521/开园活动图-压缩版.jpg` 返回非图片；展厅产品页缺表 `showroom_product_revision_attachment`；展厅大厅页缺字段 `showroom_hall.canvas_background_image_url`；`zhaojie` 生产排产页缺 `mes:pro-work-order:query` 权限，智能排产冒烟缺 `MES_SMOKE_CAPACITY_MODE` 等必填运行变量。
- GREEN: root-cause-readonly-db -> PASS，测试服只读核对：`sql/showroom/20260605_showroom_product_revision_attachment_schema.sql` 和 `sql/showroom/20260615_showroom_hall_canvas_background.sql` 未纳入发布 required SQL；`publish-int-ruoyi.ps1` 的 smoke env 默认值为空；`ragflow_compose-minio-1` 缺少 `20260521/开园活动图-压缩版.jpg`，本机源 `docker-minio-1` 存在该对象。
- BDD: 展厅运行态 schema 发布契约 -> Given 代码已访问展厅产品附件表和大厅背景字段 / When 构建发布包并部署测试服 / Then required SQL 必须包含对应 showroom schema，部署后端启动前 preflight 缺表或缺字段必须 fail fast。
- BDD: 智能排产冒烟发布契约 -> Given zhaojie 触发真实智能排产冒烟 / When 发布脚本写入测试服运行 `.env` 并应用权限迁移 / Then smoke 必填变量、四个非 admin 真实账号、Excel 报工人和审批人、API 权限均存在。
- RED: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py script\tests\test_scheduler_smoke_release_contract.py script\tests\test_showroom_release_sql_contract.py script\tests\test_publish_int_ruoyi_to_test_tooling.py script\tests\test_showroom_product_revision_attachment_sql.py script\tests\test_showroom_sql_scripts.py -q` -> FAIL，新增契约尚未实现。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py script\tests\test_scheduler_smoke_release_contract.py script\tests\test_showroom_release_sql_contract.py script\tests\test_publish_int_ruoyi_to_test_tooling.py script\tests\test_showroom_product_revision_attachment_sql.py script\tests\test_showroom_sql_scripts.py -q` -> PASS，112 passed。
```

### Match 3 (lines 27-38)

```text

- 用户需求：刚刚线程中断，继续发布后三角色测试服门禁；发布后在测试服务器用 `芋道源码` 租户账号 `gaomin`、`zhaojie`、`wangsiyu` 全量验证，失败先全部记录，统一修复后重新构建发布到测试服并复测直到通过。
- GREEN: experience-preflight -> PASS，已重新读取 `docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`docs/agent-memory/project-error-prevention.md`；用户本次明确授权测试服 `172.30.30.58`、`芋道源码` 租户和三个指定账号真实 E2E，禁止正式服、备份服、备份、恢复、回滚、mock 或接口绕过。
- GREEN: resume-evidence-read -> PASS，最新构建/部署 evidence `runtime-console-build-deploy-1781803561178.json` 为 PASS，releaseTag `release-20260619-0112-role-e2e-gate-utf8-smoke-env`；最新真实 E2E evidence `post-release-role-e2e-1781826823171.json` 为 FAIL，4 failures。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781826823171.json`：`gaomin` 仅见 `展厅` 但产品管理页 16 个产品封面接口返回 200 空 JSON/非图片并显示 `加载失败`；`zhaojie` 仅见 `智能排产` 但 `/mes/pro/task` 调用 dependencies GET 时 URL 过长返回 414，工作台通知未读请求被中断，冒烟测试失败；`wangsiyu` 仅见 `DCC文控中心` 且 16 个 DCC 子页通过。
- BDD: 智能排产依赖查询长范围契约 -> Given 生产排产页会加载数百个工单范围 / When 查询甘特图依赖线 / Then 前端必须用 POST JSON body 提交 `workOrderIds/taskIds`，后端必须接受 request body，禁止因 URL 过长返回 414。
- BDD: 智能排产冒烟账号登录契约 -> Given smoke runner 需要三类非 admin 真实账号 / When 发布脚本写入 `.env` 并 SQL 准备账号 / Then 用户名必须符合登录校验 `^[a-zA-Z0-9]{4,30}$`，不得使用下划线账号导致登录 validation 失败。
- BDD: 展厅产品封面对象一致性修复 -> Given `infra_file.config_id=28` 中 154 条 `showroom/product/cover/20260602/%` 引用 / When 测试服 MinIO 缺失对应对象 / Then 只能用真实同名对象补齐默认 bucket 路径，不改 protected config、不改域名、不放占位图。
- RED: `mvn -pl yudao-module-mes -Dtest=MesProAutoScheduleControllerContractTest test` -> FAIL，新增 controller 契约编译失败：`getDependencies(MesProAutoScheduleDependencyReqVO)` 尚不存在。
- RED: `node tests\e2e\mes-auto-schedule-dependency-post-static.spec.js` -> FAIL，前端依赖查询仍使用 GET query params。
- RED: `python -X utf8 -m pytest script\tests\test_scheduler_smoke_release_contract.py -q` -> FAIL，发布脚本/测试契约未统一到登录规则允许的 smoke 用户名。
- GREEN: `mvn -pl yudao-module-mes -Dtest=MesProAutoScheduleControllerContractTest test` -> PASS，controller POST JSON body 契约通过。
```

### Match 4 (lines 46-53)

```text
- GREEN: runtime-console-build-deploy -> PASS，证据 `evidence/runtime-console-build-deploy-1781844498623.json`，releaseTag `release-20260619-1229-role-e2e-gate-post-deps-smoke-user`，构建和测试服部署均成功；服务器 `.env`、backend/frontend 镜像 tag、后端 health、前端 HTTP 200 均通过；`20260619_post_release_role_e2e_gate_smoke_username_fix` 在测试服为 `APPLIED`。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781844737245.json`：`gaomin` 仅见 `展厅` 且 6 个子页通过；`wangsiyu` 仅见 `DCC文控中心` 且 16 个子页通过；`zhaojie` 仅见 `智能排产`，但工作台全局未读消息请求 `net::ERR_ABORTED` 被误判为 route failure，智能排产 smoke 失败，远端 `smoke-report.json` 显示三个合法 smoke 账号登录被拒绝为 `密码已过期，请修改密码后再登录`。
- BDD: 智能排产 smoke 密码有效期契约 -> Given 发布脚本准备登录规则兼容的 smoke 账号 / When 系统密码策略校验 `password_update_time` / Then 三个 smoke 账号必须刷新 `password_update_time`，否则发布后 smoke 登录必须失败并暴露。
- RED: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> FAIL，新增合同期望 `20260619_post_release_role_e2e_gate_smoke_username_password_freshness_fix.sql`，当前缺少迁移文件。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> PASS，7 passed；新增迁移刷新 `messmokeerp/messmokesupervisor/messmokenonapprover` 的 `password_update_time` 并验证 `fresh_password_count=3`。
- RED: `node doc\tasks\20260618-post-release-role-e2e-gate\scripts\post-release-role-e2e-static.test.cjs` -> FAIL，E2E 脚本尚未区分浏览器主动中止的全局未读消息请求。
- GREEN: `node doc\tasks\20260618-post-release-role-e2e-gate\scripts\post-release-role-e2e-static.test.cjs` -> PASS，E2E 脚本仅将 `GET /admin-api/system/notify-message/get-unread-count` 且 `net::ERR_ABORTED` 的请求归入 `externalRequestFailures`，其他请求失败仍计入失败。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py script\tests\test_scheduler_smoke_release_contract.py script\tests\test_showroom_release_sql_contract.py script\tests\test_publish_int_ruoyi_to_test_tooling.py script\tests\test_showroom_product_revision_attachment_sql.py script\tests\test_showroom_sql_scripts.py -q` -> PASS，114 passed。
```

### Match 5 (lines 55-66)

```text
- GREEN: runtime-console-build-deploy -> PASS，证据 `evidence/runtime-console-build-deploy-1781846618912.json`，releaseTag `release-20260619-1301-role-e2e-gate-smoke-password-freshness`，构建和测试服部署均成功；测试服 `.env`、backend/frontend 镜像 tag、后端 health、前端 HTTP 200 均通过；`20260619_post_release_role_e2e_gate_smoke_username_password_freshness_fix` 在测试服为 `APPLIED`，`messmokeerp/messmokesupervisor/messmokenonapprover` 的 `password_update_time` 均刷新为 `2026-06-19 13:21:31`。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781846902055.json`：`gaomin` 仅见 `展厅` 且 6 个子页通过；`wangsiyu` 仅见 `DCC文控中心` 且 16 个子页通过；`zhaojie` 仅见 `智能排产`，6 个子页无页面/接口错误，但智能排产 smoke 失败。远端 `smoke-report.json` 显示 `/admin-api/erp/kingdee-sync/production-order/create` 被 Kingdee 拒绝：`计划完工时间没有落在生产车间关联的工作日历的生产日上`，实际默认 `erpPlannedFinishTime=2026-06-20 17:27:00` 为周六。
- BDD: 智能排产 smoke 工作日完工时间契约 -> Given 发布后 smoke 需要创建真实 Kingdee 生产订单 / When 运行时刻加 36 小时落在周末 / Then 默认 ERP 计划完工时间必须推进到下一个工作日，不能生成会被 Kingdee 车间工作日历拒绝的周末完工时间。
- RED: `node tests/e2e/smart-scheduling-smoke-real-flow-static.spec.js` -> FAIL，新增合同期望默认 ERP planned finish 使用 `nextWeekdayDateTimeAfter(36)`，当前脚本仍为裸 `isoDateTimeAfter(36)`。
- GREEN: `node tests/e2e/smart-scheduling-smoke-real-flow-static.spec.js` -> PASS，smoke 默认 `erpPlannedFinishTime` 已改为下一个工作日固定 17:30；`erpSyncEligibleDateTime()` 在周末回退到最近工作日，保持 Kingdee 同步窗口内的生产日。
- GREEN: experience-preflight -> PASS，第三轮修复仍限定测试服 `172.30.30.58`、芋道源码租户三账号真实 E2E；不操作正式服、不备份/恢复、不 mock、不绕过前端路径。
- GREEN: runtime-console-build-deploy -> PASS，证据 `evidence/runtime-console-build-deploy-1781848691651.json`，releaseTag `release-20260619-1335-role-e2e-gate-weekday-smoke-finish`，构建和测试服部署均成功；测试服 `.env`、backend/frontend 镜像 tag、后端 health、前端 HTTP 200 均通过。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781848897783.json`：`gaomin` 仅见 `展厅` 且 6 个子页通过；`wangsiyu` 仅见 `DCC文控中心` 且 16 个子页通过；`zhaojie` 仅见 `智能排产` 且 6 个子页通过，但智能排产 smoke 失败。远端 `smoke-report.json` 显示 ERP 冒烟创建员在金蝶同步运行页等待生产工单 `kingdeeProductionOrderSyncJob` 行内“执行一次”按钮超时；截图 `evidence/zhaojie-smoke-job-trigger-failure-1781848897783.png` 显示“手动补跑”列为空。
- GREEN: root-cause-readonly-db -> PASS，只读核对测试服：ERP smoke 用户 `messmokeerp` 绑定角色 `post_release_mes_smoke_erp_creator`；角色已绑定旧菜单 `1075/infra:job:trigger`，但该按钮父菜单为 `110/定时任务`，ERP smoke 角色没有父菜单链；真实登录 `messmokeerp` 后 `get-permission-info` 仅包含 `erp:kingdee-sync:query`，不包含 `infra:job:trigger` 或 `infra:job:query`。代码核对 `filterDisableMenus()` 会过滤父菜单缺失的按钮权限，导致前端 `v-hasPermi="['infra:job:trigger']"` 隐藏按钮。
- BDD: ERP smoke 手动同步权限 -> Given zhaojie 智能排产 smoke 使用 ERP 冒烟创建员创建 Kingdee 工单 / When 打开 ERP 金蝶同步运行页 / Then 页面必须显示生产工单“执行一次”，且该账号具备定时任务查询和触发接口权限。
- RED: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> FAIL，新增合同期望 `20260619_post_release_role_e2e_gate_smoke_z_erp_job_permission_fix.sql`，当前缺少迁移文件。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> PASS，8 passed；新增迁移在 ERP 同步菜单 `6013` 下补齐 `infra:job:query` 与 `infra:job:trigger` 两个按钮权限，并绑定 ERP smoke 角色。
```

### Match 6 (lines 70-77)

```text
- GREEN: test-server-release-state -> PASS，测试服 `.env` `IMAGE_TAG=release-20260619-1430-role-e2e-gate-erp-job-permission`；backend/frontend 镜像 tag 匹配并 running；后端 health HTTP 200，前端 HTTP 200；`20260619_post_release_role_e2e_gate_smoke_z_erp_job_permission_fix` 在测试服为 `APPLIED`。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781851764170.json`：`gaomin` 仅见 `展厅` 且 6 个子页通过；`wangsiyu` 仅见 `DCC文控中心` 且 16 个子页通过；`zhaojie` 仅见 `智能排产` 且 6 个子页通过，但智能排产 smoke 失败。远端 `output/artifacts/smoke-report.json` 显示 ERP 工单创建、MES 同步、工作台八指标和 `infra/job/trigger` 均通过，失败在 `admit-confirmed-work-order-to-schedule-pool`：工单 `SMART-SCHED-20260619T064800584124551-MO` 不在 `READY_TO_ADMIT` 入池差异列表。
- GREEN: root-cause-readonly-db -> PASS，只读核对测试服真实库：`MES_SMOKE_PRODUCT_CODE=AW.106.03.08.1007`，芋道源码租户同步出的产品 `902476` 无 `mes_pro_route_product` 路线绑定，`route_process` 计数为 0；可路线就绪候选包括 `YXN.069.001.1003` / 单位 `zhi` / route `900026` / 激活版本 `4` / 工序数 `26`。同时发现远端 runner 只保留残留静态 `smart-scheduling-smoke-feedback.xlsx`，其内容写死旧产品 `AW.106.03.08.1007` 和旧工单号，不适配本次 smokeRunId。
- BDD: 智能排产 smoke 路线就绪产品 -> Given smoke 通过 Kingdee 创建真实生产工单 / When MES 同步工单并查询排产入池差异 / Then 默认产品必须已绑定启用路线、激活版本和工序，不能停留在 `BLOCKED_MISSING_ROUTE`。
- BDD: 智能排产 smoke 动态报工 Excel -> Given smoke 每次运行都有新的工单号和产品配置 / When 执行第三方报工导入 / Then 上传 Excel 必须按本次 `smokeRunId`、工单号、产品编码和工序动态生成，不能依赖测试服残留静态文件。
- RED: `python -X utf8 -m pytest script\tests\test_scheduler_smoke_release_contract.py -q` -> FAIL，发布脚本仍保留旧默认产品 `AW.106.03.08.1007` 且 runner package 未包含 `xlsx`。
- RED: `node tests\e2e\smart-scheduling-smoke-real-flow-static.spec.js` -> FAIL，smoke runner 仍将 `MES_SMOKE_EXCEL_FILE` 作为必填固定 workbook，未动态生成本次运行的报工 Excel。
- GREEN: `python -X utf8 -m pytest script\tests\test_scheduler_smoke_release_contract.py -q` -> PASS，发布脚本默认产品改为 `YXN.069.001.1003`、单位 `zhi`，并显式迁移旧无路线默认值；runner package 包含 `xlsx`。
```

### Match 7 (lines 80-82)

```text
- GREEN: `node doc\tasks\20260618-post-release-role-e2e-gate\scripts\validate-maintenance-publish-contract.cjs` -> PASS，维护仓实际发布脚本包含同样的 route-ready 默认产品、旧值迁移和 `xlsx` runner 依赖。
- GREEN: PowerShell AST -> PASS，维护仓 `ops\deploy\publish-int-ruoyi.ps1` 与业务仓 `script\deploy\publish-int-ruoyi.ps1` 均无解析错误。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py script\tests\test_scheduler_smoke_release_contract.py script\tests\test_showroom_release_sql_contract.py script\tests\test_publish_int_ruoyi_to_test_tooling.py script\tests\test_showroom_product_revision_attachment_sql.py script\tests\test_showroom_sql_scripts.py -q` -> PASS，115 passed。
```

### Match 8 (lines 87-99)

```text

- 用户需求：每次发布后在测试服务器用 `芋道源码` 租户账号 `gaomin`、`zhaojie`、`wangsiyu` 全量验证角色页签、子页访问和智能排产冒烟；失败先全部记录，统一修复后重新构建发布到测试服并复测直到通过。
- GREEN: experience-preflight -> PASS，已重新核对 `docs/experience-index.md` 命中文档约束仍适用；当前高风险动作仅限测试服 `172.30.30.58` 真实登录 E2E，不涉及正式服、备份/恢复/回滚或接口绕过。
- GREEN: resume-evidence-read -> PASS，最新构建/部署 evidence `evidence/runtime-console-build-deploy-1781854878582.json` 为 PASS，releaseTag `release-20260619-1518-role-e2e-gate-route-ready-smoke` 已部署到测试服，下一步直接运行三角色真实 E2E。

## 2026-06-19 排产工序快照缺列修复

- 用户需求：继续发布后三角色测试服门禁；先记录全部失败，再统一修复、重新构建发布到测试服并完整复测，直到三账号全部通过。
- GREEN: experience-preflight -> PASS，已再次核对 `docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`，当前高风险动作仍仅限测试服 `172.30.30.58` 的重发与真实 E2E，不涉及正式服、备份/恢复/回滚。
- GREEN: resume-evidence-read -> PASS，最新真实 E2E 证据 `evidence/post-release-role-e2e-1781856280345.json` 为 FAIL，但仅剩 `zhaojie` 智能排产 smoke 失败；远端 `/opt/intruoyi/runtime/smoke/yudao-ui-admin-vue3/output/artifacts/smoke-report.json` 明确报错 `Unknown column 'process_code' in 'field list'`，发生在 `mes_pro_schedule_order_process` 插入排产工序快照阶段。
- BDD: 排产工序快照 schema 契约 -> Given 智能排产 smoke 会把工单工序写入 `mes_pro_schedule_order_process` 快照表 / When 后端持久化 `process_code` 与 `process_name` / Then 测试服真实库必须先具备对应列并对历史记录完成回填，不能在 `create-from-work-order` 阶段因缺列失败。
- RED: `git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro show HEAD:sql/mysql/20260619_mes_schedule_order_process_snapshot_identity_p8.sql` -> FAIL，`HEAD` 中不存在该迁移文件，说明当前已部署版本未携带本次 schema 修复。
- GREEN: `python -X utf8 -m pytest script\tests\test_mes_scheduling_closed_loop_sql.py -q` -> PASS，6 passed；新增契约覆盖 `20260619_mes_schedule_order_process_snapshot_identity_p8.sql` 的 release metadata、`process_code/process_name` 加列与回填语义。
```

### Match 9 (lines 101-111)

```text

## 2026-06-19 A03388 设备工序产能冲突发布修复

- 用户需求：继续同一任务，修复重发后仅剩的 `zhaojie` 智能排产 smoke 失败，并在修复后再次构建发布测试服、复跑三账号真实 E2E。
- GREEN: experience-preflight -> PASS，已再次核对当前高风险动作仍仅限测试服 `172.30.30.58` 的重新构建发布和真实浏览器 E2E，不涉及正式服、备份/恢复/回滚。
- GREEN: runtime-console-build-deploy -> PASS，证据 `evidence/runtime-console-build-deploy-1781858207843.json`，releaseTag `release-20260619-1638-role-e2e-gate-process-snapshot` 已成功构建并部署测试服；远端 `.env` 验证 `IMAGE_TAG=release-20260619-1638-role-e2e-gate-process-snapshot`。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781858432621.json`：`gaomin` 仅见 `展厅` 且 6 个子页通过；`wangsiyu` 仅见 `DCC文控中心` 且 16 个子页通过；`zhaojie` 仅见 `智能排产` 且 6 个子页通过，但智能排产 smoke 失败。远端 `smoke-report.json` 显示 `API /admin-api/mes/pro/auto-schedule/preview failed`，错误为 `设备工序产能存在冲突: machineryId=47, processId=900370`。
- BDD: A03388 同设备同工序唯一产能契约 -> Given `芋道源码` 租户智能排产 smoke 会在自动排产预览读取 A03388 相关设备工序产能 / When 同一设备同一工序存在两条不同 `standard_hourly_capacity` 记录 / Then 发布迁移必须逻辑删除重复高产能记录，仅保留保守容量，避免 `/mes/pro/auto-schedule/preview` 因资源冲突 500。
- GREEN: root-cause-read -> PASS，结合历史任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260608-admin-resource-capacity-unify\` 与当前远端 smoke 报告，可确认 admin 租户 `A03388` 的 `machinery_id=47` 在 `process_id=900370/900371` 上存在已知重复高产能源；本次测试服尚未通过正式发布迁移承接这笔数据治理。
- RED: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> FAIL，新增契约期望 `20260619_post_release_role_e2e_gate_smoke_admin_resource_capacity_fix.sql`，当前缺少迁移文件。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> PASS，9 passed；新增迁移会在 `tenant_id=1` 中校验并逻辑删除 `machinery_id=47 / process_id=900370,900371` 的高产能冲突行，保留 `25.714286` 与 `40.000000` 两条基准记录，并在发布时强制 `remaining_conflict_count = 0`。
```

### Match 10 (lines 115-146)

```text

- 用户需求：继续同一任务，在再次发布前先记录全部剩余错误，统一修复 `gaomin` 的误报和 `zhaojie` 智能排产 smoke 的真实后端失败，再构建发布到测试服并复测三账号。
- GREEN: experience-preflight -> PASS，已重新核对 `docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`；当前高风险动作仍仅限测试服 `172.30.30.58` 的真实登录、只读排障和后续重发版，不涉及正式服、备份/恢复/回滚。
- GREEN: resume-evidence-read -> PASS，最新真实 E2E 证据 `evidence/post-release-role-e2e-1781865453288.json` 为 FAIL，但仅剩两项：`gaomin` `/showroom/company` 的 `dict-data/simple-list` 浏览器中止误报，以及 `zhaojie` 智能排产 smoke 在 `apply` 阶段失败。
- GREEN: root-cause-readonly-remote -> PASS，只读核对测试服 `172.30.30.58`：`mes_md_auto_code_rule` 已存在 `tenant_id=1 / rule_id=900070 / code=PRO_TASK_CODE` 及 `900071/900072` 两段规则；`mes_md_auto_code_record` 仅保留 `PT-0006(serial_no=6)`、`PT-0007(serial_no=7)`；`intruoyi-redis` 中不存在 `mes:md:auto_code:900070` key；后端日志堆栈固定落在 `MesMdAutoCodeRecordServiceImpl.generateAutoCode(...:90)`，说明失败根因是 Redis 流水缓存丢失后回退撞码，而非规则缺失。
- BDD: 展厅页签切页中的字典请求中止不应误判失败 -> Given `gaomin` 展厅子页真实访问成功 / When 浏览器在页面切换时主动中止 `GET /admin-api/system/dict-data/simple-list` / Then E2E 脚本应将其记为 benign external request，而不是 route failure。
- BDD: 自动编码流水缓存丢失后必须按数据库最大流水恢复 -> Given `PRO_TASK_CODE` 的 Redis key 丢失但数据库已有历史 `serial_no` / When 智能排产 `apply` 再次批量生成任务编码 / Then 系统必须从历史最大流水继续分配，不能回退到起始号并因历史 `PT-0006/PT-0007` 记录抛出 `编码生成失败`。
- RED: `node doc\tasks\20260618-post-release-role-e2e-gate\scripts\post-release-role-e2e-static.test.cjs` -> FAIL，脚本尚未将 `GET /admin-api/system/dict-data/simple-list` 的 `net::ERR_ABORTED` 归为 benign request failure。
- RED: `mvn -pl yudao-module-mes -Dtest=MesMdAutoCodeSerialNumberPartStrategyTest test` -> FAIL，新增自动编码恢复用例前，编译无法找到 `selectLatestSerialRecord(...)` 恢复契约，说明正式恢复逻辑尚未实现。
- GREEN: `node doc\tasks\20260618-post-release-role-e2e-gate\scripts\post-release-role-e2e-static.test.cjs` -> PASS，展厅脚本已将 `GET /admin-api/system/dict-data/simple-list` 且 `net::ERR_ABORTED` 纳入 benign request failure，避免把已确认 200 的切页中止误报为页面失败。
- GREEN: `mvn -pl yudao-module-mes "-Dtest=MesMdAutoCodeSerialNumberPartStrategyTest,MesProAutoScheduleServiceImplTest" test` -> PASS，28 passed；新增自动编码恢复用例覆盖 Redis key 丢失后按 `mes_md_auto_code_record` 历史最大 `serial_no` 续号，同时排产服务既有 22 个回归用例未回退。

## 2026-06-19 eDHR 批次触发门禁修复

- 用户需求：继续同一任务，在再次发布前先记录全部剩余错误，统一修复 `zhaojie` 智能排产 smoke 的新后端失败，再构建发布到测试服并复测三账号。
- GREEN: resume-evidence-read -> PASS，最新真实 E2E 证据 `evidence/post-release-role-e2e-1781869546155.json` 显示 `gaomin` 与 `wangsiyu` 已通过，`zhaojie` 的智能排产 smoke 已不再报 `编码生成失败`，但在 `/admin-api/mes/pro/auto-schedule/apply` 新失败为 `排产完成创建 eDHR 批次缺少前置条件：工序与批记录绑定`。
- GREEN: root-cause-readonly-remote -> PASS，只读核对测试服：当前 smoke 路线 `900026` 在 `mes_pro_route_use_process_config` 下无任何 `use_type='BATCH'` 的启用工序配置，在 `mes_pro_route_use_process_batch_record` 下也无任何绑定；与此同时当前代码 `MesProAutoScheduleServiceImpl.apply(...)` 会在排产完成后无条件触发 eDHR 批次创建，说明失败根因是普通路线被误纳入 eDHR 前置校验，而不是 eDHR 已启用路线缺少兜底。
- BDD: 非 eDHR 路线排产完成后不应触发批次创建 -> Given 自动排产 `apply` 成功生成普通路线任务且该路线无启用中的 `BATCH` 配置 / When 排产服务进入排产完成后置动作 / Then 不得调用 eDHR 批次创建服务，也不得因 `工序与批记录绑定` 缺失回滚整个 `apply`。
- BDD: 已启用 eDHR 的路线仍需严格校验前置条件 -> Given 路线存在启用中的 `BATCH` 工序配置 / When 排产服务触发 eDHR 批次创建 / Then 若缺少工序与批记录绑定或首任务责任来源/候选池，系统仍必须明确失败，不得吞错、降级或静默跳过。
- GREEN: `mvn -pl yudao-module-mes "-Dtest=MesProAutoScheduleServiceImplTest,MesProAutoScheduleAlgorithmContractTest,MesProAutoScheduleContractTest" test` -> PASS，35 passed；新增调度层回归测试保护普通路线跳过 eDHR 触发、已启用 eDHR 路线继续 fail fast。
- GREEN: `mvn -pl yudao-module-mes "-Dtest=MesProEdhrBatchExecutionServiceTest,MesProAutoScheduleServiceImplTest,MesProAutoScheduleAlgorithmContractTest,MesProAutoScheduleContractTest" test` -> PASS，72 passed；eDHR 批次服务既有 37 个契约测试保持全绿，说明本次改动仅修正调度触发门禁。

## 2026-06-19 报工审批人身份解析门禁修复

- 用户需求：继续同一任务，在最新发布 `release-20260619-2055-role-e2e-gate-edhr-trigger` 之后先记录全部剩余错误，统一修复 `zhaojie` 智能排产 smoke 的新阻塞，再重新构建发布到测试服并完整复测三账号。
- GREEN: experience-preflight -> PASS，已再次核对 `docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`；当前高风险动作仍仅限测试服 `172.30.30.58` 的重新构建发布与真实浏览器 E2E，不涉及正式服、备份/恢复/回滚。
- GREEN: resume-evidence-read -> PASS，最新真实 E2E 证据 `evidence/post-release-role-e2e-1781875259932.json` 显示 `gaomin` 与 `wangsiyu` 已通过，`zhaojie` 的智能排产 smoke 已越过 eDHR `apply` 门禁，但在 `/admin-api/mes/pro/feedback/import-record/attribute` 新失败为 `第三方报工导管报工第 2 行工段长匹配到多名用户：eDHR矩阵-审批人`。
- GREEN: root-cause-readonly-remote -> PASS，只读核对测试服：`/opt/intruoyi/runtime/.env` 当前包含 `MES_SMOKE_SUPERVISOR_USERNAME=messmokesupervisor` 且未显式设置 `MES_SMOKE_FEEDBACK_APPROVER_NAME`；数据库 `tenant_id=1` 下启用用户 `mes_smoke_supervisor(id=910253)` 与 `messmokesupervisor(id=910260)` 共用 nickname `eDHR矩阵-审批人`，因此依赖默认昵称的第三方报工导入在当前真实数据下稳定不唯一。
- BDD: 第三方报工导入审批人支持唯一 username 解析 -> Given 导入文件的工段长字段填写的是启用用户的唯一 username / When 系统在归属阶段解析审批人 / Then 必须把审批责任绑定到该 username 对应的唯一用户，后续审批人登录与 approveUserId 保持一致。
- BDD: 重复昵称仍然 fail fast -> Given 导入文件的工段长字段填写的是重复 nickname，且没有与之同名的唯一 username / When 系统解析审批人 / Then 必须明确返回“匹配到多名用户”，不得静默任选其一或吞错继续。
- GREEN: `mvn -pl yudao-module-mes "-Dtest=MesProFeedbackImportRecordServiceImplTest" test` -> PASS，6 passed；新增回归覆盖 supervisor username 直绑审批人、唯一 nickname 兼容与重复 nickname 继续 fail-fast。
- GREEN: `node doc\tasks\20260618-post-release-role-e2e-gate\scripts\validate-maintenance-publish-contract.cjs` -> PASS，维护发布脚本已显式输出 `MES_SMOKE_FEEDBACK_APPROVER_NAME=$effectiveMesSmokeFeedbackApproverName`，并将其绑定到当前 supervisor username，避免测试服运行态回退到历史昵称默认值。
```

### Match 11 (lines 155-157)

```text
- GREEN: `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260618-post-release-role-e2e-gate --mode preview` -> PASS，closeout preview 仅保留 `task.md`、`execution-log.md` 与最终 PASS 的构建/三角色 E2E 两份 evidence。
- GREEN: manual-closeout-apply -> PASS，按 `task.md` 中 `Cleanup Candidates` 手工删除 `bug-regression-evidence.md`、`qa-evidence.md`、`scripts/`、中间失败 build/E2E evidence、screenshots 与 MinIO 同步附属产物；任务目录最终仅保留 `task.md`、`execution-log.md`、`evidence/runtime-console-build-deploy-1781882335880.json`、`evidence/post-release-role-e2e-1781882555897.json`。
- GREEN: task-tree-recheck -> PASS，复核 `doc/tasks/20260618-post-release-role-e2e-gate/` 当前目录树与 `Cleanup Keep` 完全一致，无额外附属产物残留。
```
## doc/tasks/20260618-post-release-role-e2e-gate/task.md

### Match 1 (lines 6-12)

```text

1. `gaomin / 111111` 登录后只能看到 `展厅` 页签，展厅页签下每个子页签访问无错误。
2. `zhaojie / 111111` 登录后只能看到 `智能排产` 页签，并运行智能排产冒烟测试直到运行结束。
3. `wangsiyu / 111111` 登录后只能看到 `DCC文控中心` 页签，DCC 文控中心下每个子页签访问无错误。

如果任一角色或页面失败，先完整记录全部错误；全部测试跑完后统一修复，再构建发布到测试服务器并重新运行三角色验收，循环直到全部满足。

```

### Match 2 (lines 18-20)

```text
- 账号：`gaomin`、`zhaojie`、`wangsiyu`，密码均为 `111111`。
- 允许：Playwright 真实浏览器登录、页面访问、运行智能排产冒烟测试、记录错误、必要修复、重新构建发布到测试服、复测。
- 禁止：正式服、备份服、备份、恢复、回滚、mock 登录、接口绕过 E2E、静默切换租户或账号。
```

### Match 3 (lines 29-35)

```text

- `docs/release-build-preflight-lessons.md`：发布后必须看目标环境真实运行态、真实页面和权限响应；故障要补成门禁。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：发布入口必须是维护仓；再次修复后构建发布必须验证 manifest、远端 IMAGE_TAG、镜像和真实浏览器入口。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`：测试服 IP 为 `172.30.30.58`，远端运行目录 `/opt/intruoyi/runtime`，服务器凭据不得写入仓库。
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`：登录失败必须记录真实租户、账号、入口、失败位置；不得静默切换账号/租户/环境。用户本次明确授权测试服登录。
- `docs/agent-memory/project-error-prevention.md`：不能只看健康检查，必须核对真实浏览器入口和权限响应。

```

### Match 4 (lines 37-41)

```text

- `是否引入 fallback/降级/吞异常`：否。登录、菜单、页面访问或冒烟失败必须记录为失败，不隐藏错误。
- `是否从根因和长期维护角度解决`：是。先完整复现三角色验收，再统一修复并发布复测。
- `是否存在临时补丁或绕过`：否。不得通过前端隐藏、接口绕过或手工改测试结果伪装成功。

```

### Match 5 (lines 43-51)

```text

- `BDD: gaomin 展厅角色验收 -> Given 测试服发布完成且 gaomin 登录芋道源码租户 / When 打开管理前端 / Then 只看到展厅页签，并且展厅每个子页签访问无页面错误、网络错误或控制台错误。`
- `BDD: zhaojie 智能排产角色验收 -> Given 测试服发布完成且 zhaojie 登录芋道源码租户 / When 打开管理前端并进入智能排产 / Then 只看到智能排产页签，并且智能排产冒烟测试可运行直到结束。`
- `BDD: wangsiyu DCC角色验收 -> Given 测试服发布完成且 wangsiyu 登录芋道源码租户 / When 打开管理前端 / Then 只看到DCC文控中心页签，并且DCC文控中心每个子页签访问无页面错误、网络错误或控制台错误。`
- `BDD: 失败统一修复发布复测 -> Given 三角色验收发现错误 / When 全部错误记录完成 / Then 统一修复、重新构建发布到测试服并完整复测三角色，直到全部通过。`
- `BDD: ERP smoke 手动同步权限 -> Given zhaojie 智能排产 smoke 使用 ERP 冒烟创建员创建 Kingdee 工单 / When 打开 ERP 金蝶同步运行页 / Then 页面必须显示生产工单“执行一次”，且该账号具备定时任务查询和触发接口权限。`
- `BDD: 智能排产 smoke 路线就绪产品 -> Given smoke 通过 Kingdee 创建真实生产工单 / When MES 同步工单并查询排产入池差异 / Then 默认产品必须已绑定启用路线、激活版本和工序，不能停留在 BLOCKED_MISSING_ROUTE。`
- `BDD: 智能排产 smoke 动态报工 Excel -> Given smoke 每次运行都有新的工单号和产品配置 / When 执行第三方报工导入 / Then 上传 Excel 必须按本次 smokeRunId、工单号、产品编码和工序动态生成，不能依赖测试服残留静态文件。`

```

### Match 6 (lines 54-57)

```text
- [x] M1 建立任务文档、读取经验门禁、确认上一任务完成。
- [x] M2 编写并运行测试服三角色真实 E2E 探测，记录全部错误。
- [x] M3 汇总失败根因并统一修复。
- [x] M4 重新构建发布到测试服。
```

### Match 7 (lines 64-68)

```text
- 每个账号验证登录后一级可见菜单只包含目标页签。
- 自动遍历目标页签子菜单，记录 URL、页面文本、控制台错误、请求失败、接口错误。
- `zhaojie` 触发智能排产冒烟测试并轮询到终态。
- 若修复代码，必须补 RED/GREEN 测试、构建发布、部署测试服并重新跑三角色验收。

```

### Match 8 (lines 70-76)

```text

COMPLETED：已通过多轮“记录全部错误 -> 根因修复 -> 正式构建发布 -> 测试服真实复测”的闭环，最终测试服发布 `release-20260619-2230-role-e2e-gate-feedback-approver-wrapper` 在 `172.30.30.58` 上满足全部验收要求。最终真实 E2E 证据 `evidence/post-release-role-e2e-1781882555897.json` 显示：

- `gaomin / 111111` 登录 `芋道源码` 后仅可见 `展厅`，6 个子页全部无页面、接口或控制台错误。
- `zhaojie / 111111` 登录 `芋道源码` 后仅可见 `智能排产`，6 个子页全部通过；智能排产真实 smoke 全链路 `PASS`，远端 `smoke-report.json` 中 ERP 建单、MES 同步、入池、自动排产、日历核验、第三方报工导入、归属、审批与任务回写全部通过。
- `wangsiyu / 111111` 登录 `芋道源码` 后仅可见 `DCC文控中心`，16 个子页全部无页面、接口或控制台错误。

```

### Match 9 (lines 80-82)

```text
- 测试服运行态：`ssh root@172.30.30.58 "grep '^IMAGE_TAG=' /opt/intruoyi/runtime/.env"` -> `IMAGE_TAG=release-20260619-2230-role-e2e-gate-feedback-approver-wrapper`。
- 三角色真实 E2E：`evidence/post-release-role-e2e-1781882555897.json` -> PASS，`failures=0`。
- 智能排产 smoke：`ssh root@172.30.30.58 "cat /opt/intruoyi/runtime/smoke/yudao-ui-admin-vue3/output/artifacts/smoke-report.json"` -> PASS，`smokeRunId=SMART-SCHED-20260619T152027017032296`。
```

### Match 10 (lines 96-98)

```text

- `doc/tasks/20260618-post-release-role-e2e-gate/bug-regression-evidence.md`
- `doc/tasks/20260618-post-release-role-e2e-gate/qa-evidence.md`
```

### Match 11 (lines 104-106)

```text
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/screenshots/`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/zhaojie-smoke-job-trigger-failure-1781848897783.png`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781790158540.json`
```
## docs/request-command-log.md

### Match 1 (lines 6-8)

```text
- 计划边界：仅发布测试服 `172.30.30.58`，远端目录 `/opt/intruoyi/runtime`；发布范围为 `code-only`，不访问正式服/备用服，不执行备份、恢复、回滚或正式服动作。
- 命中经验：`release-backup-restore.md`、`server-access.md`、`login-access.md`；真实 E2E 和服务器写入前必须记录 `experience-preflight`。
- 命令记录：检查 `npx` 可用，路径为 `D:\Programs\npx.ps1`。
```

### Match 2 (lines 16-19)

```text
- 命令记录：Playwright 点击构建发布包“执行”，operation `op-2026-06-17T072458143463800Z-0d5a0145-9253-4018-991a-55bf864264ef` 初始状态 `RUNNING`。
- 命令记录：构建 operation 最终 `FAILED`；后端 Maven、前端 Vite build、后端 Docker 镜像构建成功，前端 Docker 镜像构建失败，原因是拉取 `nginx:1.27-alpine` 元数据时 Docker Hub token 请求超时。
- 阻塞记录：发布包未成功生成，禁止继续发布测试服；下一步先补齐/验证 Docker 基础镜像 `nginx:1.27-alpine`。
- 命令记录：`docker pull nginx:1.27-alpine` PASS，digest `sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`。
```

### Match 3 (lines 21-24)

```text
- 命令记录：Playwright 点击第二次构建发布包“执行”，operation `op-2026-06-17T073818610888200Z-832a7d6b-133a-45ed-abd9-84dd1abfd300` 初始状态 `RUNNING`。
- 命令记录：第二次构建 operation 仍 `FAILED`；Maven、Vite、后端镜像和前端镜像成功，发布迁移策略门禁失败，原因是 `20260617_dcc_browser_performance_indexes` 依赖缺失 `20260513_dcc_base_schema.sql`。
- 阻塞记录：发布包 manifest 未生成，禁止继续发布测试服；需要先修复迁移元数据/扫描集合。
- 命令记录：在 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 修正 `sql/mysql/20260617_dcc_browser_performance_indexes.sql` 首行 `dependsOn` 为清单实际使用的迁移 ID `20260513_dcc_base_schema`。
```

### Match 4 (lines 28-30)

```text
- 命令记录：Playwright 点击第三次构建发布包“执行”，operation `op-2026-06-17T082753879349700Z-c7f3f523-d9c6-4077-9b0f-eacc6cf5bf73` 初始状态 `RUNNING`。
- 命令记录：第三次构建 operation `FAILED`；Maven 在 `yudao-module-dcc` 执行 clean 时无法删除 `target`，发布包未生成，禁止发布测试服。
- 命令记录：`mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -DskipTests clean` PASS，DCC target 清理前置恢复。
```

### Match 5 (lines 32-34)

```text
- 命令记录：Playwright 点击第四次构建发布包“执行”，operation `op-2026-06-17T083241295814300Z-dc21fdce-0784-4465-a8d8-7e6ceb485990` 初始状态 `RUNNING`。
- 命令记录：第四次构建 operation `FAILED`；Maven、Vite build、后端 Docker 镜像成功，前端 Docker 镜像解析 `nginx:1.27-alpine` 元数据时 Docker Hub 返回 EOF，发布包未生成，禁止发布测试服。
- 命令记录：`docker pull nginx:1.27-alpine` PASS，digest `sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`，本地 `docker image inspect` PASS。
```

### Match 6 (lines 36-39)

```text
- 命令记录：Playwright 点击第五次构建发布包“执行”，operation `op-2026-06-17T084524861642300Z-d778ee83-bb2c-44c5-896d-b1ffed69814a` 初始状态 `RUNNING`。
- 命令记录：第五次构建 operation `FAILED`；发布脚本在 Maven clean 前检测到本机 `yudao-server.jar` 被 Java 进程锁定。
- 命令记录：`restart-ruoyi-backend.bat` 已把本机后端切换到 `E:\Int\CacheData\IntRuoyi\runtime\backend-20260617-164706.jar`，尽管应用最终因定时任务同步失败退出，但目标 jar 锁已解除。
- 命令记录：`mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-server -DskipTests clean` PASS，确认 `yudao-server.jar` 锁前置已恢复。
```

### Match 7 (lines 49-51)

```text
- 命令记录：测试服 `infra_release_migration` 中 `20260617_dcc_browser_performance_indexes` 最新状态为 `APPLIED`。
- 命令记录：Playwright 打开 `http://172.30.30.58:8081/`，HTTP 200，跳转到 `/login?redirect=/index`，页面标题为 `瑛泰管理系统 - 登录`，未发现 console error。
- 命令记录：`task-closeout-cleanup --mode preview` PASS，仅计划删除 `runtime-control-start.out.log` 与 `runtime-control-start.err.log`。
```

### Match 8 (lines 57-63)

```text
- 计划边界：只新增本机双击入口；不执行真实重启、不操作服务器、不 SSH、不写入数据库或对象存储。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`，正式服默认禁止操作，远端重启必须有当前任务授权；本任务仅本机入口。
- 命令记录：读取 `scripts\start.ps1`、`scripts\dev-frontend.ps1`、`scripts\dev-backend.ps1`、`ops\deploy\restart-int-ruoyi-local.ps1` 与远端 bat，确认现有脚本入口。
- 命令记录：只读解析当前维护仓库 `ops\deploy\worktree-port-map.ps1` 失败，错误为缺少 `D:\ProjectPackage\Int\yudao-ui-admin-vue3`。
- 命令记录：只读解析原 IntRuoyi `worktree-port-map.ps1` 成功，`int_main` 映射到 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`、`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`、端口 `8081/48081`。
- 命令记录：`RED` 检查 `restart-frontend-backend.bat` 不存在，按预期失败。
- 命令记录：新增 `restart-frontend-backend.bat`，默认调用原 IntRuoyi 本机重启脚本 `-Component full`。
```

### Match 9 (lines 66-68)

```text
- 命令记录：`git diff --check` PASS，仅有既有换行提示。
- 命令记录：`task-closeout-cleanup --mode preview` PASS，无删除项、无阻塞、无警告。
- 结论记录：已完成本机双击重启入口；验证阶段未执行真实重启、远端操作或数据写入。
```

### Match 10 (lines 73-85)

```text
- 计划边界：只做静态审计和本地契约验证；不执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`，运行控制台相关发布包、tested、恢复候选、DCC 链和 manifest/checksum 证据必须 fail fast；`D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`，本次不改 UI，只审计前端契约。
- 命令记录：结构化解析 controller mapping，standalone 与 original 均为 33 个规范化 HTTP 路径，差异集为空。
- 命令记录：`rg` 对比 service/action/frontend payload，核心动作校验、release-status、mark-tested、候选服务端绑定、DCC chainStatus、前端 payload 均已对齐。
- 命令记录：脚本 hash 对比显示 `apply-test-db-sql.ps1`、`backup-ops.ps1`、`show-int-ruoyi-local-status.ps1`、`restart-int-ruoyi-local.ps1` 字节一致；`publish-int-ruoyi.ps1` 独立版有 64 行差异，来自显式源码根、UTF-8 捕获、DCC inventory base64 JSON 后续修复。
- 命令记录：发现条件性差异：原版 `backupOps.executionMode=linux-local` 会生成 Linux 风格参数，独立版只切换脚本路径但仍生成 PowerShell 风格参数；默认 `powershell` 配置不触发。
- 命令记录：发现治理面差异：owner matrix / alert / incident / inspection / probe / capacity / remote-root 与完整前端治理界面为独立版简化或 fail-fast 实现。
- 命令记录：`python -X utf8 scripts\verify_contracts.py` PASS。
- 命令记录：`mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` PASS，7 tests, failures 0。
- 命令记录：`pnpm --dir frontend typecheck` PASS。
- 命令记录：`task-closeout-cleanup --mode preview` PASS，无删除项、无阻塞、无警告。
- 命令记录：`task-closeout-cleanup --mode apply` PASS，无删除项、无阻塞、无警告。
- 结论记录：核心运行控制台动作契约 PASS；若要求原版完整治理能力 1:1 复制，则为 PARTIAL。
```

### Match 11 (lines 90-95)

```text
- 计划边界：只修改本机独立维护应用；不执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`，发布包、测试通过标记和恢复候选必须使用真实 manifest/checksum/tested/recoverySet/DCC 证据并 fail fast；`D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`，前端保持紧凑运维控制台风格。
- 命令记录：`mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` RED，复现 `release-status` 版本字段为空、非动作字段未被拒绝、DCC `chainStatus=BROKEN` 未阻断。
- 命令记录：`python -X utf8 scripts\verify_contracts.py` RED，复现前端 payload 未按动作裁剪。
- 命令记录：补齐后 `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` PASS，7 tests, failures 0。
- 命令记录：补齐后 `python -X utf8 scripts\verify_contracts.py` PASS。
```

### Match 12 (lines 97-99)

```text
- 命令记录：`pnpm --dir frontend build` PASS，Vite 仅提示现有大 chunk 体积。
- 命令记录：`mvn -f backend/pom.xml test` PASS，12 tests, failures 0。
- 命令记录：`task-closeout-cleanup --mode preview` PASS，无删除项、无阻塞、无警告。
```
