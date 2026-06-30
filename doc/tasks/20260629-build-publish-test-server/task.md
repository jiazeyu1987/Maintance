# 20260629 构建并发布到测试服务器

## Task Goal

基于当前最新已提交代码，从受控发布入口重新执行一次真实 `build-release -> publish-test` 链路，只发布到测试服务器 `172.30.30.58`，并记录新的阻塞、修复与运行态验证结果。

## Scope

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 后端仓：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
- 前端仓：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
- 发布目标：测试服务器 `172.30.30.58`
- 发布动作：仅允许真实 `build-release` 与 `publish-test`

## Non-Scope

- 不执行 `mark-tested`
- 不发布正式服
- 不发布备份服
- 不用命令行直跑发布脚本替代 runtime-control 页面动作

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md`
  - 任务开始先读索引，只打开命中的发布、服务器与 worktree 经验文档。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - 发布失败按“契约层 -> 脚本层 -> 环境层”排查。
  - 构建和测试服发布都必须同时记录 operation、manifest、`.env IMAGE_TAG`、镜像 tag、health 与前端 HTTP 证据。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`
  - 这次任务只允许执行到 `build-release -> publish-test -> 测试服运行态验证`，不推进后续链路。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - `code-only` 不跳过 schema、required SQL、迁移元数据或 manifest 门禁。
  - 构建成功必须以脚本成功、manifest 存在和 NAS 产物上传完成共同判定。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
  - 当前任务仅对测试服 `172.30.30.58` 执行写入发布；正式服与备份服默认禁止操作。
- `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
  - 主工作区当前为脏状态，不得直接把主工作区当成发布输入；需要确认受控干净发布来源。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；runtime-control 不可用、manifest 缺失、发布门禁失败或测试服运行态不一致时直接阻塞。
- `是否从根因和长期维护角度解决`：是；先恢复 runtime-control 正常运行，再走真实页面发布链路。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

BDD: runtime-control 可用后才能真实发布 -> Given 本机 runtime-control 是唯一受控发布入口 When 构建前健康检查不通过 Then 先恢复并验证 runtime-control，再允许提交 `build-release`。

BDD: 测试服发布只认单一 releaseTag -> Given 本次构建得到新 releaseTag 且 manifest 校验通过 When 执行 `publish-test` Then 测试服 `.env IMAGE_TAG`、后端镜像、前端镜像、health 和前端 HTTP 必须全部与同一 releaseTag 一致。

## Milestones

1. 创建任务台账并记录经验门禁。`COMPLETED`
2. 恢复并验证 runtime-control 本机可用。`COMPLETED`
3. 真实执行 `build-release` 并校验 manifest。`COMPLETED`
4. 真实执行 `publish-test` 并验证测试服运行态。`COMPLETED`
5. 回写日志、阻塞与结论。`COMPLETED`

## Expected Verification

- 本机 `http://127.0.0.1:48181/actuator/health` 返回 `UP`
- `build-release` operation `SUCCESS`
- 新 releaseTag 的 manifest 存在，且后端/前端 `sourceRepos.dirty=false`
- `publish-test` operation `SUCCESS`
- 测试服 `.env IMAGE_TAG=<releaseTag>`
- 测试服后端/前端镜像 tag=`<releaseTag>`
- 测试服后端 health=`UP`
- 测试服前端 HTTP=`200`

## Current Status

COMPLETED：`release-20260629-1415-build-test-v3` 已通过真实 `build-release -> publish-test` 链路成功发布到测试服务器 `172.30.30.58`。最终成功 operation 为 `op-2026-06-29T054412202449600Z-dfd62758-f3b4-42bf-b53c-d5ff9761942c`，已核对测试服 `.env IMAGE_TAG=release-20260629-1415-build-test-v3`、后端镜像 `intruoyi-backend:release-20260629-1415-build-test-v3`、前端镜像 `intruoyi-frontend:release-20260629-1415-build-test-v3`、后端 health=`UP`、前端 HTTP=`200`。本轮范围到测试服为止，不推进 `mark-tested`、正式服或备份服。
