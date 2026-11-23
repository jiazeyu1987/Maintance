# 执行记录

- 已核固定275c87011代码、manifest、git变更6aa656b61，确定PATROL业务变更漏CHECK升级；两个新增迁移在测试真实账本APPLIED。
- 只读DESCRIBE/SHOW CREATE TABLE/information_schema及后端docker logs：CHECK启用且拒绝PATROL，错误3819；当前镜像与已发布包一致。原调查文件本机不存在，订单关联/本机结构历史不作独立已证实声明。
- 验证结论：调查完成；findings.md记录缺失迁移、验收范围不足及正式修复建议。未执行测试写入、DDL/DML或发布，无测试/构建需求，不创建worktree；产品修复仍按原分工由IntRuoyi处理。

- 用户要求定位原因；范围为测试服只读排障及本地源码/封包核查，无修复或再次发布授权。
- BDD: Given 活跃订单会生成巡检任务；When 新程序PATROL遇旧检查约束；Then 识别约束来源及为何发布未对齐，不通过真实写入复现制造副作用。
