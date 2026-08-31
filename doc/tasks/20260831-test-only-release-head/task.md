# 20260831 当前 HEAD 仅测试服发布

## Task Goal

在任务启动时锁定维护仓与 IntRuoyi 当前分支最新已提交 `HEAD`，仅从本轮专用干净临时发布 worktree 构建维护控制台和测试发布包，并仅发布到测试服务器。未提交改动不得进入产物；后续仓库更新不得改变本次冻结输入。

## Milestones

1. 启动门禁与任务记录：完成适用规则、上一任务、PowerShell 与发布经验预检。
2. 冻结发布输入：记录当前分支、目标提交、Git 脏状态、构建目录和本轮专用 worktree。
3. 构建与包验收：构建维护控制台和测试发布包，核验 package、manifest、版本号、变更说明与冻结提交一致。
4. 仅测试服发布：同一 `releaseTag` 只执行 `build-release -> publish-test`，禁止正式服和备份服动作。
5. 真实运行态验收：核 operation、manifest、远端 `.env IMAGE_TAG`、实际镜像、容器、健康、前端 HTTP、页面和运行控制台版本说明。
6. 问题与经验沉淀：逐项记录问题、耗时点、可前置检查和自动化机会，并合并到现有经验文档。
7. 收尾：状态先置为 `ready_for_closeout`，预览/应用任务清理，删除任务自有临时 worktree，最后标记 `completed`。

## Expected Verification

- BDD: Given 启动时冻结的当前分支已提交 HEAD，When 在本轮专用干净发布 worktree 构建并仅发布测试服，Then 产物来源、manifest、版本号、变更说明及测试服真实运行态必须全部匹配同一 `releaseTag` 和冻结提交。
- 维护仓与应用仓 worktree 均应 `git status --short` 为空，`HEAD` 等于启动时记录提交。
- 构建 operation 必须 `SUCCESS`；发布包、Manifest v1/legacy manifest、release-info/changeset 必须可验证且来源仓 `dirty=false`。
- publish-test operation 必须 `SUCCESS`；远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=UP、frontend HTTP=200、release lock/migration 状态均通过。
- Playwright 真实打开运行控制台页面，页面显示本次版本号和变更说明且无控制台错误或失败请求。
- 不执行 `mark-tested`、`promote-prod`、`promote-backup`，不操作正式服或备份服。

## 经验门禁

- Trigger: 当前 HEAD 仅测试服发布、clean release worktree、`build-release`、`publish-test`、运行控制台版本说明验收。
- Preflight check: 发布输入必须冻结为任务启动时维护仓和应用仓已提交 HEAD；每次发布新建专用 clean worktree；先核发布/服务器/登录/worktree/PowerShell 文档、依赖准备、releaseTag 占用、operation 终态与控制台配置路径；高风险动作前记录 `GREEN: experience-preflight -> PASS`。
- Blocker: worktree HEAD 不匹配或不干净、构建来源无法证明、manifest/版本号/变更说明缺失或不一致、releaseTag 已占用、存在未解释的 RUNNING/FAILED、运行控制台仍指旧工作区、测试服真实运行态任一必查项缺失时立即停止。
- Verification: 同一 `releaseTag` 完成 `build-release -> publish-test`，并核 operation=SUCCESS、manifest、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像、容器状态、backend health=UP、frontend HTTP=200、release-info/release-status 与 Playwright 页面版本说明。
- Forbidden action: 禁止从脏工作区构建、构建中追随新提交、复用旧 worktree、拼接多轮 releaseTag、临时修改发布 worktree绕过、跳过或降级验证、执行正式服/备份服动作、记录明文凭据或 raw secret-bearing 日志。
- Evidence: `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\login-access.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\worktree-memory.md`、`E:\IntRuoyi\docs\powershell-memory.md`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是。
- 是否存在临时补丁或绕过：否。

## Current Status

completed

## Milestone Status

