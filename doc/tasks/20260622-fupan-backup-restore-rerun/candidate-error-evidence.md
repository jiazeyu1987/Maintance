# Candidate Error Prevention Evidence

- Generated At: 2026-06-22T12:54:58
- Project Root: D:\ProjectPackage\Int\IntRuoyiMaintance
- Source Files Scanned: 4
- Files With Matches: 4
- Context Lines: 1
- Keywords: 错误, 失败, 阻塞, 问题, 风险, 修复, 原因, 影响, 不得, 必须, 告警, 回归, fail, failed, error, blocked, root cause, regression, risk, must, should not, do not

Review these snippets before writing any durable project rule.

## doc/tasks/20260622-backup-server-backup-restore-rerun/execution-log.md

### Match 1 (lines 5-13)

```text
- BDD: 再次执行备份服真实恢复 -> Given 新备份点已通过演练 / When 执行 restore-data / Then 备份服真实恢复成功，后端、前端、PDF Worker、OnlyOffice 健康检查通过。
- BDD: 遇错先记录再修复重走 -> Given 备份或恢复任一阶段失败 / When 采集日志、operation、manifest 和环境证据 / Then 先写入 execution-log，再按 RED/GREEN 修复并重新执行完整链路。
- GREEN: backup-dr-skill-read -> PASS，已读取 `C:\Users\BJB110\.codex\skills\backup-disaster-recovery-readiness\SKILL.md` 与 `references\recovery-contract.md`。
- GREEN: previous-task-check -> PASS，上一维护仓任务 `doc/tasks/20260621-backup-server-backup-restore-rehearsal/task.md` 已标记 `COMPLETED`。
- GREEN: baseline-docs-read -> PASS，已读取 `docs/experience-index.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`docs/agent-memory/project-error-prevention.md`。
- GREEN: Invoke-Pester -Path D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops\tests -EnableExit -> PASS，备份恢复脚本本地回归 13/13 通过。
- GREEN: backup-server-status-readonly -> PASS，备份服 `172.30.30.59` 状态脚本返回 `status=running`、`backend/frontend/pdfWorker/OnlyOffice=HTTP 200`、`currentReleaseTag=release-20260621-page-full-flow-v6`。
- RED: experience-preflight -> FAIL，首次 SSH preflight 通过 PowerShell 管道传递 Linux 脚本时出现编码/换行污染，`curl` 对 MinIO health URL 报 `Illegal characters found in URL`；已确认远端目录写入、数据盘、运行版本和主要 HTTP 检查在同次输出中通过，但该 preflight 载体不可信，必须改用 UTF-8 无 BOM、LF 行尾临时脚本重跑后才能执行备份。
- GREEN: local-log-preflight -> PASS，本机 `D:\IntRuoyi-BackupOps`、`D:\IntRuoyi-BackupOps\logs`、`D:\IntRuoyi-BackupOps\tmp` 均存在且写入探针通过。
```

### Match 2 (lines 21-23)

```text
- GREEN: backup-restore-rerun-goal -> PASS，新备份点 `20260622-063253` 已完成 `backup-now -> rehearsal -> restore-data -> post-restore health` 完整闭环。
- GREEN: final-regression -> PASS，`Invoke-Pester -Path D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops\tests -EnableExit` 最终回归 13/13 通过。
- GREEN: task-closeout-cleanup preview -> PASS，`task_status=completed`，保留 `task.md` 与 `execution-log.md`，无删除项、无阻塞、无警告。
```
## doc/tasks/20260622-backup-server-backup-restore-rerun/task.md

### Match 1 (lines 4-6)

```text

在备份服务器 `172.30.30.59` 再次真实执行一轮完整备份恢复流程，重新生成备份点并完成 `backup-now -> rehearsal -> restore-data -> post-restore health` 闭环。如出现错误，先记录失败证据，再按严格 TDD 修复并重走。

```

### Match 2 (lines 16-18)

```text
- 当前任务授权：
  - 允许对备份服务器 `172.30.30.59` 执行备份、恢复、演练、排障和必要修复。
  - 允许本机维护仓代码、脚本、配置与任务文档在本任务范围内修改。
```

### Match 3 (lines 20-22)

```text
  - 未经本任务额外授权，不访问或写入正式服 `172.30.30.57`。
  - 不使用 mock、默认成功、静默跳过或降级掩盖备份恢复失败。
  - 不把备份、恢复、演练、临时目录写到 `/mnt/intruoyi-data` 之外的根分区路径。
```

### Match 4 (lines 27-31)

```text
- 恢复契约摘录：
  - 必须记录恢复范围和数据清单。
  - 必须记录恢复步骤、恢复测试证据或阻塞。
  - 必须记录配置、凭据和外部依赖注意事项。
  - 本轮不声明完整灾备 SLO 达标；RTO/RPO 未由用户本次指定，任务目标限定为再次证明备份恢复链路可真实执行。
