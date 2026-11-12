# MAIN completed journal 连续租约

## Current Status

ready_for_parent_review；新19项、原MAIN session20项、capture12项、配置13项、FD10项全部通过；有限94项为92 PASS/2 FAIL，剩余两项是旧Archive identity测试对新增资源合同缺targetConfigRef的fixture问题，已报父处理，子任务不改父资源接线或该旧测试。原完整材料与全部真实dump时序用例在原60秒work/30秒data预算内通过。产品/新测试已冻结，只更新本文；不操作服务器、不提交，不能在相邻缺口未处理前称全部回归通过。

## 目标、里程碑与预期验证

- 目标：MAIN采集session.check不再反复全文读取全部completed journal；在原60秒work/30秒data预算内完成完整材料与真实dump退出guard用例。
- 里程碑：只读profile确认→父审持续保护设计→独立内核测试RED→最小实现GREEN→原实际采集有限回归→父审。
- 验证：Linux真实inotify/O_PATH和实际文件，无服务器；completed改后恢复、同名替换、权限/硬链接/祖先变化均拒绝；active intent仍每次全文SHA，目录精确成员集每次核验。每轮使用固定输入快照，完整原时限不变。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否；无计时缓存、不修改期限、不跳内容校验。连续租约失败永久latch；实际终态和failure证据仍可写，但不得再授权任何命令。
- 是否从根因和长期维护角度解决：是；把只追加的completed原件与唯一合法原子替换的active intent分层，使用既有ArchivePathGuard的内核租约保持首次完整SHA的有效性。
- 是否存在临时补丁或绕过：否；不豁免内核事件、不清空旧队列、不把失败快照重基线成成功。

## 经验门禁

- Trigger：60秒MAIN采集预算内完整材料/真实dump退出guard用例超时。
- Preflight check：修复前不可变快照同例失败；原profile为138 guard/1690 session.check/31216 actual_pin，actual_pin累计24.811s。父当前资源/续办测试快照163 PASS后允许修改，本轮另冻输入。
- Blocker：不能证明租约连续、未知成员/文件/目录/权限变化、内核事件溢出或FD预算不足、实际终态写回受失效admission阻断时，拒绝进入安装。
- Verification：先真实Linux内核小集合RED/GREEN，再原60秒/30秒采集session与实际Popen退出用例；记录快照pin、命令、结果和时间，不用纯unit冒充现场恢复。
- Forbidden action：不增加预算、不引入TTL/mtime缓存、不吞inotify事件、不改旧失败/凭据/保护、不把父并发文件纳入子任务提交。
- Evidence：main-capture-private-credential-plan.md、PRIVATE/capture-regression-baseline-profile-r1/stdout.log、独立本轮XML和输入清单。

## 正式租约与交接合同

1. session保留唯一completed journal租约。每份新原件发布后，先保留其原pin与native.original_pins，再建立覆盖新全集的ArchivePathGuard；新增原件在watch建立后实际全文SHA匹配原pin，旧/新租约均check通过后才交换。旧租约在新租约watch完整建立之前不关闭；旧任意queued变化会拒绝交接。
2. 旧guard仅跟踪旧原件名字及其祖先。合法新文件名尚不属于旧tracked names，因此新原件append不会使旧原件保护失效；不调整或清空旧事件。新guard建立后新增原件纳入tracked names。所有check仍验证journal目录精确成员集合，未知名字不能借append被接受。
3. 活动intent保留现有actual_pin全文读取，不使用lease替代；既有context/token/Popen所有权与唯一finished原子替换不变。finished首先写实际终态、完成context.finish_invocation并清除活动状态，再将terminal原件作为首次immutable completed纳入租约。不会为合法terminal替换豁免ArchivePathGuard事件。
4. 租约对象保留独立的深拷贝pin-map，每个check与session._pins逐值核对，防止内存pin重写。目录路径、0700/owner、完整成员集和shared budget的现有检查保留。
5. 任何租约建立/读回/连续交接异常永久latch；异常继续抛出，后续所有admission check拒绝。故障后的新failure/实际terminal仍只作证据记录，不刷新故障为成功、不产生执行资格。close关闭所有本租约FD并可重复调用，不释放业务保护。

## BDD（实现前）

1. Given 已全文核验的completed journal；When 大量重复check且文件未变；Then 不再读取这些原件SHA，仍持续读取内核事件及检查目录/owner/pin-map。
2. Given 原件改后复原、同字节重写、同名替换、chmod、硬链接或祖先变化；When 下一check或append交接；Then 拒绝且永久故障，不能由新快照抹除变化。
3. Given 合法append；When 新guard建立期间旧原件被修改；Then 旧guard仍拒绝；正常append保持所有旧原件连续保护。
4. Given 未登记的新成员；When check；Then 原精确成员集拒绝；不能用合法append消除未知成员。
5. Given 活动intent内容变化；When session.check；Then 仍由每次actual_pin拒绝。Given 实际子进程已退出且guard失效；When finished；Then 原实际终态仍写回，故障保留且无后续命令资格。
6. Given 原完整材料与真实dump退出guard用例；When 同一60秒work/30秒data预算运行；Then MATERIAL_COMPLETE、实际退出可验证，未释放原写屏障；不用单元计数代替完整回归。
7. Given 真实MAIN context中准备因非法对象权限或已记录资源admission后的错误失败；When prepare抛错且尚未离开外层context；Then 所有新journal lease FD已确定释放，原FAILED/failure pin保留，不依赖GC或进程退出，不释放业务保护。

## 第一轮证据与定点补充

