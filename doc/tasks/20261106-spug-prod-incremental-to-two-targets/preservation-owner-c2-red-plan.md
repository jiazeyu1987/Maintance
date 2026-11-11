# C2：保全派生历史首 RED 与最小接缝计划

## Current Status

ready_for_parent_review。父批准的 C2 最小实现及有限验证已完成；C 只改本 inputs 模块/C2 测试/本记录，另有父另批的新协议path规范化及其C1精确预期/必要两参数RED。consumer 由 A2 所有。沿现真实 reads、唯一私有历史与 verify，无 worker/fullvalidator/程序计划/部署改动。C1原子日志保持冻结；整体任务未完成。

## 目标、里程碑与验证

通过真实固定元数据原件证明 D1 从保全来源派生后，D1 所发布的新保全点可再次被绑定。先写正例与少量关键负例，实际运行并记录现 consumer 的 `PRESERVATION_SOURCE_RESOLVER_UNSUPPORTED`；不进入生产实现。保留 C1/A1/A2 现有语义和原限额，不引入 payload 验证成功替身。

## 经验门禁

- Trigger：历史保全 owner 再派生。Preflight check：父审 C 合同第4节、三原件、原 operation copy、执行绑定、caller-trusted root 与原代 control 闭包。Blocker：resolver 未启、原件缺失、pin/完整 owner/控制漂移、超额或无共享上下文。Verification：真实临时文件，捕获已有 unsupported 的首 RED、后续经批准才 GREEN。Forbidden action：伪造 validator PASS、读取 payload、跳过原元数据关系、扩展本轮到产品或部署。Evidence：本记录、C1冻结原件及 RED 输出。
- Trigger：Windows 元数据夹具。Preflight check：现有任务与 UTF-8 规则，现有 Windows 测试依赖。Blocker：文件归属/编码不明。Verification：只修改新 C2 测试与本记录，显式 UTF-8 回读和 SHA。Forbidden action：覆盖共享 consumer、C1 原件或父日志；Docker、SSH、HTTP、提交。Evidence：本记录与前后 SHA。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；扩展原 publisher 明确 resolver 分支，原 owner 与旧请求控制闭合。
- 是否存在临时补丁或绕过：否。

## BDD

- BDD: preservation-derived publisher -> Given 真文件构成普通 A1→保全点1→D1恢复到59→保全点2，受信 control C2 retained C1；When 新请求选点2并 verify；Then 由原 C1 三原件重建完整 D1、复核其 operation copy 与 execution binding，原件全部进入唯一账；未开点1/点2/A1 payload，四权限 false。
- BDD: historical originals and full owner -> Given 同一原件链；When 缺原 J1 或把旧 operation copy 的非 source 类型从 int 变 bool、并重新生成该 copy 的依赖 pins；Then 对应原件缺失/完整 owner 比较失败，不能用旧 operation copy 或证据字段自报结果。
- BDD: current-only trust -> Given C2 实际没有保留 C1 且 J2 精确绑定新 C2；When 递归走原 J1；Then 未受信 C1 被拒绝，不能从 NAS J1 提升控制授权。

## 实际首 RED

新 `scripts/tests/test_recovery_preservation_history.py` 复用被冻结的 A1/C1 真文件夹具，实际 `derive` 创建点1所对应的 D1；再将 D1 的完整原 bytes 写入 operation copy，用第二套 repo、身份、scope、target policy、hold、manifest、point、material、original execution binding、final/handoff 构成点2。无 injected success、全 validator PASS 或生产数据。正例将拦截两点与普通 A1 payload 的实际打开，要求真实所有祖先原件在同一报告出现、唯一计费并保持四权限 false。负例只含缺 J1、原 operation copy 的 int→bool 和 C1 未保留三个直接信任边界。

- RED: 既有 Windows Python `-B -X utf8 -m pytest -q --tb=short -p no:cacheprovider scripts/tests/test_recovery_preservation_history.py`，`PYTHONPATH` 为已有本任务 `test-dependencies`，disable pytest autoload/bytecode；native exit1，4FAIL/0skip，6.18秒。四项均从真实 `_describe_bound_preservation → _row → _historical → _publisher_owner` 到 `PRESERVATION_SOURCE_RESOLVER_UNSUPPORTED`；正例未到新成功分支，三个负例的正式拒绝码尚不可达。夹具创建 D1 已通过现真实 C1，不是缺导入/原件/环境造成的 RED。

## 最小 diff 提案（尚未批准实施）

