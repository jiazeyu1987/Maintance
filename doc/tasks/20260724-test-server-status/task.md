# 20260724 测试服务器状态检查

## Task Goal

按项目服务器访问规则，只读检查测试服务器当前运行状态，并向用户汇总健康状态、关键服务状态和发现的阻塞项。

## Milestones

- [x] 创建任务记录并摘取适用门禁。
- [x] 定位并读取测试服访问资料。
- [x] 执行只读服务器状态检查。
- [x] 记录验证证据并向用户汇总结果。

## Expected Verification

- 读取适用的服务器访问文档后再连接测试服。
- 使用只读命令检查系统时间、负载、磁盘、内存、Docker/Compose 服务状态、后端健康接口和前端 HTTP 状态。
- 命令输出不得包含未脱敏凭据。

## 经验门禁

### 服务器访问只读门禁

- Trigger: 用户要求查看测试服务器状态。
- Preflight check: 先读取项目指定的服务器访问文档，确认测试服地址、连接方式和允许的只读状态检查命令。
- Blocker: 服务器访问文档缺失、测试服地址或凭据来源无法确认、SSH 无法连接、或状态检查命令需要写入/重启/发布权限。
- Verification: 记录访问文档路径、SSH/HTTP 只读检查命令、退出码和关键状态结果。
- Forbidden action: 未经用户明确授权，不得重启服务、发布、修改远端文件、修改数据库、清理磁盘或切换环境。
- Evidence: `AGENTS.md` 要求服务器状态检查前读取 `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`；`docs/experience-index.md` 的服务器访问路由。

### PowerShell UTF-8 与命令记录门禁

- Trigger: Windows PowerShell 下读取中文文档、记录任务日志、执行 SSH/HTTP 状态检查。
- Preflight check: PowerShell 输入/输出编码设为 UTF-8；中文文件读写使用 UTF-8；不用 `&&` 串联命令。
- Blocker: 中文文档无法按 UTF-8 读取、命令输出含明文凭据、或命令退出码无法确认。
- Verification: 记录 UTF-8 读取与状态检查结果。
- Forbidden action: 禁止用默认编码读写中文文件、禁止记录明文密码/token/私钥、禁止用 fallback 地址替代指定测试服。
- Evidence: `AGENTS.md` Encoding Safety Policy；`docs/experience-index.md` PowerShell 经验路由。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，只做真实测试服只读状态核查，缺少前置资料则阻塞。
- 是否存在临时补丁或绕过：否。

## Verification Evidence

- Canonical path check: `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md` 当前不存在；本次只读定位到历史预检证据 `doc/tasks/20260709-codeonly-three-env-head-release/evidence/preflight-read-server-access.txt`，并用维护仓长期门禁 `docs/release-build-preflight-lessons.md` 交叉确认测试服为 `172.30.30.58`、运行目录为 `/opt/intruoyi/runtime`。
- Correction: 用户指出 `D:\正式服访问方式\` 下有访问方式；已只读脱敏确认 `D:\正式服访问方式\server-access.md` 存在，记录测试服 `172.30.30.58`、正式服 `172.30.30.57`、备用服 `172.30.30.59`，并确认三台服务器运行目录统一为 `/opt/intruoyi/runtime`。后续服务器访问应优先读取该目录下的访问资料。
- SSH read-only status: `ssh root@172.30.30.58 bash -s`，退出码 `0`；未执行重启、发布、数据库写入、文件修改或清理。
- System: `2026-07-24T13:23:04+08:00`，uptime `166 days`，load average `0.31, 0.40, 0.43`。
- Memory: `31Gi` total，`8.2Gi` used，`21Gi` available；swap `9Gi` total，`3.4Gi` used。
- Disk: `/` `50G` total / `37%` used；`/var/lib/docker` `/dev/vdb` `2.0T` total / `28%` used。
- Runtime: `/opt/intruoyi/runtime/.env` `IMAGE_TAG=release-20260723-dcc-viewer-permission-r260723vp-r1`。
- Containers: `intruoyi-backend` and `intruoyi-frontend` both `Up 26 hours` on tag `release-20260723-dcc-viewer-permission-r260723vp-r1`; `intruoyi-mysql`, `intruoyi-redis`, `intruoyi-onlyoffice`, `intruoyi-website`, and `ragflow_compose-minio-1` are up.
- Health: backend `/actuator/health` returns `{"status":"UP"}` with HTTP `200`; frontend HTTP `200`; showroom HTTP `200`; OnlyOffice `8080/healthcheck` HTTP `200` body `true`.

## Current Status

completed
