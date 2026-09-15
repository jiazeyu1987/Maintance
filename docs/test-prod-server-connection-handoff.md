# 测试服务器与正式服务器连接方式交付文档

## 用途

本文件交付给发布程序或发布 Agent，用于识别 IntRuoyi 测试服务器和正式服务器的非敏感连接方式。本文不包含 SSH 密码、私钥、token、数据库密码、MinIO 密钥或连接串；需要凭据时必须通过受控凭据渠道单独获取。

## 权威来源

- 服务器访问来源：`E:\IntRuoyi\docs\server-access.md`
- 本机主程序根目录：`E:\IntRuoyi`
- 后端与运维入口：`E:\IntRuoyi\IntRuoyiBackend`
- 前端工程：`E:\IntRuoyi\IntRuoyiFronted`
- 统一运维入口：`E:\IntRuoyi\IntRuoyiBackend\运维工具.bat`
- 部署脚本目录：`E:\IntRuoyi\IntRuoyiBackend\script\deploy`
- 远端运行目录：`/opt/intruoyi/runtime`

## 服务器清单

| 环境 | 主机 IP | 前端入口 | 后端健康检查 | 展厅站点 | 直接 SSH |
|---|---|---|---|---|---|
| 测试服务器 | `172.30.30.58` | `http://172.30.30.58:8081/` | `http://172.30.30.58:48081/actuator/health` | `http://172.30.30.58:8083/` | `ssh root@172.30.30.58` |
| 正式服务器 | `172.30.30.57` | `http://172.30.30.57:8081/` | `http://172.30.30.57:48081/actuator/health` | `http://172.30.30.57:8083/` | `ssh root@172.30.30.57` |

## 测试服务器运维入口

- 状态检查：`E:\IntRuoyi\IntRuoyiBackend\script\deploy\show-int-ruoyi-test-status.bat`
- 重启脚本：`E:\IntRuoyi\IntRuoyiBackend\script\deploy\restart-int-ruoyi-to-test.bat`
- 发布脚本：`E:\IntRuoyi\IntRuoyiBackend\script\deploy\publish-int-ruoyi.ps1 -Environment test -ServerHost 172.30.30.58`
- 统一入口示例：`cmd /c "E:\IntRuoyi\IntRuoyiBackend\运维工具.bat test -ServerHost 172.30.30.58"`
- 直接 SSH 仅限已授权任务：`ssh root@172.30.30.58`

## 正式服务器运维入口

- 状态检查：`E:\IntRuoyi\IntRuoyiBackend\script\deploy\show-int-ruoyi-prod-status.bat`
- 重启脚本：`E:\IntRuoyi\IntRuoyiBackend\script\deploy\restart-int-ruoyi-to-prod.bat`
- 发布脚本：`E:\IntRuoyi\IntRuoyiBackend\script\deploy\publish-int-ruoyi.ps1 -Environment prod -ConfirmText PROD -ServerHost 172.30.30.57`
- 统一入口示例：`cmd /c "E:\IntRuoyi\IntRuoyiBackend\运维工具.bat prod PROD -ServerHost 172.30.30.57"`
- 直接 SSH 仅限已授权任务：`ssh root@172.30.30.57`

## 发布参数规则

- `publish-int-ruoyi.ps1` 不会凭空选择目标主机；直接发布必须传 `-ServerHost`，或由已确认的运行控制台环境变量提供目标主机。
- 测试服务器直接发布必须显式传入：`-Environment test -ServerHost 172.30.30.58`
- 正式服务器直接发布必须显式传入：`-Environment prod -ConfirmText PROD -ServerHost 172.30.30.57`
- 使用 `build-release` / `deploy-release` 链路时，测试服务器主机参数为：`-TestServerHost 172.30.30.58`
- 使用 `build-release` / `deploy-release` 链路并需要正式服务器时，必须额外显式传入：`-ProdServerHost 172.30.30.57`
- 测试与正式服务器默认远端数据参数：
  - `RemoteDataRoot=/var/lib/docker/intruoyi-data/runtime-data`
  - `RemoteReleaseRoot=/var/lib/docker/intruoyi-releases`
  - `RemoteDataDiskMount=/var/lib/docker`
  - `RemoteDataDiskDevice=/dev/vdb`

## 访问边界

- 默认不访问任何远端服务器；测试服务器和正式服务器都必须有当前任务明确授权。
- 正式服务器按生产等级处理；发布或重启必须显式确认 `PROD`。
- 远端操作前必须确认目标环境、目标主机、操作类型、数据影响和回滚或清理方式。
- 读操作优先使用状态脚本，确认运行目录、容器状态和 HTTP 健康检查。
- 写操作优先使用统一入口或部署脚本，不直接拼接远端命令。
- 不得把测试服务器失败静默切换到正式服务器，也不得把正式服务器失败切换到测试服务器、审查服务器或其他目录。
- PowerShell 串联命令不要使用 `&&`；需要串联时使用分行或分号。
- 任何脚本失败都按真实失败处理，不做静默重试、环境切换或数据源降级。
- 交付、日志和提交中不得记录密码、私钥、token、数据库密码、MinIO 密钥、连接串或其他秘密。

## 发布完成判定

测试服务器或正式服务器发布成功时，至少需要同时确认：

- 发布操作返回 `SUCCESS`。
- manifest 与本次 releaseTag 一致。
- 远端 `.env` 中 `IMAGE_TAG` 与本次 releaseTag 一致。
- backend / frontend 实际镜像 tag 与本次 releaseTag 一致。
- 后端健康检查返回 `UP`。
- 前端入口返回 HTTP `200`。
