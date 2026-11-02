# 启动 Spug

## Task Goal
确认并提供用户所指的本机 Spug/IntRuoyi 入口；用户将 `E:\IntRuoyi` 映射为 `C:\Users\D01021\Documents\ChatGPT\IntRuoyi`。该路径对应 IntRuoyi 前后端仓库；检查后发现本机实例已运行，因此不重复启动。

## Milestones
- [x] 确认用户指定目录、现有启动入口与运行状态。
- [x] 验证当前前端和后端 HTTP 响应与健康检查；已运行时保留现有实例。
- [x] 记录结果并完成收尾。

## Expected Verification
核对仓库路径与启动脚本、监听端口、前端 HTTP 响应和后端健康 JSON；不进行登录写入、代码构建或发布。

## 经验门禁
- Trigger：本机服务启动，PowerShell 操作。
- Preflight check：先按经验索引定位 Spug 与本机启动经验；确认服务归属及启动命令。
- Blocker：缺失安装、依赖或正式启动配置时明确报告，不构造临时替代服务。
- Verification：运行状态与真实 HTTP 响应对应同一实例。
- Forbidden action：未授权远程操作、发布、数据修改、停止无关进程；不得记录凭据。
- Evidence：命令意图与脱敏验证结果写入 execution-log.md 和请求命令日志。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，使用现有正式启动方式。
- 是否存在临时补丁或绕过：否。

## Verification Evidence
- `http://localhost:8081` -> HTTP 200 (`text/html`)，由本机 IntRuoyi 前端进程 PID 18172 提供。
- `http://localhost:48081/actuator/health` -> HTTP 200，Spring Boot health endpoint。
- `http://localhost:48081/admin-api/infra/health` -> HTTP 200。
- 端口 8081 与 48081 分别由已有前端 PID 18172 和后端 PID 26648 监听；没有启动重复实例。

## Current Status
completed

## 用户澄清后的实际目标
用户再次要求启动独立 Spug。前次只验证 IntRuoyi，未完成 Spug 启动；本次继续定位现有 Spug 安装与正式启动入口，不把 IntRuoyi 运行状态作为完成证据。
- [x] 定位独立 Spug 入口。
- [x] 启动并验证 Spug 实例和 HTTP 页面。

## 当前阻塞
旧阻塞已解除：用户提供完整 Spug ZIP 并批准 C: 适配，当前按 C: 独立恢复方案执行。此前 IntRuoyi HTTP 200 不作为 Spug 验证证据。

## Ownership
本聊天首次任务，无已识别的本线程前置任务；其他任务记录不视为本线程前置任务。

## 2026-10-22 ZIP 恢复续办
用户授权从本机 Documents/Spug-complete-20261022-151627.zip 恢复本机 Spug，文件已确认存在，大小 15256164276 字节。
目标：检查归档恢复说明、镜像及数据，按正式配置恢复本机独立 Spug 并验证。
里程碑：1.归档及门禁检查；2.本机隔离恢复；3.运行态与页面验证；4.记录收尾。
预期验证：镜像/容器身份、卷与配置、数据库和页面真实响应，不以 IntRuoyi 响应代替。
经验门禁补充：恢复前读映射后 release-backup-restore/powershell-memory；检查归档路径安全、容量和端口冲突；保留现有无关资源；禁止连接远程执行发布和输出凭据；缺失恢复依据先阻塞。
设计约束：无 fallback、无临时绕过，使用备份自带正式恢复方案。
执行起始状态：in_progress

## 恢复里程碑与最终验收
- [x] 完整归档 bytes/SHA-256 全部通过，原 ZIP 保留不改。
- [x] 本机 C:/Spug 恢复独立 Compose 项目及五个持久卷；实际 bind sources 逐项匹配 C:。
- [x] 镜像 ID 一致，数据库 36 表检查 OK；3 hosts / 14 tasks / 1 user / 157 task_histories。
- [x] 真实浏览器登录、主机列表、任务列表及历史记录通过；三个页面 HTTP 200。
- [x] 发布中心页面应用选择通过，明确显示 executor unavailable；备份恢复页读取到原来源登记、原操作编号与历史，未连接远程执行器，提交入口按原门禁禁用。
- [x] scheduler autostart=false 且实际调度进程0；无本任务宿主执行器/SSH 转发。
- [x] 单独保存实现与最终任务记录，完成收尾。
- 本次没有发布构建、worktree、服务器操作或临时控制台；Spug/MariaDB 是用户要求保留的运行实例。
- 操作说明：RESTORE-C.md；运行证据：runtime-verification.json；截图 C:/Spug/restored-spug.png。
- 原安装未找到及文件不存在的旧阻塞已解除；前次路径判断错误已纠正。外部执行器接管不属于本次 Spug 本体恢复完成条件。

## 收尾阻塞
已解除：用户提供真实身份后，仅配置本仓库 user.name=jiazeyu19877、user.email=252451895@qq.com；实现已提交 d502af5，原提交阻塞解除。

## Final Verification
completed：恢复合同2项测试再次PASS；运行态复核PASS（36表、3/14/1/157、C:挂载、镜像身份、localhost端口、scheduler未启动）。无本任务临时worktree或临时控制台待清理；运行实例按用户需求保留。实现提交 d502af5，仅本任务文件；最终任务记录单独提交。
