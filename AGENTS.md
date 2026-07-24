# Related Project Paths

- IntAuth: `D:\ProjectPackage\Int\IntAuth`
- IntKB: `D:\ProjectPackage\Int\IntKB`
- IntGY: `D:\ProjectPackage\Int\IntGY`
- IntPP: `D:\ProjectPackage\Int\IntPP`
- IntBatchRecord: `D:\ProjectPackage\Int\IntBatchRecord`
- Thread baseline: IntRuoyi 主程序根目录固定为 `E:\IntRuoyi`；后端路径固定为 `IntRuoyiBackend`，前端路径固定为 `IntRuoyiFronted`，均相对该根目录。
- Thread baseline: 测试服/正式服 IP 与访问方式统一见 `E:\IntRuoyi\docs\server-access.md`；涉及服务器状态检查、重启、发布或联调时先按该文档执行。
- Thread baseline: 正式环境/测试环境登录方式统一见 `E:\IntRuoyi\docs\login-access.md`；涉及登录验证、联调或 E2E 时先按该文档使用对应租户账号。
- Thread baseline: 涉及备份、恢复、发布、构建、回滚任务前必须先阅读 `E:\IntRuoyi\docs\release-backup-restore.md`。
- Thread baseline: 正式服 /mnt/nas 是公司共享盘，禁止删除、清空或移除挂载/fstab。
- Thread baseline: 发布失败先查 migration/manifest/脚本契约，再查环境；后端产物或环境变量契约变更时，维护仓脚本与测试必须同步修改。
- Thread baseline: 完整发布只认单一 releaseTag 的 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup` 闭环；不得拼接多轮 releaseTag 结果。
- Thread baseline: 用户明确要求“仅测试服发布”时，成功范围止于同一 releaseTag 的 `build-release -> publish-test` 及测试服真实运行态、页面、版本号和变更说明验证；禁止执行 `mark-tested`、`promote-prod` 或 `promote-backup`，不得因未走完整发布链而误判测试服发布失败。
- Thread baseline: 发布成功必须同时核 operation=SUCCESS、manifest、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP 200；缺任一项不得判定完成。
- Thread baseline: 每次构建发布一律在临时发布 worktree 中执行，禁止直接在主工作区执行构建、验证或发布。
- Thread baseline: 临时发布 worktree 必须检出本次发布目标提交；构建发布输入固定为该目标提交对应的 Git 已提交内容，未提交改动、未跟踪文件和脏工作区内容一律不得进入发布包。
- Thread baseline: 主工作区固定为各仓库用于持续开发和最终融合的 `int_main` 工作区；主工作区只用于日常开发、最终融合和发布收口，不作为直接发布执行环境。
- Thread baseline: 每次发布开始前必须新建本次专用的临时发布 worktree；该 worktree 只用于本次发布隔离环境，不得跨任务复用，不得作为长期开发工作区。
- Thread baseline: 临时发布 worktree 未产生新提交时，发布完成后必须直接删除。
- Thread baseline: 临时发布 worktree 产生新提交时，必须先将新提交合回对应仓库 `int_main`，并在合并结果上完成必要验证；验证通过后必须删除该临时发布 worktree。
- Thread baseline: 临时发布 worktree 存在未确认归属的改动、未合并提交或验证未通过问题时，任务状态必须标记为阻塞；阻塞状态下不得删除该 worktree，不得宣称本次发布完成。
- Thread baseline: 发布流程和运行态验证完成后，任务状态先标记为 `ready_for_closeout`；只有发布结论已记录、本任务拥有的临时发布 worktree 已删除、本任务启动或改动的运行控制台已恢复任务前稳定路径后，才能标记 `completed`。其他并发任务的 worktree、进程和控制台实例不得删除或停止，也不因其存在阻塞本任务收尾，除非双方正在争用同一测试环境或发布锁。
- Thread baseline: 每次使用临时发布 worktree 时，任务文档和 `execution-log.md` 必须记录 worktree 路径、目标提交、构建命令、验证命令、是否产生新提交、是否已合回 `int_main`、最终删除结果。

## Mixed Git Workspace Policy

- 本项目为混合 Git 工作区；凡要求新建或使用新分支，只在本任务实际参与且需要修改的 Git 仓库创建同名分支，不得在无关仓库制造分支状态。
- Thread baseline: 涉及 worktree 创建、合并、清理或排障时，先阅读 `E:\IntRuoyi\docs\worktree-memory.md`。
- Thread baseline: Codex 并行开发默认一任务一独立 worktree 工作区；前后端成对建同名分支，根目录仅用于协调与最终集成。
- Thread baseline: IntRuoyi 根目录 Git 不作为融合结果判断项；融合以前后端 `IntRuoyiBackend` 与 `IntRuoyiFronted` 仓库为准。
- Thread baseline: worktree 合并后必须在合并结果上验证相关功能正确性；验证未通过不得视为完成或继续清理 worktree。

## Unified Frontend Style

- All frontend work must follow `D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`.
- The shared frontend baseline is the IntPP production order list style; read the style file before creating or redesigning frontend pages, components, tables, filters, forms, or action areas.
- Thread baseline: 前端本地入口固定为 `http://localhost:8081`；涉及前端调试、联调、验证或 E2E 时默认从该入口进入。
- Thread baseline: 展厅前端路径固定为 `D:\ProjectPackage\Website`；涉及展厅前端代码、调试与联调时默认使用该目录。

