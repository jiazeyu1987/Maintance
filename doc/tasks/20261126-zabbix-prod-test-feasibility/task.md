# Zabbix 接入正式服与测试服可行性评估

## Task Goal
全面评估 Zabbix 接入正式服、测试服的兼容性、部署拓扑、权限与安全、监控覆盖、告警与有限恢复衔接、资源成本和实施验收要求。按用户本次明确指定环境的评估请求，进行必要且有界的只读现场检查；不安装、不重启、不配置、不注入故障。

## Current Status
completed

## Milestones
- [x] M1：核对访问规范、经验门禁、前序状态与官方支持矩阵。
- [x] M2：只读核对两服 OS、Docker、容量、网络/安全及服务现状。
- [x] M3：形成方案、分环境结论、风险、实施门槛及验收清单。
- [x] M4：文档验证与精确任务记录收尾。

## Expected Verification
将当前实测事实、历史记录、官方产品能力和待验证假设明确分开；只读检查退出码和采样时间可追溯，不输出秘密；上线方案不等同已部署。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；成熟平台负责监测告警，既有控制器负责有界恢复，统一状态来源。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- Trigger：正式服/测试服 Zabbix 可行性、只读主机检查、SSH/PowerShell、有限自动恢复。
- Preflight check：读取 docs/server-access.md、docs/service-recovery.md 与命中索引；从已验证本地私密配置取得注册目标及 SSH 身份，严格主机密钥校验；脚本只执行明确只读字段查询，排除完整 docker inspect 环境变量和秘密文件。
- Blocker：目标/身份不符、SSH 校验失败、权限不足或现场值不明确时保留未知；不自动修改权限、防火墙、服务、挂载或系统包。
- Verification：记录采样时间、退出码、明确字段、官方兼容依据；最终核任务文档 UTF-8 与差异。
- Forbidden action：不安装/更新软件、不执行 restart/arm/pause/run/once、不访问业务写接口、不读取秘密原文输出、不修改公司 NAS、不扫描无关主机。
- Evidence：execution-log.md、feasibility-report.md 与脱敏现场快照。

## Predecessor
本线程 20261126-ops-monitoring-mature-solution 已 completed；此前评估记录可作为背景，远端现状以本次必要只读采样为准。

## Assessment Result
技术可行、正式上线有条件；推荐独立中心/专用数据库，两服主机与HTTP先行，Docker白名单及权限路线单独验收。现场发现CentOS8过保、测试现有Prometheus、178个运行容器/80%Docker盘、两服恢复策略差异、Python3.12解释器前提尚未证实、现有MySQL8.0.39不适合作Zabbix8后端。完整报告列出未来实施条件，评估本身无未完成远端操作。

## Final Verification
12个正式交付文件通过严格UTF-8、无BOM、无替换字符与凭据模式检查；5个Python文件通过AST解析，4个JSON文件解析通过；报告核心主机事实与脱敏摘要一致。评估未创建worktree、未启动持久进程、未改变运行控制台和服务器配置，无本任务待恢复资源。两份初始原始快照保留本地且不提交（含已明确作废的locale乱码字段和大量无关容器元数据）；提交摘要记录原快照SHA256，补核证据单独保留。未来安装条件不作本次已通过的部署验收。
