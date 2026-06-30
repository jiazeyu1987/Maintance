# 20260630 排程日历正式排程为空时报错回归执行日志

BDD: 月排程在正式排程为空时返回空态 -> Given 当前租户没有正式排程任务 When 前端加载月排程 Then 后端返回 `hasCurrentSchedule=false` 的正常月视图，而不是抛出“当前正式排程为空”异常。

BDD: 日详情在正式排程为空时保持可加载 -> Given 当前租户没有正式排程任务 When 前端加载某天日详情 Then 后端返回空任务/空短缺/空问题汇总，便于页面保持一致空态。

INFO: task-created -> 已创建维护仓协调任务台账，准备同步建立后端实现任务并进入严格 TDD。
INFO: root-cause-located -> 后端错误码来自 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-mes\src\main\java\cn\iocoder\yudao\module\mes\service\pro\schedule\MesProScheduleCalendarServiceImpl.java`；当前 `buildContext(...)` 在正式排程为空时直接抛 `PRO_SCHEDULE_CALENDAR_CURRENT_SCHEDULE_REQUIRED`。
INFO: contract-confirmed -> 前端 `schedule-calendar` 页面已经以 `currentScheduleStatus.hasCurrentSchedule` 展示 `已生成/未生成` 与 `当前无正式排程` 空态，因此本次属于前后端契约不一致，不应继续把空排程当作异常。
RED: mvn --% -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-mes -Dtest=MesProScheduleCalendarServiceImplTest#getMonth_shouldReturnEmptyCalendarWhenCurrentScheduleMissing+getDayDetail_shouldReturnEmptyDetailWhenCurrentScheduleMissing -Dsurefire.failIfNoSpecifiedTests=false test -> FAIL，当前模块存在与本任务无关的既有 ERP 同步测试编译错误，未能直接进入本次新增场景断言。
GREEN: backend-fix-implemented -> PASS，后端 `buildContext(...)` 已将“无正式排程”路径改为返回空上下文；月视图/日详情可基于空上下文自然返回空态响应。
GREEN: mvn --% -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-mes -Dmaven.compiler.useIncrementalCompilation=false -Dmaven.compiler.includes=**/MesProScheduleCalendarServiceImpl.java -DskipTests compile -> PASS
GREEN: javac @D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\output\mes-calendar-single-test-javac.args -> PASS，已隔离编译 `MesProScheduleCalendarServiceImplTest`，不触发模块内无关历史测试源码重编译。
GREEN: java @D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\output\mes-calendar-class-test-java.args -> PASS，`MesProScheduleCalendarServiceImplTest` 共 32 条测试全部通过，包含本次新增两条“无正式排程”空态回归测试。
INFO: closeout-preview -> `python C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260630-schedule-calendar-empty-current-schedule-regression --mode preview` 显示维护仓仅保留 `task.md`、`execution-log.md`，无可删附属物。