1. **C 所有：`recovery_preservation_inputs.py`。** 从现 `verify_preservation_restore_inputs` 提取窄私有共享读校验 `_verify_preservation_originals(reads, base_owner_pin, request_pin, *, request_configurations_root, originals, history)`；仍核确切三原件、request cap/path、固定 inputs 和完整 recovery owner。公开 API 保留相同报告/签名与 finish，私有递归只返回实际重建 owner，不新建 reads、不生成内层权限报告、不调用 finish。`_derive(..., history=...)` 将同一 `reads` 和 `history` 传给固定单点 helper。现有 C1 `reader` + `fixed_reader` 保持正式共享外层协议；固定未知 pin 不在外层预算检查前读正文。
2. **C 所有：窄历史状态。** 每个最外请求只建立一次，不接受外部成功回调。状态持 caller-trusted current 根及真实验证闭包、active 与 seen；每个递归边另传该请求从受信闭包选出的原控制闭包（子级只缩窄，不能用将来安装的控制补齐旧请求当时没有的历史信任），active/seen不随缩窄重置。每个记录按规范 `(原 operationsRoot, publicationOperationId, originTargetConfigRef)`，固定比对精确 sourcePolicy/point/operation owner/request/intent/execution binding pins；Preservation resolver 加其固定 J 原件 pin。active 再遇同 key 报 cycle、已 seen 同 key 不同指纹报 conflict，最多128个不同历史 publication、最多32层保全派生。相同指纹允许复用已读原字节账，第一步可重走真实 metadata 关系，无需缓存成功验证报告。异常必须退出 active；不能保留已完成成功状态掩盖失败。
3. **A2 所有：`recovery_preservation_source.py`。** 原 `_publisher_owner` 仍先唯一选受信 row、核原 request/operation copy 固定路径；UNCHANGED 与真实 A1 保持原算法。仅 `PreservationRestoreOwner/v1` 分支从受信 row root 定位 `restore-inputs.json`（64KiB）、`preservation-point.json`（64KiB）、`recovery.json`（16MiB/global policy较小值）。不采用 UI snapshot、目录遍历或 operation copy 的自报 control。延迟导入 C 的窄私有校验，复用原 `reads` 和同一 `history`；C用 caller 根验证 J1 control 在可保留闭包，D1 原 owner 仍采用 C1 自身历史闭包。将完整 canonical 结果与原 operation copy 比较；继续既有 intent、原 program execution binding/digest、proof、final、hold 和 handoff 核对。缺上下文不自动回退；当前不带 trust 的旧接口保留 unsupported，未知 resolver 继续 unsupported。
4. **共享协议与限额。** `history` 以可选私有参数从固定 helper 经 `_row/_historical/_publisher_owner` 传递，额外传 source-policy pin 与 final hold 的 point pin 供精确活动指纹。C 的 reads 已支持 `read(pin,maximum=None)` 与 `fixed(path,maximum=None)`；如果后续已批准的 A2 session 也直接进入同一内部函数，A2需将 `read(pin,maximum=None)` 增窄 cap（保留旧默认、同 `_fixed` 账），避免第二套解析或 ledger。原 policy bootstrap 仍单件4MiB，其他单件≤16MiB、唯一 raw≤64MiB。当前 `_policy` 会直接赋 `maximum/total_limit`；递归读取必须在第一次 ancestor body 前继承当前较小限额，进入嵌套 policy 只收紧且追溯所有实际读入 pins，不能由较宽祖先 policy 提高上限。公开旧路径的首次 policy 配置仍保持原语义，不把 bootstrap 的4MiB变成通用 cap。
5. **限额与范围待确认。** 外部 `reader/fixed_reader` 会把所有递归原件纳入外层实际唯一 raw 硬账，但不暴露其已消耗字节或预算策略，不能声称嵌套 policy 更小限额也自动追溯 C 调用之前的 page/choice 原件。若父要求嵌套更小 policy 限额覆盖整个 A2 session（含 C 之前的 page/choice），需用同一个实际 session `_Reads` 进入 C 私有验证，或明确窄 limit 收紧接口；不从 callback introspection 取状态，不复制账。首步仅 C-bound 历史闭包；接 A2 page/choice、B/worker、真实全 validator 均另行批准。

**次序：** A2 session freeze 后先由父确认两侧职责、上述 cap 范围、旧接口无上下文行为，再按本 4 项已 RED 合入 C 与 A2 最小同一接缝；预期 4 GREEN 后只重跑既有 C1/A1 和 A2 publisher/metadata 相关测试。循环/上限守卫是实施必要条件，补证方式待后续授权，不在本次首 RED 扩到大用例组或制造可伪造 SHA 的夹具。

