# 2026-08-11 仅测试服 HEAD 发布

## Task Goal

基于当前分支最新已提交代码完成一次仅测试服发布。构建产物必须只包含发布开始时记录的当前分支 HEAD，未提交改动不得进入构建产物；发布范围仅限测试服务器，不执行 mark-tested、promote-prod 或 promote-backup。

## Milestones

1. 发布前门禁：确认当前分支、HEAD、工作区状态、任务文档、经验门禁、发布文档和服务器访问文档。
2. 构建隔离：从发布开始时的 HEAD 创建干净临时发布 worktree，并记录目标提交号、构建目录、worktree 路径和 Git 状态。
3. 构建验证：构建维护控制台与测试发布包，并校验发布包、manifest、版本号、变更说明和 source repo 来源。
4. 测试服发布：按现有发布文档仅执行测试服发布，不发布正式服和备份服。
5. 运行态验收：校验测试服镜像 tag、容器状态、健康检查、前端 HTTP 状态、前端页面、运行控制台版本号与变更说明。
6. 记录沉淀：记录全部问题与耗时点，沉淀为发布前置经验，清理本任务临时 worktree 后完成收尾。
7. 契约修复：用 BDD + 严格 TDD 修复 C00 evidence-only migration 类型与维护仓发布工具不一致；提交并合回维护仓 `int_main` 后创建新的 clean release worktree，主程序发布输入仍固定为原冻结 HEAD。

## Expected Verification

- git rev-parse HEAD、git status --short、git worktree list 记录发布来源和隔离状态。
- 构建命令、发布包路径、manifest、版本号、变更说明、source repo commit 与发布开始 HEAD 一致。
- 仅测试服发布 operation 成功，且不执行正式服/备份服动作。
- 测试服 .env IMAGE_TAG、backend/frontend 实际镜像 tag、backend health、frontend HTTP 200、前端页面与运行控制台 release info 全部通过。
- execution-log.md、verification-report.md 和 docs/request-command-log.md 记录命令意图、验证结果、问题和阻塞。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；本任务按既有发布脚本、manifest、运行态验收和经验门禁闭环执行，不通过临时绕过判定成功。
- 是否存在临时补丁或绕过：否。

## 经验门禁

- 测试服发布范围：仅允许 `build-release -> publish-test` 与测试服真实运行态验证；禁止 `mark-tested`、`promote-prod`、`promote-backup`。
- Git/worktree 来源：维护仓、后端仓、前端仓必须冻结当前分支 HEAD；发布构建一律在本轮专用短路径 release worktree 执行，worktree dirty、提交不一致或 `runtime-control.local.yaml` 指向旧路径时必须 fail fast。
- Manifest/版本变更说明：`manifest.json` 为来源权威，必须确认 `releaseTag`、`component=intruoyi`、`sourceRepos[*].commit`、`dirty=false`、artifact SHA256/size、版本号与变更说明；任一无法确认不得发布。
- Publish-test 门禁：preview 必须为 `Environment=test`、主机 `172.30.30.58`、远端目录 `/opt/intruoyi/runtime`，且日志中不得出现正式服/备份服动作或旧 releaseTag 拼接。
- 运行态验收：operation=SUCCESS、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=UP、frontend HTTP 200、release lock/migration 状态、`/release-info.json` 与运行控制台页面版本/变更说明必须全部通过。
- PowerShell/SSH 编码：中文、SSH、多行脚本和 release-info 校验必须显式 UTF-8，避免 CRLF、插值和编码导致误报；不得因编码问题降级或跳过验证。
- Worktree 清理：发布与运行态验证完成后先标记 `ready_for_closeout`，运行 cleanup preview；确认 Git 注册、物理目录、state dir、运行控制台稳定路径全部恢复后才能标记 `completed`。

## Release Source Snapshot

