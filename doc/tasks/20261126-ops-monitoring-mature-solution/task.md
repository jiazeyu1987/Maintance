# 持续监测成熟方案评估

## Task Goal
评估当前运维工具第一优先项（持续健康监测、外部告警和有限自动恢复）的成熟产品方案，并给出适合现有 Docker、Spug、自定义运行控制器的落地建议。本任务只做本地文档核对和公开官方资料查询，不安装、配置或操作服务器。

## Current Status
completed

## Milestones
- [x] M1：核对现有恢复控制边界与约束。
- [x] M2：核对 Zabbix 和 Prometheus/Alertmanager 的官方能力。
- [x] M3：形成 assessment.md；文档 UTF-8 及差异检查通过，限定本任务记录提交。

## 结论
优先 Zabbix 统一监测告警，现有 service_recovery 保持唯一有限恢复执行方；Spug 与维护工具进行状态接入。Prometheus/Alertmanager/Grafana 作为指标分析和动态服务场景的可选方向，不建议当前同时建设两套监控。

## Final Verification
官方能力与现有恢复约束核对完成；任务文件严格 UTF-8 解码、无替换字符和 git diff --check 均通过。无产品实现、运行态变更、worktree 或进程需收尾。仅提交本任务文档及共享请求日志的本次追加块。

## Expected Verification
候选能力必须有官方资料依据；明确产品监控能力与本项目业务恢复逻辑的边界；不把建议写成已安装或已启用事实。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；本任务只评估方案。
- 是否从根因和长期维护角度解决：是；优先采用成熟监控平台，保留现有安全恢复控制器的业务约束。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- Trigger：监控、告警、自动恢复、Zabbix、Prometheus、Alertmanager、Docker health、service-recovery。
- Preflight check：读取已完成的运维优先级评估和 service-recovery 约束；明确本机静态事实、远端已验证事实和公开资料；不执行 arm/pause/run/once。
- Blocker：无法证明候选能力、需要远端安装授权或现有恢复边界不清时停止实施结论；不把产品默认配置当安全基线。
- Verification：官方文档链接、现有代码/文档证据、明确的实施验收清单。
- Forbidden action：未经授权不安装监控、不改服务器、不注入故障、不重启服务、不写入业务或备份数据。
- Evidence：本任务 assessment.md、execution-log.md、docs/service-recovery.md、前序运维优先级评估。