- RED：16 FAIL/0 error/skip，0.465s，全部MISSING_CAPTURE_JOURNAL_CONTINUOUS_LEASE；source SHA92690377757b804ab0d76b701895e4c192a339578091b5e9bf2351efb5b2069d，385文件，PRIVATE/capture-journal-lease-red-r1。
- GREEN：16 PASS，0.484s，capture-journal-lease-green-r1；只在正式内核租约下减少重复全文读取，不改原数据/工作期限。
- 第一轮扩大回归75 PASS/10 FAIL/6 ERROR。4个MAIN失败揭示本轮接线顺序：_finish_export会真实重入check，terminal必须先纳入pins/lease再进入该保护复核；新增精确RED为1 FAIL/16 PASS，0.791s，latch-red-r1。调整顺序后17 PASS，0.466s，latch-green-r1。
- 同轮archive回归载体漏正式baseline tgz，导致11个缺依赖失败/错误；FD低限用例另失败，须在完整输入与生命周期清理完成后重验。原失败全部保留，不把载体错误称业务RED或回归通过。
- 父审要求准备异常确定关闭新租约：已有外层context.close路径，但不能依赖调用方稍后退出context。上述BDD7先补真实权限/资源错误FD计数RED，再最小增加本地关闭；禁止停止/启动业务或释放写保护。

## 生命周期RED / GREEN

- `python -B -X utf8 <PRIVATE>/run-capture-journal-lease-linux.py lifecycle-red-r1`：19项中17 PASS/2 FAIL，0 error/skip；对象凭据非法权限失败后FD为86而原baseline74，资源admission已写记录后失败为121而baseline110。测试在真实MAIN context尚未退出时计数，不靠GC。
- 最小实现仅在_prepare异常分支`try: result._fail(error); finally: result.close()`；close只关本地租约FD，保留FAILED/failure.json和所有业务写保护，不进行恢复/重派。
- 同载体lifecycle-green-r1：19 PASS/0 error/skip，pytest1.157s，native0；两条异常路径在外层context退出前即回到原FD基线，重复close也保持。source SHA99beb660100dc6d91496746a33f0448ad9bd71a670875574f4c3a9940b03f190。

## 完整固定输入回归与边界

命令：`python -B -X utf8 <PRIVATE>/run-capture-journal-lease-linux.py regression-r2`。使用既有固定Python3.12容器image SHA14a4933e6cef421424f7a66d89a3f4eafcbd0d90e0a822251f298e05132dc735、原12份wheel pins、network none/read-only、1GiB/2CPU/128进程和本任务独占容器；不访问服务器。

- 原低FD预算文件先在干净进程顺序执行；既有restore_case/native_type fixture直接return h且不teardown其native.archive_guard，会在一进程累积FD，使该低限测试在建立guard前即EMFILE。没有调整RLIMIT阈值、64工作槽位或生产guard。
- 快照387文件，source SHA256 d2fa63a25b3094f54fecb282f7ce36cad93b238cbe7ceb03646ce26508eeb6ff，包含正式baseline tgz；PRIVATE/capture-journal-lease-regression-r2保留manifest/source.tar/runner.py/intent/stdout/stderr/XML/result。
- 结果：94节点，92 PASS/2 FAIL/0 ERROR/SKIP，pytest102.532s，载体wall113.750s；snapshotSourceUnchanged=true、localInputsUnchanged=true、containerRemoved=true，remoteActions=0、actualBusinessRestore=false。
- 分组：新journal19 PASS、原session20 PASS、capture12 PASS、配置13 PASS、FD10 PASS；Archive identity18 PASS/2 FAIL。
- 两项精确缺口：test_archive_identity_lease.py::test_minimal_data_leases_before_hash_and_closes_constructor_failure[first_hash/target_identity]，旧AST fixture仅传request={operationId:'unit-lease'}，新增资源接线读取targetConfigRef时KeyError，尚未到该测试的lease路径。父已收到完整失败；本子任务未修改该旧fixture或资源模块，不用跳过掩盖。

关键原例XML总耗时（不是放宽期限）：

| 用例 | 结果 | 秒 |
| --- | --- | ---: |
| MAIN实际完整材料且保留原屏障 | PASS | 12.619 |
| 实际dump在finite guard内退出、不抢drain reap | PASS | 13.209 |
| pending token outside-guard拒绝 | PASS | 12.552 |
| pending token reaped-tail拒绝 | PASS | 12.600 |
| 非法对象权限准备失败、本地FD即时释放 | PASS | 0.296 |
| admission记录后准备失败、本地FD即时释放 | PASS | 0.176 |

完整session继续实际Popen/gzip/schema/数据/物理对象/Redis材料与原保护实现，仅外部SQL/Docker/S3/Redis响应为原协议unit；不是业务服务器恢复验收。workSeconds=60/dataSeconds=30原值保持，测试文件未改。

## 最终实现与冻结

- recovery_target_capture.py：32933 bytes，SHA256 9d96a3340946b4f39ec341d810f3638edf0b5067e61256b668e521f74018b718。
- test_recovery_capture_journal_lease.py：11215 bytes，SHA256 6119fcddda017d47970cc0b1535f5424211da49da9d6756c738c006fdcff6ea2。
- 只新增私有_CaptureJournalLease，复用原ArchivePathGuard；无需打包依赖增补。每份completed新原件在watch后全文核pin，重叠换租约；后续check核内核事件和独立pin-map。1000次无变化check没有重复全文读completed，active每次全文读仍保留。
- finished顺序明确为真实终态写回→context.finish→clear active→retain pin并建立租约→原_finish_export保护复核→原guard。失效租约latch不阻止实际终态/failure证据写入，后续admission全部拒绝。
- 交父审后统一精确提交与clean构建/official producer；本子任务没有提交、服务器写入或业务恢复。
