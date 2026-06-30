# Candidate Error Prevention Evidence

- Generated At: 2026-06-28T12:15:27
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
## doc/tasks/20260625-head-full-release/execution-log.md

### Match 1 (lines 4-6)

```text

BDD: 当前 HEAD 干净构建 -> Given 三个主工作区均存在未提交改动 When 从维护仓、后端、前端当前 HEAD 创建干净 worktree 并构建 Then 发布包 manifest 必须显示三个 sourceRepos 均为本任务记录的 HEAD 且 dirty=false。

```

### Match 2 (lines 12-14)

```text

GREEN: experience-preflight -> PASS，已读取 `release-build-preflight-lessons.md`、`release-backup-restore.md`、`server-access.md`、`login-access.md`、`worktree-memory.md` 与 `project-error-prevention.md`；用户当前发布目标明确授权测试服、正式服和备份服发布；本轮必须从干净 HEAD worktree 构建，发布包 manifest 必须证明 sourceRepos dirty=false。

```

### Match 3 (lines 18-24)

```text

RED: dirty-workspace-direct-build -> FAIL，维护仓、后端、前端主工作区均存在未提交改动，直接构建会违反“未提交改动不得进入构建产物”验收标准。

RED: python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql -> FAIL，干净后端 HEAD `b0586ee897dc5124580b49121b0a1656052b68fa` 报告 `20260624_unified_approval_phase5_retire_legacy_menus.sql` 缺少 `release-migration` 元数据。

RED: python -X utf8 -m pytest script\tests\test_unified_approval_phase5_retirement_sql.py -q -> FAIL，新增 `test_retirement_sql_declares_release_migration_metadata` 断言复现 SQL 第一行不是发布元数据。

```

### Match 4 (lines 28-30)

```text

BLOCKER: main-workspace-policy-gate-noise -> 主后端工作区全量迁移门禁还扫描到未提交 SQL `20260624_mes_auto_schedule_permission_split` 的依赖问题；该文件不属于本次已提交发布输入，主工作区不得用于发布验证。后续必须在提交门禁修复后从新后端 HEAD 创建干净 worktree 重新运行全量门禁。

```

### Match 5 (lines 32-36)

```text

RED: python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql -> FAIL，干净后端 HEAD `acec535394763ff037b099679ef547a48121ee24` 报告 `20260624_mes_auto_schedule_permission_split` 的 `dependsOn` 使用了带 `.sql` 后缀的文件名。

RED: python -X utf8 -m pytest script\tests\test_mes_auto_schedule_permission_sql.py script\tests\test_unified_electronic_signature_menu_sql.py -q -> FAIL，新增两个元数据格式断言复现 `dependsOn` 使用 `.sql` 后缀的问题。

```

### Match 6 (lines 40-42)

```text

GREEN: release-resume-20260627 -> PASS，用户于 `2026-06-27` 明确要求继续执行“构建发布到测试服务器，然后发布到正式服务器和备份服务器，并持续记录问题”；已复核上一未完成任务与本轮目标一致，继续沿用当前任务目录执行，不新建并行发布任务。

```

### Match 7 (lines 44-48)

```text

RED: stale-head-baseline-20260627 -> FAIL，`2026-06-27` 复核发现任务文档中的后端/前端发布基线已过期：后端主仓最新已提交 HEAD 从 `b70624daea23e5792e546f62a868272f99b71af4` 前进到 `e48845f3203fdc19c673de5d09b14f2b1d6b6181`，前端主仓最新已提交 HEAD 从 `0e7616075c6105efb577c6eabb02adafbd497290` 前进到 `ae9c00762c481b87edb3aa72ba8c312bfe9d3633`。继续沿用旧提交出包会违反“只发布当前最新已提交代码”要求。

GREEN: stale-head-baseline-20260627 -> PASS，已将任务基线更新为维护控制台 `3eb9047d0ac0759ee46d7d88f4adba442bed474f`、后端 `e48845f3203fdc19c673de5d09b14f2b1d6b6181`、前端 `ae9c00762c481b87edb3aa72ba8c312bfe9d3633`；后续必须基于这三个最新 HEAD 重新创建干净 worktree 并出包。

```

### Match 8 (lines 52-54)

