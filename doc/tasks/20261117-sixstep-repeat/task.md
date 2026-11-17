# 第二轮同步发布备份恢复

## Goal
用户明确要求将上一轮六步完整再执行一次。同步最新已提交代码，独立新发布worktree构建新releaseTag，测试服发布验收，同包正式服发布，正式服新增量备份，.59清理旧目标恢复新备份链，实际公开地址验收。

## Milestones
- [x] 同步代码并固定本轮提交16719d77c及独立发布worktree build/2026-11-17-11-53-04。
- [x] 新包测试服发布验收：JOB-800548d984及独立真实用户管理/版本PASS。
- [x] 同包正式服发布验收：JOB-1be5a63753发布、JOB-a8626088d5开放，公开8081真实登录和新版本通过。
- [x] 正式服新增量8978原生SUCCEEDED/exit0、归档pin及FULL+两段增量父链绑定通过。
- [x] .59空目标准备和新链恢复（b638 SUCCEEDED/exit0）。
- [x] 公开8081登录、数据、附件、版本验收及融合清理。

## Expected Verification
本轮独立releaseTag与操作编号；发布SUCCESS/manifest/env/实际镜像/health/HTTP；备份原生成功及源恢复；目标恢复原生成功、冻结基线数据及附件SHA、真实公开URL登录。不得复用上一轮成功代替本轮证据。

## 经验门禁
Trigger：用户授权重复六步。Preflight check：上一任务completed已确认，实际Git主线/远端/dirty、当前执行器配置和任务锁、三服状态、源备份链及日志范围、新点依赖、公开8081入口配置。Blocker：来源提交不明、活动操作冲突、缺少必要恢复依赖或验收失败。Verification：每阶段保存本轮原生回执、真实页面和版本；新建临时发布worktree，只用提交内容。Forbidden action：不提交无关dirty、不删正式NAS、不伪造或覆盖旧失败、不以SSH隧道替代公开入口、不擅自切全量代替所需增量。Evidence：上一轮20261116-release-prod-incremental-restore及本轮execution-log。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，复用已修复正式流程。
- 是否存在临时补丁或绕过：否。

## Current Status
completed：本轮同步、构建、测试服与正式服发布、正式服新增量备份、备份服FULL+两段增量恢复均完成。公开59:8081登录、版本、8表计数、两图片页面字节SHA及PDF对象字节SHA通过。用户确认删除本轮临时目录后，已实际核目录不存在且Git无其worktree登记；控制台18112/PID11716仍使用稳定路径。历史PDF元数据页面问题按用户批准范围保留。最终收尾记录单独提交。

## 构建配置读取契约修复
Given 平台GxP配置保存在infra_config且租户列表不再返回平台配置，When 已经真实UI登录后执行构建配置核验，Then 使用正式只读get-value-by-key与runtime-mode核已保存及运行一致，缺失/非法/不一致仍失败。认证必须仍由真实页面完成，API仅用于最终配置核验；不把旧租户编辑页面错误当平台配置丢失，不修改数据。设计约束：无fallback、无吞错、无临时绕过，正式适配平台/租户分离。页面旧编辑组件缺口单独如实记录，不宣称配置页面验收通过。
GREEN: experience-preflight -> PASS。原JOB-e8722c8928原生failed，未新建构建worktree，未远端写入。两服实际DESCRIBE后核infra_config id49/DEVELOPMENT_DISABLED/type1/visible1/deleted0；真实prod登录成功、runtime关闭，租户page总0。先BDD+RED再最小实现，独立维护worktree修复并定向回归、真实验证后提交安装。
## 本轮融合与收尾进展
维护修复96cbe26已融合、主线Linux120PASS、两个routine worktree已删除。应用16719d77已融合，主线101Java及28前端行为验证通过，30并行dirty/untracked保全。应用临时目录integration-20261117-repeat因长路径Git删除失败，原生精确删除又被自动审批拒绝，保留残留目录，不绕过；应用子阶段ready_for_closeout，整体仍in_progress。

## 最新推进
2026-11-17 19:51：前两次恢复7e8/0d9在admission失败且PROVEN_NO_MUTATION。iptables初步归因已纠正；实际缺失新release r3 images.json，已按归档versionPin验证517字节及SHA后从正式服补齐。prepare-5102adee-8f11-4e76-84c4-8ca1bf2f5217 READY，最新恢复b638已真正进入数据库恢复。旧integration-20261116-sixstep已删除；不代表本轮20261117残留已清理。

## 附件连接适配修复
根因：本轮私有register_prepare_point.py使用next(iter(points.values()))复制首条历史配置，漏掉父点bf67已有fileStorage策略；新点8978及生成目标preparedFileStorage为空，现有引擎因此未执行存储适配。正式修复方向：按已核验父链明确选择父点配置并保留fileStorage；补齐本轮登记策略，使用既有连接适配规则修复目标，重启目标后真实页面验收。不得更改源服务器或本机受保护配置、bucket/domain及媒体URL。设计约束：无fallback、无吞错；从登记选错基线根因修复；不以对象字节通过替代页面验收。BDD：Given 新增量父点包含存储适配，When 登记新点并恢复，Then 新目标继承该策略且附件从目标MinIO可读。

## 收尾阻塞
本轮临时目录C:/SpugHandoff/release/integration-20261117-repeat连续三轮复核仍存在；此前自动审批拒绝精确删除（blocked by policy），不得绕过。功能验收及控制台复核已完成，任务保持ready_for_closeout，目标标记blocked。用户删除后核目录缺失，再单独提交最终任务记录并标记completed。

## 最终收尾
2026-11-17：用户回复本轮integration-20261117-repeat已删除。只读Test-Path=False，应用git worktree list无该登记，主线仍16719d77；18112仍由11716稳定执行器监听。收尾阻塞解除，最终验收报告与执行日志单独提交；未删除其他任务worktree或停止无关进程。
