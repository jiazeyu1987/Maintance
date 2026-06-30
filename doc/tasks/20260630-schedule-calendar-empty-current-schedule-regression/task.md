# 20260630 排程日历正式排程为空时报错回归协调

## Task Goal

定位并修复“加载月排程失败：当前正式排程为空，无法加载排程日历”回归，确保排程日历在正式排程为空时返回正常空态而不是整页失败，并同步记录维护仓协调证据与验证结果。

## Scope

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 后端仓：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
- 相关模块：MES 排程日历月视图 / 日详情接口与对应前端空态契约

## Non-Scope

- 不修改正式服、测试服或数据库真实数据
- 不引入 fallback、静默吞错或兼容分支
- 不调整排程日历现有页面布局和样式

## Previous Task Check

- 上一个维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260630-main-branch-test-server-release-closure\task.md`
- 状态：`BLOCKED`
- 处理说明：该任务已被后续发布闭环任务接续收口，当前无未完成发布动作阻塞本次缺陷排查。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 只按索引命中 PowerShell/编码经验，不全量读取无关发布文档。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\powershell-preflight-lessons.md`
  - PowerShell 5.1 不使用 `&&`；中文文件读写与终端输出统一显式 UTF-8。
- `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md`
  - 后端任务需命中 `docs\powershell-memory.md`；如涉及真实登录/E2E，再补 `docs\login-access.md`。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；本次要修正错误契约本身，不新增兜底分支。
- `是否从根因和长期维护角度解决`：是；将“正式排程为空”从异常收敛为明确空态响应。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

BDD: 月排程在正式排程为空时返回空态 -> Given 当前租户没有正式排程任务 When 前端加载月排程 Then 后端返回 `hasCurrentSchedule=false` 的正常月视图，而不是抛出“当前正式排程为空”异常。

BDD: 日详情在正式排程为空时保持可加载 -> Given 当前租户没有正式排程任务 When 前端加载某天日详情 Then 后端返回空任务/空短缺/空问题汇总，便于页面保持一致空态。

## Milestones

1. 建立维护仓与后端仓任务台账，补齐经验门禁。`COMPLETED`
2. 定位前后端契约与根因，补 RED 测试。`COMPLETED`
3. 实现最小修复并完成 GREEN 回归。`COMPLETED`
4. 更新请求命令记录、任务证据与结论。`COMPLETED`

## Expected Verification

- 后端定向单测覆盖“无正式排程”月视图/日详情空态
- 相关服务改动不再抛出 `PRO_SCHEDULE_CALENDAR_CURRENT_SCHEDULE_REQUIRED`
- 维护仓与后端仓任务文档、执行日志、请求命令日志完成回填

## Current Status

COMPLETED：后端根因修复已完成，`MesProScheduleCalendarServiceImpl.buildContext(...)` 已把“正式排程为空”改为正常空上下文返回，匹配前端既有空态契约；同时已通过隔离编译与 `JUnit Platform Console` 完成 `MesProScheduleCalendarServiceImplTest` 全类 GREEN 验证，包含本次新增两条空态回归测试。

## Final Verification Result

- 后端生产代码定向编译通过，不再抛 `PRO_SCHEDULE_CALENDAR_CURRENT_SCHEDULE_REQUIRED`
- `MesProScheduleCalendarServiceImplTest` 共 32 条测试隔离执行通过，覆盖本次新增空正式排程月视图/日详情场景
- `task-closeout-cleanup` 预览已执行，确认本维护仓任务当前无可删附属物
