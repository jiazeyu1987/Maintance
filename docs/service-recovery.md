# 前后端有限自动恢复

`ops/spug/release-center/service_recovery.py` 在应用所在 Linux Docker 主机独立运行。前端返回 HTTP 200、后端 `/actuator/health` 返回 HTTP 200 且 `status=UP` 才视为健康。连续失败达到阈值后，仅重启显式启用时绑定的原容器；不会发布、更换镜像或自动启动已停止容器。通知使用通用 JSON webhook，企业微信、飞书等接收端需要由正式告警网关转换。

示例为每 15 秒检查，连续 3 次失败后恢复；启动宽限及重启冷却各 180 秒，每个服务 15 分钟最多由本控制器重启 2 次。达到上限停止重启并记录告警；一次健康、重新启动控制器或重新 arm 均不清除窗口预算。Docker 自身的 `restart: unless-stopped` 继续处理主进程退出，其重试不计入本控制器预算。主机、Docker、数据库或关键依赖故障需要独立监控和处理。

## 安装前门禁

本仓提交不代表服务器已安装启用。安装/重启任何远端实例前，按 `server-access.md` 获取对应任务授权，核实目标环境及当前运行身份；按 `release-backup-restore.md` 核实发布和备份恢复约束。

- Trigger：安装、启用、发布后重新启用、维护和人工停服。
- Preflight check：确认 Linux、Python 3.12、本机 Docker socket、明确容器及其内部探测 IP、真实关键依赖健康检查；备份 epoch 策略已由正式备份恢复流程初始化，状态 READY、数据库 UUID 一致且未停写。
- Blocker：配置、原锁、epoch、日志采集或运行身份未知，数据库只读、maintenance、依赖不健康、停服、锁占用、预算耗尽、时间回退、通知失败、心跳陈旧均必须可见；不靠新建假锁或清空状态使检查通过。
- Verification：健康基线 arm、通知接收、status 心跳、pause 持久生效及安装后目标字节校验；故障重启验收只能在另行授权的测试实例执行。
- Forbidden action：不得由监测器初始化 epoch、解除只读、清除原失败台账、切换数据库/镜像、删除共享盘或无限重启；不得把模板覆盖已有私密配置。
- Evidence：记录来源提交、运行路径、配置摘要、目标身份、arm/pause 原因、真实通知接收结果和本机私有证据摘要，禁止记录明文凭据。

## 配置与启用

1. 将同一已提交版本的 `ops/spug/release-center/service_recovery.py`、`service_recovery_docker.py` 和 `ops/recovery/recovery_backup_epoch.py` 保持原目录关系安装到 `/opt/intruoyi-maintenance`。确认 `/usr/bin/python3 --version` 为 Python 3.12；如果正式解释器位于其他位置，在目标专属 unit 中明确修改 ExecStart。
2. 在仓库外创建 `/etc/intruoyi-service-recovery/test.json`（0600）、`/var/lib/intruoyi-service-recovery/test`（0700）。所有父目录应由可信用户管理且不可被组/其他用户写入；锁和文件必须是原始普通文件，不能使用符号链接。守护进程与原锁使用同一属主，示例 unit 使用 root。
3. 按 `service-recovery.example.json` 填写已核实配置。`stagingRoot` 必须是目标发布器实际使用的公共 `operationLockRoot`，没有该覆盖项时才是发布 `stagingRoot`，不能填某次 `attempts/JOB-*`。必须使用已存在的 `runtime-operation.lock` 和既有私密 `SourceBackupEpochPolicy/v1` 策略，控制器不会创建这些保护依据。
4. `services.*.url` 的主机必须对应该容器当前 Docker 网络 IP 或真实可解析的容器名；服务器宿主机通常不能通过 Docker 内部 DNS 解析容器名，优先填写已核实内部 IP。示例 `192.0.2.*` 不可直接启用。探测不使用代理、不跟随重定向。后端维护变量须为 false 或沿用既有未设变量的非维护契约。`dependencies` 必须列出真实关键依赖，均需 Docker healthcheck 为 healthy；确实无额外依赖才配置空数组。
5. 配置正式通知网关 URL 与 0600 token 文件，网关接收 `Authorization: Bearer` 和 JSON 事件。没有鉴权时显式 `tokenFile: null`。URL 不接受内嵌凭据、query 或 fragment。HTTPS 证书按系统可信链验证。
6. 所有服务已健康、epoch READY、无发布/备份恢复任务时，执行下面的 arm，再手动运行一次并核通知结果。arm 仅记录基线，run/once 才执行监测及投递。

