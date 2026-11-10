# 来源与目标准入读取预算修复

## Current Status

ready_for_parent_verification。源码已冻结，本机必要回归通过；未安装、真实页面仍待父验证。父任务已事前写 selection-read-budget-plan.md 并按 Subagent-Driven Development 指派本代理；阶段 B 六个源码/测试文件已冻结。本轮只改 adapter、app.js 及定向测试，不安装、不操作服务器、不构建、不提交。

## 目标与里程碑

1. RED：真实 localhost HTTP 证明选中来源仍查询无关目录及预算缺口；JS VM 执行实际 app.js 证明期限与错误状态。
2. GREEN：单来源明确选择、来源20秒/目标25秒/整次50秒的共享预算，仅 GET /selections 页面60秒。
3. REGRESSION：原目录路由、源/目标身份、历史指纹、自动增量、错误与页面状态的受影响测试；固定实际输入/日志/退出。

## BDD

- Given 目标登记多个来源、选择 A，When 刷新 A 到 T，Then 只读取 A 目录和 T 新鲜准入；B 离线不影响 A，T 离线仍失败。
- Given 未选来源，When 读取完整目录，Then 在有限共享预算内查询所有登记来源，不截断为部分成功。
- Given 来源拒绝点 P、目标副本包含 P，When 合并准入，Then P 仍不可用，应用/引擎身份错配和重复/缺失行拒绝。
- Given 实际 HTTP headers/body 持续缓慢到达，When 期限耗尽，Then BRIDGE_TIMEOUT、关闭本连接、不重试；多个来源共享剩余预算。
- Given socket.timeout 是 Python3.9 的独立 OSError 子类或 URLError.reason，When 分类，Then BRIDGE_TIMEOUT，不按含秘密文本猜原因。
- Given 页面 GET /selections，When 等候响应与正文，Then 仅该读路由60秒；普通请求20秒、自动计划60秒不变；错误仍显示实际码、旧准入清空、提交禁用。

## 设计与边界

来源单次20秒、目标单次25秒，selections()共享50秒；页面只 GET /selections 60秒。未选来源继续全量，超预算失败而不部分返回。为避免urllib单次socket timeout被慢字节重置，仅目录读使用固定origin http.client连接、同socket截止watchdog、65536正文上限与原JSON/HTTP错误合同。操作派发、查询、incremental_plan、fingerprint及凭据来源不改。操作系统DNS resolver仍非本模块可中断，不宣称控制其阻塞时长；已连接socket全过程及来源间共享期限均验证。

原TASK/test_archived_source_catalogue_routing.py中一条旧断言要求明确选来源时返回全部三来源，与本次修复目标冲突；将只更新这条的预期源列表/点/目标索引，其余断言保留。新测试先RED，不把mock成功或本机合同当真实安装/恢复通过。

## 经验门禁

- Trigger：selected-target重复三次目录且目标准入实际11.251秒超过旧10秒。
- Preflight check：已读experience-index、release-agent-checklist的包清单期限/自动增量/运行依赖闭包门禁与迁移后powershell-memory；检查实际函数和原测试。
- Blocker：来源/目标绑定错、未知错误吞掉、无限期限、旧准入复用或新资源闭包缺件。
- Verification：实际本机HTTP/JS VM RED→GREEN→受影响回归；父任务负责新代安装及真实UI。
- Forbidden action：不改旧失败/七配置/控制代次，不单纯加全局超时，不重试，不绕过准入，不操作生产。
- Evidence：本日志、父实际时序原件及独占PRIVATE测试日志/输入pins。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，消除无关来源依赖并明确完整读取预算。
- 是否存在临时补丁或绕过：否。

## TDD 记录

