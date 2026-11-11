# 三服实际安装后的真实页面验收

## Current Status

in_progress；三target a3121c6均已实际激活，来源与Spug仍为各自已核版本。只读页面先验收，之后仅按既有授权向测试服58提交一次原I2恢复；正式57/审查59只验证选择与确认，取消最终执行。旧验收工具绑定旧147包和旧恢复点，保留原件，新载体明确使用本次三目标选择合同。

2026-11-12 preview/r2已实际PASS：149项完整包清单、全量/增量分页筛选、FULL/I1/I2×三服9对身份确认均通过，loginPOST1/businessPOST0/pageError0。原r1因执行器未启动而HTTP502的失败保留；原执行器恢复后309旧任务保持。目标58提交前完整transition/native/API新鲜只读预检PASS35.422秒。当前仅页面选择完成，不等同真实数据恢复成功。

## 目标、里程碑与预期验证

1. 正式target overlay加载三份真实激活原件，保留原source/Spug/base/custody，核全部输入pin。
2. Playwright真实登录Spug，刷新全部包清单、核分页和全量/增量筛选，原FULL/I1/I2三点逐个选择三服并核确认身份，9对均不执行。
3. 仅测试服58以同一I2执行一次恢复；持久化原请求后放行唯一POST，任何结果未知均跟踪原编号，不重复提交。实际引擎执行原保全、归档读回、恢复与健康验证。
4. 真实页面跟踪唯一operation终态，核实际恢复数据/附件/服务及未受影响主机。现有未通过或坏旧链保持禁用，不修改历史追认。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否；安装/原件/页面/身份错误明确失败，原失败保留。
- 是否从根因和长期维护角度解决：是；新代次安装与真实页面选择、唯一写请求分别明确绑定。
- 是否存在临时补丁或绕过：否；不改产品控件或绕过产品恢复门禁，验证工具仅操作已有真实入口。

## 经验门禁

- Trigger：真实Spug登录、目录选择、覆盖确认和授权测试服恢复。
- Preflight check：新三目标loader完整安装闭包通过；同一成功I2原点/链/源恢复证据及实际包保持；只读阶段禁止一切业务写，提交阶段只允许源57/I2/目标58精确RESTORE一次。
- Blocker：安装原件漂移、点不在完整目录/未登记、任何目标不可选、确认身份错误、页面错误、已有提交或响应未知。
- Verification：真实登录1POST、只读业务0POST、3点×3服9对确认后取消；提交仅1业务POST、原operation单独跟踪、实际终态与服务/数据核验。
- Forbidden action：不重复备份/恢复、不向57或59执行覆盖、不通过接口/SQL代替页面提交、不删除坏链/失败原件、不扩大磁盘授权为数据删除授权。
- Evidence：本任务main-activated-i2-success-r1.json、三服实际激活PRIVATE原件、main-final-target-upgrade-plan.md、docs/server-access.md、docs/login-access.md、docs/release-backup-restore.md及experience-index命中恢复接口/真实入口门禁。

## BDD / TDD

- Given已成功FULL/I1/I2原链和三服已激活；When真实页面选择每个点及每台目标；Then均显示正确确认身份且未勾覆盖确认时最终按钮禁用。
- Given只读阶段或任何非精确目标/点/来源/请求键；When拦截业务POST；Then拒绝。Given明确submit阶段及原I2/测试服58，且未有持久化提交；When请求到达；Then先独占保存原请求，再允许唯一POST。
- RED→GREEN→REGRESSION证据追加execution-log.md；本地合同测试不替代真实页面验证。
