# 本次正式发布失败的根因分析

## 结论

此次故障由三处缺口串联：跨租户导入遗漏工序编号对象键的映射；导入冻结前未执行已有的业务语义校验；发布预检将实时业务检查错误地绑定到历史迁移是否需要执行，造成问题在停服、13项迁移生效后才暴露。原程序缺陷产生无效快照，发布脚本缺陷扩大为停服后的发布阻断。

## 证据基线

- 实际失败包：releaseTag `2026-11-19-15-03-12`，应用提交 `32f9d5f0fa7cf3ad8308fd7a3eeef4619bb5e197`。
- 只读源码核对：应用 r2 worktree 当前HEAD `dde521e6a9cf98762b526a9ad4daf0ae432e2ecf`；导入文件存在其他聊天正在实施的修复，因此分析旧行为使用 `git show 32f9d5f0:<path>`，而不将当前工作树修复误当旧实现。
- 维护候选基线 `85b6b5fb194ee3bdf50c7c16537aa4a38b8b6f9e`；旧预检与部署顺序使用 `git show 85b6b5f:ops/spug/release-center/intruoyi_runtime_agent.py`。本任务没有独立核对已安装运行脚本的完整字节指纹，真实失败效果由目标任务回执交叉印证。
- 正式数据事实引用原任务 `production-blocker.md` 与后续 `execution-log.md`：tenant163，5条ACTIVE路线，74个索引键，148项blocker；创建早于本次发布，13项迁移APPLIED，快照检查updatedCount=0。本任务不访问服务器或原始业务载荷。

## 直接缺陷：遗漏 JSON 对象键映射

应用基线 `MesProRouteResourceImportService.java` 第51行为目标租户分配/复用新ID，第64-65行重写JSON。第161-180行的递归实现，只根据 `JSON_REFERENCES` 映射字段的值，或映射 `id` 字段的值；它没有替换 JSON 对象的字段名。

`MesProRouteResourceTransferService.java` 第39-48行登记了 `routeProcessId -> mes_pro_route_process`，所以内部编号会变。但是 `scheduleConfigs` 使用工序ID作为对象键，外层键不会被替换。

例如原配置为 `{"11":{"routeProcessId":11}}`，目标工序11映射到111。旧代码结果是 `{"11":{"routeProcessId":111}}`，正确结果应为 `{"111":{"routeProcessId":111}}`。正式74项“旧键/新内部编号”与这一机制一致。

`git blame` 将上述代码定位到 `4493e9488004cc5aaf6dab12afee4da2b5662d95`，提交说明为 `fix(mes): preserve route resources across tenant workbook transfer`。这是代码归属证据，不代表已经确认具体导入操作人或导入文件来源。

## 为什么错误进入正式生效数据

应用基线导入方法第68行直接调用 `new MesProRouteSnapshotCanonicalizer().sha256(...)`；第86行写入资源，第92行调用 `recordActiveRegistered(..., "跨租户流程关联资源导入")`。导入要求原版本为ACTIVE并保留其状态。

同基线第120-145行的 `validateGraph` 校验资源关系及ACTIVE版本数量，没有校验改写后快照内的工序对象键。`MesProRouteControlledContentAdapter` 第25-31行将版本登记给通用受控内容服务，该接口执行状态与登记处理，不能替代MES快照业务校验。

已有 `MesProRouteSnapshotCanonicalizer.sha256` 第74-85行仅规范化JSON并计算摘要；正式业务校验是另外的 `validate` 方法。第281-291行明确能检查外层键是否属于流程节点，以及是否等于内部routeProcessId。

因此，错误JSON仍能得到匹配的SHA。SHA只能用于核对内容是否一致，不能证明内容中的业务关联成立。旧导入路径在生成摘要前没有调用该正式校验，已知规则未进入实际写入路径。

## 为什么在停服、迁移后才发现

维护基线 `intruoyi_runtime_agent.py` 第590-597行的 `snapshot_precheck`：

```python
applied = {entry['migrationId'] for entry in plan if entry['action'] == 'APPLY'}
return [run_snapshot_cli(..., 'PRECHECK')
        for item in selected if item['migrationId'] in applied]
```

只有本次计划为APPLY的相关快照迁移会触发停服前检查。如果相关迁移已经执行、计划为SKIP_ALREADY_APPLIED，新的业务快照也不检查。这混淆了“历史迁移已完成”和“当前业务数据仍有效”；导入是在迁移之后也会发生的业务动作。

同文件基线部署顺序为：第924行preflight；第939行stop_writers；第955行apply_migration_plan；第959行terminal_snapshot_readiness；第962行以后才替换候选程序。终端检查第1001-1004行不受APPLY条件限制，所以旧逻辑前面漏检、后面照常发现错误。

这一顺序与真实回执“前检通过 -> 13迁移APPLIED -> READINESS发现148项 -> 未启动候选/保持停止”吻合。终端检查发现错误后保持停止是保护动作；故障在于前置检查漏检及失败后进入难以直接续办的部分升级状态。

## 为什么原测试未拦住

基线 `MesProRouteResourceTransferServiceTest.java` 第118-125行验证普通字段、列表内引用和缺失资源；第19-25行验证嵌套值与null保留。该测试类没有“工序ID作为对象键，目标ID必须同步替换”的场景。后续新增测试已专门覆盖四类工序键配置及非法输入拒绝。

原任务已记录新增用例先失败、修复后通过；维护侧新增 `test_applied_enforcement_rechecks_live_data_without_repeating_mutation` 也记录旧实现返回空结果的预期失败。这些是目标聊天的测试证据，本任务没有另行运行测试。

测试服部署及登录/用户列表通过，不足以证明正式库5条导入路线有效。两个环境的业务数据不同，当前记录也没有显示当轮验收覆盖了这批正式导入数据的完整路径。

## 原因边界与恢复复杂度

- 已证实：旧代码映射遗漏、冻结前校验缺失、预检受APPLY条件限制；真实错误形态、导入登记与之吻合，技术原因具有很强证据支持。
- 不应归因：没有证据表明本次13项迁移制造了74个错键；记录显示它们在发布前存在，失败快照检查本身没有更新记录。
- 尚未知：具体导入人、源租户/工作簿、每条导入操作的完整历史；仅凭Git作者或记录创建时间不能归责到个人。
- 影响扩大因素：正式采用external恢复，本轮未形成可直接点击的Spug恢复检查点；数据库已迁移而旧程序停止，不能直接假设旧程序可安全重启。这解释后续为何需要正式迁移/续办合同，不是另一个数据产生原因。
- 最新目标聊天说明：未登记的旁路写入草稿已撤回，保留导入入口与实时预检修复，并转向发布包内可审计的迁移契约；本分析不把早先停止态独立写入设计当成已经执行或最终方案。

## 对应正式修复方向

导入须同步映射四类工序对象键及值，并在原快照身份校验、改写后业务校验通过后才冻结写入。每次发布必须重新检查当前目标数据，历史SQL仍按不可变台账跳过，不重放。正式既有冻结数据纠正须走明确授权、原件保留、精确范围和审计的正式迁移；任何修复结果都要与新包、新发布验收分别验证。
