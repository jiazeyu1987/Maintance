# 保全来源有限分页 / 单点 metadata BDD 与 TDD

## Current Status

ready_for_closeout（本有限本机小步）。父已审consumer22642与A2合同4b2605，批准本步。已保存原字节、完成真实RED→最小GREEN→限定旧合同回归；34新+115旧本机全部PASS，原失败日志保留。源与新test冻结待父审；父统一Linux实际包验证、提交/收口尚未完成，整体任务不判完成。上一publisher小步28新+87旧本机证据保持，本轮不改其记录。

## 目标、里程碑与预期验证

1. 固定22642源原件，新增独立pagination真实文件测试；缺`list_preservation_page/select_preservation_point`实际RED。
2. 按A2 section3实现小hold索引、有限页/单点metadata、精确cursor/snapshot与原目录身份；保持单请求唯一raw64MiB及nested A1同meter。
3. 新有限BDD GREEN、原v1/A1/publisher有限回归、前后pins冻结；不把metadata投影视为source admission或业务恢复。

范围仅consumer、新pagination test、本专属log。旧v1/A1/publisher测试字节不改；不改controller/UI/files/HTTP/部署，v1 resolve仍原枚举，不实现PreservationRestoreOwner。Docker/SSH/HTTP/SQL/构建/提交HOLD。

## 经验门禁

- Trigger：小目录扫描/慢载荷。Preflight check：只读受信hold目录与pin；索引每doc<=64KiB、<=2maxPoints、共同raw<=64MiB；仅读本页/单点大metadata，payload从不打开。Blocker：超限/错schema/错路径/未知身份/typed变动。Verification：真实>64MiB多row元数据、实际open记录、共同meter及原件finish；Forbidden action：不通过分页重置嵌套A1预算、不用metadata当完整readback成功。Evidence：本日志及PRIVATE原始pytest记录。
- Trigger：cursor续页/并发目录变化。Preflight check：真实目录stat身份、完整小索引pins、精确4096B cursor、固定source/repository/snapshot/after。Blocker：原件/目录增删/身份/快照变化；Verification：真实新增/删除/同bytes替换/未读point变更拒绝。Forbidden action：不自动重启cursor、不把typed错误当自然末页、不扫描全部大point以冒充全局payload快照。Evidence：独立真实文件BDD。
- Trigger：Windows有限验证/并行父输入。Preflight check：PRIVATE短唯一basetemp，先保存22642原字节与SHA；A1和旧测试固定前后pin。Blocker：Windows路径载体失败/输入漂移/需远程。Verification：实际RED→GREEN→必要旧合同回归，原失败保留。Forbidden action：不改旧fixture迎合本轮，不Docker/SSH/HTTP/SQL/构建/提交或扫脏workspace打包。Evidence：各独占日志与snapshot。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；只有精确共同metadata剩余预算不足允许已有完整row结束页，typed篡改/读错仍原错；单row装不下明确失败。
- 是否从根因和长期维护角度解决：是；复用原`_row`/publisher/A1 strict算法，独立小索引定位，不改旧出版物或原hash。
- 是否存在临时补丁或绕过：否；明确source/target/clear权限全False，未实现resolver仍unsupported，不改v1 enumeration或现产品入口。

## 事前 Given / When / Then

