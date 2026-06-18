# 执行日志: 真实 E2E 验证发布包瘦身

## BDD

BDD: 真实前端构建瘦身发布包 -> Given 运行控制台加载当前维护仓库瘦身逻辑, When 使用 Playwright 点击真实“构建发布包”入口并提交 code-only intruoyi 构建, Then operation 最终 SUCCESS，预览命令包含 build-release/intruoyi/SkipDatabaseSync/SkipMinioSync，且不包含部署、正式服、备份、恢复或回滚动作。

BDD: 发布包只保留部署必需内容 -> Given 新发布包构建完成, When 校验本地发布目录、manifest 和 artifact 清单, Then 不存在 docker-build-context，且镜像 tar、release-manifest、Manifest v1、required SQL、ops-runtime、compose/env/runtime-env 等部署必需内容仍存在。

## 执行记录

- 2026-06-18：用户要求进行真实的 E2E 测试。
- 2026-06-18：任务边界确认：只构建并验证瘦身发布包，不部署测试服、备份服或正式服，不执行备份、恢复、回滚或数据同步。
- 2026-06-18：读取经验索引并命中发布预检、发布/备份恢复基线、服务器访问基线和项目错误预防短记忆。
- 2026-06-18：`npx` 可用，Node `v24.12.0`，npm `11.6.2`。
- 2026-06-18：本机运行控制台后端 `http://127.0.0.1:48181/actuator/health` 返回 HTTP 200，前端 `http://127.0.0.1:48182/` 返回 HTTP 200。
- 2026-06-18：扫描 Dockerfile `FROM`，命中 `nginx:1.27-alpine`、`eclipse-temurin:21-jre-noble`、`eclipse-temurin:21-jre`。
- 2026-06-18：`docker pull` 和 `docker image inspect` 三个基础镜像均通过。
- 2026-06-18：`python -m pytest scripts\tests\test_release_package_slimming.py` -> PASS，2 passed。
- 2026-06-18：`ops\deploy\publish-int-ruoyi.ps1` PowerShell 解析 -> PASS。
- 2026-06-18：`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，149 个迁移通过门禁。
- 2026-06-18：`mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -DskipTests clean` -> PASS。
- 2026-06-18：`mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-server -DskipTests clean` -> PASS。

GREEN: experience-preflight -> PASS，本轮只允许通过真实前端触发 `build-release` 构建 `code-only` / `intruoyi` 发布包；禁止部署测试服、备份服、正式服，禁止备份、恢复、回滚、数据库同步和 MinIO/NAS 业务数据同步。

## 待执行门禁

- `experience-preflight` 已通过，可以触发真实构建发布包 operation。

## GREEN

GREEN: python -m pytest scripts\tests\test_release_package_slimming.py -> PASS
GREEN: powershell parse ops\deploy\publish-int-ruoyi.ps1 -> PASS
GREEN: python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql -> PASS
GREEN: maven clean yudao-module-dcc -> PASS
GREEN: maven clean yudao-server -> PASS

## E2E

- 2026-06-18：Playwright 使用真实 Chromium 打开 `http://127.0.0.1:48182/`，页面标题 `运行控制台`，console error 为 0，请求失败为 0。
- 2026-06-18：选择真实前端动作 `构建发布包`，填写 releaseTag `release-20260618-1006-slim-e2e`，填写操作原因 `2026-06-18 真实E2E验证发布包瘦身；releaseTag=release-20260618-1006-slim-e2e`。
- 2026-06-18：点击 `预览命令`，接口返回 code=0；预览参数包含 `-Mode build-release`、`-ReleaseTag release-20260618-1006-slim-e2e`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`；未命中 `deploy-release`、`promote-prod`、`backup-now`、`restore-data`、`rollback-app`、`rehearsal`、`172.30.30.57`。
- 2026-06-18：点击预览弹窗 `执行`，真实前端提交 operation `op-2026-06-18T020729024794500Z-c7d40719-71d0-4ad4-a56d-0a521020632e`。
- 2026-06-18：operation 日志显示后端 Maven package BUILD SUCCESS，随后完成前端 Vite build、Docker build、镜像保存、manifest 生成和 NAS ReleasePackage 上传。
- 2026-06-18：operation JSON 最终状态 `SUCCESS`，summary `命令执行完成`；日志记录 `Release package uploaded to NAS: Backup/ReleasePackage/release-20260618-1006-slim-e2e`。
- 2026-06-18：Playwright 刷新运行控制台后，操作记录可见该 operation 且状态 `SUCCESS`；console error 为 0，请求失败为 0。

GREEN: Playwright preview build-release release-20260618-1006-slim-e2e -> PASS
GREEN: Playwright execute build-release op-2026-06-18T020729024794500Z-c7d40719-71d0-4ad4-a56d-0a521020632e -> PASS
GREEN: operation status op-2026-06-18T020729024794500Z-c7d40719-71d0-4ad4-a56d-0a521020632e -> SUCCESS

## 发布包校验

- 发布包路径：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260618-1006-slim-e2e`。
- 顶层内容：`required-sql`、`resources`、`runtime-env`、`docker-compose.yml`、`intruoyi-images_release-20260618-1006-slim-e2e.tar`、`manifest.json`、`release-manifest.json`。
- 新发布包大小：`813,672,335 bytes` / `775.98 MiB` / `0.758 GiB`。
- 顶层大小：
  - `intruoyi-images_release-20260618-1006-slim-e2e.tar`：`773.75 MiB`
  - `manifest.json`：`1.20 MiB`
  - `required-sql`：`0.97 MiB`
  - `release-manifest.json`：`0.04 MiB`
  - `docker-compose.yml`：`0.01 MiB`
  - `runtime-env`：`0.00 MiB`
  - `resources`：`0.00 MiB`