- 父任务明确批准 20/25/50/60 秒正式预算；不使用诊断120秒等待。
- 首次 RED：真实本机HTTP 15 FAIL/1 PASS，UI 3 FAIL/66 PASS；失败原件保留。
- 第一轮桥接 GREEN：57 PASS。UI新测试把abort放在response.json监听器安装前，实际悬挂；确认本代理node runner63668/父59160、child20216归属后仅终止该测试child，原exit1记录保留。测试改为等待正文已进入的显式信号，不修改产品期限，并为后续node加15秒用例上限。
- 第二批 RED：同一来源连接返回多来源的新增3例失败（其中缺失/重复本已被原merge拒绝，仅错误阶段不同）；保留原merge拒绝码，不人为要求新码。UI明确错误丢失及未知URL泄漏的3例真实失败。
- 第二轮 GREEN：Python60 PASS、UI70 PASS。
- REGRESSION：最终Python113 PASS/0skip/exit0/56.00s；UI92 PASS/0skip/exit0/1.355s。两命令前后六修改源码/测试raw pins相同，原session88733实际终态已收。

### 旧测试精确调整

1. 原TASK目录23例仅一条选定source测试改为单来源、单次新目录请求；对应恢复点及目标索引从三行中的1改为唯一行0。原无映射、绑定、凭据、来源/目标、历史指纹和拒绝断言保持。
2. test_smallapp_cross_route.py两条call接缝增加selection_deadline=ANY，原endpoint/query断言保持；新增真实HTTP分别观察调用剩余预算19..20与24..25秒，未以ANY作为预算验证。
3. 原UI timer表加入GET selections60秒/相似路径与POST仍20秒；新增实际app.js的正文abort、服务器安全错误与未知异常脱敏，旧状态/原件/提交锁断言不改。

### 实现范围与实际限制

仅adapter/app.js两个产品文件变化；实际新增传输只由_local_selections通过selection_deadline进入。普通call/submit/query/incremental_plan无此参数，保留10/40秒原合同；for_request/历史fingerprint和执行入口未变。固定origin、原认证、无重定向/代理/重试、65536正文上限、原安全HTTP码/JSON校验保持。目标集合仍先核完整登记，明确来源只读取该源目录，未知来源不扩权。多个来源的HTTP共享50秒，任何中途超时整次失败。

新20例使用真实loopback ThreadingHTTPServer和原HttpBridge，不执行备份恢复、不模拟生产成功。socket.timeout在本机3.11+已与TimeoutError同类型，测试另用Python3.9同继承关系的独立OSError类型复现分支；实际Python3.9验证由父完成。产品AST通过feature_version=(3,9)，只新增stdlib io/threading/time；无新增第三方运行依赖。OS DNS不能由本模块中断，不能把连前resolver等待称作已强制整体deadline；一旦连接成功，同一socket watchdog限制headers/body，源码明确该边界。

## 父任务复核与调用

现有生产API不变：`HttpBridge(binding_path, source_ref, target_ref).selections()`。无需添加配置字段。可在父隔离载体导入adapter后直接核module-level SELECTION_SOURCE_SECONDS=20、SELECTION_TARGET_SECONDS=25、SELECTION_TOTAL_SECONDS=50，以及原生socket.timeout和URLError(socket.timeout)均返回BRIDGE_TIMEOUT。新测试需要现有PRIVATE/test-dependencies中的pytest；产品模块及原TASK23路由unittest只用stdlib（无需为实际3.9额外安装依赖）。

正式复核命令使用缓存Python -X utf8 -B -m pytest，完整argv见下方两回归receipt；UI node --test --test-timeout=15000。父负责真实容器3.9、已提交干净资源构建/完整14依赖、正式安装身份和真实页面逐点三目标。当前未提交、未构建、未安装、未执行B现场验证，不声称任务整体完成。

## 独占原件

所有路径以下相对PRIVATE，receipt与log均排他创建，无覆盖RED。

|原件|实际退出|bytes|SHA256|
|---|---:|---:|---|

