# Candidate Error Prevention Evidence

- Generated At: 2026-06-20T15:35:26
- Project Root: D:\ProjectPackage\Int\IntRuoyiMaintance
- Source Files Scanned: 3
- Files With Matches: 3
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
## doc/tasks/20260620-prod-release-current-latest/execution-log.md

### Match 1 (lines 4-12)

```text

- BDD: 测试服先发布再正式发布 -> Given 当前最新程序待发布 / When 执行本次发布任务 / Then 必须先构建同一发布包并部署测试服验证通过，再允许推进正式服发布。
- BDD: 正式服 Website 数据必须受保护 -> Given 正式服存在受保护的 website 数据 / When 审计并执行正式服发布 / Then 发布动作只能落在本次批准的代码包边界，若存在 Website/MinIO/NAS 数据覆盖风险则必须阻塞。
- BDD: 发布完成必须以多重证据判定 -> Given 构建和部署动作已提交 / When 判断测试服或正式服发布是否完成 / Then 必须同时具备 operation 成功、manifest 一致、远端 IMAGE_TAG 一致、镜像运行态正常和真实入口验证证据。

- GREEN: experience-preflight -> PASS，已读取 `docs/experience-index.md` 命中的发布/服务器/登录基线与维护仓发布预检经验，当前允许进入高风险动作前的环境审计阶段，但尚未执行服务器写入。
- GREEN: previous-task-check -> PASS，上一维护仓任务 `20260620-fupan-post-release-role-e2e-gate` 已标记 `COMPLETED`。
- GREEN: authorization-check -> PASS，用户已在当前任务明确授权访问和修改正式服务器；同时设定“不得影响正式服 website 数据”为硬边界。

```

### Match 2 (lines 23-28)

```text
- GREEN: remote-status-prod -> PASS，`show-int-ruoyi-remote-status.ps1` 只读核对正式服 `172.30.30.57`：后端、前端、pdf worker、OnlyOffice 均为 HTTP 200，当前 `IMAGE_TAG=26-06-02_20-13-57`。
- GREEN: prod-runtime-boundary -> PASS，SSH 只读核对正式服 `/opt/intruoyi/runtime`：运行数据盘挂载来源与 `/opt/intruoyi/runtime/data` 均为 `/dev/vdb`；`/opt/intruoyi/runtime/website` 目录存在，`intruoyi-website|nginx:1.27-alpine|Up 2 weeks`，说明正式服 website 运行态真实存在，必须视为受保护发布边界。
- GREEN: publish-script-code-only-boundary -> PASS，维护仓 `ops/deploy/publish-int-ruoyi.ps1` 明确以 `-SkipDatabaseSync -SkipMinioSync` 双条件将 `publishScope` 固定为 `code-only`，且 code-only `deploy-release` 会自动保持 `SkipMinioSync=true` 并跳过展厅媒体内容 smoke 检查；若误选 `Component=full/website` 或缺少双 skip 参数，仍可能触碰 Website/MinIO 数据边界。
- GREEN: production-write-local-config -> PASS，本机 `config/runtime-control.local.yaml` 已启用 `maintenance.runtime-control.production-write-enabled: true`，具备正式服动作本地开关前置。
- BLOCKER: prod-dry-run-evidence-missing -> 正式服 `deploy-release` 必须提供 `ProdDryRunEvidencePath`，其证据必须满足 `status=passed`、`targetEnvironment=prod`、`mode=preflight-release`、`writeActions=[]`。当前仓库仅存在 `ops/release/templates/deploy-target-config.schema.json`，未发现现成生产 target config 文件，也未发现 `INTRUOYI_SMART_RELEASE_TARGET_CONFIG_PATH` 等 Smart Release 输入环境变量，因此正式服 dry-run 证据链尚未闭合。

```

### Match 3 (lines 32-34)

```text
- GREEN: build-release-backend -> PASS，`op-2026-06-20T060518010428400Z-74f9540b-f687-4a2b-aceb-bb1cc0372585` 日志显示 `mvn -f ... -pl yudao-server -am -DskipTests clean package` 已 `BUILD SUCCESS`，后端 jar 于 `2026-06-20 14:08:40 +08:00` 重建成功。
- IN_PROGRESS: build-release-frontend -> 当前同一 operation 已进入 `node ... vite.js build --mode test` 前端静态资源构建阶段；截至记录时 operation 仍为 `RUNNING`，尚未生成最终发布成功或失败结论。

```

