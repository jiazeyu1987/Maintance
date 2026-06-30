# 20260701 排程日期产能覆盖根因修复发布到测试服务器

## Task Goal

把 `2026-09-10 / AUTO-DAY / TESTERP6640C97D318E` 触发的“日期产能覆盖窗口耗尽”根因修复，以“只发布已提交 git 版本”的正式路径重新发布到测试服务器 `172.30.30.58`，验证发布包 manifest、测试服运行镜像、后端健康与前端入口均落到本次正式修复版本，而不是继续依赖主工作区脏改或临时补数据。

## Scope

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 后端仓：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
- 前端仓：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
- 发布目标：测试服务器 `172.30.30.58`
- 发布动作：真实 `build-release -> publish-test -> 测试服运行态验证`
- 发布输入：仅允许三仓已提交 HEAD；若主工作区 dirty，则使用 clean worktree 隔离发布输入

## Non-Scope

- 不执行 `mark-tested`
- 不发布正式服
- 不发布备份服
- 不直接在命令行运行发布脚本替代 runtime-control 页面动作
- 不把主工作区未提交任务文档、临时文件或其他任务脏改混入本次发布输入

## Previous Task Check

- 上一个维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260630-zhaojie-scheduler-button-permission-fix\task.md`
- 状态：`completed`
- 处理说明：上一任务已完成排产员按钮权限正式修复，不阻塞本次测试服发布验证。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 本轮命中发布前置、运行控制台与服务器门禁；只打开相关经验文档，不扩散到无关主题。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - 用户当前目标是“只发布已提交 git 版本”，因此必须使用 clean worktree 隔离三仓 HEAD，并在 `build-release` 成功后再次复核 manifest 中 `sourceRepos.branch/commit/dirty`。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`
  - 本轮只允许执行到 `build-release -> publish-test -> 测试服运行态验证`；若任一步失败，必须先记录真实证据再修复重试。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - `code-only` 不跳过 schema、required SQL、迁移元数据或 manifest 门禁；发布完成判定必须同时核 manifest、`.env IMAGE_TAG`、运行镜像、health 与前端 HTTP。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
  - 当前任务只允许写入测试服务器 `172.30.30.58`；正式服与备份服默认禁止操作。
- `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
  - 因本轮明确使用 clean worktree 隔离已提交版本，必须记录三仓 worktree 路径、对应 commit 与运行控制台发布输入，避免路径漂移或串线。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；若 runtime-control 不可用、构建失败、manifest dirty 或测试服运行态不一致，直接阻塞并记录影响。
- `是否从根因和长期维护角度解决`：是；发布目标是验证“统一日期产能续期机制”已通过正式后端提交进入测试服，而不是继续靠单日补 SQL 或人工改产能表。
- `是否存在临时补丁或绕过`：否；若主工作区 dirty，仅按用户意图切 clean worktree 发布已提交版本，不以手工脚本或未提交文件绕过。

## BDD 场景

BDD: 只发布根因修复的已提交版本 -> Given 后端根因修复已提交且主工作区仍存在无关脏改 / When 执行测试服发布 / Then 发布输入必须锁定三仓 clean worktree，manifest 中后端 commit 应等于本次根因修复提交，且所有 sourceRepos 为 dirty=false。

BDD: 测试服运行态必须落到同一 releaseTag -> Given build-release 成功生成新的 releaseTag / When 执行 publish-test / Then 测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health 与 frontend HTTP 必须全部与该 releaseTag 一致。

BDD: 正式规则仍保持 fail fast -> Given 本次修复只是自动续齐正式日期产能覆盖，而不是制造假产能 / When 测试服运行新版本 / Then 排产链路应具备未来日期正式覆盖续期能力，但在无排班计划或无可用班次时仍保持正式阻断能力。

## Milestones

1. 建立维护仓发布任务台账并记录经验门禁。`completed`
2. 核对三仓目标 HEAD、主工作区脏改与 clean worktree 发布策略。`completed`
3. 创建 clean maintenance/backend/frontend worktree，并切换 runtime-control 发布输入。`completed`
4. 真实执行 `build-release` 并校验 manifest。`completed`
5. 真实执行 `publish-test` 并完成测试服运行态验证。`completed`
6. 回填任务证据与最终结论。`completed`

## Expected Verification

- 本机 `http://127.0.0.1:48181/actuator/health` 返回 `UP`
- clean maintenance/backend/frontend worktree 路径与 commit 已记录，并被 runtime-control 实际引用
- `build-release` operation=`SUCCESS`
- 新 releaseTag 的 manifest 存在，且 maintenance/backend/frontend `sourceRepos.dirty=false`
- manifest 中后端 commit=`1b364a2fe8d458deb14ba322bdeb1af5394d83f6`
- manifest 中前端 commit=`c8f87af720535115c233bf894e957471d68cc667`
- `publish-test` operation=`SUCCESS`
- 测试服 `.env IMAGE_TAG=<releaseTag>`
- 测试服 backend/frontend 镜像 tag=`<releaseTag>`
- 测试服 backend health=`UP`
- 测试服 frontend HTTP=`200`

## Current Status

COMPLETED：本轮已通过三套 clean worktree 完成真实 `build-release -> publish-test`，测试服当前版本为 `release-20260701-capacity-horizon-v2`。候选包 manifest 已确认 backend=`1b364a2fe8d458deb14ba322bdeb1af5394d83f6`、frontend=`c8f87af720535115c233bf894e957471d68cc667` 且两者 `dirty=false`；测试服 `.env IMAGE_TAG`、运行镜像 tag、后端 health 与前端 HTTP 均已通过只读验收。当前业务结论是：`2026-09-10 / AUTO-DAY` 产能缺失的正式长期修复已进入测试服运行版本，不再依赖人工补数据或临时绕过。
