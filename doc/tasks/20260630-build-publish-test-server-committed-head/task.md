# 20260630 将 IntRuoyi 已提交 git 版本发布到测试服务器

## Task Goal

基于 IntRuoyi 当前三个相关仓库中“已经提交到 git 的版本”，隔离未提交脏改和未纳入版本管控内容后，通过受控发布入口重新执行一次真实 `build-release -> publish-test` 链路，只发布到测试服务器 `172.30.30.58`，并验证测试服运行版本与本次已提交 HEAD 一致。

## Scope

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 后端仓：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
- 前端仓：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
- 发布目标：测试服务器 `172.30.30.58`
- 发布动作：仅允许真实 `build-release` 与 `publish-test`
- 发布输入：仅允许各仓库“已提交 HEAD”对应内容，禁止把未提交脏改或未纳入版本管控文件带入本次发布

## Non-Scope

- 不执行 `mark-tested`
- 不发布正式服
- 不发布备份服
- 不用命令行直跑发布脚本替代 runtime-control 页面动作
- 不把主工作区未提交修改、未跟踪文件或临时产物混入本次发布输入

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 任务开始先读索引，只打开命中的发布、服务器与 worktree 经验文档。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - 发布“已提交 git 版本”前必须先核三仓 HEAD、测试服当前版本、clean worktree、runtime-control 发布输入与构建前置门禁。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`
  - 这次任务只允许执行到 `build-release -> publish-test -> 测试服运行态验证`，不推进后续链路。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - `code-only` 不跳过 schema、required SQL、迁移元数据或 manifest 门禁。
  - 发布写入前必须先确认测试服目标、发布包 manifest、远端 `.env` 与运行镜像契约一致。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
  - 当前任务仅对测试服 `172.30.30.58` 执行写入发布；正式服与备份服默认禁止操作。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；runtime-control 不可用、manifest 缺失、发布输入混入未提交改动或测试服运行态不一致时直接阻塞。
- `是否从根因和长期维护角度解决`：是；通过干净 worktree 锁定各仓库已提交 HEAD，避免主工作区脏改和未跟踪文件污染发布输入。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

BDD: 只发布 git 已提交版本 -> Given 主工作区存在未提交脏改与未跟踪文件 When 执行测试服发布 Then 必须使用各仓库已提交 HEAD 对应的干净 worktree 作为唯一发布输入，且 manifest 中提交号与这些 HEAD 完全一致。

BDD: 测试服版本必须与本次已提交 HEAD 一致 -> Given build-release 成功生成新 releaseTag When 执行 publish-test Then 测试服 `.env IMAGE_TAG`、后端镜像、前端镜像、health 和前端 HTTP 必须全部与同一 releaseTag 一致，且 manifest 中前后端 commit 与本次已提交 HEAD 一致。

## Milestones

1. 创建任务台账并记录经验门禁。`COMPLETED`
2. 核对当前各仓库已提交 HEAD、未提交脏改、未跟踪文件与测试服当前运行版本差异。`COMPLETED`
3. 创建或确认干净发布 worktree，锁定仅含已提交 HEAD 的发布输入。`COMPLETED`
4. 真实执行 `build-release` 并校验 manifest 提交号与本次 HEAD 一致。`COMPLETED`
5. 真实执行 `publish-test` 并验证测试服运行态。`COMPLETED`
6. 回写日志、证据与结论。`COMPLETED`

## Expected Verification

- 本机 `http://127.0.0.1:48181/actuator/health` 返回 `UP`
- 构建使用的维护仓、后端仓、前端仓均为干净 worktree
- `build-release` operation `SUCCESS`
- 新 releaseTag 的 manifest 存在，且 `sourceRepos.backend/admin-frontend.dirty=false`
- manifest 中后端与前端 commit 分别等于本次目标已提交 HEAD
- `publish-test` operation `SUCCESS`
- 测试服 `.env IMAGE_TAG=<releaseTag>`
- 测试服后端/前端镜像 tag=`<releaseTag>`
- 测试服后端 health=`UP`
- 测试服前端 HTTP=`200`

## Current Status

COMPLETED：已通过三套 clean worktree 完成真实 `build-release -> publish-test`，最终发布测试服版本 `release-20260630-0940-committed-head-v3`。对应 manifest 中 backend commit=`bdf13bc3de04d5dcda9e76d6765c5bf3573696cc`、frontend commit=`eb577ab5edb0009a0702e669f3c6fae0834ec2cb`，且两者 `dirty=false`；测试服 `.env IMAGE_TAG`、运行镜像 tag、后端 health 与前端 HTTP 均已通过验收。