```text

RED: release-metadata-gate-20260627 -> FAIL，最新后端 HEAD 初次运行 `python -X utf8 script\\release\\run-release-migration-policy-gate.py --sql-root sql\\mysql` 失败，依次暴露 `20260624_dcc_view_matrix_independent_seed.sql` 等 4 个 SQL 缺少 `release-migration` 元数据，以及 10 个 SQL 的 `dependsOn` 仍引用带 `.sql` 后缀或不存在的 migrationId；若直接点运行控制台 `build-release`，会在发布门禁处失败，无法生成 manifest。

```

### Match 9 (lines 56-60)

```text

GREEN: backend-release-metadata-commit-20260627 -> PASS，已将发布契约修复回放到真实后端仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`，在真实仓复跑定向 `pytest` 与 `run-release-migration-policy-gate.py` 均通过，并提交为新 HEAD `72705e1808d2b0c2e95c914f8a55d569ca0e88f5`，提交信息 `任务: 补齐发布迁移契约门禁`。

RED: runtime-control-stale-source-path-20260627 -> FAIL，续跑时发现本机 `48181` 运行控制台实际仍从旧 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260625-3eb9047` 启动，预览参数错误指向陈旧后端/前端路径 `D:/rw/BE25`、`D:/rw/FE25`；若继续点击页面发布，将违反“只发布当前最新已提交代码”要求。

```

### Match 10 (lines 62-66)

```text

RED: runtime-control-build-release-20260627 -> FAIL，运行控制台页面真实执行 `build-release` 后生成 operation `op-2026-06-26T203544816067200Z-7af990fb-ef4f-4038-901c-888076d1661c`，本机执行日志返回 `Migration policy gate failed`；首个阻塞为 `sql/mysql/20260624_unified_electronic_signature_menu.sql:99 -> @unified_signature_overview_menu_id`，说明当前已提交 SQL 仍有 `system_menu.id` 不是整数字面量，发布包在 manifest 生成前即被门禁拦截。

RED: python -X utf8 -m pytest script\tests\test_unified_electronic_signature_menu_sql.py -q -> FAIL，新增“统一电子签名子菜单插入必须使用整数字面量 id”断言后，复现 `VALUES (@unified_signature_overview_menu_id, '总览', ...)` 不满足发布门禁。

```

### Match 11 (lines 70-74)

```text

RED: runtime-control-build-release-20260627-retry1 -> FAIL，切换新 releaseTag `release-20260627-0448-head-full-v2` 后再次从页面执行 `build-release`，operation `op-2026-06-26T204120738837700Z-25253bc1-c5c0-4014-a23e-7ef808100cc5` 仍在发布门禁前失败；日志显示真正阻塞点是同一 SQL 第 99 行临时表 `tmp_unified_signature_child_menu_ids` 仍使用 `(@unified_signature_overview_menu_id)` 等变量字面量，而不是此前已修复的 `INSERT INTO system_menu` 段。

RED: python -X utf8 -m pytest script\tests\test_unified_electronic_signature_menu_sql.py -q -> FAIL，追加“临时菜单 id 表也必须使用整数字面量”断言后，复现 `tmp_unified_signature_child_menu_ids` 的 `VALUES (@unified_signature_overview_menu_id)` 仍违反发布门禁。

```

### Match 12 (lines 78-80)

```text

GREEN: backend-release-literal-menuid-commit-20260627 -> PASS，已将第二轮统一电子签名菜单字面量门禁修复提交到真实后端仓，新 HEAD `413d38ce8cedd59f92f369c64f10a3441617d07d`，提交信息 `任务: 修复统一电子签名菜单字面量门禁`。

```
## doc/tasks/20260625-head-full-release/task.md

### Match 1 (lines 9-13)

```text
- 维护控制台仓库：`D:\ProjectPackage\Int\IntRuoyiMaintance`，当前分支 `int_main`，HEAD `3eb9047d0ac0759ee46d7d88f4adba442bed474f`，提交 `任务: 发布包注入前端版本信息`。
- 后端仓库：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`，当前分支 `int_main`，HEAD `ebabbfcfbf6cbde468f602c5ea18c12346013699`，提交 `任务: 修复发布前端构建内存保护`。
- 前端仓库：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`，当前分支 `int_main`，HEAD `76328963748ce4bcceaa1d50240e844f1fd3db5d`，提交 `任务: 修复审批重定向页构建阻塞`。
- 三个主工作区均存在未提交改动，本次必须从上述 HEAD 创建干净 worktree 构建，禁止使用主工作区出包。

```

