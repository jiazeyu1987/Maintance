# 三服最新代码发布方案

## Current Status
completed

## 任务目标
按用户要求编写可审查的三服发布方案。本任务仅编写文档，不构建、不发布、不操作远端、不更改业务数据。上一同链任务 `20261030-spug-handoff-install` 已 completed，安装验收为 PASS_WITH_FINDINGS；本方案必须继承其未关闭发现，不能把安装通过当作新发布通过。

## 里程碑
- [x] 核对经验索引、现有发布契约和安装验收发现。
- [x] 编写从目标提交冻结到三服推广与回滚的操作方案。
- [x] 核对文档、编码和变更范围，分别提交交付物与任务收口记录。

## 预期验证
文档须明确单一 releaseTag 全链路、最新代码定义、代码与私密状态边界、隔离 worktree、全量数据演练、真实 Playwright 登录、六项发布成功判据、失败停止及回滚、运行路径恢复和 worktree 清理。与当前固定版本代码及验收证据交叉核对；纯文档任务不执行运行测试。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；发布前显式解决契约漂移及网络冲突，不使用临时绕过。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- Trigger：三服发布方案；Preflight check：按经验索引定位发布、迁移、恢复、worktree 和真实 E2E 规则，并核对当前代码；Blocker：必需文档或契约缺失、目标版本不明确；Verification：逐阶段列证据与停止条件；Forbidden action：本任务执行构建、发布或远端写入；Evidence：execution-log.md 和交付方案。
- 继承门禁：源机单执行器、发布历史一致；原包只读保留；Git 仅更新代码；不得把三服当前镜像一致替代 .env IMAGE_TAG 契约核验。
- Trigger：构建及跨环境晋级；Preflight check：冻结完整应用/维护提交、干净专用 worktree、实际脚本字节摘要、包/manifest 双摘要；Blocker：来源不明、脏输入、摘要或目标漂移；Verification：记录不可变包和各服独立验收；Forbidden action：重建已测包或拼不同 releaseTag；Evidence：release-agent-checklist.md、release-build-preflight-lessons.md 不可变包及执行器摘要门禁、固定维护代码。
- Trigger：迁移及真实目标数据；Preflight check：历史不可变、显式注册、依赖闭包、真实结构、构建前结构演练/只读数据检查、正式完整数据演练；Blocker：未知/失败迁移、缺合同、静态计划被当作真实演练；Verification：原始台账、计划、演练编号与目标指纹；Forbidden action：改旧 SQL/ledger、在真实业务库试跑迁移或省略数据检查；Evidence：release-build-preflight-lessons.md、intruoyi_build.py 的 static-only 声明。
- Trigger：真实登录与业务验收；Preflight check：当前用户指定测试租户/账号、真实页面、私密凭据、实际入口；Blocker：租户未选中、权限/入口/基线缺失或登录失败；Verification：Playwright 登录后身份及版本、正式/审查独立业务结论；Forbidden action：接口冒充页面、改密码或权限、擅自业务写入；Evidence：test-release-preflight.md、当前发布中心 README 三项技术检查及验收代码。
- Trigger：远端写入、备份和恢复；Preflight check：当前任务环境授权、生产确认、互斥与原任务回执、writer/fence、实际恢复资源及一致性；Blocker：未知中断/写入状态、缺恢复点、共享资源归属不明；Verification：原任务、恢复点、恢复验收和开放状态；Forbidden action：自动重试部分迁移、开放后直接回灌旧数据、删除共享 NAS；Evidence：固定应用仓 release-backup-restore.md/server-access.md、维护恢复文档。
- Trigger：worktree 收口；Preflight check：实际 Git 拓扑、路径、归属和并发使用、必要提交融合及验证；Blocker：未归属修改、未融合提交或验证失败；Verification：ready_for_closeout 到 completed 的清理/稳定运行证据；Forbidden action：删除其他任务 worktree/进程或提前 completed；Evidence：固定应用仓 worktree-memory.md/worktree-restrictions.md、当前用户规则。

## BDD / TDD 范围
Given 用户仅要求发布方案，When 编写并核对文档，Then 交付明确步骤、证据、阻塞与失败处置，且不触发任何发布。没有功能或行为变更，RED/GREEN 运行测试不适用。

## 已完成与验证
- 交付物：release-plan.md，共 163 行；完整流程、现有阻塞及证据边界已写明。
- verification.json：11 项文档静态检查全部 PASS；UTF-8 无 BOM、引用路径、动作名称、必要提交、历史发现及启动命令核对通过。
- `git diff --check` 通过；未运行构建、运行测试、真实 E2E 或远端操作，没有变更运行控制台。
- 生产发布的既有发现仍列为将来执行前的阻塞；它们不阻塞本次文档交付。方案已单独提交为 `6594c8c`；最终任务记录单独提交。

## 收口结果
- 本任务没有创建临时 worktree，无需合并或删除，也没有任务进程和控制台需恢复；未触碰其他任务资源。
- 提交仅包含本任务文档与脱敏验证记录；工作区原有四项 tracked 修改保留，未推送远端。
- 最终验证结论：文档交付 PASS，实际三服发布未执行，现有发布前问题没有被改写为已解决。
