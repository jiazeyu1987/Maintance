# 任务: 真实 E2E 验证发布包瘦身

## 任务目标

通过运行控制台真实前端 E2E 触发一次新的 `code-only` 构建发布包，验证低风险瘦身已生效：发布目录和上传发布包不再包含 `docker-build-context`，同时保留部署必需内容。

## 任务边界

- 本次只执行构建发布包和发布包产物验证。
- 不部署测试服、备份服或正式服。
- 不执行备份、恢复、回滚、数据库同步、MinIO/NAS 业务数据同步。
- 目标组件固定为 `intruoyi`，发布范围固定为 `code-only`。

## 经验门禁

- `docs/release-build-preflight-lessons.md`：构建前确认运行控制台版本、基础镜像、迁移策略门禁和 Maven target/jar 锁；预览命令必须包含 `-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`，不得包含正式服、备份、恢复或回滚动作。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：构建发布包必须通过运行控制台真实前端入口提交；发布包成功出口必须具备脚本成功、Manifest v1、NAS 上传完成和包内 artifact 校验；不得用 mock/default success/静默降级掩盖失败。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`：本任务不访问远端服务器；若后续扩展为部署，必须重新确认目标主机和授权范围。
- `docs/agent-memory/project-error-prevention.md`：发布流程前预检 Dockerfile 基础镜像、迁移策略门禁和 Maven 锁；任务提交前跑 TDD 钩子，失败不生成可部署包。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。本次验证发现缺少必需产物、manifest 不一致或仍存在 `docker-build-context` 时直接失败。
- `是否从根因和长期维护角度解决`：是。验证上一任务对构建脚本的正式瘦身门禁，而不是手工删除某个历史发布目录。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 真实前端构建瘦身发布包 -> Given 运行控制台加载当前维护仓库瘦身逻辑, When 使用 Playwright 点击真实“构建发布包”入口并提交 code-only intruoyi 构建, Then operation 最终 SUCCESS，预览命令包含 build-release/intruoyi/SkipDatabaseSync/SkipMinioSync，且不包含部署、正式服、备份、恢复或回滚动作。`
- `BDD: 发布包只保留部署必需内容 -> Given 新发布包构建完成, When 校验本地发布目录、manifest 和 artifact 清单, Then 不存在 docker-build-context，且镜像 tar、release-manifest、Manifest v1、required SQL、ops-runtime、compose/env/runtime-env 等部署必需内容仍存在。`

## 里程碑

- [x] 创建任务文档并读取经验门禁。
- [x] 完成构建前 preflight，并在执行日志记录 `GREEN: experience-preflight -> PASS`。
- [x] 用 Playwright 真实前端触发新的构建发布包 operation。
- [x] 校验 operation、manifest、产物内容和包体积。
- [x] 更新证据并运行收尾清理预览。

## 预期验证

- `python -m pytest scripts\tests\test_release_package_slimming.py` 通过。
- `ops\deploy\publish-int-ruoyi.ps1` PowerShell 解析通过。
- 发布迁移策略门禁通过。
- Maven target/jar 锁预检通过。
- Playwright 真实 E2E 构建 operation 最终 `SUCCESS`。
- 新发布包无 `docker-build-context`，部署必需内容齐全，manifest 不包含该目录。
- `validate_cicd_environment.py` 通过。

## 当前状态

completed

## Current Status

completed

## 当前验证

- `npx` 可用：`D:\Programs\npx.ps1`。
- 本机运行控制台后端 `48181` 与前端 `48182` 均返回 HTTP 200。
- Dockerfile 基础镜像扫描完成：`nginx:1.27-alpine`、`eclipse-temurin:21-jre-noble`、`eclipse-temurin:21-jre`。
- 三个基础镜像均已 `docker pull` 并 `docker image inspect` 通过。
- `python -m pytest scripts\tests\test_release_package_slimming.py` 通过，2 passed。
- `ops\deploy\publish-int-ruoyi.ps1` PowerShell 解析通过。
- 发布迁移策略门禁通过，扫描 149 个迁移。
- `mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -DskipTests clean` 通过。
- `mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-server -DskipTests clean` 通过。
- Playwright 真实前端预览 `构建发布包` 通过：参数包含 `-Mode build-release`、`-ReleaseTag release-20260618-1006-slim-e2e`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`，不包含部署、正式服、备份、恢复或回滚动作。
- Playwright 真实前端执行 `构建发布包`，operation `op-2026-06-18T020729024794500Z-c7d40719-71d0-4ad4-a56d-0a521020632e` 最终 `SUCCESS`。
- 发布包路径：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260618-1006-slim-e2e`。
- NAS 发布包候选接口可读回该版本，状态 `AVAILABLE`，manifest 路径 `Backup/ReleasePackage/release-20260618-1006-slim-e2e/release-manifest.json`。
- 新发布包总大小 `813,672,335 bytes` / `775.98 MiB` / `0.758 GiB`。
- 对比旧包 `release-20260618-0056-codeonly-e2e` 的 `1,460,030,640 bytes` / `1,392.39 MiB`，实际减少 `646,358,305 bytes` / `616.42 MiB`。
- 新发布包递归路径与 `release-manifest.json`、`manifest.json` 均未命中 `docker-build-context`。
- 部署必需内容存在：`docker-compose.yml`、`release-manifest.json`、`manifest.json`、`required-sql`、`resources`、`runtime-env`、`intruoyi-images_release-20260618-1006-slim-e2e.tar`。
- Playwright 刷新运行控制台后可见该 operation `SUCCESS`，console error 为 0，请求失败为 0。
- `validate_cicd_environment.py --evidence doc\tasks\20260618-e2e-release-package-slimming\ci-cd-evidence.md` 通过。
- `task-closeout-cleanup --mode preview` 通过，无删除项、阻塞项或警告。
- `task-closeout-cleanup --mode apply` 通过，无删除项、阻塞项或警告。

## 最终结论

真实 E2E 构建发布包已完成。新发布包 `release-20260618-1006-slim-e2e` 已生成并上传 NAS，operation 为 `SUCCESS`；发布包中无 `docker-build-context`，体积从旧包 `1,392.39 MiB` 降至 `775.98 MiB`，实际减少 `616.42 MiB`。

## Cleanup Keep

- `doc/tasks/20260618-e2e-release-package-slimming/ci-cd-evidence.md`
