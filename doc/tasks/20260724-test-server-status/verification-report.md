# Verification Report

## Current Result

测试服务器当前状态正常。

## Evidence

- SSH: `root@172.30.30.58` 只读检查退出码 `0`。
- System: uptime `166 days`，load average `0.31, 0.40, 0.43`。
- Memory: `31Gi` total，`21Gi` available。
- Disk: `/` 使用率 `37%`；`/var/lib/docker` 使用率 `28%`，可用约 `1.4T`。
- Runtime tag: `release-20260723-dcc-viewer-permission-r260723vp-r1`。
- Docker: backend/frontend/mysql/redis/onlyoffice/website/minio 均 Up。
- Health: backend `UP`，frontend HTTP `200`，showroom HTTP `200`，OnlyOffice health HTTP `200` body `true`。

## Notes

- 未执行任何重启、发布、数据库写入、远端文件修改或清理动作。
- 指定的规范访问文档 `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md` 当前缺失；本次通过历史预检证据与维护仓门禁交叉确认测试服访问参数。