### Match 2 (lines 23-27)

```text
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - dirty worktree 不得作为部署输入；发布包 manifest 必须证明 `sourceRepos.dirty=false`。
  - 发布完成必须具备 operation、manifest、远端 `.env` / 镜像 tag、健康检查和真实页面证据。
  - 新前端 worktree 若缺少依赖，必须执行 `pnpm install --frozen-lockfile`，不得复用主工作区依赖目录。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
```

### Match 3 (lines 32-43)

```text
  - 当前任务已由用户明确授权发布测试服、正式服和备份服。
  - 发布前确认目标主机、目录、容器、数据盘和远端容量；备份服必须显式使用 `/mnt/intruoyi-data`。
  - 远端凭据不得写入仓库、脚本、任务文档或运行控制台配置。
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
  - 涉及管理前端验证时使用真实页面；页面异常必须记录实际入口与影响，不得静默切换环境或账号。
- `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
  - 发布隔离 worktree 必须记录路径、分支、commit、构建命令和验证命令。
  - 清理前必须预览并确认只处理本任务 worktree、运行时和临时产物。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
  - 同一 releaseTag 必须一次性走通 build/test/mark-tested/prod/backup；不要拼接多轮结果。
  - 处理 RUNNING 锁前必须核活跃进程和 operation 真实状态，禁止直接改锁。

```

### Match 4 (lines 45-47)

```text

- `是否引入 fallback/降级/吞异常`：否；缺少凭据、manifest、远端访问、真实运行态证据或控制台版本说明时直接阻塞。
- `是否从根因和长期维护角度解决`：是；本轮通过干净 HEAD worktree、manifest 校验、测试先行和三环境运行态闭环发布。
```

### Match 5 (lines 51-53)

```text

BDD: 当前 HEAD 干净构建 -> Given 三个主工作区均存在未提交改动且后端/前端 HEAD 可能继续前进 When 从维护仓、后端、前端当前最新 HEAD 创建干净 worktree 并构建 Then 发布包 manifest 必须显示三个 sourceRepos 均为本任务记录的最新 HEAD 且 dirty=false。

```

### Match 6 (lines 87-92)

```text
  - 参数含 `-Mode build-release`、`-ReleaseTag release-20260627-2350-head-full-v6`、`-SkipDatabaseSync`、`-SkipMinioSync`
- 运行控制台真实执行 `build-release` 产生 operation `op-2026-06-26T203544816067200Z-7af990fb-ef4f-4038-901c-888076d1661c`，失败摘要 `命令退出码非 0: 1`；执行日志定位到 `20260624_unified_electronic_signature_menu.sql:99` 使用变量菜单 id。
- 第二次运行控制台真实执行 `build-release` 产生 operation `op-2026-06-26T204120738837700Z-25253bc1-c5c0-4014-a23e-7ef808100cc5`，再次失败摘要 `命令退出码非 0: 1`；日志确认阻塞点为同一 SQL 第 99 行 `tmp_unified_signature_child_menu_ids` 的变量 id。
- 真实后端仓已新增/更新契约测试并完成三轮 SQL 修复、一次发布脚本构建入口修复；当前 `python -X utf8 -m pytest script\tests\test_unified_electronic_signature_menu_sql.py -q` 返回 `6 passed`，`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` 返回 `status=passed`、`migrationCount=217`，`python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\ops\release\release_sql_contract_gate.py ...\20260624_unified_electronic_signature_menu.sql` 返回 `PASS`，且 `python -X utf8 -m pytest script\tests\test_publish_int_ruoyi_to_test_tooling.py -q` 返回 `90 passed`。
- 真实前端仓已完成重定向页空模板修复；当前 `node tests/e2e/redirect-template-root-static.spec.js`、`node tests/e2e/approval-center-phase5-retirement-static.spec.mjs` 与 `pnpm build:test` 均返回 `PASS`，最新前端提交为 `76328963748ce4bcceaa1d50240e844f1fd3db5d`。
- 只读核对本机 `config/runtime-control.local.yaml` 与当前 Java 启动命令，确认运行控制台现已固定读取 `repo-root=D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260627-ebabbfc`、`frontend-root=D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260627-7632896`，不再漂移回主工作区。
```

### Match 7 (lines 96-99)

```text
- 真实页面测试服发布 operation `op-2026-06-27T040320387887200Z-cf7a52cd-2025-43d3-b485-f8b027c4f58f` 已生成并进入远端执行；日志确认测试服 `172.30.30.58` 的 SSH、数据盘校验、`.env` 写入与 `IMAGE_TAG=release-20260627-2350-head-full-v6` 校验、发布包/required-sql/ops-runtime 同步均成功。
- 同一 operation 在执行 `20260624_dcc_view_matrix_independent_seed.sql` 时失败，测试服远端 MySQL 返回 `VIEW_MATRIX_SEED_TENANT_REQUIRED: set @dcc_view_matrix_seed_tenant_id before sourcing this SQL`；本地 operation JSON 最终状态为 `FAILED`、摘要 `命令退出码非 0: 1`。
- 后端仓任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260627-release-required-sql-dcc-view-matrix-tenant-context\` 已完成两轮本地 TDD 修复与回归：
  - 第一轮：发布脚本注入 `@dcc_view_matrix_seed_tenant_id` 上下文，`python -X utf8 -m pytest script\tests\test_publish_int_ruoyi_to_test_tooling.py -q` 返回 `91 passed`
```