## Agent Task Documentation Policy

- Before starting any task, the Agent must create or identify the task directory under `doc/tasks/<task-id>/` and write the task document first.
- Thread baseline: 每次任务将用户需求、执行命令意图和验证结果记录到 `docs/request-command-log.md`；密码、token、私钥、连接串和其他凭据必须脱敏，含明文凭据的原始日志不得提交。
- Thread baseline: 每次任务创建或识别任务目录后，必须先读取 `docs/experience-index.md`，按索引只打开命中的经验文档，并在任务文档写入 `经验门禁` 小节，列出本任务适用的强制门禁；不得只写“已阅读”而不摘取门禁。
- Thread baseline: 后续新增经验默认优先写入事前文档入口；仅事后复盘内容才写入 error-prevention 类文档。
- Thread baseline: 后续新增或更新经验必须遵循 `docs/experience-index.md` 的“经验文档写入规范（强制）”；优先更新已有归宿，门禁摘要固定包含 `Trigger`、`Preflight check`、`Blocker`、`Verification`、`Forbidden action`、`Evidence`，不得只写背景、结论或“下次注意”。
- Thread baseline: 能转为前置检查的问题必须写成可执行门禁；涉及操作流程时还必须写明阶段必查项、推荐命令、Fail Fast、必须记录，并同步更新 `docs/experience-index.md` 的关键词路由和对应执行 checklist。
- Thread baseline: 涉及真实 E2E、Playwright 长链路、登录后写入、服务器写入/重启/发布/备份/恢复/回滚、大文件上传、批量导入、worktree 合并/清理、数据库 schema/迁移/权限/菜单/租户数据修改等高风险动作前，必须在 `execution-log.md` 记录 `GREEN: experience-preflight -> PASS` 或明确 `BLOCKER: experience-preflight -> <原因>`，否则不得执行该高风险动作。
- The task document must include the task goal, milestone list, expected verification, and current status before production code changes begin.
- The task document must include a fixed `设计约束检查` section before production code changes begin:
  - `是否引入 fallback/降级/吞异常`：是/否；如是，必须注明用户明确要求、触发条件、风险与移除/回滚策略。
  - `是否从根因和长期维护角度解决`：是/否；如否，必须先阻塞并说明缺少的正式方案前置条件。
  - `是否存在临时补丁或绕过`：是/否；如是，必须注明用户明确批准范围、风险和后续处理。
- After each milestone is reached, the Agent must update the task document with milestone status, completed work, verification evidence, and remaining blockers.
- Implementation and required verification完成后，如清理、合并或 worktree 删除尚未完成，`## Current Status` 必须写为 `ready_for_closeout`。
- When the task is finished, the Agent must mark the task document as completed and record the final verification result.
- Before starting a new task, the Agent must check the most recent task document owned by the current thread or current task chain in the same service repository. If it is not marked completed, the Agent must finish or explicitly block that owned task before working on the new task; unrelated concurrent task documents are not treated as the current task's predecessor.
- If the current thread's previous owned task cannot be completed because of missing prerequisites, the Agent must record the blocker and impact in that task document, then report it before starting the new task.

- For all six microservice Agents, implementation changes must be committed to the owning service Git repository after required verification passes and before destructive closeout or integration.
- Closeout、合并和 worktree 删除验证通过后，才把任务标记为 `completed`，并单独提交最终任务记录。
- Each commit must include only files directly produced by the current work item; do not include unrelated user edits, other Agent changes, or temporary output.
- If verification fails or a required precondition is missing, fail fast and report the exact blocker and impact before committing.
- Use a concise commit message that names the result, preferably in Chinese, for example `任务: 更新权限校验`.

# Global BDD + TDD Policy

- 后续所有功能、修复、重构和行为变更默认采用 BDD + 严格 TDD。
- BDD 必须先写清楚用户、业务或接口可观察的 `Given / When / Then` 场景，再进入实现。
- TDD 必须按 `RED -> GREEN -> REGRESSION` 执行：先失败测试，再最小实现，最后回归验证。
- BDD 场景与 TDD 证据必须记录到 `doc/tasks/<task-id>/execution-log.md`。
- 建议使用 `BDD: <scenario name> -> Given/When/Then`、`RED: <command> -> FAIL, <expected reason>`、`GREEN: <command> -> PASS` 标记。
- 缺少前置条件、依赖、测试环境或测试数据时必须失败并报告；不得用 mock 成功、静默跳过、降级或 fallback 掩盖。

