# 执行记录

- 用户提供现场结论：相关迁移账本有prod记录、后续SKIPPED_ALREADY_APPLIED，测试菜单值等于旧初始化SQL；缺具体覆盖操作日志。本轮不把这些现场事实标作重新查询。
- 只读核本机旧SQL：20260610_mes_schedule_order_p1.sql:107的UPDATE仅以id=5580为条件，设置name=排产工单池、parent_id=5700、path=schedule-order，同时写component、状态等字段和NOW()。确有覆盖新版配置的能力，无版本/原值保护。
- 源码搜索曾以PowerShell通配目录传rg产生路径错误，改显式目录与-g读取；SQL读取成功。未执行SQL或修改业务数据。
- 对照新版SQL20260611_mes_smart_scheduling_tabs.sql:93，同id5580的name/parent_id/path为排产工单/900120/绝对路径，与旧SQL存在明确相互覆盖。
- 发布源码：intruoyi_runtime_agent.py:134采集账本不筛target_environment，仅migration_id/sha256/status；release_preflight_plan.py:277依据已完成同摘要记录SKIP。该判断是账本去重，不校验菜单现值。读取维护文件曾在应用cwd执行导致不存在，已改回维护cwd并成功读取。
- 最终仅确认机制与推断边界：旧SQL覆盖为强候选，缺日志不能确认具体发生时间/执行者/两服同因；prod记录不独立证明当前测试环境执行。所有现场菜单和账本信息仍注明来自用户提供，未伪称本轮远端验证。