```

### Match 5 (lines 39-48)

```text
    - `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 开始前必须确认目标环境、目标主机、目标库、对象存储 endpoint、发布包或备份点。
  - 备份、恢复、演练前必须检查根分区、数据盘、临时目录、日志目录和挂载写入权限。
  - 备份服必须显式使用 `/mnt/intruoyi-data`、`/dev/mapper/cl-home`、`/mnt/intruoyi-data/Backup/BackupPackage`。
  - 备份可用性必须以最终目录、manifest、checksum、对象清单和恢复演练证据共同判定。
  - 恢复前必须校验当前 `IMAGE_TAG` 与备份 manifest `imageTag` 匹配，恢复链、对象 manifest 和 DCC manifest 均可验证。
  - 高风险动作前，`execution-log.md` 必须先记录 `GREEN: experience-preflight -> PASS` 或明确阻塞原因。

```

### Match 6 (lines 51-53)

```text
- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。如出现失败，优先修复脚本、契约、配置或测试。
- `是否存在临时补丁或绕过`：否。
```

### Match 7 (lines 59-61)

```text
- `BDD: 再次执行备份服真实恢复 -> Given 新备份点已通过演练 / When 执行 restore-data / Then 备份服真实恢复成功，后端、前端、PDF Worker、OnlyOffice 健康检查通过。`
- `BDD: 遇错先记录再修复重走 -> Given 备份或恢复任一阶段失败 / When 采集日志、operation、manifest 和环境证据 / Then 先写入 execution-log，再按 RED/GREEN 修复并重新执行完整链路。`

```

### Match 8 (lines 65-67)

```text
2. 完成经验门禁、备份恢复技能与目标环境核对。`DONE`
3. 完成高风险动作前的 `experience-preflight`。`DONE`
4. 执行新的 `backup-now` 并校验产物。`DONE`
```
## docs/agent-memory/project-error-prevention.md

### Match 1 (lines 1-6)

```text
# Project Error Prevention Memory

- 部署验证不能只看健康；要核 operation、manifest、镜像、迁移状态和真实入口；证据: 20260617-release
- 真实 E2E 先记失败再统一修复并整轮复测；不要边测边改；证据: 20260618-role-e2e
- 环境部署前先核本机控制台授权、secrets、确认文本、旧 jar/陈旧 RUNNING 锁；任一前置条件缺失直接阻塞；证据: 20260620-release-flow
- 构建完成就做候选包 preflight；manifest、required SQL、dry-run/隔离工作区、多环境迁移契约先过；证据: 20260621-release-flow
```

### Match 2 (lines 8-10)

```text
- 测试通过前先确认 AVAILABLE 恢复点；正式备份前单独校验 secrets、确认文本、DCC manifest 和 object inventory；证据: 20260620-release-flow
- 部署输入变更后必须新 releaseTag 重建并整链复测；旧候选包只作证据；证据: 20260621-flow
- 备份服路径固定 /mnt/intruoyi-data；发布前后核远端 .env、镜像与受保护对象边界；证据: 20260621-flow
```
## docs/request-command-log.md

### Match 1 (lines 5-8)

```text
- 用户需求：主程序合并修改了部分代码，担心原来的发布链路已经不对，要求重新通过页面前端点击操作完整走一遍 `构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服`。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`。
- 命令记录：重新读取 `supervised-complex-delivery` 与 `playwright` 技能，以及 `artifact-contract.md`、`task-state-schema.md`，按新一轮高风险真实页面发布任务重新建档。
- 命令记录：核对上一维护仓任务 `doc/tasks/20260621-frontend-release-full-flow-rerun/task.md` 已 `COMPLETED`，允许开启新任务 `doc/tasks/20260621-frontend-release-full-flow-main-merge-rerun/`。
```

### Match 2 (lines 14-25)

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

### Match 3 (lines 28-36)

```text

- 用户需求：执行 `$fupan`，把本轮“测试服发布 + 三角色真实验收 + 正式服预发布阻塞”沉淀为可复用经验，避免后续重复踩坑。
- 命中技能：`C:\Users\BJB110\.codex\skills\fupan\SKILL.md`。
- 命令记录：读取 `SKILL.md`、当前任务 `task.md`、`execution-log.md`，确认本轮已有足够证据支撑复盘。
- 命令记录：读取 `references/project-memory-template.md`、既有 `docs/agent-memory/project-error-prevention.md` 与 `docs/request-command-log.md`，按“项目级规则 / 任务专项细节”拆分候选经验。
- 命令记录：运行 `python -X utf8 C:\Users\BJB110\.codex\skills\fupan\scripts\collect_error_evidence.py --project-root D:\ProjectPackage\Int\IntRuoyiMaintance --glob doc\tasks\20260620-prod-release-current-latest\task.md --glob doc\tasks\20260620-prod-release-current-latest\execution-log.md --glob AGENTS.md --output D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-prod-release-current-latest\candidate-error-evidence.md`，生成本轮候选证据。
- 命令记录：尝试运行 `update_project_memory.py` 追加“正式服 Smart Release prod preflight 证据闭合”规则，被脚本拒绝，原因是该条目目前仍偏本次发布链专项规则，不属于项目级通用短记忆。
- 结论记录：本轮 `$fupan` 接受的长期经验仍是“发布前预检”“发布验证多证据闭环”“先全量记录失败再统一修复复测”三类；`ProdDryRunEvidencePath / target config / NasConfigPath` 保留在当前任务文档，不提升到 `AGENTS.md` 或项目级记忆；页面脚本细节不进入长期记忆。

