# 后继选择的真实UI载体接线

## Current Status

ready_for_parent_review；51项纯合同测试与Node语法检查通过，UI源码和测试已冻结交父执行真实preview。本轮只改main_three_target_ui.cjs、对应node合同测试和本文；未浏览器/服务器/提交。父已报告三服实际激活和完整正式loader通过；这些现场结果由父持有原文，本子任务的Node测试仅证明载体合同。

## 目标、里程碑与预期验证

- 目标：载体按明确schema选择原v1或独立Successor/v1 loader；a3121c6沿用原submission，b9caa00独占固定新submission，保留原失败关联，仅测试58可单次写入。
- 里程碑：BDD→真实RED→最小接线GREEN→有限node合同回归→父审与真实UI。
- 验证：schema映射/三服单target一致commit/原submission pin与原失败ID/新ID不同/只创建一次/preview与verify零业务写入；node纯合同不代表浏览器或恢复验收。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否；仅明确两个schema，未知拒绝，不能按commit猜loader，不接受任意receipt路径。
- 是否从根因和长期维护角度解决：是；正式版本分派和固定代次提交凭据分离，原历史保持。
- 是否存在临时补丁或绕过：否；不改旧loader、不把旧失败重派、不改变产品入口或前端行为。

## 经验门禁

- Trigger：真实UI载体、后继selection、一次测试58恢复、保留旧FAILED原件。
- Preflight check：正式loader全闭包通过、三服单target且commit一致、新旧receipt固定文件名及原pin、真实preview9对且业务POST0。
- Blocker：未知schema、target缺失/重复/混合commit、原submission错pin/错失败ID、新operation复用旧ID、已存在新receipt、缺成功preview。
- Verification：先node纯合同RED/GREEN，父真实Playwright登录/选择/提交/跟踪固定新ID，API只最终校验；原receipt读取前后保持。
- Forbidden action：不浏览器/服务器，不覆盖原submission或历史preview，不新增任意receipt参数，不用mock证明真实恢复，不改变source/Spug独立版本。
- Evidence：nas-reader-target-successor-plan.md“UI验收接线”、旧main-i2-to-test58-ui-submission.json、父持有的三服正式激活原文。

## BDD（实现前）

1. Given 原TaskMainProgramTargetControlSelection/v1或新TaskMainProgramTargetControlSuccessorSelection/v1；When loader桥分派；Then 仅调用对应正式loader，未知schema首步失败；输出保留旧summary字段并增加明确schema与完整有效controllers/build绑定。
2. Given 三服各一个target；When 核summary；Then 同代targetCommit必须全a3121c6或全b9caa00，未知/缺服/重复/混代拒绝。
3. Given 新b9caa00正式选择和原失败submission；When 通过真实UI提交测试58的I2；Then 写固定新文件并附原submission pin/原operationId，新ID必须不同；原v1沿用原固定文件不变。
4. Given preview/verify、已有新receipt或已发送一次；When 任意业务POST；Then 拒绝。提交前独占wx持久化request；响应失败也只能跟踪该原新ID，不重派。
5. Given 原submission/本载体/point或selection在过程中漂移；When 提交或结束检查；Then fail closed，保留现有结果不覆盖历史。

## RED证据

固定缓存node：`node --test scripts/tests/test_main_three_target_ui_contract.cjs` -> 49项，44 PASS/5 FAIL，0 skip/cancel，97.1289ms。失败是缺targetGeneration/assertInstallationGeneration/buildSubmissionReceipt三公开纯入口（4个正例）及旧失败ID尚未拦截（1个行为反例）；尚未改实现。

父后续实际58激活失败进入new-runtime/CONTROL_PROCESS_CHANGED，原FAILED审计和错误dropin保留；先完成明确57/58续办合同，selection仍为独立Successor/v1，旧v1模块不改。父批准恢复本UI GREEN工作后实施接线。

## GREEN与有限回归

- GREEN：原49项全部通过，93.9621ms。两个明确schema映射固定loader与固定submission文件；summary核每服恰好一个target和固定完整commit，未知schema/混代拒绝。
- 追加BDD：Given 原失败submission和正式后继summary；When 浏览器创建前检查来源；Then 不需要构造任何假新request即可验证原pin/原失败ID。Given Python桥程序；When 固定Python子进程解析；Then AST可编译且保留明确schema拒绝。先增加两个测试取得RED：缺assertPreviousSubmission入口和未导出桥程序；原49项保持通过，再最小提取公开纯来源校验并导出原桥程序。
- REGRESSION：`node --test --test-reporter=dot scripts/tests/test_main_three_target_ui_contract.cjs` -> 51 PASS，exit 0；其中Python子进程仅执行AST解析，不导入假loader、不声称正式加载或页面通过。
- `node --check doc/tasks/20261106-spug-prod-incremental-to-two-targets/main_three_target_ui.cjs` -> exit 0。
- 公开摘要继续保留MainThreeTargetInstallationSummary/v1及原controllers字段，增加selectionSchemaVersion、predecessorSelectionPin、完整effectiveControllersByHost和controllerBuildBindings；正式桥按selection的明确schema导入对应loader，并核原Records.selectionPin一致。
- 新提交文件只固定为main-i2-to-test58-ui-submission-b9caa00.json，附原submission pin及原失败operationId；新ID必须不同。业务POST前wx独占持久化，preview/verify仍零业务POST；旧receipt与历史preview原件不变。

## 源码冻结与验收边界

- main_three_target_ui.cjs：24495 bytes，SHA256 2f176555c6005d2ba635983ce86484cfaaeacd4b088ff03a2928c62372c7fc3f。
- test_main_three_target_ui_contract.cjs：9259 bytes，SHA256 73978c1a1b1ae3c8440b942a80b89789f2cd2a74142ab703d50ee53b562cc81d。
- 父报告正式后继selection main-program-targets-activated-b9caa00-r1-v1.json完整加载PASS，103.313s、1689 input pins。真实桥/登录/页面矩阵由父下一步执行，子任务未用本地合同通过替代实际E2E。
