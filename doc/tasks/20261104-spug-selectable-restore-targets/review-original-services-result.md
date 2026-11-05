# 审查/备份服 .59 原服务恢复与选择验收

2026-11-05，按用户“授权按此范围处理（PROD）”完成review-original-services-plan.md范围。.59现在可在Spug“全部包清单→恢复→覆盖现有程序”中选择。未在.59执行数据包恢复。

## 实际结果

- 原canonical路径已bind,ro到既有CIFS共享；同一新FULL point.json SHA为af95ffa94e9478bd32935c6e0c662aa5590854a0cda7597b84a25abd81a8f128。专属mount及控制依赖已登记，均active/enabled；未改fstab或共享内容。
- 仅按原ID启动mysql/redis/minio/backend，原UUID a4f03708-cc74-11f1-9cce-0242ac1def16、885表、log_bin=1；Redis PONG、MinIO200、backend UP/frontend38081 HTTP200。
- Chrome真实登录原主程序入口172.30.30.59:38081，用户管理2117条/20行，版本2026-11-03-12-15-42；测试业务写入0。完整人员页面与凭据只在私密目录。
- 全部原镜像/配置/存储身份保持；已运行frontend和其它容器PID/StartedAt保持，未创建/重建/删除容器、未停其它业务或重启Docker/整机。
- 默认bridge ID和frontend动态IP的旧登记与重启后观察不符；完整核实网段/语义/成员、数据网络/端点和启动前inspect后，仅发布新配置代次。严格MAIN运行/存储校验保留，没有修改业务网络。
- 真实Spug从侧栏进入全部包清单，选择新FULL smallapp-73cd541a95d84d6a86f9d693e4053c75，分别核.58/.59精确目标确认并返回；未勾选覆盖，未最终提交，仅登录POST。远端operation/claim/active均为0。

## 验证证据

review-authorized-final-verification.json、review-authorized-browser-choice.json、review-authorized-confirm.png、target-review-original-start-business.json及分阶段review-authorized-*.json。目标准入为HTTP200，目标intruoyi-main-59-safe-restore-20261104-v1。Spug原始页面初始化阶段的失败点击、一次BRIDGE_IO_FAILED及后续三端认证连接复核原样留存私密诊断，公开摘要见review-browser-diagnosis.json；未改超时或吞错误使其通过。

## 范围与尚未完成项

本轮只证明.59原服务恢复、只读归档、准入与页面选择；实际恢复验收仍只有此前正式→测试History350/355路径。正式服.57作为恢复目的地仍被禁用，现有可写应用挂载/对外数据端口与资源writer合同须正式补齐，原整体任务保持blocked。

本轮未新建发布worktree或替换程序包，未改原主程序restartPolicy，未执行整机重启验收。现有CIFS源挂载没有持久unit/fstab条目；新增canonical bind和控制单元已enabled，但不据此声称源共享及四个restartPolicy=no业务服务已具备开机自动恢复。重启后须重新核实际服务、原共享与严格网络登记。
