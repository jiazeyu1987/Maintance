# 三项修复延时部署
## Goal
按用户四小时后部署授权，部署已提交的来源同步、归档恢复依赖、清理与去重修复。前序本机实现任务completed，发布线程已验收正式版本2026-11-17-23-51-44并收尾。
## Milestones
- [ ] 核实际安装、任务锁、已提交版本和回退依据
- [ ] 独立worktree部署与必要验证
- [ ] 记录结果并清理本任务资源
## Expected Verification
运行组件与已提交源码一致；现有业务健康保持；来源配置绑定当前真实版本；不以单测冒充真实恢复验收。
## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，部署正式入口。
- 是否存在临时补丁或绕过：否。
## 经验门禁
- Trigger：维护执行器及恢复组件部署。
- Preflight check：发布线程完成，实际安装路径和服务身份、任务锁、来源pin、现有安装差异、可恢复原件、独立已提交worktree。
- Blocker：运行任务占用、未知安装差异或配置身份、必要入口缺失。
- Verification：源码摘要、运行进程和实际配置、健康与部署回执；真实恢复仅在授权范围验证。
- Forbidden action：不抢占其他任务，不清空目标，不改NAS，不重放已完成业务发布，不覆盖私密配置。
- Evidence：execution-log.md及前序three-point-convergence、update-and-release-prod记录。
## Current Status
in_progress（用户续办）：用户明确要求先提交推送修复，然后部署。已找到现场修复正式分支codex/spug-backend-jar-patch-20261102；核实融合与必要验证后推送，不覆盖现场能力。此前阻塞记录保留如下。
blocked：部署前发现已安装发布执行器与已提交目标存在非本任务差异，直接覆盖将移除backend-patch支持、sealed-origin发布续办及SSH ASCII载体；尚未核清这些能力的正式源码来源。正式来源控制器存在多个晚排序ExecStart覆盖项，新固定dropin不会生效。未替换运行文件、未重启服务。

## Verified state and remaining work
- 发布线程completed，正式/测试版本2026-11-17-23-51-44；执行器无running/queued任务，存在6条旧interrupted历史，未删改历史或认定其仍有进程。
- 正式来源控制器PID1858使用engine-routine-96cbe26，children为空；审查服恢复控制器PID28421同样无child。
- 新release_backup_source.py和integration_worktree_cleanup.py尚未安装；prod profile无backupSourceBinding。
- 当前已安装intruoyi_runtime.py和intruoyi_runtime_agent.py包含未纳入本次目标的功能；不能用整文件复制安装已提交版本。
- 后续先核这些现场功能的Git来源，融合三项增量并重新验证；再审计并迁移该精确systemd服务的旧ExecStart覆盖项，保留全部原件。未授权扩大为删除其它服务或业务恢复。
## Workspace
- 本次独立部署worktree：C:/SpugHandoff/release/convergence-deploy-20261118
- 目标提交：4831ef2a8faef6aad6225d2e16227ef066da84a8（含三项修复及最近发布记录）
- detached、无新提交；未构建、未部署，因未解决安装前置条件保留worktree，不宣称completed。