- Given多个真实大point/manifest合计>64MiB且每row有限；When默认limit1/续页/另页ref单选；Then只开本页或所选row大metadata、无payload、完整有序遍历、每请求raw<=64MiB；单选四权限False。
- Givenpending/empty仓库；When页或选择；Then小索引身份准确、pending后三pin/ref null、空completeTrue、pending不能选择。
- Givencursor字段/schema/pin/digest/after/limit类型或边界错误；When页；Then精确CURSOR_INVALID或CATALOGUE_CHANGED_RESTART，不按offset/first猜测，不自动续新快照。
- Givenhold单件>64KiB、目录>2maxPoints、超intent数/重复point/ref/索引总budget；When建小索引；Then读前有界拒绝，零大point读取，不把坏entry略过。
- Given页后hold新增/删除/换同bytes文件/目录身份变或policy pin改变；When续页/单选；Thenrestart。Given未读point变但hold未动；Thensnapshot只承诺索引，轮到该row实际PIN_CHANGED，不以全读所有point补诺。
- Given本页一row已完成而下row共同metadata预算不够；Whenlimit>1；Then可结束于最后完整row并给精确nextCursor；首row超限明确失败；任何typed pin/role错误不得当容量结束。
- GivenREQUEST_DERIVED普通历史；Whenpage/selection；Then真实A1三原件和共同raw闭合，原v1/A1/publisher回归保持；不stub validator PASS，不新增source admission。

精确schema/字段/限额/身份算法沿用已父审A2 section3，不引入新配置或普通JSONpatch。以上场景在测试/实现之前固定；下文记录真实阶段执行。

## 实际事前证据

22642原字节已独占保存PRIVATE/preservation-source-pre-pagination-22642-r1.py，29560B/SHA22642f6ebef75bf345dfe639693aa980c54cd73d7140d36a3e668ad732bf5aa7，与产品原文件一致。父纠正共同文档真实路径为C:/Users/D01021/Documents/ChatGPT/IntRuoyi/docs；已按该路径读取powershell-memory及release-backup-restore适用规则，不以E:缺失跳gate，不读login秘密。默认禁止远端/共享存储写、元数据不是完整读回/恢复准入、UTF-8/有界执行/原失败保留门禁适用。

RED：固定Python `-X utf8 -m pytest -q -p no:cacheprovider scripts/tests/test_recovery_preservation_source_pagination.py --basetemp=PRIVATE/ppred1 --junitxml=PRIVATE/preservation-pagination-red-r1.junit.xml`，PYTHONPATH=PRIVATE/test-dependencies。实际exit1、33FAILED/0PASS/0skip、26.68秒（外层27.047秒），均AttributeError缺`list_preservation_page/select_preservation_point/_hold_index`，无收集错误。stdout61232B/SHA4dd1e957bab0f7ff1cbdf4fe48c6067305a7f9a9c19d0888f6008d22d244b41f；JUnit65309B/SHAadc7cf96adfe08b90685ee403e808bd76620c2a406ab8c9ca0d1b5a79650708e；stderr0B/空SHA；完整argv/退出/输出pins独占PRIVATE同stem.record.json。此时consumer仍22642，尚未实现。

GREEN：相同33项使用`--basetemp=PRIVATE/ppg1`，实际exit0、33PASS/0skip、39.81秒（外层40.047秒）。实际72MiB三row元数据、独占open记录、共用A1 meter均按断言通过；consumer38908B/SHA7b7ae86b53f9c831e7f06d54fbc3042ff1c989347d68bcc4f47158e73bc69b72，pagination test15952B/SHAfdeebf332389a5666119c5107850f1cc26b6d1c3c2ea19f2f5552899b4c4ea79；consumer、新test、A1及三旧test前后pin一致。stdout235B/SHA2f4e3dfd3a6ea0eabeac9596bfb3d5e386b27bdd58eb96b77503ed23e2a4416c；JUnit5833B/SHAf12b7cbde36881a62b9a0f54c628e368809bd8bae323c2b5fb38f9b6c21cf43d。完整证据PRIVATE/preservation-pagination-green-r1.record.json。

有限自审新增BDD：Given真实NTFS长路径source policy原件使nextCursor规范化bytes超过4096；When首页面发出cursor；Then与输入cursor同样严格拒绝CURSOR_INVALID，不能生成下次必然不能消费的cursor。仅新增一个真实文件边界用例，不改变旧断言。

