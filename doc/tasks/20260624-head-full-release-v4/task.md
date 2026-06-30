# 任务：Phase5 后基于当前 HEAD 完整发布三环境

## Goal

在 Phase5 已完成后，基于当前各仓库最新已提交代码重新构建并发布 IntRuoyi。构建产物必须只包含已提交代码，不得包含维护仓、后端仓、前端仓当前工作区的未提交改动。

当前发布基线：

- 维护控制台：`int_main` / `cb0150ce964e7d5191372189b0449e557976e492`
- 后端：`int_main` / `c0f89085cb8aa293f0f725384e6a00b90dc81d32`
- 前端：`int_main` / `2f537fe22a8e4f4e521608c28586d9f6df9a46c7`

## 上一任务检查

- 上一相关任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260624-head-full-release\task.md`
- 状态：`COMPLETED`
- 处理：上一任务发布的 `release-20260624-head-full-v3` 只覆盖后端 `bdf2e35...`、前端 `317056a...`；当前 Phase5 后 HEAD 已前进到后端 `c0f89085...`、前端 `2f537fe...`，因此旧 v3 不满足本次“当前分支最新已提交代码”发布目标，必须以新 releaseTag 重建、重发和重验。

## Scope

- 记录维护仓、后端仓、前端仓的当前分支、HEAD 和 dirty 状态。
- 从当前已提交 HEAD 创建或复用干净构建来源。
- 构建维护控制台并通过运行控制台真实链路构建 `code-only` 发布包。
- 校验发布包 manifest、sourceRepos、releaseTag、变更说明和 artifact sha256。
- 依次发布测试服、正式服、备份服；每个环境发布后验证真实运行态。
- 沉淀本轮耗时点、失败点、重复操作和可自动化点。

## Non-Scope

- 不发布未提交改动。
- 不执行数据库、MinIO、展厅数据同步，除非发布脚本预检明确要求并重新记录授权。
- 不修改三环境业务数据。
- 不用 mock、默认成功、手工改状态或静默跳过替代真实发布验证。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - dirty worktree 不得作为部署输入；发布包 manifest 必须证明 `sourceRepos.dirty=false`。
  - 发布完成必须具备 operation、manifest、远端 `.env` / 镜像 tag、健康检查和真实页面证据。
  - 每次修复前置条件后使用新的 `releaseTag` 重跑构建，失败半成品不得作为候选。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - 发布包必须校验 manifest、releaseTag、component、publishScope、变更说明和 artifact sha256。
  - 测试服先发布并验证，通过后才能继续正式服和备份服。
  - 远端 `.env`、后端镜像、前端镜像和发布 manifest 必须属于同一 `IMAGE_TAG`。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
  - 当前任务已由用户明确授权发布测试服、正式服和备份服。
  - 发布前确认目标主机、目录、容器、数据盘和远端容量；备份服必须显式使用 `/mnt/intruoyi-data`。
  - 远端凭据不得写入仓库、脚本、任务文档或运行控制台配置。
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
  - 涉及管理前端验证时使用真实页面；登录或页面异常必须记录实际入口与影响，不得静默切换环境或账号。
- `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
  - 根工作区脏时不得直接出包；发布隔离 worktree 必须记录路径、分支、commit、构建命令和验证命令。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
  - 同一 releaseTag 必须一次性走通 build/test/prod/backup；不要拼接多轮结果。
  - 处理 RUNNING 锁前必须核活跃进程和 operation 真实状态，禁止直接改锁。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；缺少凭据、manifest、远端访问、真实运行态证据或控制台版本说明时直接阻塞。
- `是否从根因和长期维护角度解决`：是；本轮继续沿用干净 HEAD worktree、manifest 校验、三环境运行态和控制台 release-status 闭环。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: Phase5 后 HEAD 构建 -> Given 后端和前端 HEAD 已在 v3 发布后前进 When 使用干净 worktree 构建发布包 Then manifest sourceRepos 必须显示后端 c0f89085、前端 2f537fe 且 dirty=false。`
- `BDD: 测试服先行发布 -> Given v4 发布包 manifest 校验通过 When 部署测试服 Then 远端 .env、前后端镜像 tag、健康检查、前端页面和运行控制台版本说明均显示本次 releaseTag。`
- `BDD: 正式服与备份服发布门禁 -> Given 测试服验证通过 When 发布正式服和备份服 Then 两个环境真实运行态均与同一 releaseTag 一致，运行控制台显示版本号和变更说明。`

## Milestones

1. 任务文档、经验门禁、Git HEAD 与 dirty 状态记录。`BLOCKED`
2. 创建干净 HEAD 构建来源并构建维护控制台。`NOT_RUN`
3. 通过运行控制台构建发布包并校验 manifest。`NOT_RUN`
4. 发布测试服并验证真实运行态。`NOT_RUN`
5. 发布正式服和备份服并验证真实运行态。`NOT_RUN`
6. 记录经验沉淀、收尾清理预览、提交本任务文档。`NOT_RUN`

## Expected Verification

- 三个仓库 `git status --short --branch` 和 `git rev-parse HEAD` 已记录。
- 干净 worktree 初始 `git status --short` 为空。
- 维护控制台构建通过。
- 发布包 manifest 显示 `releaseTag=release-20260624-head-full-v4`、`component=intruoyi`、`publishScope=code-only`、后端 `c0f89085... dirty=false`、前端 `2f537fe... dirty=false`。
- 测试服、正式服、备份服：远端 `.env`、`docker compose ps`、后端健康、前端页面、运行控制台 release-status 与 release notes 均一致。

## Current Status

BLOCKED：本任务记录的目标 HEAD 已被 2026-06-25 00:08 后端/前端新提交取代，继续执行会让发布证据与当前分支最新已提交代码不一致。按用户最新发布目标，转入新任务 `20260625-head-full-release`，本任务不再创建构建产物、不部署任何环境。

## Verification Evidence

- 2026-06-25 发布前复核：维护仓 HEAD `3eb9047d0ac0759ee46d7d88f4adba442bed474f`，后端 HEAD `b0586ee897dc5124580b49121b0a1656052b68fa`，前端 HEAD `0e7616075c6105efb577c6eabb02adafbd497290`。
- 本任务原 BDD 期望的后端 `c0f89085...`、前端 `2f537fe...` 已非当前分支最新提交，不能继续作为发布输入。

## Blockers

- 目标提交过期：当前用户要求“基于当前分支最新已提交代码”发布，本任务记录的提交不再满足验收标准。

## Next Required Action

- 使用新任务 `20260625-head-full-release` 从最新 HEAD 重新创建干净 worktree、构建、发布和验证。