- Release ID：`r260812a`。
- 维护仓当前分支：`int_main`；发布目标提交：`3d980bb16a300020985f90d3b118fef45786336a`（`任务: 完成r260811a仅测试服发布收尾`）。
- 主程序仓当前分支：`int_main`；发布目标提交：`5d503ea5e5d754461031ddb4271e5db77c2c4d91`（`feat(mes): add route DCC project binding`）。
- 主工作区状态：维护仓 dirtyCount=`43`；主程序仓 dirtyCount=`253`，并出现 `target_corrupt_m4_20260802_1327` 缺失目录 warning；因此本轮构建禁止使用主工作区。
- 临时发布 worktree：维护仓 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260812a\m`；主程序仓 `D:\IntRuoyiWorktree\r260812a-release-app`。
- 构建目录：维护仓 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260812a\m`，主程序 release worktree `D:\IntRuoyiWorktree\r260812a-release-app`。
- Worktree clean 复核：维护 worktree HEAD=`3d980bb16a300020985f90d3b118fef45786336a`，`git status --short --branch` 仅 `## HEAD (no branch)`；主程序 worktree HEAD=`5d503ea5e5d754461031ddb4271e5db77c2c4d91`，`git status --short --branch` 仅 `## HEAD (no branch)`。
- Runtime state dir：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260812a-state\runtime-control`。

## Remediated Release Source Snapshot

- Release ID：`r260812b`；旧 `r260812a` 因 committed migration 契约 blocker 不再用于构建/发布。
- 维护仓发布目标：`97723ac524487595ab5b145e31251d6bc1ec0091`（本任务正式修复提交，已 fast-forward 合回 `int_main`，合并后 22 项回归和 474 迁移 gate PASS）。
- 主程序发布目标保持原冻结提交：`5d503ea5e5d754461031ddb4271e5db77c2c4d91`；不追逐发布开始后的主程序新提交。
- 待创建发布 worktree：维护 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260812b\m`；主程序 `D:\IntRuoyiWorktree\r260812b-release-app`。
- 待使用构建目录：上述两个 r260812b worktree；主工作区未提交改动仍禁止进入发布输入。
- Runtime state dir：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260812b-state\runtime-control`。

## Issue Log

| 阶段 | 现象 | 影响 | 原因判断 | 处理动作 | 结果 | 可前置检查 | 可自动化 | 下次避免 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 启动 | 只读 bootstrap 读取了发布/服务器文档，超出项目规则允许的最小 bootstrap 文件范围 | 无写入影响，但流程顺序不够严格 | 启动时同时执行了发布文档预读 | 已立即建立本任务文档，后续按任务文档和经验门禁顺序继续 | 已记录 | 是 | 是 | bootstrap 只读阶段仅读取 AGENTS、上一任务状态、experience-index、PowerShell memory，其他文档在任务文档建立后读取 |
| Git/source freeze | 主工作区较脏：维护仓 dirtyCount=43，主程序仓 dirtyCount=253；主程序 `git status` 还输出 `target_corrupt_m4_20260802_1327` 缺失目录 warning | 若直接构建会混入未提交改动或被 warning 干扰 | 主工作区同时承载并行开发和历史构建/损坏 target 目录 | 已从两个仓库发布开始 HEAD 创建本轮专用 detached release worktree，并复核 clean | 已隔离，允许继续构建 | 是 | 是 | 发布一开始固定检查 dirtyCount、warning 和 worktree clean，任何主工作区 dirty 均走 release worktree |
| 构建前 migration policy gate | `20260812_mes_pqc_dcc_qa_c00_backfill.sql` 的 committed metadata 使用 `type=backfill`，gate 返回 `invalid type` | 无法证明发布 SQL 与 manifest 契约有效；禁止 build-release、manifest 生成和 publish-test | 主程序冻结 HEAD 引入了新 migration 类型，但维护仓冻结 HEAD 的 Python gate 与 `publish-int-ruoyi.ps1` 仅接受 `schema/data/menu/config/permission/seed`，两仓已提交契约不一致 | 使用 HEAD 原文、validator 和正式发布脚本交叉核对；停止本任务维护构建和主程序前端依赖恢复进程，未执行远端写入 | BLOCKED，需先在已提交代码中统一 migration type 契约后用新 releaseTag 重启发布 | 是 | 是 | build-release 前固定运行 migration policy gate；后端新增 migration type 时同步修改维护仓 validator、发布脚本和契约测试并提交 |
| 构建前工具编排 | migration gate 失败后，维护构建和前端依赖恢复仍在并行运行 | 若继续等待会产生无发布价值的耗时并可能留下任务进程 | 三项前置工作并行启动，gate 比依赖恢复更早失败 | 确认契约阻塞后，仅停止本任务 PID/session 对应的两个本地构建进程，并复核无 `r260812a` 进程、两个 worktree 仍 clean | 已收束，本地无残留进程 | 是 | 是 | 将快速 migration gate 排在耗时 install/build 之前，gate PASS 后再启动并行构建 |
| 命令编排 | 启动检查期间出现 Python/PowerShell 引号转义失败、一次不存在 exec cell 的 wait、数次重复代理状态查询 | 增加无效操作和少量耗时，无文件/远端影响 | 工具编排字符串与 Markdown/PowerShell 引号冲突，且误触只读状态工具 | 改用更保守 UTF-8 `exec(...)` 读取；停止重复查询；相关失败未作为发布证据 | 已记录，无环境影响 | 是 | 是 | bootstrap 使用固定 UTF-8 脚本模板；wait 仅使用真实 session/cell id；发布任务不调用无关代理状态查询 |
| 测试服基线检查 | SSH 命令完成后出现 `close - IO is still pending on closed socket` | carrier 输出带 warning，但 SSH 退出码 0 且运行态字段完整 | Windows OpenSSH 关闭 socket 时的已知 carrier warning | 以 SSH 退出码、`.env IMAGE_TAG`、容器 JSON、health 与 HTTP 字段交叉确认；未把 warning 静默删除 | 只读基线有效，测试服保持旧 releaseTag，未发生写入 | 是 | 部分 | 远端证据同时记录退出码和结构化字段，不仅按 stderr 文本判定 |
| 契约修复 TDD | 新增“可执行迁移不得依赖仅证据迁移”测试后，当前 gate 未报错，单测 FAIL | 若不修复，PowerShell 排除证据脚本后可能留下悬空依赖 | 原 gate 只校验依赖存在和环境集合，没有校验 executable/evidence-only 边界 | 在统一 Python policy gate 增加依赖闭包检查，保留 evidence-only 元数据审计但禁止 executable 依赖 evidence-only | RED 后 GREEN；目标回归 14 passed | 是 | 是 | 将可执行依赖闭包纳入 build-release 前 policy gate |
| 契约修复复验 | 首次复验调用了不存在的 `run_release_migration_policy_gate.py` | 复验命令失败一次，未改变源码、构建产物或远端 | 将真实入口 `run-release-migration-policy-gate.py` 误写为下划线名称 | 先用 `rg --files` 定位真实入口，再按仓库文件名重跑 | 正确入口 PASS，migrationCount=474 | 是 | 是 | 运行前固定检查脚本路径和 `--help`，不凭记忆拼入口名 |
| 维护前端依赖 | frozen install 在本机 pnpm store 链接阶段长时间停在 69/70，最终耗时 16m45s | 延长维护控制台构建，但未改变冻结源码 | store 位于 E 盘，包复用/链接阶段 I/O 慢；唯一 pnpm 子进程持续 Responding 且有 CPU 增量 | 保留唯一安装进程并阶段检查进程树，不并发重启；等待正式退出码 | install 成功，70/70 完成 | 是 | 部分 | 新 worktree 先恢复依赖并记录真实子进程；无进展时检查 CPU/目录时间，不重复启动 install |
| pnpm 构建脚本门禁 | 临时 allowlist 后直接执行 `pnpm ignored-builds` 一度返回 `Cannot identify as no node_modules found`，但 node_modules/.modules.yaml 与关键二进制存在 | 命令输出自相矛盾，不能直接作为最终门禁证据 | 系统 `pnpm` 解析版本与项目 Corepack 版本不同，且恢复 package.json 后无外部 policy 上下文 | 固定 `corepack pnpm@10.25.0`，使用任务外部 JSON 通过 `npm_config_only_built_dependencies_file` 注入，再执行 rebuild/ignored-builds | `ignored-builds=None`、`pendingBuilds=[]`，package/lockfile 无 diff | 是 | 是 | 构建脚本统一固定 Corepack 版本和外部 build policy，不混用系统 pnpm |
| 构建测试清理 | `Remove-Item -Recurse` 及空目录删除被执行策略拒绝 | 四个测试 JSON 需清理；空目录暂留 worktree 物理路径但不进入 Git | 安全策略拦截递归/目录删除 | 用 `apply_patch` 精确删除四个已列明 JSON；空目录留到 worktree closeout 的 allowlist 清理 | `git status` 不含 runtime，files=0 | 是 | 部分 | 测试应使用自动清理临时目录；closeout 对固定任务路径做注册/进程/边界守卫后清理 |

## Long-Running Progress Notes

- 2026-08-11 启动：已开始发布前门禁和任务文档建立。
- 2026-08-12 继续：复用本目录作为当前仅测试服 HEAD 发布任务记录；已完成只读 bootstrap、读取 CI/CD 技能、经验索引、测试服发布、构建、PowerShell、worktree、发布备份、服务器访问与登录文档的命中门禁。
- 2026-08-12 source freeze：已创建并复核 `r260812a` 维护仓与主程序仓 release worktree；主工作区 dirty 不进入构建输入。
- 2026-08-12 pre-build blocker：migration policy gate 因 committed SQL `type=backfill` 与 committed 发布脚本允许枚举不一致而失败；已停止本任务本地构建进程，未执行 build-release/publish-test，测试服仍运行 `release-20260811-intmain-head-test-r260811a-r2`。
- 2026-08-12 continuation：中断后以当前 worktree 复核同一 blocker 再次失败，两个 worktree 仍 clean 且无任务残留进程；已将跨仓 migration type 集合一致性沉淀到既有发布前置经验和索引。
- 2026-08-12 remediation decision：C00 package 明确包含 `preflight/backfill/postflight/rollback-dry-run` evidence SQL；这些脚本不得作为普通 required migration 自动执行。正式修复将让 policy gate 识别并验证它们，同时让 PowerShell 发布脚本在 required SQL 收集阶段显式排除 evidence-only 类型；不在 release worktree 做临时修改。
- 2026-08-12 remediation GREEN：修复 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260812a-fix\m` 已完成严格 RED/GREEN；14 项目标测试、22 项相关回归、PowerShell parser 和冻结 app SQL 全量 gate 均通过，migrationCount=474。下一步构建维护控制台、提交修复、合回 `int_main`，再用新的 release worktree/releaseTag 执行发布。
- 2026-08-13 maintenance build GREEN：外部 pnpm build policy 后 `ignored-builds=None`、`pendingBuilds=[]`；最终 `scripts\build.ps1` 前端 typecheck/Vite build、Maven 26 tests/package 全部通过，jar SHA256=`3eae95d8b68f802509a29d66e85e06b1dd54074d49b95b9686826a2b13341e58` 且包含静态 `index.html`。
- 2026-08-13 integration GREEN：实现提交 `97723ac524487595ab5b145e31251d6bc1ec0091` 只含四个契约修复文件，已安全 fast-forward 合回维护 `int_main`；目标文件无并发 staged/unstaged 改动，合并结果目标回归 22 passed、冻结 app SQL gate 474 passed。
- 2026-08-13 build-release GREEN：r260812b-r2 构建 operation=`op-2026-08-12T190406618402500Z-3771efa2-38a7-d5e6d99f107e` 记录更正为完整 ID `op-2026-08-12T190406618402500Z-3771efa2-38a7-4bf1-be8e-3e0f1f237bde`；manifest、484 artifact、sourceRepos、release-info 和 changeSet 全部通过。
- 2026-08-13 publish-test blocker/remediation：首次 publish 因 DCC 活跃上传槽重复失败；冻结完整备份/rollback 后经用户授权精确清理一条冗余槽，重复组归零。
- 2026-08-13 publish-test GREEN：重试 operation=`op-2026-08-13T001732036464300Z-1541e376-2561-40b8-82c8-77c33bcfda17` SUCCESS；仅测试服，未执行 mark-tested/promote-prod/promote-backup。
- 2026-08-13 runtime/page GREEN：远端 `.env`、实际镜像、容器、Actuator、HTTP、release-info、lock、430 条 migration 全通过；Playwright 测试前端与运行控制台“查看变更”页面通过，无 console errors。
- 2026-08-13 experience GREEN：DCC 活跃上传槽、releaseTag 占用、双 NAS 配置块、日志脱敏自测和页面版本 fail-fast 已合并到既有经验文档与索引。

## Cleanup Results

- r260812a、r260812a-fix、r260812b 的维护 worktree、r260812a/r260812b 主程序 worktree 与两个 state 根均已删除；Git 注册和物理路径复核无残留。
- r260812a 修复分支提交已合回 `int_main`，ancestor 校验通过后删除任务分支；r260812b release worktree 未产生新提交，无需合回。
- 48181 已恢复到主维护路径 PID=5600，health=UP，testCurrentReleaseTag=`release-20260813-intmain-head-test-r260812b-r2`，正式服/备份服访问保持禁用。

## Current Status

completed