|selection-budget-red-python-r1.log|1|8912|2c24c5b6c7e5759de5c1f8bca6a0c980d9a269d103298b129a2fbba1756b7d8e|
|selection-budget-red-ui-r1.log|1|9108|2ae077c63389f62be3083782efd2a01db39d10cb998161f0751af851c79036b9|
|selection-budget-green-python-r1.log|0|102|f461f61785b2a1b4de90aefdbbea002c776211b07495b561a6af0e2d933930f0|
|selection-budget-green-ui-r1.log|1|432|e55d678dc0f70664baf06dffa641d24e6937688d94cc9a4e032fb18f210b0f9f|
|selection-budget-red-source-scope-r2.log|1|3296|821628d5dcf8dfc9b3ed1e46a3b1eb662abca130b58a9adea1d2287f734e40c1|
|selection-budget-red-errors-ui-r2.log|1|9896|a724fda90316a4ceaeff60a2932d31349b5f55b7c1c98dde5d6f1f0eb2afd5b1|
|selection-budget-green-python-r2.log|0|102|004c1d0a0b43e04f8a68751a3d6a424cb834b8617af28c1847381024f432c564|
|selection-budget-green-ui-r2.log|0|7142|727a8204f1efc291bd29a13d73a326a438161fb340de6950c6fe6d6f49eb7af7|
|selection-budget-regression-python-r1.log|0|184|275d70a7c4f2dfa100719d2851b541603b0f7ae2a7b00d09fc024daa73bb125e|
|selection-budget-regression-ui-r1.log|0|9016|edbfd9db258cbd1a375cdb52b01e2a3ac3c48fdfc49b3733f8b2c406fe98b34c|

### 最终命令及输入闭包

- `selection-budget-regression-python-r1.private.json`：2558 B / SHA256 `05bb71d2ef4c9a36dc70c139a5682f11997f7e2af444916c92f5516d18133156`；actualExitCode=0，sourceUnchanged=True。

```text
C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -X utf8 -B -m pytest -q --tb=short -p no:cacheprovider --rootdir C:\Users\D01021\.codex\worktrees\spug-restore-targets\Maintance --confcutdir C:\Users\D01021\.codex\worktrees\spug-restore-targets\Maintance ops/spug/test_smallapp_selection_budget.py ops/spug/test_smallapp_cross_route.py ops/spug/test_smallapp_bridge_errors.py ops/spug/test_smallapp_safety.py ops/spug/test_smallapp_source_rotation.py ops/spug/test_smallapp_display_context.py ops/spug/test_automatic_incremental_entry.py ops/spug/test_automatic_incremental_proxy.py ops/spug/test_automatic_incremental_http.py doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_archived_source_catalogue_routing.py
```

- `selection-budget-regression-ui-r1.private.json`：1978 B / SHA256 `3515f8dc761648cd4f8aad3b97d76344a0d8ea7098e1dae268598d9c10a15cf6`；actualExitCode=0，sourceUnchanged=True。

```text
node --test --test-timeout=15000 ops/spug/smallapp_ui_safety.test.cjs ops/spug/smallapp_restore_result.test.cjs ops/spug/smallapp-ui/package-catalog.test.cjs ops/spug/smallapp-ui/package-catalog-dialog.test.cjs ops/spug/smallapp-ui/embedded.test.cjs
```

### 冻结文件

|文件|bytes|SHA256|
|---|---:|---|
|ops/spug/smallapp_adapter.py|37158|09e6798a00ec88459682a2f1def7042727ed60ae1c19cbd86a20afab23563858|
|ops/spug/smallapp-ui/app.js|32015|c24ef715767f96dfe52f6135d72564f5ec448531e8f4c89222ad30d57da9ae7f|
|ops/spug/test_smallapp_selection_budget.py|10694|591af193a838f676bfe0616cc49161db76b54a9c1668e3c00619cf04e17ca83e|
|ops/spug/smallapp_ui_safety.test.cjs|66012|1f49458408c81b18299f4624bdab9cca9b277496a33fddb7d2e68a1ccf2e532f|
|ops/spug/test_smallapp_cross_route.py|13641|22d23baf7340ceed1771e5ad9bcce4c00bbbacc1ee469fb1b3261035576355a2|
|doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_archived_source_catalogue_routing.py|19711|1e9b80ca7a4a92df3d5ed59d8e051cccd10575272e78e031f0c61d370d5ba5c6|

