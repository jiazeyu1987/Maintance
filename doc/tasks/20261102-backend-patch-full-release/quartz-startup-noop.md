# Quartz 启动重复写入修复

## 范围与依据
真实失败JOB-6aa7b1fac9：JobStartupSyncRunner调用syncJob，对所有已有任务无条件delete/add/pause，被数据库只读门禁拒绝。用户已明确批准“允许同类修复后继续补丁→全量”，此处仅避免相同定义和相同状态的任务重复持久化，沿用现有同步差异处理；不关闭定时任务、不吞异常、不调整数据库保护。

三服均36项infra_job/Quartz定义。测试/备份实际启动覆盖auto-startup=false；正式仅确认dev profile，无显式覆盖，调度器自动启动有效值仍需核实，不猜测。不因这个未知项阻塞独立的无必要写入修复；它阻塞正式服补丁试运行。

## BDD 与验收
- Given实际任务定义、JobDataMap、cron/时区、执行策略及状态一致，When启动同步，Then只读取，不delete/add/pause，不重置下次触发时间。
- Given任务缺失、参数/cron/重试/任务类/关键标识或状态差异，When启动同步，Then保留原同步，数据库只读时继续拒绝，不伪装一致。
- GivenQuartz查询或同步失败，Then异常继续传播，不能当作无差异。
- RED先验证无条件删除问题；GREEN/REGRESSION覆盖匹配、不匹配、异常和真实内存Quartz。随后固定新提交、新包实际Spug测试。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，避免相同定义重复重建。
- 是否存在临时补丁或绕过：否。

## 当前状态
in_progress；恢复证据restoration-JOB-1746423a99.json、ui-gxp-quartz-recovery-test.json PASS；只读配置和实际DESCRIBE见quartz-effective-complete-inventory.json。
