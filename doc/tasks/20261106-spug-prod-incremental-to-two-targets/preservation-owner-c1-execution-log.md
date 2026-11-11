# C1：保全恢复原件与完整 owner 派生

## Current Status

ready_for_parent_review。父已审设计并仅批准 C1：新 inputs 模块、独占新测试和本记录。C1实现与有限验证通过，待父复审与后续集成；consumer 窄 metadata helper 归 A2，已真实接通。历史 Preservation 派生递归、数据/程序/worker 接线留待后续，当前不授真实恢复准入，不判整体任务完成。

## 目标、里程碑与验证

实现严格七字段 binding、十三字段 bound source、三原件、caller-trusted current/retained 控制闭包、无环控制映射和完整 owner 确定派生/verify；只证明 metadata，不授 source/target/clear 权限。先覆盖真实 unchanged 与普通 A1 publisher 终点。

1. 写 Given/When/Then 与实际 RED。
2. A2 helper 合同冻结后最小实现并实际 GREEN。
3. 有限回归 A1、consumer metadata，核 UTF-8/文件归属并向父交付；不提交或构建。

验证使用本机 Python/pytest 与真实临时文件，记录原命令、退出码和结果。不调用 Docker、SSH、HTTP、运行服务或业务数据。

## 经验门禁

- Trigger：保全 source owner 派生。Preflight check：受信 control/base、原 binding/request/三原件、完整类型严格比较、现 consumer 元数据关系。Blocker：helper 缺失、原件/pin/路径不等、控制不可信、循环、超限或未实现 Preservation 祖先。Verification：真实 RED→GREEN→有限 REGRESSION。Forbidden action：fake validator PASS、自报 admission、复制 consumer、改 A1/程序/worker 或放宽原 false。Evidence：父已审 C 合同设计与本记录。
- Trigger：Windows 文件操作。Preflight check：显式 UTF-8、Python -X utf8；不使用系统默认编码。Blocker：未知编码/并行文件归属。Verification：新文件回读与 SHA。Forbidden action：覆盖 A2 consumer、父主日志或凭据。Evidence：本子项原始工具结果。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；独立 typed source 分支和确定完整 owner，真实原件绑定。
- 是否存在临时补丁或绕过：否。

## BDD 与首 RED

- BDD: unchanged publisher -> Given 真文件形成的受信 repo/base/policy/control 和完整原保全 metadata；When 新请求 derive/verify；Then 仅所选 source 改为精确十三字段，三原件闭合、其他 owner 全文保持、四权限 false、零 payload 打开。
- BDD: ordinary A1 publisher -> Given 原 ordinary RESTORE 的 base/request/archive-point/recovery/operation副本与 execution binding；When 新保全来源 derive；Then 真实 A1 重建完整原 owner，不把旧点伪装 ordinary，不调用全 validator。
- BDD: trust and binding -> Given 精确原件；When 控制不在 caller trust、mapping/base/root/policy/point/reference/op/字段漂移或非 source owner 改动；Then 明确拒绝，不尝试其它代次或 resolver。
- BDD: retained generation -> Given 受信新控制保留旧控制；When 用旧绑定重建；Then bound source 控制列表仍来自原控制，未来部署不改变历史 owner；循环/重复/超过32控制明确拒绝。
- BDD: raw accounting and finish -> Given 实际大小、SHA、身份、reader 和有限 metadata；When 边界/超限/同路径冲突/guard时修改早期原件；Then 唯一 raw 计费、文档16MiB/总64MiB不放宽，实际 finish 不能被注入 reader 免除。

## 接口协商

父已批准 A2 独占 helper 方向：`_describe_bound_preservation(reads, source_policy_pin, request, point_binding) -> (policy, repository, row, history)`。复用 outer 同一 raw 账与 guard，固定旧op/hold intent/final，不扫描全目录/不取 UI snapshot，真实 `_policy/_row/_historical`；PUBLISHED 仅 metadata。control/base 信任归本模块。helper 不新建 meter、不 finish、不调用完整 validator；C1 不提供替身。

父另批准由本模块唯一实现 `resolve_preservation_control_pins(current_control_pin, *, guard, reader=None)`，精确返回 `schemaVersion currentControlPin publisherControlPins originalResultPins metadataBytes`，schema=`PreservationControlPinsResolution/v1`。列表当前首位、全部 transitive retained 按规范 path/bytes/SHA 排序、总最多32；原件与实际唯一 raw 计费作为证据。derive/verify 内复用同一 reads；B 可用 `reader=outer.raw`，outer64MiB 账和 caller最终 finish 不能省略，与既有 A1 接缝同义。B 已接受此返回结构，不另复制控制图算法。

## 实际 RED / 初步验证

公共命令环境最终固定：Python=`C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`；`PYTHONPATH=C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/test-dependencies`、`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`、`PYTHONDONTWRITEBYTECODE=1`。参数 `-B -X utf8 -m pytest -q --tb=short -p no:cacheprovider`。没有安装依赖。

- 两次环境探测失败不记功能 RED：直接 Python 未安装pytest；误选既有 Linux载体deps缺Windows rpds二进制。随后只读定位本任务既有Windows test-dependencies，实际可运行。
- RED: `... pytest -q -p no:cacheprovider scripts/tests/test_recovery_preservation_inputs.py` -> 实际 shell exit1，1 collection ERROR，唯一功能原因为 `ModuleNotFoundError: recovery_preservation_inputs`，模块此时不存在。测试与BDD先于产品模块。
- 初实现后全文件：实际 native exit1，20FAILED/16PASS/0skip，21.33秒。全部20失败均为缺 A2 `_describe_bound_preservation` 的 AttributeError，未用 fake helper 隐藏；consumer保持A2所有权。其余独立字段/信任/字节边界实际通过。
- GREEN（独立有界子集，非全C1）: 同一新测试 `-k 'control_closure or control_retained or control_resolver or external_reader or document_limit or raw_budget'` -> native exit0，11PASS/46deselected/0skip，1.80秒。包括实际32/33控制原件、顺序/重复/路径循环/严格pin类型、shared outer预算、注入reader不能免除实际finish、doc16MiB和raw64MiB边界。

