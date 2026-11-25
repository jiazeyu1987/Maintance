## 20261125-intruoyi-fenbeitong-test-prod-release 最终结果

- 用户需求：发布intruoyi到测试服务器和正式服务器；本次不包含助手、审查服或财务配置修改。
- 命令意图：同一已提交输入隔离构建，build-release -> publish-test -> mark-tested -> promote-prod -> accept-prod，再独立核两服运行态和真实登录页面；全部使用正式执行器，未重新构建正式包。
- 结果：2026-11-26-01-52-12 / eb866bbaf4ea1b1c6db93daa63e77576766c3684，两服operation、manifest、IMAGE_TAG、实际双镜像一致，backend UP/frontend HTTP200，三阶段数据库合同PASS，正常入口和维护验收入口页面PASS_WITH_OBSERVATIONS。
- 修复及验证：SQL发布登记6a099294a、分贝通可信签发租户上下文eb866bbaf，均先RED再GREEN并融合int_main；67项JUnit和24项维护配置回归通过。旧构建失败和第二包认证503保留，不拼接版本成功记录。
- 收尾命令：cleanup.py前三项PASS、第四项因未知缓存保护拒绝；核精确派生后finish-maintenance-cleanup.py调用原清理器PASS，release-slot.ps1、release-tenant-slot.ps1、final-local-proof.py均PASS；本任务6个worktree无Git/物理残留，slot9/10释放，稳定执行器和私密配置保持。
- 未完成业务：两服助手报销字段映射未保存、部分租户注册证提醒配置缺失；财务同步/生成/记账和工作台初始化没有验收通过，全部观察显式保留。
- 证据：doc/tasks/20261125-intruoyi-fenbeitong-test-prod-release/verification.md、release-result.json、local-closeout-proof.json。原始私密证据不进入Git。
- 收尾记录时间：2026-11-26T05:00:36+08:00。
