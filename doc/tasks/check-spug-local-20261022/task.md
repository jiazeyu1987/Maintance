# Spug 本机使用检查

## Task Goal
用户在恢复后要求继续，并明确选择“只检查 Spug 本机使用情况”。只读核对本机服务、数据、页面和异常，不启动执行器、SSH 转发或调度器，不操作服务器。

## Milestones
- [x] 核对容器、数据、镜像、挂载及调度状态。
- [x] 浏览器检查登录后的主机、任务与集成页面。
- [x] 记录结果及已知使用限制，提交本任务记录。

## Expected Verification
沿用恢复验收脚本检查 36 张表及 3/14/1/157 记录基线，三个入口 HTTP 200，浏览器真实数据可见；检查新容器日志异常，不泄露凭据。

## 经验门禁
- Trigger：本机 Spug 只读运行检查。
- Preflight check：前置恢复任务 completed；读取经验索引与既有恢复操作说明；明确本次不接管执行器。
- Blocker：数据库、挂载、镜像、页面出现真实失败时如实报告，不重置、补数据或隐藏错误。
- Verification：脚本、HTTP、浏览器证据指向同一 localhost 实例。
- Forbidden action：服务器操作、任务执行/激活、业务备份恢复、SSH 转发、修改权限或凭据。
- Evidence：execution-log.md 记录实际检查结果，日志只记录脱敏摘要。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，仅核对现有环境，不改产品。
- 是否存在临时补丁或绕过：否。

## Current Status
completed

## Verification Result
- 本机核心使用检查 PASS：登录有效，主机/任务/历史可见，36 表检查通过，记录数 3/14/1/157；三个入口 HTTP 200。
- 镜像及 C: 挂载一致；Spug 仅监听 127.0.0.1:18080，scheduler 无运行进程，所核对执行器/转发端口均无监听。
- 发布中心明确报告执行器不可用；备份恢复页面保留原来源未验证状态。本次不接管外部集成，不能据此认定发布或备份恢复可执行。
- Docker 输出日志未见 ERROR/Traceback；MariaDB 有 io_uring、skip-name-resolve 及 binlog 过期配置启动警告，当前表校验和查询通过。
- 未创建 worktree、临时运行控制台或后台服务；无清理、合并事项，既有业务容器和其他工作区改动保持原状。

## Ownership
同线程前置任务 start-spug-20261022 已 completed，实现 d502af5、记录 b83e0ae。