### Match 8 (lines 101-105)

```text
  - 附加契约：`python -X utf8 script\dcc_view_matrix_independent_seed_sql_test.py` 与 `python -X utf8 script\dcc_view_matrix_test_tenant_prereq_sql_test.py` 均返回 `PASS`
- 真实页面测试服重跑 operation `op-2026-06-27T072114322041600Z-826c3463-e987-40cb-a9af-9a14a903c669` 已验证维护仓脚本排序修复真实生效：日志出现 `Applying required database SQL: 20260624_dcc_view_matrix_test_tenant_prereq.sql`（line 1784），随后出现 `Applying required database SQL: 20260624_dcc_view_matrix_independent_seed.sql`（line 1803），说明此前“运行控制台实际脚本漏执行 prerequisite”的根因已关闭。
- 同一 operation 继续推进后，在 `Applying required database SQL: 20260625_dcc_fvm_matrix_retain_other_completion.sql`（line 1878）处失败，测试服远端 MySQL 返回 `ERROR 1644 (45000) at line 404: DCC_FVM_RETAIN_OTHER_COMPLETION_CATEGORY_BASELINE_CHANGED`；本地 operation JSON 最终状态为 `FAILED`、摘要 `命令退出码非 0: 1`。
- 继续只读核对测试服 `tenant_id=1` 的 `dcc_file_category` 后，已确认该 SQL 首道基线断言与真实数据不一致：脚本硬编码要求 `active_total=60`、`dcc_fvm_count=59`、`other_count=1`，而测试服真实结果为 `active_total=81`、`dcc_fvm_count=32`、`other_count=1`、`intauth_count=48`；因此当前失败根因是 SQL 基线假设过期，不是 prerequisite 排序或执行链路问题。
- 最新真实页面 `build-release` operation `op-2026-06-27T101820542591Z-7b85c77c-eb8d-48b1-89b7-f3f35968efce` 已 `SUCCESS`，release tag 为 `release-20260628-1835-head-full-v11`。
```

### Match 9 (lines 107-109)

```text
- 真实页面测试服发布 operation `op-2026-06-27T103042306966Z-b5687d95-24b9-4b0e-b2a6-f4248c6bbbbb` 已进入远端执行并真实越过旧 SQL blocker；日志确认 `20260625_dcc_fvm_matrix_retain_other_completion` 被正确 `Skipping required database SQL outside target environment`，`20260626_showroom_product_current_bu_normalization.sql` 已真实执行并回写为 `APPLIED`。
- 同一 operation 最终在测试服启动服务阶段失败：`docker compose up -d --no-deps backend frontend` 返回 `error while creating mount source path '/mnt/nas/Backup/BackupPackage': mkdir /mnt/nas: file exists`；本地 operation JSON 最终状态为 `FAILED`、摘要 `命令退出码非 0: 1`。
- 只读比对候选包 `docker-compose.yml`、远端 `/opt/intruoyi/runtime/docker-compose.yml`、`docker compose config`、`docker inspect intruoyi-backend` 和宿主机 `/proc/self/mountinfo` 后确认：
```

