# PQC PATROL约束不一致根因

结论：已发布应用规则变更遗漏配套CHECK约束迁移；不是现有迁移未执行，也没有本次被旧SQL覆盖的证据。测试服运行新程序，数据库仍按原合同拒绝PATROL。只读调查，未修改服务器。

## 已核证据

1. 当前测试58 IMAGE_TAG=2026-11-23-22-02-22，backend镜像ID=sha256:90def9be4d4ff678181d04d4511402dc2ec7361727801ec40f1bcf2520630e8e，绑定275c870118f8096328d94bd38700455de3e76fc0，排除旧后端未更新。
2. 真实SHOW CREATE TABLE及information_schema确认mes_pqc_inspection_task.chk_mes_pqc_inspection_rule_key启用（ENFORCED=YES），只允许FIRST/PATROL_AM/PATROL_PM/FINAL。当前后端日志检出该约束违反，MySQL错误3819。
3. 固定已发布提交的20260814_mes_c015_route_dcc_qa_reconciliation_schema.sql:113—117声明上述约束，当前manifest包含相同SQL摘要c473825e04e21a847d50edc32046ee5ea3bec8e5f8d33270c67c7a5627963eec。
4. Git变更6aa656b613688421922a0767f69211fd11932ec0（2026-11-05）将MesTeamLeaderActiveOrderServiceImpl的RULE_KEY_PATROL_AM/PM改为RULE_KEY_PATROL="PATROL"，SHIFT也改为PATROL。已发布源码4335—4343加入活跃订单时创建FIRST及首次PATROL任务，4379将inspectionRuleKey写入DO。
5. 同次提交20261104_mes_pqc_dynamic_patrol_rounds.sql仅增加冻结来源版本字段；20261104_mes_pqc_patrol_cancellation.sql仅增加取消相关字段。没有处理旧CHECK。固定发布源码SQL中该约束名仅见于历史创建脚本，无更新/删除该约束的迁移。
6. 测试真实账本：上述两个20261104迁移均target_environment=test、status=APPLIED，release_tag=2026-11-16-17-52-43。旧20260814迁移也有APPLIED匹配摘要，但环境标记为prod，release_tag=2026-10-23-16-51-17；这条历史记录不能证明当时实际在测试环境执行。当前约束存在由真实结构独立确认。

## 为什么发布没拦住

现有SQL及账本可以全部合法、摘要匹配，同时应用生成值与数据库约束不兼容。当前包没有表达这条新语义的迁移/目标断言；结构相同也可能同样错误。前一轮验收只覆盖实际登录、排产只读列表、版本和打印入口，没有执行加入活跃订单→生成PQC任务，不能据此证明该写入流程可用。

这是IntRuoyi业务变更及迁移交付缺口；发布验收亦缺少对此变更的数据库合同验证和真实写入回归证据。不能靠反复发布相同包解决。

## 正式处理建议

由IntRuoyi新增不可变前向迁移，明确新PATROL及历史AM/PM任务的兼容规则；不得直接删约束、改已执行SQL或重写冻结任务身份。补真实MySQL反例与迁移幂等测试：旧约束下PATROL失败，新迁移后新任务可写且历史行保留、非法值仍拒绝。发布登记该迁移及只读目标合同检查，测试服更新后通过真实页面在授权测试租户验证加入活跃订单及PQC生成；满足后再晋级正式。

## 边界

- 用户引用的D:/ProjectPackage/IntRuoyi/IntRuoyiAll/workspace/pressure-pump-active-order-cause-20261124.md在本机不存在，因此未独立复核其本地数据库、具体订单日志关联及事务回滚结论。当前日志采样未找到881MO083056文本，不将约束错误样本冒充该订单完整追踪。
- 本机缺约束若属实，能够解释本机未暴露此错误；具体何时/为何缺失需在该机器核迁移史，不能断言。
- 本轮未访问正式库。正式刚晋级同一包，属于必须排查的同类风险，不直接声称已复核正式约束。
- 原始只读证据：C:/SpugHandoff/release/private/pqc-patrol-investigation-20261124/，没有远端DDL/DML、登录写入、重启或发布。
