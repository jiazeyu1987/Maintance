# Execution Log

- 用户范围：只检查 Spug 本机使用情况；不接通执行器或远端。
- BDD: Given 已恢复的本机 Spug；When 只读检查服务和真实页面；Then 数据可访问，集成未接管状态明确可见，不提交业务任务。
- 本任务不修改产品行为，复用既有只读验收，不新增产品测试。
- GREEN: experience-preflight -> PASS，前置任务 completed、经验门禁已摘录；浏览器仅登录/读取，不执行业务任务。
- GREEN: bundled Python 执行 start-spug-20261022/verify_runtime.py -> PASS；36 表、3 主机、14 任务、1 用户、157 历史，镜像及 C: 挂载正确，scheduler autostart=false、进程数 0。脚本结果与前次证据一致。
- GREEN: docker ps / HTTP GET -> 两个恢复容器运行，三个入口 /、/release-center/、/backup-restore/ 均 HTTP 200；其他四个业务容器未操作。
- GREEN: Get-NetTCPConnection 指定本机 Spug/集成端口检查 -> 仅 127.0.0.1:18080 监听；所检查执行器与转发端口无监听。
- GREEN: 真实浏览器 -> 已登录主机管理可见 3 台；任务计划共 14 条、历史记录可见。主机行的“已验证”为备份保存状态，不代表本次远程连通性验证。
- 使用限制：发布中心显示 Release executor unavailable；备份恢复显示 SOURCE_NOT_VERIFIED_BY_W01、提交禁用。未点击执行、激活、远程查询、恢复或发布。
- 日志：docker logs --tail 300 分别检查应用 19 行、数据库 88 行；应用无错误关键词，数据库 9 条启动 Warning（io_uring/native AIO、skip-name-resolve、binlog 过期设置），无 ERROR/Traceback；只记录脱敏摘要，未保存原始日志。
- Closeout: 无产品修改、无新增 worktree/服务/控制台，前置恢复包保持不改；只提交本任务文档及请求日志。验证完成，状态 completed。