## 父批准的 HTTP 已证状态补充与最终重冻

初次冻结后静态审查发现新严格读路径遇到HTTP503可选正文截断会先抛BRIDGE_RESPONSE_INCOMPLETE，违背旧call在HTTPError可选正文读取失败时保留已证状态。父明确批准新增唯一真实HTTP503截断用例、最小修复与新测试+bridge-errors受影响回归；父r1容器候选已独占固定，不覆盖。

BDD：Given真实HTTP503且Content-Length=100但只发送部分JSON后关闭，When读取该错误正文，Then保留BRIDGE_HTTP_503；整体deadline耗尽仍BRIDGE_TIMEOUT，不回显原异常。

RED：新例实际1 FAIL/20 deselected/exit1，原生响应触发BRIDGE_RESPONSE_INCOMPLETE。
GREEN/REGRESSION：21新HTTP/预算用例+6旧bridge-errors共27 PASS/0skip/exit0/2.98s，3输入前后SHA保持。UI和普通调用逻辑未改，不重复原92UI；此前113Python的原记录保持，不宣称是新SHA的单次完整回归。仅read_selection optional body异常/短读转为HTTPError，再使用原call安全HTTP错误分支。Python3.9 AST再次PASS，实际3.9由父执行。

以下最终pins取代上表adapter和新test的第一冻结pins，其余四个源/测试保持。

- selection-budget-red-http-status-r3.log：1650 B / SHA256 `02593f5cec2474e8219d0ddb9abb51c91f8a97211eba11557c3a88f1939b8c32`，actualExitCode=1。同stem.private.json保留原argv/退出。
- selection-budget-green-http-status-r3.log：101 B / SHA256 `fa50677584fca5d00b263d4cacad7fdcae85c854f6de6a8a5365431e01d06460`，actualExitCode=0。同stem.private.json保留原argv/退出。
- 最终 `smallapp_adapter.py`：37636 B / SHA256 `3240e06390ba005ebf4319bdc97c1e82e3dcd4a7efa3fb58f97c689c09d6874c`。
- 最终 `test_smallapp_selection_budget.py`：11343 B / SHA256 `173eb8dffbf6d8a5db432474d8c0ab6c3932bd946e813b22154607d3753710c8`。

## 父独立最终复核

- REGRESSION：最终六文件字节上的原 session75977 实际 exit0；Python 114 PASS/0skip，UI 92 PASS/0skip，全部输入前后保持。完整命令和原日志校验值见 selection-budget-parent-regression-r1.json。没有将初次冻结的113项结果挪用到最终实现。
- 原生运行时：原 session22236 实际 exit0，实际 Python3.9.23 上新预算/真实HTTP、旧bridge-errors和跨来源共39 PASS/0skip；明确覆盖该运行时 socket.timeout 与 TimeoutError 并非同类的分类合同。见 selection-budget-py39-parent-r2.json。首个r1因测试依赖版本不兼容失败原件保留；只在任务私密测试目录准备兼容依赖，没有修改容器已安装依赖或运行资源。
- 真实候选只读：原 session78683 实际 exit0；来源57读取7.295秒、目标58新鲜准入11.606秒，总19.143秒，33应用中1项validated。见 spug-selection-candidate-r1.json。只发生两次selections读取，无配置写入、备份或恢复派发。
- 当前结论：产品实现和受影响回归通过，可独立提交并进入已提交资源构建；候选未安装，以上不代表现网UI或恢复验收。
- Git提交前原始字节全等检查先拒绝：adapter及两旧测试在工作区是CRLF，Git index按已有规则保存LF。随后逐六文件严格证明仅CRLF转LF、原测试输入pin保持，selection-budget-git-normalization-r1.json记录两侧原始bytes/SHA，不把不同SHA说成相同。后续正式构建仍必须采用已提交内容并独立验证，不沿用工作区原始SHA冒充构建产物。
