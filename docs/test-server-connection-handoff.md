# 测试服务器连接方式交付文档

## 用途

本文件交付给新的发布程序或发布 Agent，用于识别 IntRuoyi 测试服务器和本机发布入口。本文只记录非敏感连接方式，不包含 SSH 密码、私钥、token、数据库密码、MinIO 密钥或连接串。

## 权威来源

- 服务器访问来源：`E:\IntRuoyi\docs\server-access.md`
- 本机主程序根目录：`E:\IntRuoyi`
- 后端与运维入口：`E:\IntRuoyi\IntRuoyiBackend`
- 前端工程：`E:\IntRuoyi\IntRuoyiFronted`
- 远端运行目录：`/opt/intruoyi/runtime`

## 测试服务器

| 项目 | 值 |
|---|---|
| 环境名称 | 测试服务器 |
| 主机 IP | `172.30.30.58` |
| 前端入口 | `http://172.30.30.58:8081/` |
| 后端健康检查 | `http://172.30.30.58:48081/actuator/health` |
| 展厅站点 | `http://172.30.30.58:8083/` |
| 远端运行目录 | `/opt/intruoyi/runtime` |

## 本机运维入口

- 状态检查：`E:\IntRuoyi\IntRuoyiBackend\script\deploy\show-int-ruoyi-test-status.bat`
- 重启脚本：`E:\IntRuoyi\IntRuoyiBackend\script\deploy\restart-int-ruoyi-to-test.bat`
- 发布脚本：`E:\IntRuoyi\IntRuoyiBackend\script\deploy\publish-int-ruoyi.ps1 -Environment test -ServerHost 172.30.30.58`
- 统一入口示例：`cmd /c "E:\IntRuoyi\IntRuoyiBackend\运维工具.bat test -ServerHost 172.30.30.58"`
- 直接 SSH 仅限已授权任务：`ssh root@172.30.30.58`

## 发布参数

- 直接发布到测试服务器时必须显式传入：`-Environment test -ServerHost 172.30.30.58`
- 使用 `build-release` / `deploy-release` 链路时，测试服务器主机参数为：`-TestServerHost 172.30.30.58`
- 测试服务器默认远端数据参数：
  - `RemoteDataRoot=/var/lib/docker/intruoyi-data/runtime-data`
  - `RemoteReleaseRoot=/var/lib/docker/intruoyi-releases`
  - `RemoteDataDiskMount=/var/lib/docker`
  - `RemoteDataDiskDevice=/dev/vdb`

## 访问边界

- 默认不访问远端服务器；必须先获得当前任务明确授权。
- 写操作优先使用统一入口或部署脚本，不直接拼接远端命令。
- 不得把测试服务器失败静默切换到正式服务器、审查服务器或其他目录。
- PowerShell 串联命令不要使用 `&&`；需要串联时使用分行或分号。
- 任何脚本失败都按真实失败处理，不做静默重试、环境切换或数据源降级。
- 交付、日志和提交中不得记录密码、私钥、token、连接串或其他秘密。

## 测试服发布完成判定

仅测试服务器发布成功时，至少需要同时确认：

- 发布操作 `publish-test` 返回 `SUCCESS`。
- manifest 与本次 releaseTag 一致。
- 远端 `.env` 中 `IMAGE_TAG` 与本次 releaseTag 一致。
- backend / frontend 实际镜像 tag 与本次 releaseTag 一致。
- 后端健康检查返回 `UP`。
- 前端入口返回 HTTP `200`。

## 交接说明

如新的发布程序需要 SSH、数据库、MinIO 或运行控制台凭据，必须通过受控凭据渠道单独获取。本文档不提供、也不允许补写任何明文凭据。