- 与旧包 `release-20260618-0056-codeonly-e2e` 对比：旧包 `1,392.39 MiB`，新包 `775.98 MiB`，减少 `616.42 MiB`。
- `release-manifest.json` meta：`releaseTag=release-20260618-1006-slim-e2e`、`component=intruoyi`、`publishScope=code-only`、`includeShowroomBuildPackage=false`、`onlyOfficeIncluded=false`。
- `manifest.json` meta：`releaseTag=release-20260618-1006-slim-e2e`、`publishScope=code-only`。
- 必需内容校验缺失项：`[]`。
- 递归路径命中 `docker-build-context`：`[]`。
- `release-manifest.json` / `manifest.json` 文本命中 `docker-build-context`：`[]`。
- `GET /admin-api/infra/runtime-control/release-status` 返回该 releaseTag，状态 `AVAILABLE`，`checksumPresent=true`，manifestPath 为 `Backup/ReleasePackage/release-20260618-1006-slim-e2e/release-manifest.json`。

GREEN: package required artifacts release-20260618-1006-slim-e2e -> PASS
GREEN: package no docker-build-context path or manifest entry -> PASS
GREEN: release-status sees release-20260618-1006-slim-e2e as AVAILABLE -> PASS

## Evidence Validation And Closeout

- 2026-06-18：`python C:\Users\BJB110\.codex\skills\ci-cd-environment-delivery\scripts\validate_cicd_environment.py --evidence doc\tasks\20260618-e2e-release-package-slimming\ci-cd-evidence.md` -> PASS。
- 2026-06-18：关闭 Playwright Chromium 浏览器 -> PASS。
- 2026-06-18：`python C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260618-e2e-release-package-slimming --mode preview` -> PASS；keep 为 `task.md`、`execution-log.md`、`ci-cd-evidence.md`，delete/blocked/warnings 均为空。
- 2026-06-18：首次 `task-closeout-cleanup --mode apply` -> BLOCKED，原因是 cleanup 脚本未识别中文 `当前状态`，读到 current status 为 `unknown`；已补充英文 `## Current Status` 为 `completed` 后重试。
- 2026-06-18：第二次 `task-closeout-cleanup --mode apply` -> PASS；delete/blocked/warnings/deleted_paths 均为空。

GREEN: validate_cicd_environment -> PASS
GREEN: task-closeout-cleanup preview -> PASS
GREEN: task-closeout-cleanup apply -> PASS
