# 任务: 构建发布到测试服和备份服

## 任务目标

通过运行控制台真实前端 E2E 构建新的 IntRuoyi `code-only` 发布包，先发布到测试服务器并验收，再发布到备份服务器并验收。

目标边界：

- 构建方式：运行控制台真实前端 E2E。
- 发布范围：`code-only`，即 `-Component intruoyi -SkipDatabaseSync -SkipMinioSync`。
- 测试服：`172.30.30.58`，远端目录 `/opt/intruoyi/runtime`。
- 备份服：`172.30.30.59`，远端目录 `/opt/intruoyi/runtime`，数据盘 `/mnt/intruoyi-data`，发布根 `/mnt/intruoyi-data/intruoyi-releases`。
- 授权：用户本轮已提供 `PROD`；发布责任人沿用本线程已确认的 `admin`。
- 数据前置授权：用户在阻塞诊断后补充 `授权`，允许补齐测试服与备份服 `tenant_id=122` 的 MES 排产/计划角色前置数据，并处理测试服 stale release lock / migration 状态后重试发布。
- 禁止范围：不访问正式服 `172.30.30.57`，不执行备份、恢复、回滚或数据同步。

## 经验门禁

- `docs/release-build-preflight-lessons.md`：构建发布前必须预检 Docker 基础镜像、迁移策略门禁、Maven target/jar 锁、真实 E2E 预览边界；完成判定必须核 operation、manifest、远端 `IMAGE_TAG`/镜像、迁移状态和真实浏览器入口。
- `docs/agent-memory/project-error-prevention.md`：环境发布流程前先预检 Dockerfile 基础镜像、迁移策略门禁和 Maven target/jar 锁；失败不生成可部署包。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：构建发布包必须通过运行控制台前端按钮提交；测试服先发布并验证；`code-only` 不同步数据库或 MinIO/NAS，但仍不跳过 schema、required SQL、迁移元数据和发布 manifest 门禁。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`：测试服/备份服写入必须有当前任务授权；备份服与正式服同等级门禁，必须提供发布责任人与 `PROD` 确认；备份服必须显式使用 `/mnt/intruoyi-data` 参数。
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`：涉及真实浏览器入口或登录路径验证时先确认授权；缺少远端账号不得静默切换账号或环境。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。缺少发布包 manifest、测试服验收、备份服 `PROD` 确认、发布责任人、环境访问或验证证据时直接阻塞。
- `是否从根因和长期维护角度解决`：是。按发布预检清单先排除重复失败原因，再用 operation、manifest、远端版本和真实页面证据闭环。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 构建 code-only 发布包 -> Given 本机运行控制台可访问且发布范围为 code-only, When 操作者通过真实前端预览并执行构建发布包, Then operation 成功，manifest 与 releaseTag、component、publishScope 一致，且不包含正式服、备份、恢复、回滚或数据同步动作。`
- `BDD: 发布到测试服 -> Given code-only 发布包构建成功, When 操作者通过真实前端预览并执行部署测试服, Then 测试服 operation 成功，远端 IMAGE_TAG 与 releaseTag 一致，容器运行，后端健康且前端真实入口可访问。`
- `BDD: 补齐 MES 发布前置数据 -> Given 测试服与备份服测试租户缺少 MES 排产/计划目标角色且租户包缺少智能排程子菜单, When 在授权范围内只为 tenant_id=122 克隆并切换完整菜单套餐且创建启用的 mes_scheduler 角色, Then required SQL 20260617_mes_scheduler_role_smart_scheduling_tab 可重试通过，且不影响其它租户。`
- `BDD: 发布到备份服 -> Given 同一 releaseTag 已在测试服成功发布且用户提供 admin/PROD 授权, When 操作者通过真实前端预览并执行上线备份服, Then 备份服 operation 成功，远端 IMAGE_TAG 与 releaseTag 一致，容器运行，后端健康且前端真实入口可访问。`
- `BDD: 禁止越界动作 -> Given 本次只授权测试服与备份服发布, When 执行构建、发布和验证, Then 不得访问正式服 172.30.30.57，不得执行备份、恢复、回滚、数据库同步或 MinIO/NAS 同步。`

## 里程碑

- [x] 创建任务文档并读取经验门禁。
- [x] 记录备份服发布责任人与 `PROD` 确认。
- [x] 完成发布前预检。
- [x] 通过 Playwright 真实前端 E2E 构建 code-only 发布包。
- [x] 补齐测试服与备份服 `tenant_id=122` 的 MES 发布前置数据。
- [x] 通过 Playwright 真实前端 E2E 发布到测试服并验证。
- [x] 通过 Playwright 真实前端 E2E 发布到备份服并验证。
- [x] 收尾清理并提交本任务改动。

## 预期验证

- `npx` 可用。
- 本机运行控制台健康且页面可见。
- Docker 基础镜像预拉和 inspect 通过。
- 发布迁移策略门禁通过。
- Maven target/jar 锁预检通过。
- 构建预览包含 `-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`，不包含正式服、备份、恢复、回滚动作。
- 测试服发布预览包含 `-Mode deploy-release`、`-Environment test`、`-ServerHost 172.30.30.58`。
- 备份服发布预览包含 `-Environment backup`、`-ServerHost 172.30.30.59`、`-ConfirmText PROD`、`RemoteDataDiskMount=/mnt/intruoyi-data`、`RemoteReleaseRoot=/mnt/intruoyi-data/intruoyi-releases`。
- 构建、测试服发布、备份服发布 operation 均为 `SUCCESS`。
- 测试服与备份服 `tenant_id=122` 均存在启用的 `mes_scheduler` 角色，当前租户包包含智能排程菜单树；测试服 stale release lock 与 stale migration 状态不再阻塞重试。
- 测试服和备份服 `.env` / 镜像 tag 与发布包一致。
- 测试服和备份服后端健康，管理前端真实浏览器入口可访问。

## 当前状态

completed

## Current Status

completed

## 2026-06-18 01:21 测试服部署失败

- 操作：通过运行控制台真实前端执行“部署测试服”。
- operation：`op-2026-06-17T171309722400800Z-72fd40ab-f703-496f-999d-c9011b2a9c8d`。
- 结果：`FAILED`。
- 失败原因：必需 SQL `20260617_mes_scheduler_role_smart_scheduling_tab.sql` 在测试库主动失败，报错 `Missing enabled MES scheduler/planner role with smart scheduling tenant package; cannot grant scheduler role tab`。
- 影响：测试服发布未完成；备份服发布依赖测试服成功验收，因此当前不得继续发布备份服。

## 阻塞详情

- 测试服只读核对：核心菜单 `900120/5590/5580/5262/5540` 均存在且启用；`小租户` 与 `测试租户` 的租户包均包含 `900120`；但不存在任何启用且满足 SQL 条件的角色名称 `排产员/计划员/生产计划员/排产员/计划员` 或角色编码 `planner/scheduler/mes_planner/mes_scheduler/production_planner/production_scheduler`。
- 备份服只读核对：核心菜单数量为 5，租户包包含 `900120`；满足上述角色条件的记录数为 0，因此备份服直接发布预计也会命中同一前置数据阻塞。
- 测试服失败后状态：`/opt/intruoyi/runtime/.env` 已写入 `IMAGE_TAG=release-20260618-0056-codeonly-e2e`，但 `docker compose ps` 显示 backend/frontend 容器仍运行上一版 `release-202606172114-codeonly-e2e` 镜像；迁移表中 `20260617_mes_scheduler_role_smart_scheduling_tab` 为 `RUNNING` 且未完成。
- 需要决策：是否授权在测试服与备份服目标租户补齐或启用正式的 MES 排产/计划角色，并在处理迁移状态后重新通过运行控制台真实前端执行测试服发布；未获得该授权前不得继续备份服发布。

## 2026-06-18 重新授权后的数据修复方案

- 用户授权：用户已回复 `授权`。
- 新增只读发现：测试服与备份服 `tenant_id=122` 当前租户包均缺少 `5542/5543/5544/5545` 四个智能排程子菜单；直接只补角色仍会失败。
- 修复方式：不直接修改原套餐，改为克隆 `tenant_id=122` 当前套餐，向克隆套餐补齐缺失菜单，再仅更新 `system_tenant.id=122` 指向克隆套餐；随后创建或启用 `system_role.code=mes_scheduler` 的 `排产员` 角色。
- stale 状态处理：测试服上一轮失败遗留的 `infra_release_operation_lock` 置为 `FAILED`，对应 `infra_release_migration` 的 `RUNNING` 置为 `FAILED`，以允许发布脚本按既有机制重新 APPLY。
- 风险控制：不访问正式服；不改源代码；不改其它租户角色；不执行备份、恢复、回滚或数据同步。

## 2026-06-18 数据修复结果

- 测试服：`tenant_id=122` 已切换到克隆套餐 `114`，套餐名 `mes-release-20260618-0056`；启用角色 `mes_scheduler/排产员` 已存在；智能排程菜单树缺失数为 0。
- 测试服 stale 状态：`infra_release_operation_lock` 中 `release-20260618-0056-codeonly-e2e` 已从 `RUNNING` 改为 `FAILED`；`infra_release_migration.20260617_mes_scheduler_role_smart_scheduling_tab` 已从 `RUNNING` 改为 `FAILED`，允许发布脚本重新 APPLY。
- 备份服：`tenant_id=122` 已切换到克隆套餐 `113`，套餐名 `mes-release-20260618-0056`；启用角色 `mes_scheduler/排产员` 已存在；智能排程菜单树缺失数为 0。
- 备份服影响边界：`tenant_id=121` 仍指向原套餐 `111`，未被切换。

## 2026-06-18 测试服重试发布结果

- 真实前端操作：Playwright 预览并执行“部署测试服”。
- operation：`op-2026-06-18T010137328120900Z-1f312235-29b4-4954-b631-3f09874801a4`。
- 结果：`SUCCESS`。
- 远端验证：`IMAGE_TAG=release-20260618-0056-codeonly-e2e`，backend/frontend 镜像均为 `release-20260618-0056-codeonly-e2e` 且运行中；后端健康 HTTP 200，前端入口 HTTP 200。
- 迁移验证：`20260617_mes_scheduler_role_smart_scheduling_tab=APPLIED`，测试服 release lock 为 `APPLIED`。
- 浏览器验证：Chromium 打开 `http://172.30.30.58:8081/`，最终进入 `/login?redirect=/index`，标题 `瑛泰管理系统 - 登录`，console error 0，failed request 0。

