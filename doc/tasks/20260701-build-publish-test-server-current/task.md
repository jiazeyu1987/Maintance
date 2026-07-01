# 20260701 当前版本构建并发布到测试服务器

## Task Goal

按当前仓库发布规范，完成一次“构建并发布到测试服务器 `172.30.30.58`”任务。本轮用户已明确选择“先提交主工作区再发布”，因此先把三仓在途改动收口为正式可发布输入，再继续执行真实 `build-release -> publish-test -> 测试服运行态验证`。

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
3. 明确发布输入方案并完成构建前门禁。`COMPLETED`
4. 真实执行 `build-release` 并校验 manifest。`COMPLETED`
5. 真实执行 `publish-test` 并完成测试服运行态验证。`COMPLETED`
6. 回填证据并完成任务收尾。`COMPLETED`

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

COMPLETED：本轮已完成“先提交主工作区再发布”的测试服真实发布闭环，并严格停在测试服，不执行 `mark-tested`、备份服或正式服发布。

- 维护仓提交：`29bd0aa`（`任务: 更新测试服发布任务记录`）
- 后端仓提交：`1985ac31a4ff57e52ff78721302ac0bd77ba505c`（`任务: 收口展厅与SRM发布修复`）
- 前端仓提交：`9662a85e7e54c41cbbc594a843a47dff8d1dfa7f`（`任务: 收口待归属与排产前端修复`）
- 成功构建 operation：`op-2026-07-01T092718393431Z-e0ee2912-b24f-46d6-9a2e-5608c0426cde`
- 成功测试服发布 operation：`op-2026-07-01T094350943851500Z-35882b3a-115c-44c0-b76e-57a2c4906633`
- 成功 `releaseTag`：`release-20260701-1720-current`
- manifest 复核：后端 `1985ac31a4ff57e52ff78721302ac0bd77ba505c / int_main / dirty=false`；前端 `9662a85e7e54c41cbbc594a843a47dff8d1dfa7f / int_main / dirty=false`
- 测试服运行态验收：
  - `.env IMAGE_TAG=release-20260701-1720-current`
  - `backend|intruoyi-backend:release-20260701-1720-current|running`
  - `frontend|intruoyi-frontend:release-20260701-1720-current|running`
  - 后端健康：`{"status":"UP"}`
  - 前端入口：HTTP `200`
  - PDF worker：HTTP `200 application/javascript`
