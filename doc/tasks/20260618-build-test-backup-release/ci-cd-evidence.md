# CI/CD 证据: 测试服与备份服发布

## Environment

- 发布包：`release-20260618-0056-codeonly-e2e`。
- 测试服：`172.30.30.58`，远端目录 `/opt/intruoyi/runtime`。
- 备份服：`172.30.30.59`，远端目录 `/opt/intruoyi/runtime`，数据盘 `/mnt/intruoyi-data`，发布根 `/mnt/intruoyi-data/intruoyi-releases`。
- 授权：责任人 `admin`，用户提供 `PROD`。
- 禁止边界：未访问正式服 `172.30.30.57`；未执行备份、恢复、回滚、数据库同步或 MinIO/NAS 数据同步。

## Commands

- 构建：运行控制台真实前端“构建发布包”，`-Component intruoyi -SkipDatabaseSync -SkipMinioSync`。
- 测试服发布：运行控制台真实前端“部署测试服”，operation `op-2026-06-18T010137328120900Z-1f312235-29b4-4954-b631-3f09874801a4`。
- 备份服发布：运行控制台真实前端“上线备份服”，operation `op-2026-06-18T011250606902100Z-4ca1df68-7dc0-4e79-a9a5-16f9e1e76bd3`。

## Secrets

- 未在任务文档记录密钥明文。
- 发布过程使用既有本机运行控制台配置和远端容器环境变量。

## Pipeline

- 发布流：构建发布包 -> 测试服发布与验证 -> 备份服发布与验证。
- 门禁：Docker 基础镜像预拉、迁移策略门禁、Maven clean 锁检查、真实前端预览、operation 终态、远端 tag/容器/健康检查/浏览器验证。

## Verification

- 测试服：operation `SUCCESS`，`IMAGE_TAG=release-20260618-0056-codeonly-e2e`，backend/frontend 镜像 tag 匹配，后端和前端 HTTP 200，浏览器进入登录页且 console error 0。
- 备份服：operation `SUCCESS`，`IMAGE_TAG=release-20260618-0056-codeonly-e2e`，backend/frontend 镜像 tag 匹配，后端和前端 HTTP 200，浏览器进入登录页且 console error 0。
- Required SQL：`20260617_mes_scheduler_role_smart_scheduling_tab` 在 test 与 backup 均为 `APPLIED`。

## Rollback

- 本任务未执行回滚。
- 若后续需要回退，按 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md` 的发布回滚流程另行授权执行；不得用未验证状态冒充成功。

## Blockers

- 当前无阻塞。