完整 unchanged/A1 publisher 派生与verify尚待A2真实helper，因此C1当前不判GREEN或完成。

## 父早审后的有界修正

父已接受完整 owner/control 信任方案，仅批准本轮先修明确的首次读取边界：`restore-inputs.json` 固定原件在 derive 路径也必须先核 64KiB，不能先按16MiB读取再拒绝。其他测试面不扩张。

- BDD: fixed restore-inputs cap -> Given 有效 restore-inputs JSON 以空白填充到65537原始字节；When derive 固定路径发现原件；Then 在首次正文读取前以 typed metadata-limit 拒绝，unchanged/A1 两个真实 publisher 场景一致。
- 已向父/A2暴露共享预算接缝：仅有 `reader=outer.raw(reference,maximum)` 时，未知pin的固定文件须先读正文才能发现SHA，无法据此提前知道outer已消耗预算；本地剩余额预检不能替代outer门禁。待冻结最小正式接口，不以读完再拒绝称作前置门禁。
- RED: 新增 `-k restore_inputs_64kib` -> native exit1，2FAIL/57deselected，0.93秒；失败直接为 `C1_RESTORE_INPUTS_BODY_OPENED_BEFORE_64KIB_CHECK`，未读过正文后再算成功门禁。
- GREEN: `fixed(path,maximum=None)` 保留旧默认，derive固定inputs显式65536；相同命令 -> native exit0，2PASS/57deselected，0.88秒。
- 真实 helper 接入 GREEN: A2 consumer `42538B/0d304e3cec9a27290f9931ca2f465138b4501285ca05f74a2d21b51b4d291b8b` 前后SHA一致；新测试全文件 -> native exit0，59PASS/0skip，45.36秒。此结果包含真实 unchanged、普通A1历史终点与四权限false，没有全validator成功替身；随后仍须完成父批准的shared-fixed首读前边界修正。

父已批准最小共享固定接口：derive/verify 在外部reader模式显式接受 `fixed_reader(path,maximum)->(pin,value)`。C先核自己的stat/cache/remaining，再由唯一outer fixed核其剩余预算后首读；返回实际pin必须同路径/字节限额，value不能替代经raw的实际字节验证，actual finish不省略。需要固定读取但未提供callback时typed拒绝，禁止本地先读fallback。control resolver仅known pins不强求此callback。A2负责其fixed增加可选maximum，本模块不改consumer。

- BDD: shared fixed budget -> Given outer 已实际读入原件且剩余额小于新的固定文件；When C以同一个outer raw/fixed读取该文件；Then outer在首次正文前拒绝，C/outer都不记录该文件；缺少fixed callback明确typed拒绝，callback错路径/超额pin/错hash不能被当作真实正文。
- RED: `-k 'shared_fixed or external_fixed'` -> native exit1，5FAIL/59deselected，0.24秒；4项为缺正式fixed_reader参数、1项直接证明旧代码未提供callback仍读取body。
- GREEN: 同一5项 -> native exit0，5PASS/59deselected，0.16秒；实际outer已读2B、剩31B时对32B固定文件首body前拒绝，另验证错路径/超额bytes/错SHA以及缺callback。
- 有限回归首跑：64项新C1+36项既有A1 -> native exit1，2FAIL/98PASS，48.84秒。两项是已有metadata-only用例把physical outer也接了注入reader、却未给该outer固定callback，新正式门禁正确拒绝；只改测试布线为最外physical `_Reads(reader=None)`，spy包在其raw上，C传该raw与实际outer.fixed，未放宽产品门禁。该2项复查 -> native exit0，2PASS/62deselected，1.98秒。
- REGRESSION: 新C1与既有A1两个文件 -> native exit0，100PASS/0skip，36.44秒。
- A2实际fixed集成：A2将consumer.fixed增加显式maximum可选参数后，既有sharedbudget场景改用实际consumer._Reads为outer，并同时拦截C和consumer首body函数；同一5项 -> native exit0，5PASS/59deselected，0.19秒，没有增加测试数量。
- 最终 REGRESSION: Python/环境同前，完整命令 `-B -X utf8 -m pytest -q --tb=short -p no:cacheprovider scripts/tests/test_recovery_preservation_inputs.py scripts/tests/test_recovery_restore_inputs.py` -> native exit0，100PASS/0skip，53.13秒。输入consumer为A2冻结的42680B/f13f27646b10b4e50b81124d7156d6ad843aed1641fd9e44422065f247f74b57，未由本子项修改。

## C1交付边界

里程碑1 BDD/实际RED、里程碑2严格C1实现与实际GREEN、里程碑3有限A1回归均已完成。新模块公开control resolve精确5字段报告、完整owner derive与三原件verify；derive/verify可显式共享outer.raw/outer.fixed，最终outer.finish仍由caller完成。metadata原件、完整owner、控制闭包和真实普通A1终点均通过；四权限保持false。

仅本模块、新测试与本子日志归本子项。没有Docker、SSH、HTTP、构建、服务器操作或提交。递归Preservation历史仍未在C1启用，缺少对应元数据闭包时明确失败；实际完整validator、source/target admission、数据/程序dispatch和guarded worker均未接线。父待复审，不扩大到C2或宣称一键真实恢复已完成。
