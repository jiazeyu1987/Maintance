## 2026-11-01 提交推送三服一致性修复

- 用户要求：将三服一致性修复改动提交并推送到Git。
- 范围：IntRuoyiAll与Maintance的codex/three-server-schema-20261101独立分支；保留主工作区和无关改动，不合并int_main，不重新发布服务器。
- 已提交代码：源码fb88105af40e4ee6366a20dae2df721f1de2dcb0；维护实现43e4d3e、验收收尾ef647752。既有531项回归及真实MySQL和三服验收证据沿用，未改变产品代码。
- 推送预检：扫描待上传历史，源码6提交/19 blob、维护12提交/115 blob；最大文件851128字节，无实际私密凭据、私钥或超限对象。配置文件路径的字符串匹配经脱敏核对属于路径，不是密码。
- 网络与钩子：Git直连443超时；只在本次命令采用Windows已启用的127.0.0.1:7890代理，不改变系统/Git配置。钩子使用已有Python3.12；旧主目录检查器不支持新清单，在精确目标提交的独立worktree执行完整菜单/权限及端口钩子后通过，没有跳过钩子。
- 结果：维护16:46:42推送ef647752成功，源码16:52:27推送fb88105a成功；ls-remote精确核对一致，普通推送无force。
- 收尾：推送worktree无新提交、未构建或启动应用；干净状态核实后Git删除，物理路径及登记均不存在，slot3释放，保留其他任务登记。最终Git操作记录另做维护分支提交，并核对远端最终哈希。
- 证据：doc/tasks/20261101-push-three-server-fix内push-source.json、push-maintenance.json、push-audit.json、worktree-closeout.json、slot-closeout.json及records-commit.json。
