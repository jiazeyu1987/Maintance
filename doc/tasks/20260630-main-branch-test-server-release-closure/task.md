# 20260630 基于主分支完成测试服务器真实发布闭环

## Task Goal

基于当前三仓主分支版本，真实执行一次测试服务器发布闭环，至少完成 `build-release -> publish-test` 与测试服运行态验证，并把全过程中的问题、排查、根因、修复、验证证据完整记录到任务文档；发布成功后，把通用问题前移沉淀到发布前置经验，同时保留失败排障方案作为事后学习材料。

## Scope

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 后端仓：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
- 前端仓：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
- 发布目标：测试服务器 `172.30.30.58`
- 真实动作：`build-release`、`publish-test`、测试服运行态验证
- 文档交付：任务记录、执行日志、问题总结、经验文档更新、失败排障材料沉淀

## Non-Scope

- 不执行 `mark-tested`
- 不发布正式服
- 不发布备份服
- 不使用命令行直跑发布脚本替代运行控制台真实动作
- 不把未提交主工作区脏改、未跟踪临时文件或历史候选结果静默混入本次发布输入

## Previous Task Check

- 上一个维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260630-release-main-branch-baseline\task.md`
- 状态：`COMPLETED`
- 处理说明：上一任务已把“默认按主分支发布、主分支脏改先提示用户选择方案”固化到长期基线，本次可在该基线上继续推进真实发布闭环。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 任务开始只按索引命中发布相关经验，不全量扫读无关文档。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - 默认发布先核三仓主分支名、HEAD 与 dirty 状态；主分支 dirty 时不得默认继续，也不得默认切 worktree 规避。
  - 发布成功判定必须同时核 operation、manifest、远端 `.env IMAGE_TAG`、运行镜像 tag、backend health、frontend HTTP。
  - 发布失败优先按“契约层 -> 脚本层 -> 环境层”排查，并把通用问题补成 preflight。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`
  - 本轮只允许执行到 `build-release -> publish-test -> 测试服运行态验证`，若任何一步失败，必须先记录证据和修复策略再重试。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - `code-only` 不等于跳过 schema、required SQL、迁移元数据或 manifest 门禁。
  - 发布前必须确认测试服目标、发布包 manifest、远端 `.env`、运行镜像与 releaseTag 契约一致。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
  - 当前任务仅授权写入测试服务器 `172.30.30.58`；正式服与备份服默认禁止操作。
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
  - 如需真实浏览器验证登录或页面入口，必须优先走官方最小登录路径，不得用接口旁路伪造结果。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；若 runtime-control 不可用、发布源头不干净、manifest 缺失或测试服运行态不一致，直接阻塞并记录影响。
- `是否从根因和长期维护角度解决`：是；本次不仅追求单次发布成功，还要求把通用问题转成发布前置经验和门禁。
- `是否存在临时补丁或绕过`：否；如必须采用临时处理，需先记录用户批准范围、风险与移除策略。

## BDD 场景

BDD: 主分支真实发布测试服闭环 -> Given 三仓主分支输入已明确且运行控制台可用 When 真实执行 `build-release -> publish-test` Then 测试服 `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health、frontend HTTP 必须全部与同一 releaseTag 一致。

BDD: 发布失败必须形成可复用排障材料 -> Given 任一步真实发布失败 When 记录问题并排查 Then 必须保留失败现象、定位过程、根因、修复动作和复验结果，且不得用默认成功、静默跳过或手工改环境掩盖失败。

BDD: 通用问题前移沉淀为事前经验 -> Given 本轮发布暴露出可复用的构建或部署问题 When 发布闭环完成 Then 必须把可前移的问题补到发布前置经验文档，把失败后排障方案保留为事后学习材料。

## Milestones

1. 创建任务台账、写入经验门禁与初始阻塞。`COMPLETED`
2. 核对三仓主分支状态、runtime-control 可用性与发布前置条件。`BLOCKED`
3. 真实执行 `build-release` 并校验 manifest。`PENDING`
4. 真实执行 `publish-test` 并完成测试服运行态验证。`PENDING`
5. 回填全过程问题、根因、解决、验证证据。`PENDING`
6. 更新经验文档，沉淀前置经验与事后学习材料。`PENDING`

## Expected Verification

- 本机运行控制台 `http://127.0.0.1:48181/actuator/health` 返回 `UP`
- 三仓本次实际发布输入清晰且符合“默认主分支发布”规则
- `build-release` operation `SUCCESS`
- 对应 releaseTag 的 manifest 存在且契约正确
- `publish-test` operation `SUCCESS`
- 测试服 `.env IMAGE_TAG=<releaseTag>`
- 测试服 backend/frontend 实际镜像 tag=`<releaseTag>`
- 测试服 backend health=`UP`
- 测试服 frontend HTTP=`200`
- 任务文档、执行日志、请求命令记录与经验文档已同步更新

## Current Status

BLOCKED：该任务已被后续任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260630-main-branch-build-publish-test-server\task.md` 接续并完成同一目标范围内的真实主分支测试服发布闭环。

1. 原计划中的主分支脏改与 runtime-control 健康前置问题，已在后续任务中完成收敛、提交与验证。
2. 当前不再继续在本任务目录内推进发布动作；以接续任务中的最终 `build-release -> publish-test -> 测试服运行态验收` 结果为准。
3. 阻塞原因不是缺少前置条件，而是目标已被后续同类任务替代收口，按仓库规则显式标记为 `BLOCKED`，避免与已完成任务并行悬挂。
