# 单目标登记阻塞范围修复

## Goal
六步发布续办发现 register-targets target=prod 被其他环境历史失败任务拒绝。使失败副作用阻塞范围与显式登记目标一致；不修改历史记录，不降低同目标或未知目标保护。

## Milestones
- [ ] RED：真实 submit 路径复现跨目标错误阻塞。
- [ ] GREEN / REGRESSION：最小判断修复，保留运行中、同目标、未知目标及三服登记保护。
- [ ] 提交、融合、安装与真实正式服登记验证。

## Expected Verification
定向单元测试覆盖提交入口；实际单服登记和正式发布预检提供运行证据。测试中的线程替身仅阻止真实远端执行，不冒充部署或 E2E 成功。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，单目标操作使用对应目标的历史副作用门禁。
- 是否存在临时补丁或绕过：否，不修改任务状态或关闭门禁。

## 经验门禁
- Trigger：登记接口修复及维护控制台安装。
- Preflight check：基于已提交 int_main 的专用 worktree；确认受影响文件无用户修改、无运行发布任务，先 RED 后实现，安装已提交内容。
- Blocker：未知目标仍阻塞；存在活动执行器任务不得重启。
- Verification：提交入口测试、融合结果复测、安装字节一致、真实登记终态。
- Forbidden action：不伪造历史 resolution、不修改 SQLite、不触碰其他 worktree 或服务器数据。
- Evidence：execution-log.md、父任务 20261122-sixstep-repeat 的 HTTP409 与登记日志。

## Current Status
in_progress