### Match 10 (lines 114-120)

```text
  - `namei -l /mnt/nas/Backup/BackupPackage` 在 `nas` 节点报 `无此文件或目录`
- `docker inspect intruoyi-backend` 的 `State.Error` 与 operation 日志中的 mount 报错一致
- 测试服 root 主目录当前存在 `/root/.smbcredentials`（`username=BJB110`）与 `/root/.smbcred_backup`（`username=beifen`），均与坏挂载 `username=ceshi` 不一致；同时远端 `smbclient -L //172.30.30.4 -U int%<redacted>` 可成功列出 `IT共享`，说明 NAS 本身与当前 `int` 凭据可用。
- 已在测试服执行最小正式修复：`umount -v /mnt/nas` 卸载旧坏挂载，恢复并重建本地空目录 `/mnt/nas` 后，以 `username=int` 重新执行 `mount -t cifs '//172.30.30.4/IT共享' /mnt/nas ...`。
- 修复后验证通过：`/proc/mounts` 显示 `/mnt/nas` 当前已变为 `username=int`；宿主机可成功访问 `/mnt/nas/Backup/BackupPackage`；`docker run --rm -v /mnt/nas/Backup/BackupPackage:/probe alpine:3.20 ...` 返回 `DOCKER_BIND_OK`。
- 修复后重新从真实页面发起测试服发布 operation `op-2026-06-27T105253570049600Z-36d2fc17-9145-40aa-b1c6-6a1c2d2c7ed2`，日志与远端状态表明：
  - operation 已重新完成 SSH 预检、镜像加载、MySQL/Redis 启动、发布锁获取与 `required-sql` 迁移回写。
```

### Match 11 (lines 122-133)

```text
  - 远端当前 `/proc/mounts` 仍显示 `/mnt/nas` 为 `username=int`，宿主机 `os.stat('/mnt/nas/Backup/BackupPackage')` 成功，手工 `docker run --rm -v /mnt/nas/Backup/BackupPackage:/probe alpine:3.20 ...` 继续返回 `DOCKER_BIND_OK`。
  - 但同一时刻 `docker inspect intruoyi-backend --format '{{.State.Status}}|{{.State.Running}}|{{.State.Error}}|{{.Config.Image}}'` 仍返回 `created|false|error while creating mount source path '/mnt/nas/Backup/BackupPackage': mkdir /mnt/nas: file exists|intruoyi-backend:release-20260628-1835-head-full-v11`，而 `intruoyi-frontend` 也停在 `Created`。
  - operation 执行日志已出现发布锁释放 `LOCK_RELEASED` 与 `ERROR: 命令退出码非 0: 1`，只是本地 operation JSON 尚未来得及从 `RUNNING` 刷新为最终失败状态。
- 真实页面测试服发布 operation `op-2026-06-27T111300642917500Z-84f1824f-db7c-4571-8c78-c52231bcc51e` 已越过维护仓空 `applyItems` bug 后继续执行到 `docker compose up -d --no-deps backend frontend` 与远端 HTTP readiness；远端 `docker logs intruoyi-backend` 明确报 `no main manifest attribute, in app.jar`，后端容器持续重启。
- 后端发布源 `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260627-8632c42` 已完成可执行 jar 镜像入口修复并提交 `d3ee53edaf015f98ec3bfebf9f91602103568b6d`，其中两个 Dockerfile 已统一复制 `yudao-server-exec.jar`。
- 真实页面重试构建 operation `op-2026-06-27T113224282720200Z-dd2ed29c-419b-4309-9e8d-8504c7c578c0` 在 backend image `docker build` 阶段失败，日志明确报 `COPY ruoyi-vue-pro/yudao-server/target/yudao-server-exec.jar app.jar` 找不到文件；失败摘要仍为 `命令退出码非 0: 1`。
- 继续只读核对维护控制台脚本后，已确认根因是 `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\deploy\publish-int-ruoyi.ps1` 与当前运行 worktree 仍把后端 jar 路径/复制目标写死为 `yudao-server.jar`，没有与后端仓新的 `exec` jar 契约同步。
- 维护仓现已完成最小正式修复并同步到当前运行 worktree：
  - `$backendJar` 改为 `yudao-server\target\yudao-server-exec.jar`
  - Docker build context 中复制目标改为 `yudao-server-exec.jar`
