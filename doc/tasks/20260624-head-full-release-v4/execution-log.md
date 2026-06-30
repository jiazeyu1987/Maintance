# Execution Log

## BDD

BDD: Phase5 后 HEAD 构建 -> Given 后端和前端 HEAD 已在 v3 发布后前进 When 使用干净 worktree 构建发布包 Then manifest sourceRepos 必须显示后端 c0f89085、前端 2f537fe 且 dirty=false。

BDD: 测试服先行发布 -> Given v4 发布包 manifest 校验通过 When 部署测试服 Then 远端 .env、前后端镜像 tag、健康检查、前端页面和运行控制台版本说明均显示本次 releaseTag。

BDD: 正式服与备份服发布门禁 -> Given 测试服验证通过 When 发布正式服和备份服 Then 两个环境真实运行态均与同一 releaseTag 一致，运行控制台显示版本号和变更说明。

## Preflight

GREEN: experience-preflight -> PASS，已读取 `release-build-preflight-lessons.md`、`release-backup-restore.md`、`server-access.md`、`login-access.md`、`worktree-memory.md` 与 `project-error-prevention.md`；用户当前发布目标明确授权测试服、正式服和备份服发布；旧 `release-20260624-head-full-v3` 不含当前后端 `c0f89085...` 与前端 `2f537fe...`，本轮必须使用新 releaseTag 重新构建、发布和验证。

GREEN: git-preflight -> PASS，维护控制台 `int_main/cb0150ce964e7d5191372189b0449e557976e492`，后端 `int_main/c0f89085cb8aa293f0f725384e6a00b90dc81d32`，前端 `int_main/2f537fe22a8e4f4e521608c28586d9f6df9a46c7`；三个主工作区均存在未提交改动或任务文档改动，禁止直接作为构建来源。

## RED

RED: old-release-baseline-check -> FAIL，`release-20260624-head-full-v3` manifest 记录后端 `bdf2e35a30a1b679c59b6253f2a62250b62ffd43`、前端 `317056aa6a2db9dc1cf51e5bbf5e00d9e163729d`，不等于当前 Phase5 后 HEAD，不能作为本轮验收候选。

## GREEN

- 未执行构建或发布；本任务在创建发布产物前被最新 HEAD 发布请求取代。

## BLOCKER

BLOCKER: stale-release-target -> 2026-06-25 复核时维护仓 HEAD 已为 `3eb9047d0ac0759ee46d7d88f4adba442bed474f`，后端 HEAD 已为 `b0586ee897dc5124580b49121b0a1656052b68fa`，前端 HEAD 已为 `0e7616075c6105efb577c6eabb02adafbd497290`；旧任务期望的后端 `c0f89085...`、前端 `2f537fe...` 不再是当前分支最新提交，按“构建产物只包含当前分支最新已提交代码”的验收标准终止旧任务，转入 `20260625-head-full-release`。
