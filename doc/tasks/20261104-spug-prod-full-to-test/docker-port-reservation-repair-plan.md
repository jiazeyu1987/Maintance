# 正式服 Docker 内部端口登记恢复计划

## 已完成与当前阻塞
2026-11-05 10:04–10:08 北京时间：原NAS三挂载及来源控制服务已恢复；测试服原四容器已启动，原后端health=UP、实际前端172.30.30.58:8081首页及healthz HTTP200。未提交本轮FULL或恢复。

正式服原backend仍exited。精确旧代理6860/6868已按批准范围SIGTERM，ss证明48081无任何监听，但Docker start原ID仍明确返回“port is already allocated”。Docker26.1.3内部端口分配状态尚未释放，不能通过继续kill或反复start解决。原backend名称/ID/镜像/业务Config/挂载不变；失效静态网络登记已改为同一网络已核空闲的172.21.0.11并恢复原backend别名。其它应用未停止。

## 只读验证
- Docker LiveRestoreEnabled=false，Swarm=inactive；docker ps列出13个容器，其中本任务frontend本来就在循环重启。另12个受保护容器均运行且PID/StartedAt/镜像相对修复前不变。
- docker.service KillMode=process，ExecReload仅SIGHUP，未定义ExecStop；不停止整个containerd或整机。
- /etc/docker/daemon.json原字节SHA256=ecb0765019541bf61bf120ce3c022ad38c2bdb578f768f6a3e1c1b50737dde37。现有registry-mirrors/log-driver/log-opts保留。
- 仅增加live-restore=true的新JSON通过本机服务器/usr/bin/dockerd --validate --config-file=/dev/stdin，exit0，configuration OK；未写配置或reload/restart。
- [Docker官方live-restore文档](https://docs.docker.com/engine/daemon/live-restore/)支持通过systemctl reload docker在线启用，并在daemon参数、bridge和存储驱动不变时保留运行容器。该机制减少停机风险，不把它当作无风险保证。

## 待授权的唯一新增范围
1. 再次核源主机、原配置摘要、12个受保护容器PID/StartedAt/镜像/数据绑定、无其它维护或备份恢复任务；本任务frontend现有循环重启单独记录，不伪装为稳定。记录私密快照。
2. 备份daemon.json原字节，只增加live-restore=true，保留其它键与语义，按原权限原子替换；再次dockerd --validate，通过后systemctl reload docker。
3. 强制要求docker info确认LiveRestoreEnabled=true，当前所有原运行容器PID和StartedAt均不变，docker.service KillMode=process且无ExecStop；任一失败则停止，绝不重启daemon。
4. 在已确认保活生效后，仅systemctl restart docker.service，不重启整机/containerd，不主动stop/restart其它业务容器，不清理容器/镜像/卷/网络数据库。
5. daemon恢复后检查原12个受保护容器PID/StartedAt保持、网络/端口/配置正确；对原IntRuoyi backend再核状态，必要时仅start原ID，再恢复原frontend。若出现不可核资源或其它业务状态变化，停止进一步数据操作并报告，不自动扩大修复。
6. 正式后端UP、前端HTTP200、源/目标全部准入通过后，继续已要求的真实Spug本轮FULL及该新包测试服恢复；失败保留原operationId。

## 回退与风险
该操作期间Docker管理API短暂不可用。live-restore配置验证或热加载失败时不进入daemon重启；保留原配置与全部证据，回退原字节后只做热加载核验。若daemon重启失败或运行容器发生异常，不自动重启整机、不重建容器、不覆盖数据，保留现场并报告。成功启用后保留正式live-restore配置，避免同类管理进程重启停止其它容器。

## 授权边界
用户已批准post-boot-repair-plan.md，但其“不包含的动作”明确排除了整个Docker重启。本计划中的daemon配置/热加载/重启超出该范围，需一次明确PROD授权；其余已批准恢复工作继续执行。当前未执行本计划服务器变更。