```

### Match 4 (lines 38-44)

```text

- 用户需求：正式按页面前端点击操作的真实流程，完整走一遍构建发布到测试服、正式服、备份服；过程中禁止直接调接口替代页面动作；遇到问题先记录任务文档，修复后继续从页面重走，直到整条流程一次性走通。
- 命中经验：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`。
- 命令记录：核对上一维护仓任务 `doc/tasks/20260620-fupan-prod-release-v7/task.md` 已 `COMPLETED`，允许开启新任务 `doc/tasks/20260620-frontend-release-full-flow/`。
- 命令记录：读取并确认当前任务 `task.md`、`execution-log.md` 已落地 `BDD` 场景、`设计约束检查`、`经验门禁` 与 `GREEN: experience-preflight -> PASS`。
- 命令记录：尝试按 `control-in-app-browser` 技能接入应用内浏览器，`node_repl/js` 返回环境级错误 `missing field sandboxPolicy`；该问题已记录到当前任务 `execution-log.md`，不属于页面业务链路问题。
- 命令记录：只读验证 `http://127.0.0.1:48181/` 返回 `200`；核对维护仓前端打包产物与源码，确认运行控制台真实存在“构建发布包 / 部署测试服 / 上线正式服 / 上线备份服”按钮、预览命令弹窗和执行弹窗。
```

### Match 5 (lines 50-52)

```text
- 计划边界：仅发布测试服 `172.30.30.58`，远端目录 `/opt/intruoyi/runtime`；发布范围为 `code-only`，不访问正式服/备用服，不执行备份、恢复、回滚或正式服动作。
- 命中经验：`release-backup-restore.md`、`server-access.md`、`login-access.md`；真实 E2E 和服务器写入前必须记录 `experience-preflight`。
- 命令记录：检查 `npx` 可用，路径为 `D:\Programs\npx.ps1`。
```

### Match 6 (lines 60-63)

```text
- 命令记录：Playwright 点击构建发布包“执行”，operation `op-2026-06-17T072458143463800Z-0d5a0145-9253-4018-991a-55bf864264ef` 初始状态 `RUNNING`。
- 命令记录：构建 operation 最终 `FAILED`；后端 Maven、前端 Vite build、后端 Docker 镜像构建成功，前端 Docker 镜像构建失败，原因是拉取 `nginx:1.27-alpine` 元数据时 Docker Hub token 请求超时。
- 阻塞记录：发布包未成功生成，禁止继续发布测试服；下一步先补齐/验证 Docker 基础镜像 `nginx:1.27-alpine`。
- 命令记录：`docker pull nginx:1.27-alpine` PASS，digest `sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`。
```

### Match 7 (lines 65-68)

```text
- 命令记录：Playwright 点击第二次构建发布包“执行”，operation `op-2026-06-17T073818610888200Z-832a7d6b-133a-45ed-abd9-84dd1abfd300` 初始状态 `RUNNING`。
- 命令记录：第二次构建 operation 仍 `FAILED`；Maven、Vite、后端镜像和前端镜像成功，发布迁移策略门禁失败，原因是 `20260617_dcc_browser_performance_indexes` 依赖缺失 `20260513_dcc_base_schema.sql`。
- 阻塞记录：发布包 manifest 未生成，禁止继续发布测试服；需要先修复迁移元数据/扫描集合。
- 命令记录：在 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 修正 `sql/mysql/20260617_dcc_browser_performance_indexes.sql` 首行 `dependsOn` 为清单实际使用的迁移 ID `20260513_dcc_base_schema`。
```

### Match 8 (lines 72-74)

```text
- 命令记录：Playwright 点击第三次构建发布包“执行”，operation `op-2026-06-17T082753879349700Z-c7f3f523-d9c6-4077-9b0f-eacc6cf5bf73` 初始状态 `RUNNING`。
- 命令记录：第三次构建 operation `FAILED`；Maven 在 `yudao-module-dcc` 执行 clean 时无法删除 `target`，发布包未生成，禁止发布测试服。
- 命令记录：`mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -DskipTests clean` PASS，DCC target 清理前置恢复。
```