- Thread baseline: 未明确说明时，e2e 测试用例必须使用真实数据，不得使用 mock 数据。
- Thread baseline: 测试统一使用独立测试租户登录，禁止用备份数据方案代替真实测试环境。

## Git 自动提交规范

- 实现和必要验证通过后，先单独提交本任务实现变更；task-closeout、合并和 worktree 删除验证通过后，再单独提交最终任务记录。不得把 `completed` 作为实现提交的前置条件。
- 提交前只暂存与当前任务直接相关的文件，不得顺手提交其他任务、用户改动或临时输出。
- 如果验证失败、缺少前置条件或存在未解决阻塞，必须先报告失败原因和影响，不得用 mock 成功、静默跳过、降级或 fallback 掩盖后提交。
- 提交信息必须简洁说明任务结果，优先使用中文，格式建议为 `任务: <简短说明>`。

## Change Design Policy

- 凡涉及任何修改，包括功能、修复、重构、配置、脚本、文档、测试与其他交付物变更，必须先从长期可维护、可扩展的方向评估方案，优先采用正式可持续方案，不得默认提交短期临时方案、一次性补丁或仅为绕过当前问题的权宜改动。
- 如用户明确要求临时方案，必须先记录适用范围、触发条件、风险与后续移除/回滚策略，并仅在用户明确批准的范围内最小化实施。

## Refactor Workflow Policy

- 凡涉及重构，必须先从长期可维护、可扩展的方向评估方案，先写任务文档，再采用 Subagent-Driven Development 方式执行重构。

- Thread baseline: E2E 必须走真实用户路径；只用 Playwright 操作前端，接口仅用于最终校验。发布、审计或独立验证时若前端无入口必须 fail fast 并记录，不得临时改产品扩大范围；功能或修复任务仅在入口属于已批准范围且先完成 BDD + TDD 时补入口。
- Thread baseline: Playwright 版本、运行目录与浏览器路径继承 `D:\ProjectPackage\AGENTS.md`，维护仓不重复定义共同规则。

- Thread baseline: E2E 不得为测试额外增加前端控件或内容；发现错误必须主动暴露，不得隐藏或绕过。
- Thread baseline: 删除前端控件时必须先确认是“仅隐藏入口”还是“下线完整功能”；只有用户范围或正式需求明确下线完整功能时才同步删除后端能力。无此依据不得扩大为后端删除；两种情形都必须更新相关文档和测试并运行受影响测试。
- Thread baseline: DCC审核矩阵/审批路线必须保持与 `D:\ocr2\resource\审核会签.pdf` 确认版一致；未经用户明确批准，任何测试、联调或 E2E 不得切换、覆盖或改写 live 审核矩阵版本。
- Thread baseline: 本机展厅默认文件配置 `infra_file_config.id=28`、默认 bucket `yudao`、默认域 `http://127.0.0.1:9000/yudao` 视为受保护资源；未经用户明确授权，任何 E2E、联调、脚本或人工操作不得修改、切换、覆盖或绑定到其他 bucket/domain/endpoint。
- Thread baseline: 任何 E2E、联调、脚本或人工操作都不得把 `config_id=28` 且 `path LIKE 'showroom/%'` 的默认展厅媒体 URL 改写到非默认受保护域；发现默认展厅文件配置或 `showroom/%` 媒体 URL 漂移时必须 fail fast，禁止继续启动、继续 E2E 或用临时同步/回填掩盖问题，除非用户明确批准本次修复范围。
- Thread baseline: PowerShell 5.1 不使用 `&&`；命令改为分行执行或用 `;` 连接。
- Thread baseline: PowerShell 任务涉及中文参数、中文正则、中文 SQL、SSH/MySQL 标准输入、多行 inline 脚本或 here-string 时，执行风险命令前必须读取 `E:\IntRuoyi\docs\powershell-memory.md` 并按其设计编码与退出码验证路径。

## Encoding Safety Policy

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
- Thread baseline: 所有端到端测试必须由 Playwright 实际打开页面并先登录后操作；只读场景复用既有真实数据；创建、导入、编辑、删除等写入型场景允许且必须仅通过真实前端在测试租户创建带任务标识、可追踪且可清理的用例数据。禁止 mock、接口或 SQL 绕过、修改芋道源码租户、使用备份数据冒充测试环境或兜底成功；缺少必要基线数据必须 fail fast。
- Thread baseline: `测试租户`指租户名称`测试租户`、账号名称`aoteman`；`芋道源码`指租户名称`芋道源码`、账号名称`admin`。
