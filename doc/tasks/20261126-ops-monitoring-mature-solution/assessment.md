# 成熟监控方案建议

评估日期：2026-11-26。仅核对本地既有事实与公开官方资料，没有安装或操作远端服务器。

## 推荐

按目前少量 Linux/Docker 业务服务器、Spug 发布和既有专用恢复控制器的情况，首选 Zabbix 作为统一监测与告警平台，保留 service_recovery 作为有限恢复的唯一执行方。该推荐是针对现有架构与管理成本的判断，不是产品性能基准测试结论。

Zabbix 负责主机、磁盘/inode、Docker、HTTP/HTTPS、关键依赖、监控心跳和备份年龄；负责事件展示、维护期抑制、人员确认、通知和升级。现有恢复控制器负责健康判断、原容器身份、依赖检查、重启预算、冷却、发布/备份恢复锁、pause/arm 和故障证据。Spug 保持发布入口，维护工具汇总健康、待处理事件和恢复状态并链接详情。

尚需开发的是小范围接入：将恢复控制器状态/心跳/预算及备份成功点年龄暴露为固定监控项，将发布维护状态与监控维护窗口协调。Zabbix 维护抑制只影响监控/告警，不自动等价于恢复控制器 pause，两个状态必须分别成功确认。不能直接绑定告警到 docker restart 或让 Zabbix 和控制器重复重启。

## 候选比较

| 方案 | 适用性 | 主要取舍 |
| --- | --- | --- |
| Zabbix | 本次首选；集中管理少量服务器及基础依赖、处理告警 | 内置监测、告警操作、确认、维护与升级；本项目状态及通知渠道仍需配置或适配 |
| Prometheus + Alertmanager + Grafana | 更适合已有指标体系、微服务指标分析或未来动态容器环境 | 多维指标和查询灵活；需组合采集器、展示和告警组件；人员认领、值班升级需要独立事件管理接入或设计，不能把 silence 当确认 |

两者都能发现故障；项目级自动修复需要理解发布、停写和数据恢复的业务约束。Zabbix 虽支持远程命令，本次推荐默认不以该能力直接执行容器恢复。

## 部署与验收边界

- 监控平台放在独立常驻主机或虚拟机，并核其实际故障域不与被监测生产主机完全重合；另设独立心跳观察覆盖监控服务自身。虚拟机位于同一故障物理主机并不能提供主机故障隔离。
- 采集与恢复权限分别设计；Docker 官方 Agent 2 模板需要 Docker socket 访问，不能把监控采集身份宣传为天然低权限。部署前单独审查实际 socket 访问范围及受限采集替代方式。
- HTTP 探测检查状态、内容与响应耗时；后端健康明确检查 UP。容器 running 不足以证明业务可用。Zabbix HTTP web scenario 不代表真实浏览器业务 E2E；最终 E2E 仍遵循仓库 Playwright 规则。
- 初期集中告警：主机失联、业务不可用、依赖故障、磁盘/inode 不足、备份超期、恢复控制器未启用/心跳过期/预算耗尽。
- 官方 webhook/媒体类型与企业微信或飞书网关的具体兼容需选定后验收；HTTP 接收成功不代表人员已确认。
- 测试环境验收应用假死、主机/监控失联、通知失败、维护停服、预算耗尽及恢复事件；必须证明维护/备份恢复期间零误重启、过期快照不显示健康。
- 软件版本在实际实施时选择仍受支持且与服务器兼容的稳定版本，使用对应版本模板；此次不承诺硬件规格或容量，须根据采集频率、指标数量和保留期估算。

## 官方能力依据

- Zabbix Docker Agent 2 官方集成：容器状态、健康与资源指标；需要 Docker socket 权限。https://www.zabbix.com/integrations/docker
- Zabbix Web monitoring：HTTP/HTTPS、响应耗时/状态码及内容检查。https://www.zabbix.com/documentation/current/en/manual/web_monitoring
- Zabbix Escalations：按步骤和时间升级通知与动作。https://www.zabbix.com/documentation/current/en/manual/config/notifications/action/escalations
- Zabbix Maintenance：维护期采集及告警抑制规则。https://www.zabbix.com/documentation/current/en/manual/maintenance
- Zabbix Problem acknowledgment and suppression：问题确认及抑制能力。https://www.zabbix.com/documentation/current/en/manual/acknowledgment
- Zabbix Remote commands：告警动作可执行远程命令；本项目建议仍统一由专用恢复控制器执行恢复。https://www.zabbix.com/documentation/current/en/manual/config/notifications/action/operation/remote_command
- Prometheus Overview：多维时序指标、HTTP 采集与动态服务架构适用性。https://prometheus.io/docs/introduction/overview/
- Alertmanager：去重、分组、路由、静默和抑制。https://prometheus.io/docs/alerting/latest/alertmanager/

本地恢复约束见 docs/service-recovery.md。上述网页经公开 GET 获取核对；web 搜索工具失败没有被当作资料验证成功。
