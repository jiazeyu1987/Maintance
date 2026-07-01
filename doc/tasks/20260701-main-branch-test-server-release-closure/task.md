# 20260701 基于主分支完成测试服务器真实发布闭环

## Task Goal

基于维护仓、后端仓、前端仓当前主分支 `int_main` 的最新已提交版本，真实执行一次测试服务器发布闭环，至少完成 `build-release -> publish-test` 与测试服运行态验证，并把全过程中的问题、排查、根因、解决、验证证据完整记录；发布成功后，将本轮通用问题前移沉淀到构建发布经验，同时保留失败排障方案作为事后学习材料。

## Scope

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 后端仓：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
- 前端仓：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
- 目标环境：测试服务器 `172.30.30.58`
- 真实动作：提交三仓主工作区、真实 `build-release`、真实 `publish-test`、测试服运行态验证
- 文档交付：任务台账、执行日志、请求命令记录、问题总结、经验文档更新、失败排障材料

## Non-Scope

- 不执行 `mark-tested`
- 不发布备份服
- 不发布正式服
- 不使用命令行直跑发布脚本替代运行控制台真实动作

## Previous Task Check

- 上一个维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260630-main-branch-build-publish-test-server\task.md`
- 状态：`COMPLETED`
- 处理说明：上一任务已完成 2026-06-30 主分支测试服真实发布闭环；本次因 2026-07-01 三仓主工作区已有新的在途改动，需要先提交主工作区，再对新的已提交输入重新执行完整测试服真实发布闭环。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 任务开始先读索引，只打开命中的发布经验文档。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - 默认只发布三仓主分支当前已提交版本；若主工作区 dirty，必须先向用户确认处理方案，再继续真实发布。
  - 发布成功判定必须同时核 operation、manifest、远端 `.env IMAGE_TAG`、运行镜像 tag、backend health、frontend HTTP。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`
  - 高风险发布动作前必须先完成 `experience-preflight`、主分支输入核对、运行控制台健康检查和预览参数确认。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - `code-only` 不等于跳过 schema、required SQL、迁移元数据或 manifest 门禁。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
  - 当前任务仅授权写入测试服务器 `172.30.30.58`，正式服和备份服禁止操作。
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
  - 若需要真实浏览器验证登录或页面入口，必须先走官方最小登录路径。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；主分支提交、构建、发布或远端验收任一步不满足就直接阻塞并记录。
- `是否从根因和长期维护角度解决`：是；本轮不仅要求发布成功，还要求把通用问题沉淀为发布前置经验。
- `是否存在临时补丁或绕过`：否；不默认切回 worktree，不手工改测试服文件或数据库绕过发布链路。

## BDD 场景

BDD: 三仓主分支脏改先提交再发布 -> Given 当前维护仓、后端仓、前端仓主工作区存在脏改 When 用户确认先提交主工作区 Then 必须分别提交三仓当前主分支在途成果，并以新提交版本作为本轮发布输入。

BDD: 主分支真实发布测试服闭环 -> Given 三仓主分支输入已提交且运行控制台可用 When 真实执行 `build-release -> publish-test` Then 测试服 `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health、frontend HTTP 必须全部与同一 `releaseTag` 一致。

BDD: 通用问题前移沉淀为事前经验 -> Given 发布过程中出现可复用的阻塞、根因或排查路径 When 本轮发布闭环完成 Then 必须把通用问题补到事前发布经验，把失败排障保留在任务记录或事后材料。

## Milestones

1. 创建本轮发布任务台账并记录经验门禁。`COMPLETED`
2. 核对三仓主分支脏改范围并分别提交。`COMPLETED`
3. 真实执行 `build-release` 并校验 manifest。`COMPLETED`
4. 真实执行 `publish-test` 并完成测试服运行态验证。`COMPLETED`
5. 回填全过程证据、问题总结和经验文档更新。`COMPLETED`

## Expected Verification

- 三仓当前主分支均为 `int_main`
- 三仓主分支工作区在真实发布前已清空脏改
- 本机 `http://127.0.0.1:48181/actuator/health` 返回 `UP`
- `build-release` operation `SUCCESS`
- manifest 存在且与本次 `releaseTag`、前后端提交一致
- `publish-test` operation `SUCCESS`
- 测试服 `.env IMAGE_TAG=<releaseTag>`
- 测试服 backend/frontend 实际镜像 tag=`<releaseTag>`
- 测试服 backend health=`UP`
- 测试服 frontend HTTP=`200`
- 任务文档、执行日志、请求命令记录与经验文档已同步更新

## Current Status

COMPLETED：本轮已基于三仓主分支最新已提交版本完成真实 `build-release -> publish-test -> 测试服运行态验收` 闭环。

- 成功构建 operation：`op-2026-07-01T033034704182700Z-1f28bee7-89e4-4557-8a7f-133704a26751`
- 成功测试服发布 operation：`op-2026-07-01T035959878754100Z-fba9c2e2-7656-49d4-9003-3ab0627a22c8`
- 成功 `releaseTag`：`release-20260701-main-branch-commit-head-v2`
- manifest 复核：后端 `291cbc29e825307cb3cf1e6d35b64e713d1d0d94 / int_main / dirty=false`；前端 `57bd4d394e0795279eccf2d505b54534060aec9a / int_main / dirty=false`
- 测试服运行态验收：
  - `/opt/intruoyi/runtime/.env`：`IMAGE_TAG=release-20260701-main-branch-commit-head-v2`
  - 运行镜像：`intruoyi-backend:release-20260701-main-branch-commit-head-v2`、`intruoyi-frontend:release-20260701-main-branch-commit-head-v2`
  - 后端健康检查：`http://172.30.30.58:48081/actuator/health` -> HTTP `200` / `UP`
  - 前端入口：`http://172.30.30.58:8081/` -> HTTP `200`

- 本轮关键问题收敛：
  - 运行控制台曾从旧维护 worktree 启动，导致首次 `build-release` 使用错误发布输入；已切回当前维护仓实例并保留阻塞证据。
  - 维护控制台测试服参数一度被误判为备份服口径，真实发布后只读核对证明测试服当前仍以 `/var/lib/docker`、`/dev/vdb`、`ragflow_compose-minio-1` 为准；已把“测试服参数不得套用备份服经验”前移到发布前置经验并回写服务器访问文档。