## 本轮批准后的有限守卫 BDD

- BDD: narrow history state -> Given 实际元数据文件和规范路径形成的 publication key/精确pins；When active重复、33层派生、129个不同op或已完成同key不同pin；Then 分别cycle/history-limit/operation-conflict拒绝。以私有状态机真实输入验证守卫，不伪造SHA循环或假fullvalidator成功。
- BDD: monotone limits -> Given 实际已计费metadata；When嵌套policy上限小于已读文档或总额；Then立即追溯拒绝；较宽后续policy不能扩大已收紧limit，不恢复上层较宽值。

- RED: C2文件 `-k 'state or limits'` -> native exit1，6FAIL/4deselected，0.74秒，唯一原因缺 `_History` 和 `_tighten_preservation_limits`。最小C实现后5PASS/1FAIL，12.49秒；cycle夹具重复put改写已读原件，真实identity门禁先拒绝，故仅修夹具复用实际已存在pin，不放宽产品检查。

已与A2冻结私有接口：`_History.publication(operations_root,operation,origin,pins,*,derived)`；fingerprint精确七字段 `sourcePolicyPin pointPin configurationPin requestPin intentPin executionBindingPin originals`，前六严格pin，originals为空或精确三原件；`_verify_preservation_originals(reads,...,publisher_control_pins,history)`返回 `(owner,binding)`，不finish。`_tighten_preservation_limits`是唯一单调收紧算法，实际reads.budget追溯所有已读pin和总raw后再赋值。C公开签名/报告不变。A2单独负责consumer propagation、optional read cap与真实resolver分支。

## 独立合同规范化：同一 binding 原路径拼写

A2真实focus为15PASS/2FAIL；C2正例与copy-type均先在历史完整owner严格比较处失败。只读runtime诊断原样执行真实比较并打印差异，唯一差异是bound source.pointBindingPin.path：fixture put输出Windows反斜杠，而实际固定回读 `_read_file` 总生成 as_posix。完整字段值和原件SHA/bytes相同；C1原derive原样嵌入caller pin使完整新协议owner不确定。不是control闭包或可跳过的比较。

父批准先新增必要 RED证明同一actual binding两合法path spelling生成同完整D，再仅把新协议嵌入pointBindingPin.path规范为 `_pin(pin).as_posix()`。现C1尚未部署，不重写旧历史、不放宽canonical完整owner比较、不信recovery自报source字段；原失败证据独立保留。只同步原C1精确预期与C2受影响预期，C1其他合同不变。

- RED: C1 `-k path_spellings` -> native exit1，2FAIL/64deselected，6.14秒；同actualpath/bytes/SHA却完整D的唯一canonical差为斜杠拼写，未由guard或依赖缺失触发。
- GREEN: C1 `-k 'path_spellings or complete_owner'` -> native exit0，4PASS/62deselected，141.06秒；只新生成bound source.pointBindingPin.path规范as_posix，其余完整owner严格比较不变。此合同修复独立于历史resolver，不把C2准入失败算作路径修复测试成功。
- 守卫复查：6PASS/4deselected/native exit0，11.50秒。

- C2真实分支首次接通：10项中9PASS/1FAIL，111.59秒；正例derive/verify的完整D和四false均通过，最后测试evidence用了字典literal path equality。仅将证据查找改为actual Path/bytes/SHA严格相等（与真实pin比较同义）、唯一Path集合；未放宽生产owner比较。复查10PASS/0skip/native exit0，68.24秒。
- 最后必要守卫：现conflict用例增加同一actualpin的合法as_posix重入，真实RED为误报OPERATION_CONFLICT；最小history指纹按实际_path.as_posix规范化所有固定pin，owner比较仍严格。另增加一项坏声明pin首body前限额：实际已读2B、policy总额33B/单件32B、待读实际32B但谎报2B；首次夹具实际大于doc只证已有doc门禁，缩为合法32B JSON后真实RED为 `_read_file` body spy `C2_KNOWN_PIN_OPENED_BEFORE_ACTUAL_REMAINING_CHECK`。最小C read在未缓存实际stat时先核min(doc,remaining)，不只核声明bytes，禁止读后拒绝冒称前置门禁。两项精确复查2PASS/9deselected/native exit0，0.19秒；consumer未改。

## 最终有限验证与交付边界