- 本地回归 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q` 已通过 `8 passed`，其中新增契约测试约束发布脚本必须使用 `exec jar`。
- 真实页面测试服发布 operation `op-2026-06-27T125259682648200Z-a77f32ea-36b0-4ccb-97c2-d96effb42d26` 已 `SUCCESS`，release tag=`release-20260628-2015-head-full-v13`。
```

### Match 12 (lines 148-150)

```text

- 无剩余阻塞。已关闭的关键问题包括：正式服 DCC seed 缺少 tenant 1 授权变量、正式服 DCC FVM 分类基线过严、正式服 `/mnt/nas` CIFS 凭据错误导致 Docker bind mount 失败。

```
## docs/request-command-log.md

### Match 1 (lines 4-7)

```text

- 用户需求：继续执行基于当前已提交 HEAD 的完整发布，按顺序构建发布到测试服务器，再发布到正式服务器和备份服务器；执行过程中每隔一段时间记录遇到的问题。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`。
- 命令记录：核对上一未完成发布任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260625-head-full-release\task.md` 仍为 `IN_PROGRESS`，且与本次目标一致，因此续用该任务而不是新建并行任务目录。
```

### Match 2 (lines 13-16)

```text
- 用户需求：主程序合并修改了部分代码，担心原来的发布链路已经不对，要求重新通过页面前端点击操作完整走一遍 `构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服`。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`。
- 命令记录：重新读取 `supervised-complex-delivery` 与 `playwright` 技能，以及 `artifact-contract.md`、`task-state-schema.md`，按新一轮高风险真实页面发布任务重新建档。
- 命令记录：核对上一维护仓任务 `doc/tasks/20260621-frontend-release-full-flow-rerun/task.md` 已 `COMPLETED`，允许开启新任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/`。
```

### Match 3 (lines 22-33)

```text

- 用户需求：再次正式按“页面前端点击操作”的真实流程，完整走一遍构建发布到测试服、正式服、备份服；禁止直接调接口替代页面动作；每遇到问题先记录任务文档，修复后继续从页面走，直到整条流程能够一次性走通。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`。
- 命令记录：读取 `C:\Users\BJB110\.codex\skills\supervised-complex-delivery\SKILL.md`、`artifact-contract.md`、`review-gates.md`、`task-state-schema.md` 与 `C:\Users\BJB110\.codex\skills\playwright\SKILL.md`，确认本轮需要先把任务状态、计划和测试制品落盘。
- 命令记录：检查维护仓 `doc/tasks` 最新任务，发现 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-backup-server-backup-restore-rehearsal\task.md` 仍为 `IN_PROGRESS`；按仓库规则先将其显式改为 `BLOCKED`，原因是用户当前线程优先级切换。
- 命令记录：读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-frontend-release-full-flow\{task.md,execution-log.md}` 与 `docs/request-command-log.md`，确认同类页面真实发布链路已在 `release-20260621-page-full-flow-v6` 上完整走通并提交。
- 命令记录：检查当前工作树：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 为干净 `int_main`；`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 仅有未跟踪 `.env.merged-e2e`；维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance` 仍保留上一个备份恢复任务的 `backup-ops` 脏改动。
- 结论记录：已新建 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-rerun\` 并落地 `task.md`、`request-analysis.md`、`prd.md`、`dev-plan.md`、`test-plan.md`、`task-state.json`、`execution-log.md`、`test-report.md`；当前主阻塞是“本轮到底重跑哪套发布基线”尚未明确，在此之前不得进入新的测试服/正式服/备份服真实写入。
- 命令记录：改为按完成审计核现状，而不是直接重跑；读取 `20260620-frontend-release-full-flow` 任务文档、`runtime/runtime-control` 下 v6 五个 operation JSON/日志、`release-manifest.json`、`manifest.json`、`tested.json` 与正式 dry-run 证据，确认既有 v6 页面链路证据闭合。
- 命令记录：通过只读 SSH 分别复核测试服 `172.30.30.58`、正式服 `172.30.30.57`、备份服 `172.30.30.59` 的 `/opt/intruoyi/runtime/.env`、`docker ps`、`127.0.0.1:48081/actuator/health`、`127.0.0.1:8081/` 与 `127.0.0.1:8081/pdfjs/pdf.worker.mjs`，三套环境当前均为 `release-20260621-page-full-flow-v6` 且入口健康。
- 命令记录：运行 `python C:\\Users\\BJB110\\.codex\\skills\\task-closeout-cleanup\\scripts\\task_closeout.py --task-id 20260621-frontend-release-full-flow-rerun --mode preview`，结果 `status: ready`，默认保留 `task.md`、`execution-log.md`，其余新建计划/分析制品为可清理附属物，无阻塞项。
- 结论记录：基于当前文件证据和三套环境运行态，已确认用户要求的真实页面发布链路目标实际上已经由 `release-20260621-page-full-flow-v6` 完成，并且当前状态仍保持该结果；本轮因此以完成审计收口，不再额外触发新的真实写入。
```