```sh
/usr/bin/python3 -B /opt/intruoyi-maintenance/ops/spug/release-center/service_recovery.py --config /etc/intruoyi-service-recovery/test.json arm --reason "verified healthy installation baseline"
/usr/bin/python3 -B /opt/intruoyi-maintenance/ops/spug/release-center/service_recovery.py --config /etc/intruoyi-service-recovery/test.json once
/usr/bin/python3 -B /opt/intruoyi-maintenance/ops/spug/release-center/service_recovery.py --config /etc/intruoyi-service-recovery/test.json status
```

7. 核对 unit 路径、环境和解释器后，复制 `intruoyi-service-recovery@.service` 到 `/etc/systemd/system/`，执行 `systemd-analyze verify`、`systemctl daemon-reload`，在已授权目标启用 `systemctl enable --now intruoyi-service-recovery@test`。每个环境使用独立配置、状态目录和 unit 实例。控制器启动不自动 arm；未建立基线则明确退出。daemon 锁禁止同一实例 run/once 重复运行。

## 发布、维护与人工停服

先执行并确认 pause 成功，再开始人工停止容器或独立于发布器的维护；pause 与恢复循环共用控制锁，命令成功返回后禁止后续恢复。直接使用未协调的 `docker stop` 与正在执行的 Docker restart 仍存在竞态，必须遵守 pause 顺序。

```sh
/usr/bin/python3 -B /opt/intruoyi-maintenance/ops/spug/release-center/service_recovery.py --config /etc/intruoyi-service-recovery/test.json pause --reason "approved maintenance before stopping services"
```

发布、备份、覆盖恢复期间，监测器同时取得发布公共锁和原备份 sourceLockPath；锁占用或 epoch 非 READY 时零重启。发布操作台账或 epoch 改变后，即使原锁释放也不继续旧基线。发布后、配置变化或容器重建后，先恢复全部健康并核实目标，再显式 arm；配置变化还需重启控制器读取新配置。备份恢复留下的停写/维护状态须由其原任务正式处理，监测器不会解锁或代为完成恢复。

## 故障与通知证据

状态以 fsync + 原子替换保存，重启请求先持久记录预算及 pendingRestart，再调用 Docker；结果未知时停在 OUTCOME_UNKNOWN，不重放请求。只有人工核对且全量健康后才允许显式重新 arm。重启前采集容器状态及最近 80 行 Docker 日志到状态目录 `evidence/`，权限 0600；日志可能含敏感信息，不发送通知、不提交 Git。采集失败不重启。通知包含事件 ID、环境、服务、探测摘要、容器/镜像标识及私有证据路径/摘要。

投递状态独立保存为 PENDING、FAILED、DELIVERED、EXHAUSTED；每轮最多投递 4 项，每项有限次数重试，接收网关应按事件 ID 去重。DELIVERED 只证明网关接受 HTTP，不代表人员已读。`status` 输出各类通知数量；监控必须检查 FAILED/EXHAUSTED 和陈旧心跳。服务恢复会另发 RECOVERED。

`status` 非 HEALTHY 返回退出码 2；连续心跳超过配置阈值即 STALE，不能拿旧 HEALTHY 当现状。独立于该主机的监控需要检查此状态及主机存活；宿主机宕机时本控制器自身不能发送通知。

状态最多 8 MiB、2000 个事件，私有故障文件最多 128 个；容量达到上限会阻断操作并暴露错误。归档需先 pause 并停止该 unit，由明确授权维护任务保全事件、证据、哈希和完整预算；不能删除 state.json、失败记录或重建空状态来解除限额。

## 本机验证

`test_service_recovery.py` 使用真实 Linux Docker/MySQL/HTTP、文件锁和CLI；仅允许任务自有网络与卷，通过 `RECOVERY_TEST_NETWORK`、`RECOVERY_TEST_VOLUME` 显式指定。运行于 Linux 测试容器，将维护仓只读挂载 `/repo`、自有卷挂载 `/case` 并接入本机 Docker socket。测试会创建及删除自己的服务，不应在业务主机直接运行。测试通知只发往隔离 runner 内的真实 HTTP 接收器。
