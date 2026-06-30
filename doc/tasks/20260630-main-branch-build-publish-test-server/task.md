# 20260630 基于主分支构建并发布到测试服务器

## Task Goal

基于维护仓、后端仓、前端仓当前主分支 `int_main`，真实执行一次 `build-release -> publish-test` 测试服务器发布闭环，并在全过程中记录问题、排查、根因、解决与验证证据；发布成功后，将本轮通用问题前移沉淀为发布前置经验，同时保留失败排障过程作为事后学习材料。

## Scope

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 后端仓：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
- 前端仓：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
- 目标环境：测试服务器 `172.30.30.58`
- 发布动作：真实 `build-release`、真实 `publish-test`、测试服运行态验证
- 文档范围：任务台账、执行日志、请求命令日志、事前发布经验、事后排障材料

## Non-Scope

- 不执行 `mark-tested`
- 不发布正式服
- 不发布备份服
- 不使用发布 `worktree` 作为默认输入

## Previous Task Check

- 上一个维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260630-release-main-branch-baseline\task.md`
- 状态：`COMPLETED`
- 处理说明：上一任务已完成主分支发布规则固化；本次直接按新基线执行真实测试服发布。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 先读索引，只打开命中的发布经验文档。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - 默认发布按主分支检查；若主分支脏改则先提示用户选择方案。发布成功后需把本轮通用问题回写成事前经验。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`
  - 真实发布前必须完成 `experience-preflight`、主分支输入核对、运行控制台健康与预览参数确认。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - 发布成功判定必须同时核 operation、manifest、远端 `.env IMAGE_TAG`、运行镜像、health 与前端入口。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
  - 当前任务仅允许写入测试服 `172.30.30.58`，正式服和备份服不触达。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；主分支发布如遇缺前置条件、控制台不可用、契约失败或远端验收不通过，直接阻塞并记录。
- `是否从根因和长期维护角度解决`：是；本轮不仅要发布成功，还要把通用问题沉淀为前置门禁，把失败排障保留为学习材料。
- `是否存在临时补丁或绕过`：否；不默认切回 `worktree`、不手工改测试服文件或数据库绕过发布链路。

## BDD 场景

BDD: 主分支真实发布到测试服 -> Given 维护仓、后端仓、前端仓当前主分支输入可用于发布 When 通过运行控制台真实执行 `build-release -> publish-test` Then 测试服必须切换到本次主分支构建出的同一 `releaseTag` 并通过运行态验收。

BDD: 本轮问题要形成前置经验 -> Given 发布过程中出现可复用的阻塞、根因或排查路径 When 本轮发布完成 Then 必须把通用问题前移到事前发布经验，把具体失败排障保留到任务记录或事后材料。

## Milestones

1. 建立本轮主分支发布任务台账并记录经验门禁。`COMPLETED`
2. 核对三仓主分支输入、工作区状态与运行控制台前置条件。`COMPLETED`
3. 真实执行 `build-release` 并校验 manifest。`BLOCKED`
4. 真实执行 `publish-test` 并完成测试服运行态验证。`BLOCKED`
5. 回填全过程证据、问题总结和经验文档更新。`IN_PROGRESS`

## Expected Verification

- 三仓当前主分支均为 `int_main`
- 三仓主分支工作区无未提交脏改
- 本机 `http://127.0.0.1:48181/actuator/health` 返回 `UP`
- `build-release` operation `SUCCESS`
- `publish-test` operation `SUCCESS`
- manifest 存在且与本次 `releaseTag`、前后端提交一致
- 测试服 `.env IMAGE_TAG=<releaseTag>`
- 测试服 backend/frontend 镜像 tag=`<releaseTag>`
- 测试服 backend health=`UP`
- 测试服 frontend HTTP=`200`

## Current Status

BLOCKED：当前仍不满足“只发布 Git 已提交版本”的主分支输入门禁，不能继续真实测试服发布。

- 历史阻塞：真实 `build-release` 虽已于 `2026-06-30 18:36` 成功完成并上传 NAS 发布包 `release-20260630-1825-main-branch-v1`，但随后的发布包核对发现 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260630-1825-main-branch-v1\manifest.json` 中后端仓记录为 `branch=int_main`、`commit=93bdb0f9aad11b2da8e10f396484e4512ae587e4`、`dirty=true`，因此该发布包已判废。
- 当前门禁复核时间：`2026-06-30 18:58:06`。
- 当前维护仓主分支状态：`int_main`，存在未提交改动 `docs/release-agent-checklist.md`、`docs/release-build-preflight-lessons.md`、`docs/request-command-log.md`，以及未纳入版本控制的任务目录 `doc/tasks/20260630-main-branch-build-publish-test-server/`。
- 当前后端仓主分支状态：`int_main`，仍存在未提交业务改动与任务文档改动，包括 `yudao-module-erp`、`yudao-module-mes` 相关源码/测试文件以及 `doc/tasks/20260630-edhr-gray-fillable-cell-rules/`、`doc/tasks/20260630-schedule-order-replan-production-material-required/` 台账。
- 当前前端仓主分支状态：`int_main`，存在未纳入版本控制的真实 E2E 文件 `tests/e2e/mes-schedule-order-replan-881mo090863-real-flow.e2e.js`。
- 按当前线程基线，发布默认只发布三仓主分支当前版本；任一主分支工作区 dirty 时，必须先提示用户选择处理方案，未得到明确选择前不得继续真实 `build-release` 或 `publish-test`。