RED：精确node `test_generated_cursor_also_obeys_4096_bytes_with_real_long_policy_path`，PRIVATE/ppocr1；实际exit1、1FAIL/0skip、1.37秒（外层1.64秒），实际原件创建与读取成功，失败为DID NOT RAISE RepositoryError，证明出参未应用4096B约束。stdout1737B/SHA2bbd6c1eb5872b18a5301d620fb59cb4934ec02d82aef5d814d19a1c9897eec9；JUnit1634B/SHAbbf6a16109fe32fd41e43f4227859186faf19db558436feaa06a7333e14da932；stderr0B。PRIVATE/preservation-pagination-output-cursor-red-r1.record.json保留真实argv/退出/pins。下一最小修复复用既有严格cursor validator校验新出参，不新增第二套算法。

GREEN r2：新增出参边界后34项全组，实际exit0、34PASS/0skip、40.57秒（外层40.812秒）；精确argv沿用r1的测试文件，短basetemp=PRIVATE/ppg2、JUnit=PRIVATE/preservation-pagination-green-r2.junit.xml。consumer39019B/SHA606e68b00958eab3611835fa5bc85ef18b76888717e058fda428b73a24f42063；新test16674B/SHAe9555d10aca6e58aad48dd39cb983b96baebb28f68119af3c3bc35fc3057f9af。stdout235B/SHAfb508e6fc8e67a0e432d604314efd094d2996fa79a34d8fbd03d1d429b704b04；JUnit6007B/SHA2a8e42a1abe03aaa17900b514cb2edbd863710d9dd497baaef5b7f55a2117145；stderr0B。PRIVATE/preservation-pagination-green-r2.record.json保留精确命令与六文件前后pin，全部一致。

REGRESSION r1：旧source36+A1 36+publisher28+ordinary15=115项，实际exit0、115PASS/0skip、51.61秒（外层51.859秒）。命令为固定Python `-X utf8 -m pytest -q -p no:cacheprovider`，三个旧test文件及PRIVATE/ri-budget-regression-r2.record.json已冻结的15个ordinary node，短basetemp=PRIVATE/ppr1；完整argv在PRIVATE/preservation-pagination-regression-r1.record.json。stdout322B/SHA747623aecdb3be7ff120de04e393cbbfe97c1f816999965f701abff0eb6d2102；JUnit19400B/SHAb4db528c878ad2ebaa791e523f479e34041ac08ca13e48a4c27ccfe184940656；stderr0B。consumer、新test及全部旧test/A1前后pin一致；旧ordinary test26503B/SHAfe354697d1b37e2eacd7093c002ba269e7e31fbb7f10682d8f2516a292ebe072。

## 交付边界与冻结

新增API只接受显式v2受信source policy：`list_preservation_page(source_policy_pin, *, cursor=None, limit=1, guard)`及`select_preservation_point(source_policy_pin, reference, *, snapshot_digest, guard)`。小索引复用原hold元数据解析，单件64KiB、最多2maxPoints目录项/最多maxPoints意图；所有唯一实际raw与nested A1共64MiB。点/manifest仍单件16MiB有界。limit1默认、上限32，cursor输入输出4096B、精确schema/pins/snapshot/after，目录原stat身份和小索引完整pins固定快照。

v1公开枚举/resolve仍完整枚举，原resolver与完整严格validator未改接线；本步没有从metadata生成source admission。只有共同剩余budget专属异常可在已有完整row时结束页；pin/hash/schema/role/目录变化仍严格失败。选择返回payloadContentVerified/sourceAdmissionGranted/targetAdmitted/clearAuthorized全False，原controlledRestoreEligible/sourceRestored False与writersRemainQuiesced True保持。未读point的内容变动不会被小索引snapshot冒充已验证，真正读取该row时按pin拒绝。

原22642源码独占snapshot保留，避免父旧B载体变化；旧v1/A1/publisher和ordinary测试未改。只修改consumer、新pagination test、本日志，未改controller/UI/files/HTTP/其余产品，未Docker/SSH/SQL/NAS/构建/部署/提交。Windows合同验证不是Linux真实包或真实恢复通过；后者仍待父独占安排。本轮没有新增未知格式放行、resolver降级或自动重试。
