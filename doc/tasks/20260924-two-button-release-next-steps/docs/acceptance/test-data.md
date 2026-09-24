# 测试数据与资源归属

## Purpose and Scope
定义锁、工作流和真实按钮验收数据边界；不复用失败R2作为新版成功证据，不使用备份数据冒充测试租户。

## Evidence Reviewed
AGENTS租户/资源归属规则、锁SQL测试、源冻结、同包晋级及实施计划。

## Required Test Data
- 隔离MySQL临时库：无锁、旧FAILED/APPLIED、活动他人锁、同tag旧lease、失权fence及并发数据；运行生产生成SQL。
- 代码测试fixture：唯一任务标识、批准提交、有效/漂移双摘要、有效/过期测试证据/preview/grant；不得冒充真实发布证明。
- 真实验收：登录权限、批准版本、可用恢复候选、NAS容量、镜像工具和目标配置。只读业务验收复用既有真实数据，不顺手修改业务库。
- 每轮新worktree/newtag，测试服与正式服共用同一发布包。

## Reset Procedure
只清理任务自有临时库和目录。远端锁、台账、tested和.env不得手工补绿；失败保留证据，通过正式恢复入口及精准owner条件处置。删除worktree前确认无未合并提交、失败验证和进程依赖。

## Data Ownership
数据/进程记录taskId、owner、创建时间、清理方式、PID与源路径。不触碰别的任务索引、worktree或端口。密码、连接串、认证头和真实lease token不入文档/截图/提交。

## Test Blockers
缺账号菜单、隔离数据库、容量、依赖服务、批准范围或恢复条件即阻断；日志只记录安全注入存在性/身份匹配，不复制口令。