- REGRESSION: 既有Windows依赖环境，完整命令 `-B -X utf8 -m pytest -q --tb=short -p no:cacheprovider scripts/tests/test_recovery_preservation_inputs.py scripts/tests/test_recovery_restore_inputs.py scripts/tests/test_recovery_preservation_history.py` -> native exit0，113PASS/0skip，144.75秒。组成66项C1（原64+路径合同2）、原36项A1、11项C2。consumer为A2固定49186B/7442a0f4b4b7e9faec1842cede5b8e87cf0cab45e12bfb4d8ad3c76aaeba3ef9；C未修改consumer。
- 三原件、完整owner和operation copy比较仍canonical严格；同一实际reads承载祖先原件，只有最外finish；控制信任每代只缩窄。所有原payload未打开，没有外部成功validator或新报告假闭包。
- 当前只支持已由caller current+retained control DAG证明的C-bound历史；无可信traversal上下文时consumer仍unsupported。公开session形状和UNCHANGED/A1路径由A2保持原合同。跨服capsule/roster、真实全validator/worker/程序计划不在本轮。测试为元数据真文件，不能作为真实恢复完成的证据。
- C仅持inputs、C1测试的必要path规范化、新C2测试和本记录；C1原子执行日志未改。无Docker/SSH/HTTP/构建/提交/服务器操作。父复审后再决定下步。

## C3/C4 只读承接：下一唯一真实 RED 建议（2026-11-11）

**已有证据足够的部分：** C 的113项已覆盖完整owner/A1终点、current+retained控制闭包、共享raw64MiB/doc16MiB、祖先递归/循环/深度/操作冲突、单调收紧及原件结束身份复核；不再新增同义C3组。A2的固定单点26项已证明不枚举hold目录、加入无关坏hold不改变旧点、所选原件漂移拒绝；fixed10项、session26项及listing8项已覆盖首次body前剩余预算、唯一账/finish和目录变化。分页34项覆盖页/cursor/容量与快照重启。已有独立Linux capacity报告为37PASS/0skip/原生0，但输入是其冻结载体，不代表本次C2或最终STANDARD/FAST包已在Linux验收。

**唯一下一节点建议为 C4a：真实producer → 完整发现 → 租约 → 受保护的单点数据计划。** 复用 `test_recovery_target_preservation_handoff.handoff_case`，实际执行 TargetPreservation.prepare/capture_and_publish/handoff，接真实C1请求三原件和derived owner；原 `test_recovery_preservation_source_v2_history` 已用此链调用真实历史validator并验证payload篡改失败，不需要新造成功validator。Given 此真实closure；When metadata发现完成并一次捕获ArchivePathGuard，再在同一连续guard下重读、调用真实validator/binder及原material/index/physical/SQL计划；Then 实际读取集合全部受保护、保持原保全点schema和false字段、无业务mutation。一个正例加一项在发现后且租约内更换真实payload inode的负例足够首步；已有预算/历史/程序门禁不重铺。实现前才新增该BDD测试并记录真实RED，当前未运行。

**最小接口缺口须先冻结：** 原设计两个plan API仅有owner/request，不能从bound source自报字段建立信任；应显式接收launcher受信current control pin，经其闭包核J绑定的原control，再用该原control的route/taskRoot唯一取得base和请求原件，复用C真实verify。A2现公开 `resolve_preservation_source` 仍新建reads、枚举catalogue且没有绑定单点/trusted history参数；不能直接作为此计划入口。下一步由A2提供窄的完整bound resolver，借同一实际reads/history和固定binding，内部仍固定调用真实validator，无外部成功回调。C新增 `recovery_preservation_plan.py` 及专属新测试；producer/full validator/_Reader/ArchivePathGuard不改。完整有限schema发现须包含原生terminal、readback全部originals、binder、版本原件、payload与闭合目录，metadata仍16/64MiB；发现后捕获，再按原pin重读，不能先全validator后补租约。worker实际首次selected_chain位于租约及native constructor之前，后续只在该处分派；本首节点不提前接worker或C5程序切换。

**真实边界：** 可复用fixture证明同host的TargetPreservationPolicy/v1出版闭包；文件名/source policy的v2不等于target policy/v2。后者现有history_v2只有真实非CIFS负例，正例仍缺实际CIFS设施，不准伪造观察通过。跨服E capsule/roster合同未冻结，原绝对路径/原claim依赖保持，任何local成功不得解释为三服可恢复。父先修实际STANDARD缺导入并统一安排Linux窗口；本次仅只读核查和追加本页，产品/测试冻结，未启动测试、构建或远端操作。
