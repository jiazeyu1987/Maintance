# 执行日志

- BDD: 仅已验收包可晋级 -> Given 同一 releaseTag 已在测试服发布成功且测试验收凭证有效，When 有权限操作者打开运行控制台，Then “发布到正式服务器”按钮可进入预检；否则按钮禁用并显示精确阻断原因。
- BDD: 正式服发布复用不可变包 -> Given 发布包 manifest、package digest 和 tested 凭证一致，When 操作者确认正式发布，Then 系统直接晋级该包且不触发 build-release、不生成新 releaseTag、不改写包内容。
- BDD: 服务端绑定正式目标 -> Given 浏览器提交 promote-prod 请求，When 服务端解析目标，Then host、运行目录、数据盘和 NAS 参数只来自受控服务端配置，客户端不能覆盖。
- BDD: 生产二次确认 -> Given 包已具备晋级资格，When 操作者未输入精确确认文本或未通过最终确认对话框，Then 不创建生产写操作。
- BDD: 正式服只读预检先于写入 -> Given 正式服存在迁移依赖、包摘要、锁、容量、挂载、恢复候选或当前运行态阻断，When 执行 preview/preflight，Then 返回结构化 blockers 且生产环境零写入。
- BDD: 重复点击幂等 -> Given 同一 releaseTag 已有活动中的 promote-prod operation，When 相同用户或另一用户重复点击，Then 返回现有 operation 或冲突状态，不创建第二个写操作。
- BDD: 部分写入失败保持隔离 -> Given promote-prod 已取得生产环境锁并发生任一写入，When 后续迁移、镜像切换、启动或验收失败/中断，Then workflow 进入 `RECOVERY_REQUIRED`、锁保持、页面显示恢复入口，且不得宣称回滚或成功。
- BDD: 成功由运行态证据决定 -> Given 部署脚本退出为零，When 最终验收发现 operation、manifest、`.env`、实际镜像、health、HTTP 或页面 releaseTag 任一不一致，Then 状态不是成功并保留诊断证据。
- BDD: 审计身份可信 -> Given 登录用户执行测试验收或正式晋级，When 服务端写入 operation/tested/audit evidence，Then 操作者身份取自服务端认证上下文，不接受客户端伪造。
- BDD: 正式服与审查服隔离 -> Given promote-prod 成功，When 流程结束，Then 不自动执行 promote-backup，审查服保持不变。

- GREEN: documentation-bootstrap -> PASS；已读取适用 AGENTS、前序任务状态、经验索引、PowerShell 经验、发布/服务器/登录/worktree 文档以及 CI/CD、PRD、系统设计、BDD/TDD 技能约束。
- BLOCKER: predecessor-closeout -> 前序任务因主工作区未归属改动和发布 worktree 未融合保持 `blocked`；本设计任务仅引用其已验证行为，不处理其合并/清理。
- GREEN: documentation-worktree -> PASS；已创建 `D:\IntRuoyiWorktree\r260918-prod-button-docs\m`，基线 `4dadb8a592ca0df99a5137087b03e93419e2f609`，分支 `codex/prod-promotion-button-design`。
- SCOPE: documentation-only -> 本任务不访问或写入任何远端服务器，不运行正式发布。
- GREEN: product-doc-validator -> PASS；`validate_product_requirements.py --root <task-root>` 通过。
- GREEN: system-design-validator -> PASS；`validate_system_design.py --root <task-root>` 通过。
- GREEN: acceptance-plan-validator -> PASS；`validate_acceptance_plan.py --root <task-root>` 通过。
- GREEN: cicd-evidence-validator -> PASS；`validate_cicd_environment.py --evidence docs/environments/ci-cd-evidence.md` 通过。
- GREEN: cross-document-contract -> PASS；通过 `rg` 核对 `promote-prod`、`TESTED`、`PROD`、`RECOVERY_REQUIRED`、同一 `releaseTag`、禁止 `build-release`/`promote-backup` 等关键门禁在 PRD、系统设计、BDD/TDD/E2E 和 CI/CD 文档中一致出现。
- GREEN: project-experience-consolidation -> PASS；将“正式服按钮必须绑定 TESTED workflow/不可变包、禁止 generic promote-prod 手填入口、失败保持 RECOVERY_REQUIRED”的长期门禁合并到现有 `docs/release-agent-checklist.md` 和 `docs/experience-index.md`，未新建重复经验文档。
- GREEN: independent-backend-frontend-audit -> PASS；确认应用前后端已有受控 release-workflows、一次性授权、摘要绑定和 RECOVERY_REQUIRED 基础能力；维护 standalone console 仍是旧 `/actions` 通用执行器，允许手填 releaseTag/targetEnvironment，不能作为正式按钮权威入口。
- BLOCKER: implementation-baseline -> R93 应用/维护候选提交尚未安全融合到对应 `int_main`；后续实现必须先确认融合策略，不能在当前脏主工作区直接开发。
- BLOCKER: task-closeout-cleanup -> preview 识别当前 worktree 为 linked worktree，主工作区 `D:\ProjectPackage\Int\IntRuoyiMaintance` 非 clean，故不能执行 ff-only 合并和 worktree 删除；本轮不 apply、不删除、不合并。
- STATUS: ready_for_closeout -> 文档交付物已形成；未修改生产代码，未访问/写入测试服、正式服或审查服。
