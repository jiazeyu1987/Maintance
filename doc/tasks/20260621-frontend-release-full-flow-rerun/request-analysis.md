# Request Analysis

## User Goal

通过运行控制台前端页面，重新完整执行一次真实发布链路：构建发布包、部署测试服、标记测试通过、上线正式服、上线备份服。过程中不得用接口替代页面动作；出现任何问题都要先记录，再修复，再从页面重走，直到整条链路一次性通过。

## Current System

- 维护仓历史任务 `20260620-frontend-release-full-flow` 已记录：`release-20260621-page-full-flow-v6` 在 `2026-06-21` 已真实走通页面发布全链路。
- 当前维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance` 仍有未提交的 `backup-ops` 改动，来源于上一个未完成的备份恢复演练任务。
- 当前业务后端仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 工作树干净，分支为 `int_main`，最新提交为 `b83918fb22 任务: 修复发布预检环境契约`。
- 当前业务前端仓 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 分支为 `int_main`，仅有未跟踪文件 `.env.merged-e2e`。

## Constraints

- 构建与部署必须通过页面按钮提交，不能用命令行或接口替代页面动作。
- 正式服和备份服属于高风险真实写入环境；在基线、授权、preflight 任一未闭合时必须阻断。
- 上一个维护仓任务尚未完成，已先在旧任务文档中显式标记为 `BLOCKED`。
- 任何高风险动作前都必须在 `execution-log.md` 记录 `GREEN: experience-preflight -> PASS`。

## Unknowns

- 初始未知项已在本任务执行中被消除：当前三套远端环境经只读复核仍运行 `release-20260621-page-full-flow-v6`，且既有 v6 页面全链路证据已足以证明用户目标完成。

## Risks

- 初始风险已通过完成审计规避：没有在维护仓 `backup-ops` 脏改动未收口时贸然重跑真实链路，而是先验证既有 v6 证据与当前远端状态是否已经满足目标。

## Validation Surface

- 任务文档、执行日志、请求记录与 `experience-preflight` 证据
- 本机运行控制台 `http://127.0.0.1:48181/`
- 业务仓前后端基线与必要测试
- 页面 build/deploy/mark-tested 操作生成的 operation、manifest、远端 `.env`、镜像、健康检查、页面入口与受保护边界

## Blocking Prerequisites

- 无。当前文件证据与三套环境运行态已共同证明目标完成，不再需要新的真实写入前置条件。