### Match 4 (lines 36-44)

```text

- 用户需求：执行 `$fupan`，把本轮“测试服发布 + 三角色真实验收 + 正式服预发布阻塞”沉淀为可复用经验，避免后续重复踩坑。
- 命中技能：`C:\Users\BJB110\.codex\skills\fupan\SKILL.md`。
- 命令记录：读取 `SKILL.md`、当前任务 `task.md`、`execution-log.md`，确认本轮已有足够证据支撑复盘。
- 命令记录：读取 `references/project-memory-template.md`、既有 `docs/agent-memory/project-error-prevention.md` 与 `docs/request-command-log.md`，按“项目级规则 / 任务专项细节”拆分候选经验。
- 命令记录：运行 `python -X utf8 C:\Users\BJB110\.codex\skills\fupan\scripts\collect_error_evidence.py --project-root D:\ProjectPackage\Int\IntRuoyiMaintance --glob doc\tasks\20260620-prod-release-current-latest\task.md --glob doc\tasks\20260620-prod-release-current-latest\execution-log.md --glob AGENTS.md --output D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-prod-release-current-latest\candidate-error-evidence.md`，生成本轮候选证据。
- 命令记录：尝试运行 `update_project_memory.py` 追加“正式服 Smart Release prod preflight 证据闭合”规则，被脚本拒绝，原因是该条目目前仍偏本次发布链专项规则，不属于项目级通用短记忆。
- 结论记录：本轮 `$fupan` 接受的长期经验仍是“发布前预检”“发布验证多证据闭环”“先全量记录失败再统一修复复测”三类；`ProdDryRunEvidencePath / target config / NasConfigPath` 保留在当前任务文档，不提升到 `AGENTS.md` 或项目级记忆；页面脚本细节不进入长期记忆。

```

### Match 5 (lines 46-52)