### Match 4 (lines 40-42)

```text
- GREEN: test-runtime-http -> PASS，测试服后端 `http://172.30.30.58:48081/actuator/health`、前端 `http://172.30.30.58:8081/`、`http://172.30.30.58:8081/pdfjs/pdf.worker.mjs` 均返回 HTTP `200`。
- GREEN: test-release-migrations -> PASS，发布日志确认以下 SRM SQL 已在测试服真实 `APPLIED`：`20260618_srm_d7_1_code_rule_baseline`、`20260619_srm_d7_2_supplier_access_risk`、`20260619_srm_d7_3_plan_framework`、`20260619_srm_d8_1_non_bidding`、`20260620_srm_d10_1_tender`、`20260620_srm_d9_1_contract`。
- GREEN: code-only-boundary-on-test -> PASS，发布日志明确 `Skipping showroom smoke image content check for code-only deploy without Website or MinIO data sync`，本次测试服部署仍保持 `code-only` 边界。
```

### Match 5 (lines 46-48)

```text
- GREEN: fupan-evidence-source -> PASS，本次复盘使用了 `AGENTS.md`、当前任务 `task.md` / `execution-log.md`、既有项目记忆文件与本次构建门禁证据。
- DEFER: fupan-memory-promotion -> `release-migration` 元数据细则已收集，但 `update_project_memory.py` 判定其更偏本次发布链专项规则，暂不提升到 `docs/agent-memory/project-error-prevention.md`；后续若多任务重复出现同类问题，再按项目级模式归纳。

```

### Match 6 (lines 51-54)

```text
- GREEN: role-e2e-script-bootstrap -> PASS，已在当前任务目录新增 `scripts/post-release-role-e2e.cjs`，复用 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 自带 `playwright` 依赖执行测试服真实浏览器验收，并将证据落到当前任务 `evidence/`。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260620-prod-release-current-latest/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781937433288.json` 与 `evidence/post-release-role-e2e-1781937503848.json`：当前脚本初始版本未稳定捕获登录后的菜单树，不能把该结果当成业务结论。
- GREEN: role-e2e-login-debug -> PASS，已补充 `scripts/debug-gaomin-login.cjs`、`scripts/debug-role-page.cjs` 对登录表单和菜单缓存做真实 DOM/缓存探测；初始“账号密码错误”结论已证实为脚本误填用户名输入框，不是业务真实失败。
- GREEN: role-e2e-route-path-fix -> PASS，已修正子路由拼接逻辑：对 `showroom` / `dcc` 子页补齐父级 path 前缀，避免误将 `/showroom/company` 访问成 `/company` 这类伪 404。
```
## doc/tasks/20260620-prod-release-current-latest/task.md

### Match 1 (lines 4-8)

```text

在用户已明确授权访问和修改正式服务器的前提下，先将当前最新程序构建并发布到测试服务器，完成发布后必要验证；确认不会影响正式服 `website` 数据边界后，再将同一发布包发布到正式服务器，并完成发布后验证。

本任务必须严格保护正式服 `website` 数据，不得误触发 Website/展厅数据同步、MinIO/NAS 覆盖或其他超出“当前最新程序发布”范围的数据写入。

```

### Match 2 (lines 12-14)

```text
- 状态：`COMPLETED`
- 处理：上一任务已完成复盘，不存在未收尾阻塞；本任务作为新的发布任务单独建档推进。

```

### Match 3 (lines 17-23)

```text
- 用户已明确授权：访问测试服务器与正式服务器，并执行当前最新程序发布。
- 强制边界：不得影响正式服 `website` 数据。
- 约束落地：
  - 发布前必须确认本次发布为代码包发布边界，避免触发 Website/展厅构筑包、MinIO 同步、整库数据覆盖或其他 `with-data` 行为。
  - 发布前必须核对正式服当前运行目录、挂载、compose、镜像 tag、数据根与 Website 相关目录边界。
  - 若正式服当前架构与维护仓发布脚本不兼容，必须先阻塞并说明具体风险，不得带风险直接发布。

```

