# 已验收版本晋级正式服
## Current Status
completed
## 目标及授权
用户明确要求发布正式服；目标172.30.30.57，沿用测试通过的2026-11-20-23-36-11，前后端同包晋级，不重新构建混入新提交。前序测试发布任务completed。审查服不属于本次明确要求。
## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，使用正式晋级链、迁移前置与恢复记录。
- 是否存在临时补丁或绕过：否。
## 经验门禁
- 先核experience-index、server-access、release-backup-restore、release-agent-checklist与worktree规则；同tag测试验收、manifest、包SHA及晋级授权必须真实有效。
- 正式写入前记录experience-preflight PASS，核锁、目标版本、迁移、磁盘和恢复依据；不修改共享/mnt/nas。
- 仅使用已提交输入与独立发布执行环境，不直接主工作区构建或发布。
- 完成须operation成功、manifest/IMAGE_TAG/双镜像同包、UP/200、真实登录菜单与版本说明通过；异常逐项归因。
- 先ready_for_closeout，再确认自有worktree/控制台收尾后completed；凭据不记录。
## 里程碑及验证
- [x] 复核同包晋级资格、正式现状与预检。
- [x] 执行正式晋级及恢复记录核验。
- [x] 运行态、真实页面、版本与菜单验收。
- [x] 收尾记录和提交。

## 最终验证
已先ready_for_closeout；预检、部署、开放全部成功，独立运行态及维护/开放两轮页面验收完成，见acceptance.md。原构建worktree物理不存在，本轮无新worktree需融合/删除。稳定执行器43352仍在原source路径，未改运行控制台，无活动发布任务。正式已开放目标版本。