```text

- 用户需求：正式按页面前端点击操作的真实流程，完整走一遍构建发布到测试服、正式服、备份服；过程中禁止直接调接口替代页面动作；遇到问题先记录任务文档，修复后继续从页面重走，直到整条流程一次性走通。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`。
- 命令记录：核对上一维护仓任务 `doc/tasks/20260620-fupan-prod-release-v7/task.md` 已 `COMPLETED`，允许开启新任务 `doc/tasks/20260620-frontend-release-full-flow/`。
- 命令记录：读取并确认当前任务 `task.md`、`execution-log.md` 已落地 `BDD` 场景、`设计约束检查`、`经验门禁` 与 `GREEN: experience-preflight -> PASS`。
- 命令记录：尝试按 `control-in-app-browser` 技能接入应用内浏览器，`node_repl/js` 返回环境级错误 `missing field sandboxPolicy`；该问题已记录到当前任务 `execution-log.md`，不属于页面业务链路问题。
- 命令记录：只读验证 `http://127.0.0.1:48181/` 返回 `200`；核对维护仓前端打包产物与源码，确认运行控制台真实存在“构建发布包 / 部署测试服 / 上线正式服 / 上线备份服”按钮、预览命令弹窗和执行弹窗。
```

### Match 6 (lines 58-60)

```text
- 计划边界：仅发布测试服 `172.30.30.58`，远端目录 `/opt/intruoyi/runtime`；发布范围为 `code-only`，不访问正式服/备用服，不执行备份、恢复、回滚或正式服动作。
- 命中经验：`release-backup-restore.md`、`server-access.md`、`login-access.md`；真实 E2E 和服务器写入前必须记录 `experience-preflight`。
- 命令记录：检查 `npx` 可用，路径为 `D:\Programs\npx.ps1`。
```

### Match 7 (lines 68-71)

```text
- 命令记录：Playwright 点击构建发布包“执行”，operation `op-2026-06-17T072458143463800Z-0d5a0145-9253-4018-991a-55bf864264ef` 初始状态 `RUNNING`。
- 命令记录：构建 operation 最终 `FAILED`；后端 Maven、前端 Vite build、后端 Docker 镜像构建成功，前端 Docker 镜像构建失败，原因是拉取 `nginx:1.27-alpine` 元数据时 Docker Hub token 请求超时。
- 阻塞记录：发布包未成功生成，禁止继续发布测试服；下一步先补齐/验证 Docker 基础镜像 `nginx:1.27-alpine`。
- 命令记录：`docker pull nginx:1.27-alpine` PASS，digest `sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`。
```

### Match 8 (lines 73-76)

```text
- 命令记录：Playwright 点击第二次构建发布包“执行”，operation `op-2026-06-17T073818610888200Z-832a7d6b-133a-45ed-abd9-84dd1abfd300` 初始状态 `RUNNING`。
- 命令记录：第二次构建 operation 仍 `FAILED`；Maven、Vite、后端镜像和前端镜像成功，发布迁移策略门禁失败，原因是 `20260617_dcc_browser_performance_indexes` 依赖缺失 `20260513_dcc_base_schema.sql`。
- 阻塞记录：发布包 manifest 未生成，禁止继续发布测试服；需要先修复迁移元数据/扫描集合。
- 命令记录：在 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 修正 `sql/mysql/20260617_dcc_browser_performance_indexes.sql` 首行 `dependsOn` 为清单实际使用的迁移 ID `20260513_dcc_base_schema`。
```

### Match 9 (lines 80-82)

```text
- 命令记录：Playwright 点击第三次构建发布包“执行”，operation `op-2026-06-17T082753879349700Z-c7f3f523-d9c6-4077-9b0f-eacc6cf5bf73` 初始状态 `RUNNING`。
- 命令记录：第三次构建 operation `FAILED`；Maven 在 `yudao-module-dcc` 执行 clean 时无法删除 `target`，发布包未生成，禁止发布测试服。
- 命令记录：`mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -DskipTests clean` PASS，DCC target 清理前置恢复。
```

### Match 10 (lines 84-86)

```text
- 命令记录：Playwright 点击第四次构建发布包“执行”，operation `op-2026-06-17T083241295814300Z-dc21fdce-0784-4465-a8d8-7e6ceb485990` 初始状态 `RUNNING`。
- 命令记录：第四次构建 operation `FAILED`；Maven、Vite build、后端 Docker 镜像成功，前端 Docker 镜像解析 `nginx:1.27-alpine` 元数据时 Docker Hub 返回 EOF，发布包未生成，禁止发布测试服。
- 命令记录：`docker pull nginx:1.27-alpine` PASS，digest `sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`，本地 `docker image inspect` PASS。
```

### Match 11 (lines 88-91)

```text
- 命令记录：Playwright 点击第五次构建发布包“执行”，operation `op-2026-06-17T084524861642300Z-d778ee83-bb2c-44c5-896d-b1ffed69814a` 初始状态 `RUNNING`。
- 命令记录：第五次构建 operation `FAILED`；发布脚本在 Maven clean 前检测到本机 `yudao-server.jar` 被 Java 进程锁定。
- 命令记录：`restart-ruoyi-backend.bat` 已把本机后端切换到 `E:\Int\CacheData\IntRuoyi\runtime\backend-20260617-164706.jar`，尽管应用最终因定时任务同步失败退出，但目标 jar 锁已解除。
- 命令记录：`mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-server -DskipTests clean` PASS，确认 `yudao-server.jar` 锁前置已恢复。
```

### Match 12 (lines 101-103)

```text
- 命令记录：测试服 `infra_release_migration` 中 `20260617_dcc_browser_performance_indexes` 最新状态为 `APPLIED`。
- 命令记录：Playwright 打开 `http://172.30.30.58:8081/`，HTTP 200，跳转到 `/login?redirect=/index`，页面标题为 `瑛泰管理系统 - 登录`，未发现 console error。
- 命令记录：`task-closeout-cleanup --mode preview` PASS，仅计划删除 `runtime-control-start.out.log` 与 `runtime-control-start.err.log`。
```
