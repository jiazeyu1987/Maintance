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
3. 真实执行 `build-release` 并校验 manifest。`COMPLETED`
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

BLOCKED：本轮主分支 `build-release` 已成功且 manifest 通过“只发布 Git 已提交版本”门禁，但测试服 `publish-test` 继续被 required SQL / 发布后角色门禁契约阻断，暂不能完成测试服发布闭环。

- 已完成构建：`op-2026-06-30T111930929156700Z-ee491e68-372d-4812-89bd-365f22bfc4fd` 于 `2026-06-30 19:19:30` 后最终 `SUCCESS`，发布包为 `release-20260630-1912-main-branch-v2`。
- 已完成 manifest 复核：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260630-1912-main-branch-v2\manifest.json` 中后端 `commit=8241c309026bb37c3ba4d13da858afe1aea3ae07 branch=int_main dirty=false`，前端 `commit=513adf9a53f62c8c2fca318a0c75b137f794df89 branch=int_main dirty=false`，该发布包满足“只发布 Git 已提交版本”。
- 当前阻塞 operation：`op-2026-06-30T113310680094600Z-844a0e48-aaec-4638-b63f-514985aad00e`。
- 当前阻塞根因：测试服执行 required SQL `20260624_mes_schedule_issue_structured_backflow.sql` 时，MySQL 报错 `ERROR 1060 (42S21) at line 4: Duplicate column name 'status'`；说明真实库已具备该列，而 SQL 仍使用裸 `ALTER TABLE ... ADD COLUMN status`，不满足可重复执行契约。
- 当前锁状态：发布日志已确认 `LOCK_RELEASED`，本轮可在修复 SQL 契约后直接重新走新的主分支 `build-release -> publish-test`。
- 最新真实构建：`op-2026-06-30T122943908590100Z-9a31cf90-8660-414f-9a6f-caeba66a3477` 于 `2026-06-30 21:35` 左右最终 `SUCCESS`，发布包为 `release-20260630-2135-main-branch-v4`。
- 最新 manifest 复核：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260630-2135-main-branch-v4\manifest.json` 中后端 `commit=2709509b960c1f4ed0abb3c2d7413dc46054cade branch=int_main dirty=false`，前端 `commit=513adf9a53f62c8c2fca318a0c75b137f794df89 branch=int_main dirty=false`。
- 最新测试服阻塞 operation：`op-2026-06-30T124330918809800Z-e45cfcee-3242-4752-a407-eec8cb860ebc`。
- 最新阻塞根因：测试服执行 required SQL `20260618_post_release_role_e2e_gate.sql` 时，MySQL 报错 `ERROR 1644 (45000) at line 244: Missing enabled wenkong role; cannot prepare wangsiyu DCC E2E account`。只读核对测试服真实库后确认：租户 `1/芋道源码` 存在启用用户 `wangsiyu`，但不存在启用角色 `code='wenkong'`；当前真实角色基线为 `doc_control/文控` 与 `wenkong_download/文控下载`，说明本轮阻塞属于发布后角色门禁 SQL 契约与当前角色编码基线漂移不一致。
- 当前锁状态：最新发布日志已确认 `LOCK_RELEASED`，本轮可在修复 `20260618_post_release_role_e2e_gate.sql` 契约后直接重新走新的主分支 `build-release -> publish-test`。