1. 启动门禁与任务记录：completed。已读取发布、服务器、登录、worktree、PowerShell、测试服发布和构建发布规则，并建立任务、执行日志、验证报告与请求命令记录。
2. 冻结发布输入：completed。已冻结维护仓 `int_main@ed282ac4d1bff57ba9320191bab948f21d5e5e6e` 与 IntRuoyi `int_main@58479242435efa1f7eafd6e0a17e36bd9c811e5f`；本轮 detached release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260831a\m`、`D:\IntRuoyiWorktree\r260831a\a` 均已登记、HEAD 匹配且 status count=0。
3. 构建与包验收：completed。历史 r1 已判废；新 r260831b build operation `op-2026-08-31T024323515301800Z-795a60df-e388-4a13-aeff-2caf1e26d2f6` SUCCESS。官方 validator 通过，manifest/镜像 release-info/source commit/dirty/changeSet/修复后 dependsOn 均匹配 `c3a134a7`。
4. 仅测试服发布：completed。历史 r1/r260831b 均判废；最终 r260831c 同一 releaseTag 完成 build-release + publish-test，两个 operation 均 SUCCESS，未执行 mark/prod/backup。
5. 真实运行态验收：completed。`.env`、compose/实际镜像、容器、backend UP、frontend 200、release-info、lock/migration、运行控制台 API 与 Playwright 页面全部匹配 r260831c。
6. 问题与经验沉淀：completed。发布/required SQL、测试服闭环、PowerShell 跨层载荷经验已合并到现有 preflight 文档、索引和发布清单，关键词与 UTF-8/diff-check 验证通过。
7. 收尾：completed。经验沉淀、两轮 task-closeout apply、任务自有控制台/8 worktree/slots/state/Playwright 临时产物清理和最终远端复核全部通过；app 子任务收尾 commit=`7ad8cde64`。

## Authorized Recovery

- 用户授权：恢复测试服 `.env IMAGE_TAG` 到实际运行版本；按 BDD+严格 TDD 修正迁移依赖；提交新 HEAD；使用新 releaseTag 重新构建并仅发布测试服。
- 范围边界：不复用失败 r1；不手工执行 data SQL；不修改 migration ledger/release lock；不执行 `mark-tested`、`promote-prod`、`promote-backup`；不操作正式服/备份服。
- 恢复策略：仅在 `.env` 精确等于失败 r1 且 backend/frontend 实际镜像精确等于同一上一版本时，原子替换单一 `IMAGE_TAG` 行；不重启容器，替换后交叉验证 `.env`、实际镜像、health 和 HTTP。

## New Release Attempt

- Maintenance frozen HEAD: `ed282ac4d1bff57ba9320191bab948f21d5e5e6e`。
- App frozen HEAD: `c3a134a797c3aab24feba3aafec32815f8345cf1`，commit subject=`任务: 修正批记录项目代码迁移依赖`。
- Planned worktrees: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260831b\m`、`D:\IntRuoyiWorktree\r260831b\a`。
- Planned releaseTag: `release-20260831-project-code-dependency-test-r260831b-r1`。
- 约束：新 worktree 创建后只使用以上提交；不追逐后续主线提交；历史 r1 package/worktree/operation 不复用。

## R260831C Release Attempt

- Maintenance frozen HEAD: `ed282ac4d1bff57ba9320191bab948f21d5e5e6e`。
- App frozen HEAD: `735f69782756fdc62ea1a1a69202e7d8a94e6d60`，subject=`任务: 修正批记录单元格链接迁移幂等性`。
- Planned worktrees: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260831c\m`、`D:\IntRuoyiWorktree\r260831c\a`。
- Planned releaseTag: `release-20260831-cell-link-idempotency-test-r260831c-r1`。
- 约束：r260831a/r260831b package、worktree、state、operation 均只作历史证据，不参与本轮构建发布。

## Final Release Result

- ReleaseTag: `release-20260831-cell-link-idempotency-test-r260831c-r1`。
- Build operation: `op-2026-08-31T041314765504800Z-b1fc20d9-91a1-4658-8360-86dccead48d6` SUCCESS。
- Publish operation: `op-2026-08-31T053012842131200Z-9cafc46c-e123-4da6-88c1-f5ec4c85acb7` SUCCESS。
- Source: maintenance `ed282ac4`、app `735f6978`，manifest/release-info dirty=false。
- Runtime: test `.env`/backend/frontend image tag 一致，containers running、health=UP、frontend HTTP 200、lock=APPLIED、migration FAILED/RUNNING=0。
- Page: Playwright 1.60.0 打开测试服登录页与本地运行控制台；查看变更对话框可见 releaseTag、组件、commit 和摘要，console/page/request errors=0。
- Scope: 仅测试服；未执行 `mark-tested`、`promote-prod`、`promote-backup`，未访问正式服/备份服。

## Blocker

- Missing precondition: 测试服没有 `20260829_mes_old_form_template_binding_switch` 的 APPLIED 记录，而冻结提交中的 schema 迁移 `20260830_mes_batch_record_report_project_code` 对其存在正式 dependsOn。
- Impact: code-only 发布在 required SQL 前被 target preflight fail fast；本轮 r1 已判废，不能复用、不能 mark/promote，也不能宣称测试服发布成功。
- Read-only audit: `20260830_mes_batch_record_report_project_code.sql` 只为 `mes_pro_batch_record_report` 添加 `project_code` 列，不读取或依赖旧表单绑定迁移产生的数据；真实表创建迁移 `20260514_mes_batch_record_report` 在测试服已 APPLIED。因此当前 dependsOn 指向高风险 data 迁移属于不必要的发布依赖。
- Recommended decision: 授权在主分支按 BDD+TDD 正式把 dependsOn 修正为已应用的 `20260514_mes_batch_record_report` 并补回归测试，提交后冻结新 HEAD、新建 worktree、使用新 releaseTag 重建/发布。with-data 会为一个独立加列动作执行无关高风险数据迁移，不建议作为绕过。未经授权不得改初始冻结 worktree、手工执行 SQL 或修改迁移台账。
