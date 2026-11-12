# MAIN准备失败与采集实现验证

## Current Status

ready_for_closeout（本地实现验证完成）；本文件只说明本轮产品实现。安装、真实测试服恢复、主线融合及构建worktree清理由父任务继续，整体任务未完成。没有发起新的覆盖恢复。

## 用户目标与范围

继续Spug自动增量备份、完整目录及三服目标恢复。用户已要求容量按实际观察，不因178 GiB预测阻断。当前三服OBSERVE_ONLY保持；本次修复对象只读凭据权限合同、无写入准备失败的正式续办及采集重复读取成本。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。S3对象凭据允许0400/0600，其他秘密仍0600；原件、保护和实际子进程失败拒绝保持。
- 是否从根因和长期维护角度解决：是。沿用不可变配置、完整程序历史验证、宿主锁与正式append-only clearance；以连续内核租约替代对同一已完成原件的重复全文读取。
- 是否存在临时补丁或绕过：否。未修改历史配置、结果或pin，未手工删除预约，未延长原60秒/30秒期限。

## 里程碑与验收

1. PASS：对象凭据权限正反向真实Linux10项；相邻session全20项已通过。
2. PASS：准备失败与原历史合同163项，0失败/跳过。真实原历史55原件/23调用只读验证满足新条件，但尚未执行正式release/authorize。
3. PASS：连续journal租约19项、原session20、capture12、配置13、FD10项。完整材料12.619秒、真实dump guard退出13.209秒，原期限保持。
4. PASS：旧identity fixture两项缺targetConfigRef先复现2 FAIL；修为实际modules_from、合法dataLimits、targetConfigRef后完整identity20 PASS，0失败/跳过。没有改产品或降低断言。
5. 待父任务：已提交专用clean构建、官方包生产者完整用例、正式后继安装、旧失败正式续办、新UI恢复与数据/页面验收。

## BDD与TDD证据

- Given冻结S3凭据0400或0600 / When实际MAIN准备 / Then PREPARED且无停写动作；非法权限及MySQL/Redis0400拒绝。见main-capture-private-credential-plan.md。
- Given完整验证的PREPARATION失败、无mutation/unknown/generation、保护未安装、原调用全终态成功 / When正式release与clearance消费 / Then仅释放本operation预约且原失败保持；不安全阶段/调用/保护/原件/其它预约拒绝。
- RED preparation-no-mutation-red-r1：11 PASS/1预期FAIL。消费端独立RED6 FAIL后GREEN/REGRESSION preparation-clearance-green-r1：163 PASS/0skip/native0，输入不变/容器移除，快照23e1de4f4b831cd95e2f52de77d1a4acd496dbccdf7a998014ab09f7ce860db6。
- Given completed原件 / When重复检查及append交接 / Then内核事件/精确pin-map连续有效；活动intent每次全文核验，变化永久拒绝，失败仍保留实际终态。完整RED/GREEN及FD证据见capture-journal-lease-tdd.md。
- 原扩大采集94项为92 PASS/2旧fixture失败，不把该轮改写为通过。后续identity-fixture-red-r1：2 FAIL（KeyError targetConfigRef），snapshot d52749615a6b3e12cd33eca9a075559ec0ae3e37143d97819ce595cb3dc0cc4e；identity-fixture-green-r1：完整20 PASS/0skip/native0，测试4.513秒，输入不变/容器移除，snapshot a5fe2a8767bde67a1f5c867785d0ade136bf66d80beb3f49f9ff505358dd1a19。

## 经验门禁

- Trigger：MAIN准备失败与组件升级。Preflight check：原进程结束、完整原件/目标/宿主预约、原服务与保护阶段、已提交clean输入。Blocker：mutation/unknown、已安装保护、原件漂移或未验证包。Verification：真实Linux合同及后续真实UI。Forbidden action：改旧失败、删active绕过、重发旧operation、冒充恢复成功。Evidence：上述独立报告和父execution-log.md。
- Trigger：Windows写文件与提交。Preflight check：UTF-8读回、精确文件暂存、无敏感日志。Blocker：外部改动、编码或测试失败。Verification：diff --check与staged清单。Forbidden action：广泛暂存或提交私密材料。Evidence：本次实现提交。
