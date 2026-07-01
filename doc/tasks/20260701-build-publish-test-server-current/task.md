# 20260701 当前版本构建并发布到测试服务器

## Task Goal

按当前仓库发布规范，完成一次“构建并发布到测试服务器 `172.30.30.58`”任务。本轮用户已明确选择“先提交主工作区再发布”，因此当前目标是先把三仓在途改动收口为正式可发布输入，再继续执行真实 `build-release -> publish-test -> 测试服运行态验证`。

## Scope

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 后端仓：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
- 前端仓：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
- 目标环境：测试服务器 `172.30.30.58`
- 发布动作：真实 `build-release -> publish-test -> 测试服运行态验证`

## Non-Scope

- 不执行 `mark-tested`
- 不发布备份服
- 不发布正式服
- 不以命令行直跑发布脚本替代运行控制台真实动作

## Previous Task Check

- 上一个维护仓发布任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260701-main-branch-test-server-release-closure\task.md`
- 状态：`COMPLETED`
- 处理说明：上一轮主分支测试服发布闭环已完成，不阻塞本次新一轮测试服发布任务。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 任务开始先读索引，只打开命中的发布经验文档。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - 默认只发布三仓主分支当前版本；若任一主工作区 dirty，必须先提示用户选择处理方案，未经明确选择不得继续真实发布。
  - 发布完成判定必须同时核 operation、manifest、远端 `.env IMAGE_TAG`、运行镜像 tag、backend health、frontend HTTP。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`
  - 高风险发布动作前必须先写入 `experience-preflight`，并完成主分支输入、运行控制台与测试服预览参数检查。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - `code-only` 不等于跳过 schema、required SQL、迁移元数据或 manifest 门禁。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
  - 当前任务仅允许写入测试服务器 `172.30.30.58`，正式服与备份服禁止操作。
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
  - 若需要真实浏览器登录验证，必须先走官方 `login-preflight` 最小路径。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\powershell-preflight-lessons.md`
  - PowerShell 5.1 不使用 `&&`，中文读写与输出必须显式 UTF-8。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；主分支输入、构建、发布、远端验收任一步不满足就直接阻塞。
- `是否从根因和长期维护角度解决`：是；先按仓库发布契约核对主分支输入和运行控制台，再执行真实发布。
- `是否存在临时补丁或绕过`：否；不默认绕过主工作区脏改，不手工改服务器文件、数据库或发布脚本掩盖前置条件缺失。

## BDD 场景

BDD: 默认发布只允许明确的主分支输入 -> Given 用户要求构建并发布到测试服务器 When 三仓主工作区存在未提交改动 Then 先阻塞并请用户选择“先提交主工作区”或“仅发布已提交 git 版本”的正式方案，未经确认不得继续真实发布。

BDD: 用户选择先提交主工作区后才能继续真实发布 -> Given 用户已明确选择“先提交再发布” When 三仓当前改动完成任务归属、验证与独立提交 Then 才允许把这些新提交作为本轮 `build-release -> publish-test` 的发布输入。

BDD: 测试服运行态必须落到同一 releaseTag -> Given 发布输入已满足仓库门禁且运行控制台可用 When 真实执行 `build-release -> publish-test` Then 测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health 与 frontend HTTP 必须全部与同一 `releaseTag` 一致。

## Milestones

1. 建立任务台账并记录经验门禁。`COMPLETED`
2. 核对三仓当前分支、HEAD 与 dirty 状态。`COMPLETED`
3. 明确发布输入方案并完成构建前门禁。`BLOCKED`
4. 真实执行 `build-release` 并校验 manifest。`PENDING`
5. 真实执行 `publish-test` 并完成测试服运行态验证。`PENDING`
6. 回填证据并完成任务收尾。`PENDING`

## Expected Verification

- 三仓发布输入方案已明确并符合仓库规则
- 本机 `http://127.0.0.1:48181/actuator/health` 返回 `UP`
- `build-release` operation=`SUCCESS`
- manifest 存在，且 `sourceRepos.branch/commit/dirty` 与本轮计划一致
- `publish-test` operation=`SUCCESS`
- 测试服 `.env IMAGE_TAG=<releaseTag>`
- 测试服 backend/frontend 镜像 tag=`<releaseTag>`
- 测试服 backend health=`UP`
- 测试服 frontend HTTP=`200`

## Current Status

BLOCKED：当前线程优先级已切换为“统一构建发布临时 worktree 规则固化”。本任务原先基于“先提交主工作区再发布”的旧发布基线推进，现已不再符合最新线程规则。后续如恢复本任务，必须先按新的统一发布规则重写发布输入方案、任务文档和执行门禁，再决定是否继续真实发布。

- 维护仓：当前仅保留 `docs/request-command-log.md` 与本轮 `doc/tasks/20260701-build-publish-test-server-current/` 的任务记录改动，提交后可恢复 clean
- 后端仓：本轮待提交范围主要对应 `20260701-showroom-product-excel-audio-keyword-roundtrip`、`20260701-srm-nas-locator-blacklist-srm-admin-binding`、`20260701-srm-nas-locator-wildcard-search-error` 与 `20260701-local-admin-api-48081-connection-refused`
- 前端仓：本轮待提交范围主要对应 `20260701-showroom-product-excel-audio-keyword-roundtrip`、`20260701-zhaojie-feedback-attribution-permission-fix`、`20260701-zhaojie-feedback-attribution-success-permission-toast-fix`、`20260701-schedule-order-main-table-wrap-display` 与 `20260701-zhaojie-feedback-user-select-simple-list-fix`
- 影响：若在提交前直接构建，仍会把未独立提交的在途改动混入测试服版本，违反“先提交再发布”的当前用户选择