## 2026-06-18 备份服发布结果

- 真实前端操作：Playwright 预览并执行“上线备份服”，包含 `PROD` 确认。
- operation：`op-2026-06-18T011250606902100Z-4ca1df68-7dc0-4e79-a9a5-16f9e1e76bd3`。
- 结果：`SUCCESS`。
- 远端验证：`IMAGE_TAG=release-20260618-0056-codeonly-e2e`，backend/frontend 镜像均为 `release-20260618-0056-codeonly-e2e` 且运行中；后端健康 HTTP 200，前端入口 HTTP 200。
- 迁移验证：`20260617_mes_scheduler_role_smart_scheduling_tab=APPLIED`，备份服 release lock 为 `APPLIED`。
- 浏览器验证：Chromium 打开 `http://172.30.30.59:8081/`，最终进入 `/login?redirect=/index`，标题 `瑛泰管理系统 - 登录`，console error 0，failed request 0。

## 最终验证结果

- `validate_database_schema.py --evidence doc/tasks/20260618-build-test-backup-release/database-schema-evidence.md`：PASS。
- `validate_cicd_environment.py --evidence doc/tasks/20260618-build-test-backup-release/ci-cd-evidence.md`：PASS。
- 测试服与备份服均已发布 `release-20260618-0056-codeonly-e2e`，并通过 operation、远端 tag、容器、HTTP、迁移状态和真实浏览器入口验证。
- `task-closeout-cleanup --mode preview/apply`：PASS，无删除项、无阻塞、无警告。

## Cleanup Keep

- `doc/tasks/20260618-build-test-backup-release/database-schema-evidence.md`
- `doc/tasks/20260618-build-test-backup-release/ci-cd-evidence.md`
