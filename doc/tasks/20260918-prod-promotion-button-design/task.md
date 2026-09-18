# 20260918 已测试发布包晋级正式服按钮设计

## Current Status
ready_for_closeout

## 任务目标
为运行控制台设计一个独立的“发布到正式服务器”按钮，使已经在测试服务器成功部署并完成测试验收的同一不可变发布包，在显式生产确认和全部前置门禁通过后晋级到正式服务器；本任务只形成实施文档，不访问或写入正式服务器。

## 里程碑与预期验证
1. [completed] 明确前序测试服按钮任务的收尾状态；因主工作区改动归属和发布 worktree 尚未安全融合，已将前序任务明确标记为 `blocked`，不删除或合并其产物。
2. [completed] 核对现有运行控制台、发布脚本、状态机、测试验收凭证和正式服门禁。
3. [completed] 编写 PRD、用户流程和可测试验收标准。
4. [completed] 编写前端、后端 API、数据模型、配置/安全/部署设计。
5. [completed] 编写 BDD、严格 TDD、真实 E2E、测试数据、CI/CD 证据和实施计划。
6. [completed] 运行文档验证器和交叉一致性检查，记录验证报告。

## 预期验证
- 产品需求文档、用户流程和验收标准通过 `validate_product_requirements.py`。
- 系统设计文档通过 `validate_system_design.py`。
- BDD/TDD/E2E 计划通过 `validate_acceptance_plan.py`。
- CI/CD 证据文档通过 `validate_cicd_environment.py`。
- 所有文档统一规定：复用同一 `releaseTag` 和同一包摘要，不重新构建；未完成测试验收、生产确认、正式服只读预检或恢复前置条件时 fail fast；任何部分写入失败进入 `RECOVERY_REQUIRED`，不得显示成功或自动释放隔离。

## 经验门禁
- Trigger: 已部署测试服的发布包需要晋级正式服。
- Preflight check: 只允许同一 `releaseTag` 沿 `build-release -> publish-test -> mark-tested -> promote-prod` 顺序推进；验证测试服 operation、manifest、包摘要、测试运行态证据、可信 `TestedBy` 和恢复候选；正式服目标必须来自服务端受控配置并先执行只读 target-bound preflight。
- Blocker: 测试服未验收、tested 凭证缺失或摘要不匹配、正式服目标/凭据/锁/容量/数据盘/NAS/迁移依赖/恢复条件任一不满足、存在活动生产发布、确认文本错误或操作者无权限时，按钮必须禁用或请求被服务端拒绝，且不得产生远端写入。
- Verification: 成功必须同时核对 production operation=`SUCCESS`、manifest/摘要、正式服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health=`UP`、frontend HTTP=`200`、页面 releaseTag 和环境锁终态。
- Forbidden action: 禁止重新构建或改写已测试包；禁止浏览器传任意 host/path/脚本；禁止手工标绿 tested；禁止跳过 preview/二次确认/恢复候选；禁止失败后自动切换环境、复用失败操作或把旧容器健康当作新版本成功；本设计任务禁止访问或写入正式服。
- Evidence: `docs/release-agent-checklist.md`、`docs/release-build-preflight-lessons.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、R92/R93 测试服发布证据。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；采用不可变发布包晋级、服务端状态机、服务端目标绑定、生产双重确认和可恢复失败态。
- 是否存在临时补丁或绕过：否。

## 范围边界
- 本任务只写设计与验收文档，不修改生产代码，不运行构建、发布、远端登录、数据库写入、服务重启或正式服探测。
- 首版仅设计“测试验收后的包晋级正式服”；不自动发布审查服，不把正式服按钮与构建按钮合并，不提供任意命令/主机/路径输入。

## 前序任务阻塞说明
- `20260916-release-button-remediation` 已完成 R92/R93 测试服发布验证，但两个 `r260917-button-publish9` worktree 尚未安全融合到对应 `int_main`；主工作区存在未归属改动和分叉提交。
- 本任务不处理、删除、合并或重置这些前序产物；后续实现开始前必须先明确实现基线和合并策略。

## Worktree 记录
- 本任务文档 worktree：`D:\IntRuoyiWorktree\r260918-prod-button-docs\m`。
- 目标基线提交：`4dadb8a592ca0df99a5137087b03e93419e2f609`。
- 分支：`codex/prod-promotion-button-design`。
- 当前只产出文档；不构建、不发布。

## Cleanup Keep

- `doc/tasks/20260918-prod-promotion-button-design/development-plan.md`
- `doc/tasks/20260918-prod-promotion-button-design/docs/`
