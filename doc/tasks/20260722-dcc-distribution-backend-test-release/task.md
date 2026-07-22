# DCC 分发待办后端测试服发布

## Task Goal

将已包含 DCC 分发任务与培训任务 `my-page` 接口的当前已提交后端发布到测试服务器 `172.30.30.58`，修复测试服个人工作台请求 `admin-api/dcc/distribution-tasks/my-page` 返回业务码 404 的问题。

## Scope

- 发布源：维护仓、后端仓、前端仓冻结提交组成的干净 release worktree。
- 目标环境：仅测试服务器 `172.30.30.58`。
- 发布范围：`build-release -> publish-test -> 测试服运行态、运行包 class 和真实页面验证`。
- 禁止动作：不执行 `mark-tested`、`promote-prod`、`promote-backup`；不操作正式服 `172.30.30.57` 或备份服 `172.30.30.59`。
- 数据范围：code-only，不同步业务数据库 dump、MinIO 或 NAS 业务文件；required SQL 和 migration 契约仍必须通过。

## Milestones

- P0 前置门禁：完成发布、登录、服务器、PowerShell、worktree 和 SQL 解析门禁记录。
- P1 冻结输入：创建维护仓、后端仓、前端仓本轮专用短路径干净 release worktree。
- P2 构建前验证：后端目标测试、Controller 契约、migration policy 和菜单 SQL 静态解析门禁通过。
- P3 构建发布包：生成新的 intruoyi code-only releaseTag，manifest 证明冻结提交且 dirty=false。
- P4 发布测试服：publish-test operation 成功，未执行任何正式服、备份服或 mark-tested 动作。
- P5 运行态验证：测试服镜像、health、HTTP、release-info、运行包 class 与 release lock 一致。
- P6 真实 E2E：官方登录预检和个人工作台真实页面通过，分发/培训 `my-page` 均不再返回业务码 404。
- P7 收尾：恢复运行控制台稳定路径，清理本任务 release worktree 和任务附属临时产物。

## BDD Scenarios

- BDD: 测试服提供 DCC 分发待办接口 -> Given 测试服用户已登录; When 个人工作台请求 `/dcc/distribution-tasks/my-page`; Then 后端返回真实分页业务响应而不是 `code=404`。
- BDD: 测试服提供 DCC 培训待办接口 -> Given 个人工作台同时加载培训待办; When 请求 `/dcc/training-tasks/my-page`; Then 后端命中真实 Controller 而不是不存在地址。
- BDD: 仅测试服发布边界 -> Given 用户要求继续修复测试服; When 本次构建发布完成; Then 只更新 `172.30.30.58`，不执行 `mark-tested`、正式服或备份服动作。

## Expected Verification

- GREEN: release-worktrees-clean -> PASS。
- GREEN: backend-distribution-target-tests -> PASS。
- GREEN: release-sql-contract-gate -> PASS。
- GREEN: build-release -> SUCCESS。
- GREEN: publish-test -> SUCCESS。
- GREEN: test-runtime-and-app-classes -> PASS。
- GREEN: distribution-training-my-page-e2e -> PASS。

## 经验门禁

- 测试服发布：只走同一 releaseTag 的 `build-release -> publish-test -> 测试服真实验收`；禁止拼接历史成功结果。
- 发布 worktree：维护仓、后端仓、前端仓使用短路径干净 worktree，构建输入只来自已提交冻结 HEAD；主工作区脏改不得进入发布包。
- SQL 解析：`system_menu.id` 门禁只解析真实 `INSERT INTO system_menu (...) VALUES (...)`；若错误指向 `INSERT ... SELECT`、更新子句或临时表，必须修维护仓解析器并补测试，不得改业务 SQL迎合误解析。
- code-only：`SkipDatabaseSync` / `SkipMinioSync` 不跳过 schema、required SQL、migration policy 或 manifest 门禁。
- PowerShell/SSH：显式 UTF-8，原生命令退出码及时保存；远端脚本使用 UTF-8 bytes + LF；不记录完整命令行、容器 env 或明文凭据。
- 运行态：operation、manifest、远端 `.env IMAGE_TAG`、实际镜像、health、HTTP、release-info、运行包 class 和真实页面必须一致。
- E2E：先运行官方 `login-preflight.mjs`，再用 Playwright 走真实页面；接口只做最终补充校验。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，发布包含真实 Controller/Service 的后端，并正式修复发布 SQL 解析门禁。
- 是否存在临时补丁或绕过：否。

## Current Status

completed

## Progress

- P0: completed，已确认根因是测试服后端运行版本落后；发布范围锁定为测试服。
- P1: completed，已创建本轮专用 release worktree：维护仓 `r260722d\m`、后端 `r260722d\b`、前端 `r260722d\f`。
- P2: completed，已完成 DCC 目标测试、菜单 SQL 契约测试与 migration policy；后续发布 required SQL 阻断均按 TDD 正式修复并重新验证。
- P3: completed，失败的 `r1` / `r2` / `r3` / `r4` releaseTag 均未复用；`release-20260722-dcc-distribution-backend-r260722d-r5` 构建成功并上传 NAS。
- P4: completed，`release-20260722-dcc-distribution-backend-r260722d-r5` 已发布到测试服，required SQL 已应用，未执行 `mark-tested`、正式服或备份服动作。
- P5: completed，测试服 `.env`、实际后端镜像、健康检查、前端镜像保持、运行包 class 均通过。
- P6: completed，官方登录预检、接口会话验证和个人工作台真实页面 E2E 均通过，两个 `my-page` 接口不再返回业务码 404。
- P7: completed，后端修复已合入主工作区 `int_main`；本轮 release worktree 已清理，验证报告与经验门禁已补齐。

## Final Verification

- 测试服 `172.30.30.58` 后端镜像：`intruoyi-backend:release-20260722-dcc-distribution-backend-r260722d-r5`。
- 运行态健康：`/actuator/health` 返回 `UP`。
- 官方登录预检：`http://172.30.30.58:8081` / `芋道源码` / `admin` 通过。
- 真实页面 E2E：`/user/profile` 触发的 DCC 分发/培训 `my-page` 请求均为 HTTP 200、业务码 `0`。
- 主工作区回归：后端 SQL 契约集合 `25 passed`。
