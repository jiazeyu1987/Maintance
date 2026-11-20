# 同步最新代码并发布前后端
## Current Status
completed
## 目标
同步最新已提交IntRuoyi代码，承接当前测试服范围，发布前后端并验证；正式服不在本轮范围。前序菜单任务仍等待应用修复交付，本轮先复核实际进度。
## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，走正式发布链及版本一致性验收。
- 是否存在临时补丁或绕过：否。
## 经验门禁
- 使用已验证配置确认源码路径，fetch核远端，不把脏改动打包。
- 每轮新建目标提交专用worktree，先读worktree-memory与release-backup-restore。
- 发布前核目标迁移、manifest、锁和恢复依据；高风险动作前记录experience-preflight PASS。
- 同一releaseTag构建发布；核operation、manifest、IMAGE_TAG、实际前后端镜像、UP和HTTP200及真实页面。
- 仅测试服不执行mark-tested或晋级；完成前清理本任务worktree并保留证据，凭据不进日志。
## 里程碑与预期验证
- [x] 核代码远端、应用修复和运行环境。
- [x] 同步并冻结目标提交，在独立worktree构建。
- [x] 发布测试服前后端并完成全部运行态及页面验收。
- [x] 收口记录与自有worktree清理。

## 最终结果
同tag2026-11-20-23-36-11已完成测试服双端发布、运行态及真实页面验收，详见acceptance.md。测试A三个模块及218个排除菜单ID均不返回，正常MES入口保留。已先记录ready_for_closeout，再核本任务worktree物理/注册均删除及原稳定控制台路径未变，完成收口。后补实时远端引用查询两次网络失败，仅该附加检查未完成；发布开始时fetch/ff-only成功，冻结提交及构建来源已验证，不追逐发布期间的新提交重建。未操作正式服。
