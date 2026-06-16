# PRD: 运行控制台原版逻辑对齐

- Task ID: `20260616-runtime-control-align-original`
- Created: `2026-06-16T16:44:42`
- Workspace: `D:\ProjectPackage\Int\IntRuoyiMaintance`
- User Request: `改成与原版也就是intruoyi一致`

## Goal

将独立运行控制台的运行控制台业务逻辑对齐到 `D:\ProjectPackage\Int\IntRuoyi` 原版：公共接口、候选解析、发布包校验、SQL 动作入口、治理接口和前端请求契约应与原版一致；仍保留独立应用本机运行、不接入芋道登录/菜单/角色权限的既定边界。

## Scope

- 后端 `backend/src/main/java/com/intruoyi/maintenance/runtime/**`。
- 后端契约测试 `backend/src/test/java/com/intruoyi/maintenance/runtime/**`。
- 前端 `frontend/src/App.vue` 与 `frontend/src/api/runtimeControl.ts`。
- 任务文档、证据文档、请求命令日志。

## Non-Goals

- 不重新接入芋道 Spring Security、`@PreAuthorize`、动态菜单或登录用户态。
- 不触发真实发布、备份、恢复、回滚、重启、SSH、数据库写入或对象存储写入。
- 不把原 IntRuoyi 整套业务源码复制进独立应用。
- 不用 mock 成功、默认可用或静默降级掩盖缺少 manifest、候选、配置或脚本的问题。

## Preconditions

- 当前独立仓库位于 `D:\ProjectPackage\Int\IntRuoyiMaintance`，原版比较源位于 `D:\ProjectPackage\Int\IntRuoyi`。
- 本机具备 Java 17、Maven、Node/pnpm，且当前项目已有 Spring Boot/Vue 构建链路。
- 运维真实写动作必须保持禁用，本任务只运行静态测试、单元/契约测试、构建和只读页面验证。
- 若后续验证需要访问远端、执行发布/恢复/回滚或读取敏感 NAS 数据，必须另行记录 `GREEN: experience-preflight -> PASS` 并获得授权。

## Impacted Areas

- `/admin-api/infra/runtime-control/*` HTTP 接口契约。
- 发布包候选与 `release-manifest.json` / `tested.json` 校验。
- rollback / restore / rehearsal 的候选 ID 服务端解析。
- `apply-test-db-sql` 的页面入口、请求字段与后端 SQL 路径校验。
- owner matrix、wizard、alert resend site message 这 6 个原版接口。
- 前端运行控制台动作表单与 API 类型。

## 经验门禁

- 命中 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：发布包不能只按目录名判定，必须读取 manifest 校验 releaseTag、packageDirectoryName、artifact sha256、tested 状态；恢复候选必须按 manifest / recoverySet / checksum 判断，不得默认可恢复。
- 命中 `D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`：前端保持安静、紧凑、表格优先的运维控制台风格，使用蓝/中性色，不引入营销式布局。
- 本任务不执行高风险动作；只读和本机测试可继续，任何真实运维写入直接阻断。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；缺 manifest、候选、SQL 文件、配置或路径时 fail fast。
- `是否从根因和长期维护角度解决`：是；将独立版公共契约和服务端校验收敛到原版规则，而不是只隐藏前端字段。
- `是否存在临时补丁或绕过`：否。

## Phase Plan

### P1: 后端原版契约对齐

- Objective: 补齐原版接口和服务端门禁，特别是发布包 manifest/tested 校验、候选 ID 服务端解析和内部字段拒绝。
- Owned paths: `backend/src/main/java/com/intruoyi/maintenance/runtime/**`, `backend/src/test/java/com/intruoyi/maintenance/runtime/**`。
- Dependencies: 原版 IntRuoyi runtimecontrol controller/service/VO 作为行为基线；本机配置仍使用 `maintenance.runtime-control`。
- Deliverables: 后端契约测试、运行控制台服务实现、候选/发布包读取逻辑、治理接口最小持久化或明确本地实现。

### P2: 前端原版请求与动作入口对齐

- Objective: 前端 API 类型、动作列表、请求 payload 与原版保持一致，补回 `apply-test-db-sql`，移除客户端直传内部候选实际值。
- Owned paths: `frontend/src/App.vue`, `frontend/src/api/runtimeControl.ts`, frontend tests or static contract checks。
- Dependencies: P1 后端契约。
- Deliverables: 前端静态契约测试、类型检查、构建、页面只读验证。

## Phase Acceptance Criteria

### P1

- P1-AC1: 原版 33 个运行控制台公共接口均由独立应用暴露；无 Spring Security / `@PreAuthorize` 依赖。
- P1-AC2: `selectedImageTag` 与 `selectedBackupId` 只能由服务端候选解析；客户端直传时请求失败且不启动命令。
- P1-AC3: 发布/晋级动作必须校验 release package 存在、`release-manifest.json` 可解析、artifact sha256 存在；正式/备份晋级必须要求 `tested.json`。
- P1-AC4: rollback、restore、rehearsal、mark-tested 使用服务端候选 ID 解析 imageTag、backupId、recoverySetId、manifestHash、programVersion、redisPolicy。
- P1-AC5: `apply-test-db-sql` 校验 `.sql` 普通非空文件，非 SQL 或缺文件 fail fast。
- Evidence expectation: `mvn -f backend/pom.xml test` 与后端证据文档。

### P2

- P2-AC1: 前端 `RuntimeControlActionReqVO` 与原版一致，不包含 `selectedImageTag`、`selectedBackupId`、recoverySet 内部字段。
- P2-AC2: 页面动作列表包含 `apply-test-db-sql`，并且 SQL 路径仅对该动作提交。
- P2-AC3: 页面不再出现“镜像标签”“备份点”自由文本输入，只保留候选 ID 输入或选择。
- P2-AC4: 前端 API 文件包含 owner-matrix、wizard、alert resend、rollback candidates、restore candidates、release packages 等原版 API 方法。
- Evidence expectation: `pnpm --dir frontend typecheck`、`pnpm --dir frontend build`、前端静态契约检查与只读页面验证。

## Done Definition

- P1、P2 全部完成，所有 acceptance id 有证据。
- 后端、前端验证命令通过。
- 任务文档、执行日志、测试报告和请求命令日志更新。
- 工作区只提交本任务相关文件，提交信息使用 `任务: 对齐运行控制台原版逻辑`。

## Blocking Conditions

- 缺少本机测试依赖、构建工具或必需配置导致测试无法启动。
- 需要访问远端/NAS真实数据或执行真实写动作才能继续时，本任务必须阻断并向用户报告。
- 无法以本地独立应用边界实现原版规则，且需要重新接入芋道登录权限时，必须先向用户报告取舍。