### Match 4 (lines 31-33)

```text
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
```

### Match 5 (lines 35-40)

```text
  - 发布前先预检 Docker 基础镜像、迁移策略门禁、Maven target/jar 锁。
  - 发布验证不能只看健康检查，必须同时核 operation、manifest、远端 `IMAGE_TAG`、运行镜像和真实入口。
  - 发布相关配置、required SQL、smoke 环境变量必须进入发布链与产物校验，不能依赖服务器残留默认值。
  - 真实发布、备份、恢复、回滚前必须明确目标环境、目标主机、目标目录、目标数据盘和数据边界；缺一项即阻塞。
  - 正式服 `website` 数据受保护；未证明本次发布不会触碰相关数据前，不得进入正式服写操作。

```

### Match 6 (lines 42-46)

```text

- `是否引入 fallback/降级/吞异常`：否。本任务按正式发布链路执行，前置不满足即阻塞。
- `是否从根因和长期维护角度解决`：是。发布前先核对脚本与环境边界，避免靠服务器手工补丁或一次性绕过完成上线。
- `是否存在临时补丁或绕过`：否。若需临时绕过，必须先回到用户确认并补充风险说明。

```

### Match 7 (lines 48-52)

```text

- `BDD: 测试服先发布再正式发布 -> Given 当前最新程序待发布 / When 执行本次发布任务 / Then 必须先构建同一发布包并部署测试服验证通过，再允许推进正式服发布。`
- `BDD: 正式服 Website 数据必须受保护 -> Given 正式服存在受保护的 website 数据 / When 审计并执行正式服发布 / Then 发布动作只能落在本次批准的代码包边界，若存在 Website/MinIO/NAS 数据覆盖风险则必须阻塞。`
- `BDD: 发布完成必须以多重证据判定 -> Given 构建和部署动作已提交 / When 判断测试服或正式服发布是否完成 / Then 必须同时具备 operation 成功、manifest 一致、远端 IMAGE_TAG 一致、镜像运行态正常和真实入口验证证据。`

```

### Match 8 (lines 54-57)

```text

1. M1：建立任务文档、完成经验门禁预检并记录高风险动作前置证据。`DONE`
2. M2：核对维护仓发布脚本、运行控制台与测试服/正式服环境边界，确认正式服 `website` 数据不会被影响。`DONE`
3. M3：构建当前最新发布包并发布测试服，完成发布后验证。`DONE`
```

### Match 9 (lines 62-64)

```text

- 高风险动作前置：
  - `execution-log.md` 中存在 `GREEN: experience-preflight -> PASS`
```

### Match 10 (lines 80-84)

```text
- 正式服当前 `IMAGE_TAG=26-06-02_20-13-57`
- 正式服 `/opt/intruoyi/runtime/website` 目录存在且 `intruoyi-website` 容器正在运行，因此 `website` 数据和站点运行态必须被视为真实受保护边界
- 本地 `config/runtime-control.local.yaml` 已显式启用 `production-write-enabled: true`
- 正式服 `deploy-release` 仍有额外硬门禁：必须提供通过的 `preflight-release` 只读证据文件 `ProdDryRunEvidencePath`
- 当前仓库缺少现成的生产 target config 文件与对应 Smart Release 环境变量，导致正式服 dry-run 证据链尚未闭合
```

### Match 11 (lines 90-94)

```text
- 三角色真实验收最终已通过，证据 `evidence/post-release-role-e2e-1781939411338.json` 显示：
- `gaomin / 111111` 登录 `芋道源码` 后仅可见 `展厅`，6 个子页访问无页面、接口或控制台错误
- `zhaojie / 111111` 登录 `芋道源码` 后仅可见 `智能排产`，6 个子页访问通过，智能排产 smoke 已真实运行至结束
- `wangsiyu / 111111` 登录 `芋道源码` 后仅可见 `DCC文控中心`，16 个子页访问无页面、接口或控制台错误

```
